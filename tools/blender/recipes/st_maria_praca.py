"""Scaffold the authoritative, hand-editable St. Maria Praca source scene.

This creates level-design massing, not finished art.  It may create the source
once, but refuses to overwrite it: after adoption the .blend is the authority.

Blender/world frame (metres): +X camera depth, -Y screen right, +Z up.
The runtime action lane is X=7.8, Z=-1.5, Y=0..23.699.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BLEND = (ROOT / "projects" / "hichaukitoden-game" / "assets"
                 / "authoring" / "environments" / "st_maria_praca.blend")
MAP = ROOT / "projects" / "hichaukitoden-game" / "data" / "maps" / "17.json"
GROUND_Z = -1.5
LANE_X = 7.8


def collection(name, parent=None):
    coll = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(coll)
    return coll


def link_only(obj, coll):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def box(name, size, location, coll, color):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.color = (*color, 1.0)
    return link_only(obj, coll)


def empty(name, location, coll, display="PLAIN_AXES", size=0.45):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    coll.objects.link(obj)
    return obj


def build(output: Path):
    if output.exists():
        raise SystemExit(
            f"refusing to overwrite authoritative source {output}; edit it in Blender"
        )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene["sr_document_role"] = "authoritative_environment_source"
    scene["sr_map_id"] = 17
    scene["sr_authoring_units"] = "metre"
    scene["sr_editing_note"] = (
        "Edit semantic collections directly. Gameplay guides do not render. "
        "Never regenerate this adopted source."
    )

    source = collection("TH_SOURCE")
    architecture = collection("20_ARCHITECTURE", source)
    foreground = collection("21_FOREGROUND", source)
    props = collection("30_PROPS", source)
    lighting = collection("40_LIGHTING", source)
    render = collection("TH_RENDER")
    collision = collection("TH_COLLISION")
    anchors = collection("TH_ANCHORS")
    preview_actors = collection("TH_PREVIEW_ACTORS")
    preview_only = collection("TH_PREVIEW_ONLY")
    design = collection("10_LEVEL_DESIGN", preview_only)
    scale = collection("11_SCALE_GUIDES", preview_only)
    camera_coll = collection("TH_CAMERA_PREVIEW")

    # Level-design truth: lane, route ends and authored interaction positions.
    lane = box("LD_walkable_lane_0.0_to_23.699", (2.0, 23.699, 0.04),
               (LANE_X, 11.8495, GROUND_Z - 0.03), design, (0.12, 0.55, 0.18))
    lane.display_type = "WIRE"
    lane["sr_lane_min_y"] = 0.0
    lane["sr_lane_max_y"] = 23.699
    lane["sr_movement_speed"] = 3.4

    map_data = json.loads(MAP.read_text(encoding="utf-8"))
    positions = {
        event["instanceId"]: event["worldPosition"]
        for event in map_data["events"] if "worldPosition" in event
    }
    anchor_positions = {
        "spawn_player": (LANE_X, 11.85, GROUND_Z),
        "quay_stair": positions["st-maria-praca-quay_stair"],
        "alicia_door": positions["st-maria-praca-alicia_door"],
        "churchyard_stair": positions["st-maria-praca-churchyard_stair"],
        "chapel_door": positions["st-maria-praca-chapel_door"],
        "east_backstreet": positions["st-maria-praca-east_backstreet"],
        "npc_child": positions["st-maria-praca-child"],
        "npc_registrar": positions["st-maria-praca-registrar"],
    }
    for name, position in anchor_positions.items():
        marker = empty(name, position, anchors, size=0.38)
        marker["sr_anchor"] = name
        guide = empty("LD_" + name, position, design, "SPHERE", 0.9)
        guide.color = (0.95, 0.35, 0.08, 1.0) if "npc_" not in name else (0.15, 0.45, 1.0, 1.0)

    # Human scale is permanently visible in the source but excluded from render.
    actor = box("SCALE_actor_1.75m", (0.35, 0.6, 1.75),
                (LANE_X, 11.85, GROUND_Z + 0.875), scale, (0.15, 0.45, 1.0))
    actor.display_type = "WIRE"
    for name, y in (("Alicia", 4.625), ("Chapel", 20.81)):
        door = box(f"SCALE_{name}_door_1.05x2.15m", (0.28, 1.05, 2.15),
                   (10.05, y, GROUND_Z + 1.075), scale, (0.95, 0.35, 0.08))
        door.display_type = "WIRE"

    # Fresh architectural massing. Individual blocks remain independently
    # selectable: the source should read like a level, not a fused export.
    stone = (0.42, 0.40, 0.35)
    plaster = (0.72, 0.70, 0.61)
    roof = (0.30, 0.12, 0.08)
    box("ARCH_square_ground", (5.8, 31.0, 0.35), (8.0, 11.85, GROUND_Z - 0.2), architecture, stone)
    for name, y, width, height in (
        ("west_house", 3.9, 7.0, 5.0),
        ("registrar_house", 14.6, 8.5, 5.8),
        ("chapel_house", 21.2, 5.0, 6.6),
    ):
        box("ARCH_" + name, (3.8, width, height),
            (11.7, y, GROUND_Z + height / 2), architecture, plaster)
        box("ARCH_" + name + "_roof", (4.5, width + 0.5, 0.45),
            (11.7, y, GROUND_Z + height + 0.2), architecture, roof)

    # A fountain splits the long lane into readable civic rooms while leaving
    # the traversal line unobstructed in front of it.
    box("PROP_fountain_basin", (1.7, 3.0, 0.65),
        (9.35, 11.9, GROUND_Z + 0.325), props, stone)
    box("PROP_fountain_plinth", (1.0, 1.1, 1.65),
        (9.35, 11.9, GROUND_Z + 1.15), props, stone)
    box("ARCH_churchyard_stair_mass", (2.8, 3.2, 1.2),
        (9.9, 9.827, GROUND_Z + 0.6), architecture, stone)

    # Real foreground depth, broad enough to remain meaningful while panning.
    box("FG_arcade_left", (1.1, 4.2, 3.6),
        (4.6, 2.0, GROUND_Z + 1.8), foreground, stone)
    box("FG_arcade_right", (1.1, 4.2, 3.6),
        (4.6, 21.7, GROUND_Z + 1.8), foreground, stone)

    # Runtime collections begin as explicit, coarse placeholders; they are not
    # inferred from source naming when this scene is eventually promoted.
    render_proxy = box("RT_square_depth_proxy", (5.8, 31.0, 0.35),
                       (8.0, 11.85, GROUND_Z - 0.2), render, stone)
    render_proxy.hide_render = True
    collision_proxy = box("COL_walkable_surface", (2.0, 23.699, 0.1),
                          (LANE_X, 11.8495, GROUND_Z - 0.08), collision, (0.2, 0.8, 0.2))
    collision_proxy.display_type = "WIRE"
    collision_proxy.hide_render = True

    # Neutral clay lighting and the established level side-view camera.
    world = bpy.data.worlds.new("St Maria exterior preview")
    scene.world = world
    world.color = (0.035, 0.045, 0.06)
    bpy.ops.object.light_add(type="AREA", location=(-1.0, 11.85, 10.0))
    sun = link_only(bpy.context.object, lighting)
    sun.name = "LIGHT_overcast_sky"
    sun.data.energy = 900.0
    sun.data.shape = "RECTANGLE"
    sun.data.size = 18.0
    sun.rotation_euler = (0.0, 0.55, 0.0)

    camera_data = bpy.data.cameras.new("town_sideview")
    camera = bpy.data.objects.new("CAMERA_town_sideview", camera_data)
    camera_coll.objects.link(camera)
    camera.location = (-13.3175, 11.85, 0.7604)
    camera.rotation_euler = (1.5707963268, 0.0, -1.5707963268)
    camera_data.lens = 43.27
    camera_data.sensor_width = 36.0
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    preview_actors.hide_render = True
    preview_only.hide_render = True
    render.hide_render = True
    collision.hide_render = True
    anchors.hide_render = True

    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    print("PRACA SOURCE OK " + json.dumps({
        "blend": str(output), "anchors": sorted(anchor_positions),
        "lane": [0.0, 23.699], "units": "metre"
    }))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_BLEND)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    build(args.output.resolve())


if __name__ == "__main__":
    main()
