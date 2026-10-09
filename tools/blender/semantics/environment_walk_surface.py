"""Compile explicit Blender walk semantics into an environment package.

This is intentionally a semantic compiler beside the beauty/collision exporter,
not an inference pass over ``TH_COLLISION``. The runtime continuous-surface
primitive needs ordered planar XY loops; arbitrary 3D collision geometry does
not carry enough information to reconstruct that meaning safely.

Authoring contract (V1):

* ``TH_WALKABLE`` is required when walk semantics are authored and contains one
  or more direct planar mesh faces. Every face becomes one unioned walk region.
* ``TH_OBSTACLES`` is optional and contains direct planar mesh faces on the same
  ground plane. Every face becomes one blocking polygon.
* Mesh objects in these semantic collections must not have modifiers. The
  semantic source is the authored face loop itself, not evaluated beauty output.
* Object transforms are applied before XY/Z extraction.

The canonical environment exporter imports this module directly when a
``TH_WALKABLE`` collection is present. The command-line entry point remains
useful for auditing or patching an already-exported manifest::

    blender --background room.blend \
      --python tools/blender/semantics/environment_walk_surface.py -- \
      --manifest path/to/environment.json

Both paths use ``apply_manifest`` so package schema and provenance are defined
once. Render mesh, atlas, bounds, anchors and collisionMesh remain owned by the
ordinary environment exporter.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Iterable, Sequence

WALKABLE_COLLECTION = "TH_WALKABLE"
OBSTACLE_COLLECTION = "TH_OBSTACLES"
PLANE_EPSILON = 1.0e-5


def _finite(value: float, label: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def compile_polygons(
    faces: Iterable[Sequence[Sequence[float]]],
    label: str,
    *,
    plane_z: float | None = None,
    epsilon: float = PLANE_EPSILON,
) -> tuple[list[dict], float]:
    """Compile XYZ face loops to runtime XY polygons on one ground plane.

    ``faces`` is intentionally plain Python data so the geometric contract is
    testable without Blender. Blender extraction is just an adapter that feeds
    authored world-space face loops into this function.
    """

    polygons: list[dict] = []
    resolved_z = None if plane_z is None else _finite(plane_z, f"{label} plane Z")

    for face_index, raw_face in enumerate(faces, start=1):
        if len(raw_face) < 3:
            raise ValueError(f"{label} face {face_index} must contain at least 3 vertices")
        points: list[list[float]] = []
        for vertex_index, raw_vertex in enumerate(raw_face, start=1):
            if len(raw_vertex) < 3:
                raise ValueError(
                    f"{label} face {face_index} vertex {vertex_index} must be XYZ"
                )
            x = _finite(raw_vertex[0], f"{label} face {face_index} vertex {vertex_index} X")
            y = _finite(raw_vertex[1], f"{label} face {face_index} vertex {vertex_index} Y")
            z = _finite(raw_vertex[2], f"{label} face {face_index} vertex {vertex_index} Z")
            if resolved_z is None:
                resolved_z = z
            if abs(z - resolved_z) > epsilon:
                raise ValueError(
                    f"{label} must be planar at Z={resolved_z:g}; "
                    f"face {face_index} vertex {vertex_index} is Z={z:g}"
                )
            points.append([x, y])
        polygons.append({"points": points})

    if not polygons:
        raise ValueError(f"{label} must contain at least one mesh face")
    assert resolved_z is not None
    return polygons, resolved_z


def _collection_face_loops(collection_name: str, *, required: bool) -> list[list[list[float]]]:
    try:
        import bpy  # type: ignore
    except ImportError as exc:  # pragma: no cover - only available inside Blender
        raise RuntimeError("Blender bpy is required for collection extraction") from exc

    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        if required:
            raise ValueError(f"missing required Blender collection {collection_name}")
        return []

    loops: list[list[list[float]]] = []
    mesh_objects = [obj for obj in collection.all_objects if obj.type == "MESH"]
    if required and not mesh_objects:
        raise ValueError(f"{collection_name} contains no mesh objects")

    for obj in sorted(mesh_objects, key=lambda item: item.name):
        if len(obj.modifiers) > 0:
            raise ValueError(
                f"{collection_name} object {obj.name!r} has modifiers; "
                "semantic face loops must be direct authored geometry"
            )
        mesh = obj.data
        for polygon in mesh.polygons:
            loop: list[list[float]] = []
            for vertex_index in polygon.vertices:
                world = obj.matrix_world @ mesh.vertices[vertex_index].co
                loop.append([float(world.x), float(world.y), float(world.z)])
            loops.append(loop)
    return loops


def compile_blender_walk_surface() -> dict:
    walk_faces = _collection_face_loops(WALKABLE_COLLECTION, required=True)
    regions, ground_z = compile_polygons(walk_faces, WALKABLE_COLLECTION)

    obstacle_faces = _collection_face_loops(OBSTACLE_COLLECTION, required=False)
    obstacles: list[dict] = []
    if obstacle_faces:
        obstacles, _ = compile_polygons(
            obstacle_faces,
            OBSTACLE_COLLECTION,
            plane_z=ground_z,
        )

    return {
        "groundZ": ground_z,
        "regions": regions,
        "obstacles": obstacles,
    }


def apply_manifest(manifest: dict, walk_surface: dict) -> dict:
    """Install the compiled semantic record into one environment manifest.

    This mutates and returns ``manifest`` so the canonical exporter can compose
    beauty/collision/anchor facts and walk semantics before a single write.
    """

    if manifest.get("contractVersion") != 1:
        raise ValueError(
            f"unsupported environment contract {manifest.get('contractVersion')!r}"
        )

    manifest["walkSurface"] = walk_surface
    provenance = manifest.setdefault("provenance", {})
    if not isinstance(provenance, dict):
        raise ValueError("environment manifest provenance must be an object")
    provenance["walkSurfaceAuthority"] = (
        f"Blender collections {WALKABLE_COLLECTION}/{OBSTACLE_COLLECTION}"
    )
    return manifest


def patch_manifest(path: Path, walk_surface: dict) -> None:
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    apply_manifest(manifest, walk_surface)

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile TH_WALKABLE/TH_OBSTACLES into environment.json walkSurface"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv
        argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    args = _arguments(argv)
    walk_surface = compile_blender_walk_surface()
    patch_manifest(args.manifest, walk_surface)
    print(
        "WALK SURFACE OK "
        f"regions={len(walk_surface['regions'])} "
        f"obstacles={len(walk_surface['obstacles'])} "
        f"groundZ={walk_surface['groundZ']:g}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
