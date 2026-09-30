"""Blender side of test_eevee_backend.py: writes a tiny room source .blend for the room exporter.

A 5 m deep, 7.7667 m long, 3 m high room with its front wall (toward the camera) open, two colours on its
walls so the atlas has something to hold, and one point light. It is just enough for the real exporter to
open, bake and package, in either backend.

    blender -b --factory-startup -P eevee_backend_blender.py -- OUT.blend
"""
import sys
from pathlib import Path

import bpy

SPAN = 7.7667


def material(name, colour):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = 1.0
    return mat


def room():
    half = SPAN / 2.0
    # x = 0 is the open front; the room runs back to x = 5. Faces point inward (into the room).
    verts = [(x, y, z) for x in (0.0, 5.0) for y in (-half, half) for z in (0.0, 3.0)]
    v = {(x, y, z): i for i, (x, y, z) in enumerate(verts)}
    a, b = (0.0, 5.0), (-half, half)

    def quad(*points):
        return tuple(v[p] for p in points)

    faces = [
        quad((5.0, -half, 0.0), (5.0, half, 0.0), (5.0, half, 3.0), (5.0, -half, 3.0)),      # back wall
        quad((0.0, -half, 0.0), (5.0, -half, 0.0), (5.0, -half, 3.0), (0.0, -half, 3.0)),    # side
        quad((5.0, half, 0.0), (0.0, half, 0.0), (0.0, half, 3.0), (5.0, half, 3.0)),        # side
        quad((0.0, -half, 0.0), (0.0, half, 0.0), (5.0, half, 0.0), (5.0, -half, 0.0)),      # floor
        quad((0.0, -half, 3.0), (5.0, -half, 3.0), (5.0, half, 3.0), (0.0, half, 3.0)),      # ceiling
    ]
    mesh = bpy.data.meshes.new("room")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("room", mesh)
    bpy.context.scene.collection.objects.link(obj)
    paint = [material("warm", (0.8, 0.45, 0.25)), material("cool", (0.3, 0.45, 0.8))]
    for m in paint:
        obj.data.materials.append(m)
    for poly in mesh.polygons:
        poly.material_index = 0 if poly.index in (0, 3) else 1
    return obj


def main():
    out = Path(sys.argv[sys.argv.index("--") + 1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    room()
    light = bpy.data.lights.new("lamp", "POINT")
    light.energy = 400.0
    holder = bpy.data.objects.new("lamp", light)
    holder.location = (2.5, 0.0, 2.4)
    bpy.context.scene.collection.objects.link(holder)
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print("EEVEE_BACKEND_ROOM " + str(out))


if __name__ == "__main__":
    main()
