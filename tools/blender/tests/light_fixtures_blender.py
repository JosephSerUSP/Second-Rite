"""Blender side of test_light_fixtures.py: a lamp inside a small closed box, in front of a wall.

Four point lights, each 0.14 m in radius: one inside a 0.16 m box (a corridor lantern, smaller than its
light), one beside a 2 m table (which must keep its shadow), one inside a 0.3 m box (a shop lantern,
bigger than its light, which Cycles shades too), and one in open air. Then the real thing, in EEVEE:
the wall beside the first is rendered before and after, to see whether the light actually gets out.
"""
import json
import sys
import tempfile
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import light_fixtures  # noqa: E402


def cube(name, centre, size):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=centre)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return obj


def point(name, location, watts=30.0, radius=0.14):
    data = bpy.data.lights.new(name, "POINT")
    data.energy = watts
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    return obj


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    wall = cube("wall", (0.0, 1.0, 0.0), (6.0, 0.1, 4.0))
    lantern = cube("lantern_box", (0.0, 0.0, 0.0), (0.16, 0.16, 0.22))
    point("lantern_light", (0.0, 0.0, 0.0))
    table = cube("table", (-3.0, -1.0, -1.0), (2.0, 1.0, 0.2))
    point("lamp_on_table", (-3.0, -1.0, -0.85))
    cube("far_box", (3.0, -1.0, 1.0), (0.2, 0.2, 0.2))
    point("lamp_in_air", (3.0, -2.0, 1.0))
    cube("big_lantern", (2.0, 0.0, -1.0), (0.3, 0.3, 0.3))        # larger than the 0.14 m light inside it
    point("lamp_in_big_lantern", (2.0, 0.0, -1.0))
    return scene, wall


def render_wall(scene, wall):
    bpy.ops.object.camera_add(location=(0.0, -6.0, 0.0), rotation=(1.5708, 0, 0))
    scene.camera = bpy.context.active_object
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = scene.render.resolution_y = 64
    scene.eevee.taa_render_samples = 16
    scene.eevee.light_threshold = 0.0002
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "OPEN_EXR"
    path = Path(tempfile.mkdtemp()) / "wall"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(str(path) + ".exr")
    pixels = np.array(image.pixels[:]).reshape(64, 64, 4)[..., :3]
    bpy.data.images.remove(image)
    # the wall a little way around the lantern, not the lantern's own box
    return float(pixels[22:42, 8:24].mean())


def main():
    scene, wall = build()
    shadows_before = {o.name: o.visible_shadow for o in scene.objects if o.type == "MESH"}
    before = render_wall(scene, wall)
    report = light_fixtures.release_fixture_lights(scene)
    after = render_wall(scene, wall)
    result = {"report": report, "visibleShadowBefore": shadows_before,
              "visibleShadowAfter": {o.name: o.visible_shadow for o in scene.objects if o.type == "MESH"},
              "wallBefore": before, "wallAfter": after}
    print("LIGHT_FIXTURES_PROBE " + json.dumps(result))


if __name__ == "__main__":
    main()
