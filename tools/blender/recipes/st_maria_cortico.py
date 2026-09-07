"""Create the authoritative modelled exterior source for map 26, Cortico.

The map is the source of truth for the lane, doors, NPCs, and their positions.
This script reads those facts mechanically, creates an editable scene once, and
refuses to overwrite an adopted blend.  The generated scene is intentionally a
composition of the shared exterior, house-grammar, and tree vocabularies; it is
not a replacement plate or a map-specific exporter path.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

import thestra_camera  # noqa: E402
import tree_material  # noqa: E402
import tree_mesh  # noqa: E402
from exterior import Exterior  # noqa: E402
from house_grammar import VerandaSpec, build as build_house  # noqa: E402
from house_grammar import emit_blender  # noqa: E402
from house_grammar.library import canopy_steps_house, l_plan_house  # noqa: E402
from tree_generator import generate, preset, reduce_lod, validate  # noqa: E402

MAP = ROOT / "projects" / "hichaukitoden-game" / "data" / "maps" / "26.json"
DEFAULT_BLEND = (ROOT / "projects" / "hichaukitoden-game" / "assets"
                 / "authoring" / "environments" / "st_maria_cortico.blend")
CAMERA_FIXTURE = ROOT / "tools" / "blender" / "fixtures" / "town_sideview_camera.json"
LANE_X = 7.8
MAP_ID = 26
EVENT_PREFIX = "st-maria-cortico-"


def collection(name, parent=None):
    made = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(made)
    return made


def link_only(obj, target):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def empty(name, location, target, display="PLAIN_AXES", size=0.38):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    target.objects.link(obj)
    return obj


def read_map():
    data = json.loads(MAP.read_text(encoding="utf-8"))
    if data.get("id") != MAP_ID:
        raise SystemExit(f"expected map {MAP_ID}, got {data.get('id')}")
    traversal = data.get("traversal") or {}
    lane = traversal.get("lane") or {}
    required = ("minY", "maxY", "depthX")
    if any(key not in lane for key in required):
        raise SystemExit("map 26 lane is missing an authoritative bound")
    events = data.get("events") or []
    anchors = {
        "spawn_player": (LANE_X, (float(lane["minY"]) + float(lane["maxY"])) / 2.0, 0.0)
    }
    for event in events:
        instance = event.get("instanceId", "")
        if not instance.startswith(EVENT_PREFIX) or "worldPosition" not in event:
            continue
        name = instance[len(EVENT_PREFIX):]
        if event.get("sprite"):
            name = "npc_" + name
        position = tuple(float(value) for value in event["worldPosition"])
        if len(position) != 3:
            raise SystemExit(f"malformed worldPosition for {instance}")
        anchors[name] = position
    expected = {"west_praca", "lodging_door", "padaria_back", "port_stair",
                "east_market", "npc_scholar", "npc_euler", "spawn_player"}
    missing = sorted(expected - set(anchors))
    if missing:
        raise SystemExit("map 26 missing expected anchors: " + ", ".join(missing))
    return data, lane, anchors


def make_uv_proxy(target):
    mesh = bpy.data.meshes.new("TH_RENDER_contract_proxy_mesh")
    mesh.from_pydata([(0, 0, 0), (0.2, 0, 0), (0.2, 0.2, 0), (0, 0.2, 0)],
                     [], [(0, 1, 2, 3)])
    mesh.uv_layers.new(name="UVMap")
    obj = bpy.data.objects.new("TH_RENDER_contract_proxy", mesh)
    target.objects.link(obj)
    obj.hide_render = True
    return obj


def make_collision(target, lane_min, lane_max):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.object
    obj.name = "COL_walkable_surface"
    obj.dimensions = (2.0, lane_max - lane_min, 0.12)
    obj.location = (LANE_X, (lane_min + lane_max) / 2.0, -0.06)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    link_only(obj, target)
    obj.hide_render = True
    obj.display_type = "WIRE"
    return obj


def make_tree(target, exterior, lane_y):
    spec = preset("round_shade", seed_offset=17, crown_bias=.65,
                  crown_bias_deg=25.0, branch_twist_deg=110.0)
    full = generate(spec, "authoring")
    validate(full)
    skeleton = reduce_lod(full, "low")
    validate(skeleton, "low")
    origin = (11.7, exterior.y(lane_y), 0.0)
    branches, faces = tree_mesh.branch_mesh(skeleton, sides=6)
    branch_mesh_data = bpy.data.meshes.new("CORTICO_TREE_BRANCHES_mesh")
    branch_mesh_data.from_pydata(branches, [], faces)
    branch_mesh_data.update()
    branch_obj = bpy.data.objects.new("CORTICO_TREE_BRANCHES", branch_mesh_data)
    target.objects.link(branch_obj)
    branch_obj.location = origin
    branch_obj.data.materials.append(exterior.wood)
    cards, card_faces, uvs = tree_mesh.foliage_mesh(skeleton, lod="low")
    card_mesh = bpy.data.meshes.new("CORTICO_TREE_CARDS_mesh")
    card_mesh.from_pydata(cards, [], card_faces)
    card_mesh.update()
    uv = card_mesh.uv_layers.new(name="UVMap")
    for index, coord in enumerate(uvs):
        uv.data[index].uv = coord
    card_obj = bpy.data.objects.new("CORTICO_TREE_CARDS", card_mesh)
    target.objects.link(card_obj)
    card_obj.location = origin
    card_obj.data.materials.append(tree_material.foliage_material())
    for obj in (branch_obj, card_obj):
        obj["sr_export"] = True
        obj["sr_tree_preset"] = "round_shade"
        obj["sr_tree_variant"] = "biased_twist"
        obj["sr_tree_seed"] = 17
        obj["sr_tree_lod"] = "low"
    return {"preset": "round_shade", "variant": "biased_twist", "seed": 17,
            "laneY": lane_y, "segments": len(skeleton.segments),
            "cards": len(skeleton.foliage_indices)}


def tag_source(source):
    for obj in source.all_objects:
        if obj.type == "MESH" and obj.name != "COL_walkable_surface":
            obj["sr_export"] = True
    # Ground is tagged by semantic role, never by a name recognized by an exporter.
    ground = bpy.data.objects.get("CORTICO_ground")
    if ground is None:
        raise SystemExit("CORTICO_ground was not created")
    ground["sr_ground"] = True


def build(output: Path):
    if output.exists():
        raise SystemExit(f"refusing to overwrite authoritative source {output}; edit it in Blender")
    map_data, lane, anchors = read_map()
    lane_min, lane_max = float(lane["minY"]), float(lane["maxY"])
    lane_center = (lane_min + lane_max) / 2.0
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene["sr_document_role"] = "authoritative_environment_source"
    scene["sr_map_id"] = MAP_ID
    scene["sr_scene_contract_version"] = 1
    scene["sr_authoring_units"] = "metre"
    scene["sr_runtime_y_mode"] = "lane_mirror"
    scene["sr_lane_center_y"] = lane_center
    scene["sr_lane_min_y"] = lane_min
    scene["sr_lane_max_y"] = lane_max
    scene["sr_lane_depth_x"] = LANE_X
    scene["sr_editing_note"] = (
        "Edit semantic source collections directly. Lane guides and gameplay "
        "anchors are derived from data/maps/26.json; never move them by eye. "
        "This source is adopted and must not be regenerated over."
    )

    # Exterior resets the disposable Blender scene and establishes the shared
    # material vocabulary. Create the contract collections afterwards so the
    # reset cannot invalidate their RNA handles.
    exterior = Exterior("CORTICO", lane_max - lane_min, back_x=16.0,
                        near_x=4.0, margin=6.0)
    exterior.lane_centre = lane_center
    source = collection("TH_SOURCE")
    architecture = collection("20_ARCHITECTURE", source)
    foreground = collection("21_FOREGROUND", source)
    props = collection("30_PROPS", source)
    lighting = collection("40_LIGHTING", source)
    render = collection("TH_RENDER")
    collision = collection("TH_COLLISION")
    anchor_collection = collection("TH_ANCHORS")
    preview_actors = collection("TH_PREVIEW_ACTORS")
    preview_only = collection("TH_PREVIEW_ONLY")
    design = collection("10_LEVEL_DESIGN", preview_only)
    scale = collection("11_SCALE_GUIDES", preview_only)
    camera_collection = collection("TH_CAMERA_PREVIEW")

    ground = exterior.ground(name="CORTICO_ground")

    # The two authored houses carry different silhouettes and a continuous
    # veranda, while the vocabulary walls keep the lane legible between them.
    veranda = VerandaSpec(id="front_veranda", wing="front", width=5.2,
                          depth=1.0, height=2.55, roof_rise=.22,
                          roof_thickness=.12, support_count=3,
                          support_width=.14)
    lodging = replace(l_plan_house(), id="cortico_veranda_house", version=2,
                      attachments=(veranda,))
    emit_blender.emit(build_house(lodging), name="lodging_house",
                      collection=architecture, lane_y=anchors["lodging_door"][1] + 1.8,
                      back_x=16.0, exterior=exterior, namespace="CORTICO_",
                      recipe=lodging)
    padaria = canopy_steps_house()
    emit_blender.emit(build_house(padaria), name="padaria_house",
                      collection=architecture, lane_y=anchors["padaria_back"][1] + 1.25,
                      back_x=15.3, exterior=exterior, namespace="CORTICO_",
                      recipe=padaria)

    for name, lane_y, width, height, depth in (
        ("CORTICO_west_facade", lane_min + 1.7, 4.4, 5.4, 3.4),
        ("CORTICO_shrine_facade", 5.5, 3.8, 5.8, 3.0),
        ("CORTICO_east_facade", lane_max - 2.0, 5.0, 5.6, 3.6),
    ):
        exterior.facade(name, lane_y, width=width, height=height, depth=depth,
                         x=15.2, dado=True)
    exterior.doorway("CORTICO_shrine_door", 5.5, x=15.12, lamp=True)
    exterior.low_wall("CORTICO_left_low_wall", lane_min + .5, 6.5,
                       x=4.2, height=.82)
    exterior.low_wall("CORTICO_right_low_wall", 18.0, lane_max - .5,
                       x=4.2, height=.82)
    exterior.planter("CORTICO_planter", 17.0, x=4.0, height=.58, spread=1.0)
    exterior.hedge("CORTICO_hedge", 21.0, 24.5, x=4.1, height=.72,
                   depth=.8, seed=26, rows=2)
    tree_report = make_tree(architecture, exterior, 6.8)
    exterior.sky_rig(dome_energy=38.0, sun_energy=1.2)

    # Move helper-created root-owned objects into semantic source collections.
    source_names = {obj.name for obj in source.all_objects}
    for obj in list(bpy.context.scene.collection.all_objects):
        if obj.name.startswith("CORTICO_") and obj.name not in source_names:
            link_only(obj, architecture if obj.type == "MESH" else lighting)
    # House roots are authoring handles, not render inputs. Keep them visible in
    # the level-design hierarchy while their mesh children remain TH_SOURCE.
    for root_name in ("CORTICO_lodging_house_ROOT", "CORTICO_padaria_house_ROOT"):
        root = bpy.data.objects.get(root_name)
        if root is not None:
            link_only(root, design)
    tag_source(source)

    # Anchors remain in engine coordinates because the canonical pipeline reads
    # them directly. Preview actors/guides are mirrored into Blender screen Y.
    for name, position in anchors.items():
        marker = empty(name, position, anchor_collection, size=.34)
        marker["sr_anchor"] = name
        preview_position = (position[0], lane_center - position[1], position[2])
        guide = empty("LD_" + name, preview_position, design,
                      "SPHERE", .8)
        guide.color = ((.95, .35, .08, 1.0) if not name.startswith("npc_")
                       else (.15, .45, 1.0, 1.0))

    actor = bpy.data.objects.new("SCALE_actor_1.75m", None)
    actor.empty_display_type = "CUBE"
    actor.empty_display_size = .875
    actor.location = (LANE_X, -lane_center, .875)
    scale.objects.link(actor)
    for name, position in anchors.items():
        if name.endswith("_door") or name in {"port_stair", "west_praca", "east_market"}:
            guide = empty("SCALE_" + name, (10.0, lane_center - position[1], 1.075),
                          scale, "CUBE", .5)
            guide.color = (.95, .35, .08, 1.0)
    make_uv_proxy(render)
    make_collision(collision, lane_min, lane_max)

    record = thestra_camera.load_calibration(str(CAMERA_FIXTURE))
    camera = thestra_camera.create_or_update_camera(record, scene=scene,
                                                     name="TH_CAMERA_PREVIEW",
                                                     make_active=True)
    camera.location.y = 0.0
    link_only(camera, camera_collection)
    sprite = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "town" / "npc_scholar.png"
    for name in ("npc_scholar", "npc_euler"):
        runtime_pos = anchors[name]
        actor_preview = thestra_camera.create_actor_preview(
            sprite, camera,
            anchor=(runtime_pos[0], lane_center - runtime_pos[1], runtime_pos[2]),
            frame_width=24, frame_height=48, frame_index=0,
            world_height=1.75, name="TH_ACTOR_PREVIEW_" + name)
        link_only(actor_preview, preview_actors)

    preview_actors.hide_render = True
    preview_only.hide_render = True
    render.hide_render = True
    collision.hide_render = True
    anchor_collection.hide_render = True
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str((ROOT / "out" / "st-maria-cortico" / "source-preview.png").resolve())

    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()))
    report = {
        "blend": str(output.resolve()), "map": MAP_ID,
        "lane": [lane_min, lane_max], "anchors": sorted(anchors),
        "tree": tree_report,
        "sourceAuthority": "new; refuse overwrite",
        "runtimeYAdapter": {"mode": "lane_mirror", "laneCenterY": lane_center},
    }
    print("CORTICO SOURCE OK " + json.dumps(report, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_BLEND)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    build(args.output)


if __name__ == "__main__":
    main()
