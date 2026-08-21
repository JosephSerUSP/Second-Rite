"""Emit authored and exported mesh counts for the Second Gate handoff."""

import json
import sys
from pathlib import Path

import bpy


def mesh_counts(collection_name):
    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        return {"objects": 0, "vertices": 0, "triangles": 0}

    objects = [obj for obj in collection.objects if obj.type == "MESH"]
    vertices = 0
    triangles = 0
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        vertices += len(mesh.vertices)
        triangles += len(mesh.loop_triangles)
    return {"objects": len(objects), "vertices": vertices, "triangles": triangles}


def main():
    if "--" not in sys.argv:
        raise SystemExit("usage: blender --background scene.blend --python inspect_second_gate_town.py -- output.json")
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) != 1:
        raise SystemExit("expected one output path after --")

    output_path = Path(args[0])
    report = {
        "scene": bpy.data.filepath,
        "collections": {
            "TH_SOURCE": mesh_counts("TH_SOURCE"),
            "TH_RENDER": mesh_counts("TH_RENDER"),
            "TH_COLLISION": mesh_counts("TH_COLLISION"),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
