"""Verify the Second Gate town source/runtime package and write evidence."""

from __future__ import annotations

import argparse
import json
import math
import struct
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def count_obj_faces(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("f "))


def png_dimensions(path: Path):
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    return [struct.unpack(">I", data[16:20])[0], struct.unpack(">I", data[20:24])[0]]


def mesh_triangles(obj, depsgraph):
    if obj.type != "MESH":
        return 0
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        return len(mesh.loop_triangles)
    finally:
        evaluated.to_mesh_clear()


def main():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    args = parser.parse_args(values)

    import bpy

    bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    collections = {collection.name: collection for collection in bpy.data.collections}
    required = ["TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS", "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW"]
    collection_check = {name: name in collections for name in required}
    source_tris = sum(mesh_triangles(obj, depsgraph) for obj in collections["TH_SOURCE"].objects)
    render_tris = sum(mesh_triangles(obj, depsgraph) for obj in collections["TH_RENDER"].objects)
    collision_tris = sum(mesh_triangles(obj, depsgraph) for obj in collections["TH_COLLISION"].objects)
    render_uv = []
    for obj in collections["TH_RENDER"].objects:
        if obj.type == "MESH":
            render_uv.append({"object": obj.name, "uvLayers": len(obj.data.uv_layers), "vertices": len(obj.data.vertices)})
    displaced = []
    for obj in collections["TH_SOURCE"].objects:
        if obj.type != "MESH":
            continue
        for modifier in obj.modifiers:
            if modifier.type == "DISPLACE" and obj.get("sr_source_displacement") is True:
                displaced.append({"object": obj.name, "strength": obj.get("sr_displacement_strength_world"), "texture": obj.get("sr_displacement_texture")})
    actor_mat_ok = True
    actor_facts = []
    for obj in collections["TH_PREVIEW_ACTORS"].objects:
        if obj.type != "MESH":
            continue
        material = obj.data.materials[0] if obj.data.materials else None
        image_interp = None
        image_name = None
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    image_interp = node.interpolation
                    image_name = node.image.name
                    break
        ok = image_interp == "Closest" and "sr_feet_anchor_world" in obj
        actor_mat_ok = actor_mat_ok and ok
        feet = obj.get("sr_feet_anchor_world")
        actor_facts.append({"object": obj.name, "image": image_name, "interpolation": image_interp, "feet": list(feet) if feet is not None else None, "ok": ok})
    camera = next((obj for obj in collections["TH_CAMERA_PREVIEW"].objects if obj.type == "CAMERA"), None)
    camera_ok = bool(camera and abs(camera.data.lens - 43.27) < 0.001 and abs(camera.rotation_euler[0] - math.pi / 2) < 0.001 and abs(camera.rotation_euler[1]) < 0.001 and abs(camera.rotation_euler[2]) < 0.001)
    anchor_names = sorted(obj.name for obj in collections["TH_ANCHORS"].objects if obj.type == "EMPTY")
    required_anchors = ["spawn_player", "street_center", "market_interaction", "bell_tower_vfx", "left_arch_occlusion"]
    anchor_ok = all(name in anchor_names for name in required_anchors)

    package = args.package.resolve()
    manifest_path = package / "environment.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runtime_obj = package / "environment.obj"
    runtime_tris = count_obj_faces(runtime_obj)
    atlas = package / "environment.png"
    proof = args.proof.resolve()
    proof_files = ["source_proof.png", "runtime_tracking_mesh_strip.png", "runtime_tracking_actors_strip.png", "source_vs_runtime_center.png", "runtime_tracking.json"]
    proof_ok = {name: (proof / name).is_file() for name in proof_files}
    dimensions_ok = True
    for name in ["source_proof.png", "runtime_mesh_m96.png", "runtime_mesh_zero.png", "runtime_mesh_p96.png", "runtime_actors_m96.png", "runtime_actors_zero.png", "runtime_actors_p96.png"]:
        path = proof / name
        if path.is_file() and png_dimensions(path) != [426, 240]:
            dimensions_ok = False
    anchor_ok = anchor_ok and bool(manifest.get("anchors"))
    checks = {
        "collections": collection_check,
        "requiredCollectionsOk": all(collection_check.values()),
        "sourceTriangles": source_tris,
        "renderAuthoringTriangles": render_tris,
        "runtimeTriangles": runtime_tris,
        "reductionRatioSourceToRuntime": round(source_tris / runtime_tris, 4) if runtime_tris else None,
        "sourceDisplacement": {"count": len(displaced), "objects": displaced, "ok": len(displaced) >= 1},
        "renderUv": {"objects": render_uv, "ok": all(item["uvLayers"] > 0 for item in render_uv)},
        "atlas": {"path": "environment.png", "dimensions": png_dimensions(atlas), "bytes": atlas.stat().st_size, "ok": atlas.is_file() and atlas.stat().st_size > 10000},
        "collision": {"path": "collision.obj", "triangles": collision_tris, "runtimeFaces": count_obj_faces(package / "collision.obj"), "ok": (package / "collision.obj").is_file() and collision_tris > 0},
        "anchors": {"required": required_anchors, "found": anchor_names, "ok": anchor_ok},
        "camera": {"lensMm": camera.data.lens if camera else None, "rotation": list(camera.rotation_euler) if camera else None, "native": "426x240", "offsetsPx": [-96, 0, 96], "ok": camera_ok},
        "walkerActors": {"actors": actor_facts, "ok": actor_mat_ok},
        "proof": {"files": proof_ok, "nativeDimensionsOk": dimensions_ok, "ok": all(proof_ok.values()) and dimensions_ok},
        "packageManifest": manifest,
    }
    checks["allChecksOk"] = all([
        checks["requiredCollectionsOk"], checks["sourceDisplacement"]["ok"], checks["renderUv"]["ok"],
        checks["atlas"]["ok"], checks["collision"]["ok"], checks["anchors"]["ok"], checks["camera"]["ok"],
        checks["walkerActors"]["ok"], checks["proof"]["ok"], runtime_tris > 0, source_tris > runtime_tris,
    ])
    (proof / "integration-evidence.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    manifest.update({
        "camera": checks["camera"],
        "projectionWindowTracking": {"nativeResolution": [426, 240], "offsetsPx": [-96, 0, 96], "proof": "runtime_tracking.json"},
        "stats": {**manifest.get("stats", {}), "sourceTriangleCount": source_tris, "renderAuthoringTriangleCount": render_tris, "runtimeTriangleCount": runtime_tris, "sourceToRuntimeReductionRatio": checks["reductionRatioSourceToRuntime"]},
        "bake": {"type": "DIFFUSE_COLOR", "receiver": "TH_RENDER", "uvUnwrap": "SMART_PROJECT", "sourceMaterials": "TH_RENDER materials authored from TH_SOURCE semantic material graphs", "atlasEvidence": "environment.png"},
        "verification": "projects/hichaukitoden-game/assets/authoring/second_gate_town/integration-evidence.json",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"allChecksOk": checks["allChecksOk"], "sourceTriangles": source_tris, "runtimeTriangles": runtime_tris, "reductionRatio": checks["reductionRatioSourceToRuntime"]}, sort_keys=True))


if __name__ == "__main__":
    main()
