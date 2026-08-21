"""Promote the owner-supplied Meshy village OBJ into a Thestra environment package.

The source is a very dense, single-material textured OBJ.  This authoring tool
keeps the supplied texture, reduces only the render mesh for the runtime OBJ
loader, applies the explicit OBJ-to-world placement used by the town map, and
writes a small floor collision placeholder.  Traversal meaning remains in map
data; the mesh does not silently become gameplay authority.

Authoring dependencies are trimesh, fast-simplification, scipy and numpy.  They
are not runtime dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree


DEFAULT_CENTER_X = 8.0
DEFAULT_CENTER_Y = 5.5
DEFAULT_GROUND_Z = -1.5
DEFAULT_SCALE = 8.0
DEFAULT_TARGET_FACES = 60000
DEFAULT_MODEL_YAW_DEGREES = 90.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_mesh(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(path, file_type="obj", force="scene", process=False)
    if isinstance(loaded, trimesh.Trimesh):
        return loaded
    if not loaded.geometry:
        raise RuntimeError("source OBJ contains no geometry")
    meshes = [geometry for geometry in loaded.geometry.values() if isinstance(geometry, trimesh.Trimesh)]
    if not meshes:
        raise RuntimeError("source OBJ contains no mesh objects")
    if len(meshes) == 1:
        return meshes[0]
    return trimesh.util.concatenate(meshes)


def write_render_obj(path: Path, mesh: trimesh.Trimesh, uv: np.ndarray, scale: float,
                     center_x: float, center_y: float, ground_z: float,
                     model_yaw_degrees: float) -> tuple[np.ndarray, np.ndarray]:
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    # Runtime converts OBJ (x, y, z) to engine (x, -z, y).  The source is
    # Blender Y-up.  Place its horizontal axes in the town frame, then rotate
    # around the authored center.  The supplied Meshy square presents its
    # broad walkable axis edge-on to the town side-view without this explicit
    # 90-degree placement.
    source_x = vertices[:, 0] * scale
    source_y = vertices[:, 2] * scale
    yaw = np.deg2rad(model_yaw_degrees)
    cosine, sine = np.cos(yaw), np.sin(yaw)
    base_world_x = center_x + source_x
    base_world_y = center_y - source_y
    offset_x = base_world_x - center_x
    offset_y = base_world_y - center_y
    world_x = center_x + cosine * offset_x - sine * offset_y
    world_y = center_y + sine * offset_x + cosine * offset_y
    world_z = vertices[:, 1] * scale + (ground_z - float(vertices[:, 1].min()) * scale)
    obj_vertices = np.column_stack((
        world_x,
        world_z,
        -world_y,
    ))
    source_normals = np.array(mesh.face_normals, dtype=np.float64, copy=True)
    # Apply the same horizontal rotation to normals in the emitted OBJ frame.
    face_normals = np.column_stack((
        cosine * source_normals[:, 0] + sine * source_normals[:, 2],
        source_normals[:, 1],
        -sine * source_normals[:, 0] + cosine * source_normals[:, 2],
    ))
    face_normals /= np.maximum(np.linalg.norm(face_normals, axis=1, keepdims=True), 1e-12)

    with path.open("w", encoding="utf-8", newline="\n") as output:
        output.write("# Second Gate render mesh promoted from the owner-supplied Meshy village OBJ\n")
        output.write("mtllib environment.mtl\n")
        output.write("o town_church_meshy\n")
        for vertex in obj_vertices:
            output.write(f"v {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
        for texcoord in uv:
            output.write(f"vt {texcoord[0]:.8f} {texcoord[1]:.8f}\n")
        for normal in face_normals:
            output.write(f"vn {normal[0]:.8f} {normal[1]:.8f} {normal[2]:.8f}\n")
        output.write("usemtl EnvironmentTexture\n")
        for face_index, face in enumerate(np.asarray(mesh.faces, dtype=np.int64)):
            normal_index = face_index + 1
            output.write("f " + " ".join(
                f"{int(vertex_index) + 1}/{int(vertex_index) + 1}/{normal_index}"
                for vertex_index in face
            ) + "\n")

    world_vertices = np.column_stack((
        obj_vertices[:, 0],
        -obj_vertices[:, 2],
        obj_vertices[:, 1],
    ))
    return world_vertices.min(axis=0), world_vertices.max(axis=0)


def write_collision(path: Path, minimum: np.ndarray, maximum: np.ndarray) -> None:
    # Collision is deliberately a separate, simple authored floor envelope.
    # The current bounded-lane provider owns movement, but this keeps the
    # package ready for the future walkable-environment collision consumer.
    z = float(minimum[2])
    corners_world = [
        (minimum[0], minimum[1], z),
        (maximum[0], minimum[1], z),
        (maximum[0], maximum[1], z),
        (minimum[0], maximum[1], z),
    ]
    corners_obj = [(x, world_z, -y) for x, y, world_z in corners_world]
    with path.open("w", encoding="utf-8", newline="\n") as output:
        output.write("# Explicit town traversal floor envelope; not inferred from the render mesh\n")
        for x, y, z_value in corners_obj:
            output.write(f"v {x:.6f} {y:.6f} {z_value:.6f}\n")
        output.write("f 1 2 3\n")
        output.write("f 1 3 4\n")


def build(source_obj: Path, source_texture: Path, output: Path, target_faces: int) -> None:
    output.mkdir(parents=True, exist_ok=True)
    source = load_mesh(source_obj)
    source_uv = getattr(source.visual, "uv", None)
    if source_uv is None or len(source_uv) != len(source.vertices):
        raise RuntimeError("source OBJ must provide one UV coordinate per source vertex")

    simplified = source.simplify_quadric_decimation(face_count=target_faces, aggression=5)
    # fast-simplification does not carry UV attributes.  Project the source UV
    # field back by nearest authored vertex; this keeps the Meshy texture rather
    # than replacing it with a generated material or a flat color.
    nearest = cKDTree(np.asarray(source.vertices)).query(np.asarray(simplified.vertices), k=1)[1]
    uv = np.asarray(source_uv, dtype=np.float64)[nearest]

    minimum, maximum = write_render_obj(
        output / "environment.obj", simplified, uv, DEFAULT_SCALE,
        DEFAULT_CENTER_X, DEFAULT_CENTER_Y, DEFAULT_GROUND_Z,
        DEFAULT_MODEL_YAW_DEGREES,
    )
    (output / "environment.mtl").write_text(
        "# Second Gate material adapter for the owner-supplied Meshy texture\n"
        "newmtl EnvironmentTexture\n"
        "Ka 1.000 1.000 1.000\n"
        "Kd 1.000 1.000 1.000\n"
        "map_Kd environment.png\n",
        encoding="utf-8",
    )
    shutil.copy2(source_texture, output / "environment.png")
    write_collision(output / "collision.obj", minimum, maximum)

    manifest = {
        "contractVersion": 1,
        "environmentId": "town_church_meshy",
        "renderMesh": "environment.obj",
        "materialLibrary": "environment.mtl",
        "textureAtlas": "environment.png",
        "collisionMesh": "collision.obj",
        "bounds": [round(float(value), 4) for value in (*minimum, *maximum)],
        "stats": {
            "triangleCount": int(len(simplified.faces)),
            "vertexCount": int(len(simplified.vertices)),
            "materialGroupCount": 1,
            "textureDimensions": [],
            "pngSizeBytes": (output / "environment.png").stat().st_size,
            "renderMeshSizeBytes": (output / "environment.obj").stat().st_size,
            "packageSizeBytes": sum((output / name).stat().st_size for name in ("environment.obj", "environment.mtl", "environment.png", "collision.obj")),
        },
        "anchors": {
            "spawn_player": {"id": "spawn_player", "position": [7.8, 5.5, -1.5]},
            "npc_merchant": {"id": "npc_merchant", "position": [8.0, 7.8, -1.5]},
            "npc_guard": {"id": "npc_guard", "position": [7.6, 3.2, -1.5]},
            "npc_citizen": {"id": "npc_citizen", "position": [8.0, 10.2, -1.5]},
            "church_entrance": {"id": "church_entrance", "position": [8.0, 5.5, -1.5]},
            "torch_arch": {"id": "torch_arch", "position": [6.4, 1.8, 0.5]},
        },
        "provenance": {
            "generator": "tools/asset-production/build_meshy_town_package.py",
            "sourceObj": source_obj.name,
            "sourceTexture": source_texture.name,
            "sourceObjSha256": sha256(source_obj),
            "sourceTextureSha256": sha256(source_texture),
            "targetFaces": target_faces,
            "scale": DEFAULT_SCALE,
            "modelYawDegrees": DEFAULT_MODEL_YAW_DEGREES,
            "worldOrigin": [DEFAULT_CENTER_X, DEFAULT_CENTER_Y, DEFAULT_GROUND_Z],
        },
    }
    # The source texture dimensions are useful evidence but not required to
    # load the package.  Read them without making PIL a runtime dependency.
    try:
        from PIL import Image
        with Image.open(output / "environment.png") as image:
            manifest["stats"]["textureDimensions"] = [int(image.width), int(image.height)]
    except Exception:
        manifest["stats"]["textureDimensions"] = []
    (output / "environment.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "triangles": len(simplified.faces), "bounds": manifest["bounds"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--texture", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-faces", type=int, default=DEFAULT_TARGET_FACES)
    args = parser.parse_args()
    build(args.source.resolve(), args.texture.resolve(), args.output.resolve(), args.target_faces)


if __name__ == "__main__":
    main()
