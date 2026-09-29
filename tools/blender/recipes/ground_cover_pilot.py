"""Disposable ground-cover study on one exterior lane (the #1257 pilot).

Like ``tree_lab.py`` this is deliberately not an exterior source recipe: it
builds a marked study document, never a hand-authored source, so it can be
regenerated freely.  It stages one exterior at the town camera contract -- a
ground with a bank at the back, a painted density group, and the walkable lane
as a keep-out object -- and lets ``ground_cover.py`` scatter over it.

Run through the pinned Blender::

    blender -b --python tools/blender/recipes/ground_cover_pilot.py -- \
        --output out/ground-cover/pilot.blend --render out/ground-cover/pilot.png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
sys.path.insert(0, str(ROOT / "tools/blender/recipes"))
from exterior import Exterior  # noqa: E402
import ground_cover  # noqa: E402
import thestra_camera  # noqa: E402

GROUP = "cover_density"
#: Ground: 30 m deep (x) and 16 m across (y), centred where the camera looks.
GROUND_CENTRE = (4.0, 0.0)
GROUND_SIZE = (30.0, 16.0)
#: The walkable lane runs across the frame at the action plane (x = 0).
LANE_HALF_DEPTH = 1.3
LANE_HALF_WIDTH = 9.0
BANK_START_X = 9.0


def build_ground(exterior):
    """A subdivided ground with a bank at the back and painted density."""
    cuts_x, cuts_y = 60, 32
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=cuts_x, y_subdivisions=cuts_y,
                                    size=1.0, location=(*GROUND_CENTRE, 0.0))
    ground = bpy.context.object
    ground.name = "COVER_GROUND"
    ground.scale = (GROUND_SIZE[0], GROUND_SIZE[1], 1.0)
    bpy.ops.object.transform_apply(scale=True)
    group = ground.vertex_groups.new(name=GROUP)
    for vertex in ground.data.vertices:
        world_x = vertex.co.x + GROUND_CENTRE[0]
        # The back bank rises 1:1 after BANK_START_X, so the slope limit has a
        # real cliff to refuse.
        vertex.co.z = max(0.0, world_x - BANK_START_X) * 1.0
        # Painted: full verge near the lane, thinning to nothing toward the
        # camera so the foreground stays paving.
        weight = min(1.0, max(0.0, (world_x + 2.5) / 4.0))
        group.add([vertex.index], weight, "REPLACE")
    ground.data.materials.append(exterior.paving)
    return ground


def build_lane():
    """The walkable lane, an ordinary object in the keep-out collection."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
    lane = bpy.context.object
    lane.name = "COVER_LANE"
    lane.scale = (2 * LANE_HALF_DEPTH, 2 * LANE_HALF_WIDTH, 0.2)
    bpy.ops.object.transform_apply(scale=True)
    lane.display_type = "WIRE"
    keep_out = bpy.data.collections.new(ground_cover.KEEP_OUT_COLLECTION)
    for owner in list(lane.users_collection):
        owner.objects.unlink(lane)
    keep_out.objects.link(lane)
    return lane, keep_out


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    exterior = Exterior("COVER_PILOT", 12.0, back_x=8.0, near_x=-4.0)
    ground = build_ground(exterior)
    lane, keep_out = build_lane()
    return exterior, ground, lane, keep_out


def add_cover(ground, keep_out, **overrides):
    values = {"Density": 14.0, "Slope Limit": 38.0, "Max Tufts": 20000,
              "Keep Out Margin": 0.3, "Seed": 1}
    values.update(overrides)
    return ground_cover.add(ground, keep_out=keep_out, density_group=GROUP, **values)


def stage_camera_and_light(scene):
    record = json.loads((ROOT / "tools/blender/fixtures/town_sideview_camera.json").read_text())
    thestra_camera.create_or_update_camera(record, make_active=True)
    world = bpy.data.worlds.new("Ground cover world")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.36, .45, .58, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.1
    bpy.ops.object.light_add(type="SUN", location=(-6, 4, 9))
    sun = bpy.context.object
    sun.name = "COVER_SUN"
    sun.data.energy = 2.2
    sun.rotation_euler = (0.9, 0.2, 0.5)


def render(path, samples=16):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.render.resolution_x = 512
    scene.render.resolution_y = 288
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(Path(path).resolve())
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "out/ground-cover/pilot.blend")
    parser.add_argument("--render", type=Path, default=ROOT / "out/ground-cover/pilot.png")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    _exterior, ground, _lane, keep_out = build_scene()
    add_cover(ground, keep_out)
    stage_camera_and_light(bpy.context.scene)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    render(args.render)
    print("GROUND COVER PILOT OK", args.output, args.render)


if __name__ == "__main__":
    main()
