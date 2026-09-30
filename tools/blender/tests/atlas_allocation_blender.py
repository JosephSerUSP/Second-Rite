"""Blender side of test_atlas_allocation.py: one run measures every layout on a three-quad scene.

A wide wall the camera faces (A), a small crate face in front of it (B), and a quad behind the
wall that the wall hides completely (C). What a correct allocator does with them is obvious:
A and B are seen, C never is.
"""
import json
import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import atlas_allocation as alloc  # noqa: E402

SIZE = 1024
CAMERAS = [0.4, 2.0, 3.8833, 5.8, 7.4]        # lane positions in engine space; the mesh is in Blender space


def quad(name, x, y0, y1, z0, z1, facing):
    """A single quad at `x`, `facing` -1 toward the camera (at -x)."""
    verts = [(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)]
    if facing > 0:
        verts.reverse()
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    return mesh


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    world = bpy.data.worlds.new("w")
    scene.world = world
    # Blender space: the lane runs -3.5 to +3.5 around y = 0.
    parts = [("A_wall", quad("A", 0.0, -3.5, 3.5, 0.0, 3.0, -1)),
             ("B_crate", quad("B", -1.0, -0.5, 0.5, 0.0, 1.0, -1)),
             ("C_hidden", quad("C", 5.0, -2.5, 2.5, 0.0, 2.5, 1))]
    objects = []
    for name, mesh in parts:
        obj = bpy.data.objects.new(name, mesh)
        scene.collection.objects.link(obj)
        objects.append(obj)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    target = bpy.context.view_layer.objects.active
    target.name = "ROOM"
    # Three separate quads: remember which polygon is which by its plane.
    return target


def islands_by_part(target):
    mesh = target.data
    island_of = alloc.uv_islands(mesh)
    uv = mesh.uv_layers.active.data
    out = {}
    for poly in mesh.polygons:
        x = mesh.vertices[poly.vertices[0]].co.x
        part = "A" if abs(x) < 0.01 else "B" if x < -0.5 else "C"
        pts = [uv[k].uv for k in poly.loop_indices]
        area = 0.5 * abs(sum(pts[n][0] * pts[(n + 1) % 4][1] - pts[(n + 1) % 4][0] * pts[n][1] for n in range(4)))
        out[part] = {"island": island_of[poly.index], "uvArea": area, "worldArea": poly.area,
                     "density": area / poly.area}
    return out


def measure(layout, view_bias=0.85):
    target = build()
    if layout == "loose":
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.02)
        bpy.ops.object.mode_set(mode="OBJECT")
        report = {}
    elif layout == "packed":
        alloc.pack(target, SIZE)
        report = {}
    else:
        report = alloc.allocate_by_view(target, CAMERAS, SIZE, view_bias=view_bias,
                                        out=Path(bpy.app.tempdir))
    return {"coverage": alloc.layout_report(target, SIZE)["islandCoverage"],
            "parts": islands_by_part(target), "report": report}


def main():
    result = {"loose": measure("loose"), "packed": measure("packed"),
              "view": measure("view", 0.85), "worldBias": measure("view", 0.0)}
    print("ATLAS_ALLOCATION_PROBE " + json.dumps(result))


if __name__ == "__main__":
    main()
