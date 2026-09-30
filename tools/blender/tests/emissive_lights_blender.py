"""Blender side of test_emissive_lights.py: a white room with a glowing slab on one wall.

The slab is a 1 x 1 m emissive face looking into the room, with five more faces (its thin sides and
its back) that must NOT get a light. A second, tiny emitter is under the watt floor, and one more
emitter has a material that is excluded by name in one of the runs.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import emissive_lights  # noqa: E402


def material(name, colour=(0.8, 0.8, 0.8), strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    if strength > 0:
        bsdf.inputs["Emission Color"].default_value = (*colour, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def box(name, low, high, mat, flip=False):
    (x0, y0, z0), (x1, y1, z1) = low, high
    verts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [tuple(reversed(f)) if flip else f for f in faces])
    mesh.update()
    mesh.polygons.foreach_set("use_smooth", [False] * len(mesh.polygons))
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def build(strength=2.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    white = material("white")
    # the room: a 6 x 4 x 3 box, normals in (faces reversed)
    box("room", (-3, -2, 0), (3, 2, 3), white, flip=True)
    glow = material("glow", (1.0, 0.5, 0.2), strength)
    # a 0.1 thick slab in the +x wall, 1 x 1 m toward the room
    box("slab", (2.9, -0.5, 1.0), (3.0, 0.5, 2.0), glow)
    # far too small to matter
    box("ember", (-2.9, 1.5, 1.0), (-2.85, 1.7, 1.25), glow)
    other = material("other_glow", (0.2, 0.6, 1.0), 3.0)
    box("panel", (-0.5, -2.0, 1.0), (0.5, -1.9, 2.0), other)
    return bpy.context.scene


def lights(scene):
    return [o for o in scene.objects if o.type == "LIGHT"]


def describe(obj):
    light = obj.data
    shines = obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))
    return {"name": obj.name, "type": light.type, "shape": light.shape, "watts": light.energy,
            "colour": list(light.color), "size": [light.size, light.size_y],
            "position": list(obj.matrix_world.translation), "shines": list(shines),
            "determinant": obj.matrix_world.to_3x3().determinant(),
            "cutoff": light.cutoff_distance if light.use_custom_distance else None,
            "of": obj.get("sr_companion_of")}


def main():
    result = {}
    scene = build(2.0)
    report = emissive_lights.add_companion_lights(scene, min_watts=0.5)
    result["default"] = {"lights": [describe(o) for o in lights(scene)], "report": report}

    scene = build(4.0)
    emissive_lights.add_companion_lights(scene, min_watts=0.5)
    result["doubled"] = [describe(o) for o in lights(scene)]

    scene = build(2.0)
    result["excluded"] = {"report": emissive_lights.add_companion_lights(scene, exclude=("glow",), min_watts=0.5),
                          "lights": [describe(o) for o in lights(scene)]}

    # the atlas study's joined mesh repeats the source meshes' faces: an ignored object adds no light
    scene = build(2.0)
    emissive_lights.add_companion_lights(scene, ignore=(scene.objects["slab"],), min_watts=0.5)
    result["ignored"] = [describe(o) for o in lights(scene)]

    # negative control: a glowing quad whose face looks into the wall, away from the room
    scene = build(2.0)
    quad = bpy.data.meshes.new("backwards")
    quad.from_pydata([(-2.99, -0.5, 1.0), (-2.99, -0.5, 2.0), (-2.99, 0.5, 2.0), (-2.99, 0.5, 1.0)], [], [(0, 1, 2, 3)])
    quad.update()
    quad.materials.append(bpy.data.materials["other_glow"])
    scene.collection.objects.link(bpy.data.objects.new("backwards", quad))
    emissive_lights.add_companion_lights(scene, min_watts=0.5)
    result["backwards"] = [describe(o) for o in lights(scene)]
    print("EMISSIVE_LIGHTS_PROBE " + json.dumps(result))


if __name__ == "__main__":
    main()
