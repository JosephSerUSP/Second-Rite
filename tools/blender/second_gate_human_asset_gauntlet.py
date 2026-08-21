"""Fresh Second Gate town visual gauntlet using public human-made assets.

This is an experimental authoring script, not a runtime generator.  Each
direction is reset to an empty Blender scene before it is assembled.  The
only authored visual input from the repository is walker.png; all other
meshes are downloaded from the provenance-recorded public sources.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
TOOL_ROOT = ROOT / "tools" / "blender"
OUT_ROOT = ROOT / "projects" / "hichaukitoden-game" / "assets" / "experimental" / "second-gate-human-assets"
SOURCE_ROOT = OUT_ROOT / "sources"
KAY_ROOT = SOURCE_ROOT / "kaykit-medieval-hexagon" / "addons" / "kaykit_medieval_hexagon_pack" / "Assets" / "gltf"
PH_ROOT = SOURCE_ROOT / "polyhaven"
WALKER = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
CALIBRATION_PATH = OUT_ROOT / "camera-calibration.json"

sys.path.insert(0, str(TOOL_ROOT))
import second_gate_render  # noqa: E402
import thestra_camera  # noqa: E402


CALIBRATION = {
    "contract": "thestra.world-camera-calibration",
    "version": 1,
    "projection": "perspective",
    "eye": {"x": -17.5, "y": 0.0, "z": 1.0},
    "orientation": {
        "forwardX": 1.0,
        "forwardY": 0.0,
        "rightX": 0.0,
        "rightY": 1.0,
        "pitchRadians": 0.0,
    },
    "projectionScale": {"x": 1.0, "y": 1.0},
    "fovHalfX": 0.25,
    "fovHalfY": 0.140625,
    "nearPlane": 0.05,
    "farPlane": 60.0,
    "targetWidth": 426,
    "targetHeight": 240,
    "baseViewportWidth": 256,
    "baseViewportHeight": 144,
    "viewportCenterX": 213.0,
    "viewportCenterY": 110.0,
    "projectionWindowOffsetX": 0.0,
    "projectionWindowOffsetY": 0.0,
    "coordinateSystem": {
        "handedness": "right-handed",
        "worldUp": "+Z",
        "worldHorizontal": "XY",
        "cameraForward": "+depth",
        "cameraRight": "+right",
        "screenOrigin": "top-left",
        "screenY": "+down",
        "blenderCameraForward": "-Z",
        "blenderCameraUp": "+Y",
    },
}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def empty_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.055, 0.075, 0.11, 1.0)
    bg.inputs["Strength"].default_value = 0.28
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except (TypeError, ValueError):
        pass
    init_materials()


def collection(name: str) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def link_only(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    target.objects.link(obj)


def material(name: str, color, roughness=0.82, metallic=0.0, emission=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 2.0
    return mat


MATS = {}


def init_materials() -> None:
    global MATS
    MATS = {
        "ground": material("SG_Ground", (0.14, 0.13, 0.14), 0.95),
        "path": material("SG_WornPath", (0.28, 0.20, 0.15), 0.9),
        "mortar": material("SG_Mortar", (0.24, 0.22, 0.21), 0.9),
        "plaster": material("SG_DuskPlaster", (0.30, 0.22, 0.20), 0.88),
        "timber": material("SG_DarkTimber", (0.11, 0.07, 0.055), 0.86),
        "roof": material("SG_RoofSlate", (0.10, 0.13, 0.17), 0.9),
        "water": material("SG_CanalWater", (0.055, 0.15, 0.18), 0.35),
        "warm": material("SG_WarmWindow", (0.43, 0.17, 0.055), 0.55, emission=(0.55, 0.08, 0.015)),
        "haze": material("SG_DistantHaze", (0.12, 0.18, 0.23), 1.0),
        "stone": material("SG_StoneGlue", (0.23, 0.26, 0.28), 0.93),
    }


def box(name: str, location, dimensions, mat, bevel=0.0, target=None):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(MATS[mat] if isinstance(mat, str) else mat)
    if bevel:
        mod = obj.modifiers.new("soft_edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    if target:
        link_only(obj, target)
    return obj


def add_ground(source_col: bpy.types.Collection, direction: str) -> None:
    box(f"SRC_{direction}_Ground", (3.2, 0.0, -0.28), (42.0, 28.0, 0.5), "ground", target=source_col)
    box(f"SRC_{direction}_WalkLane", (0.6, 0.0, 0.015), (10.0, 25.0, 0.08), "path", target=source_col)
    # A few broad paver bands make the floor read at native size without
    # turning the street into a procedural tile texture.
    for i, y in enumerate(range(-12, 13, 2)):
        box(f"SRC_{direction}_Paver_{i:02d}", (0.45, y, 0.07), (4.7, 0.055, 0.04), "mortar", target=source_col)
    box(f"SRC_{direction}_Canal", (3.5, 7.0, -0.02), (8.5, 3.1, 0.05), "water", target=source_col)


def add_ambient_architecture(source_col: bpy.types.Collection, direction: str, warm=False) -> None:
    # Overscan and a deep inhabited wall keep projection-window extremes from
    # exposing a void.  These are intentionally coarse glue pieces.
    box(f"SRC_{direction}_BackWall", (8.2, 0.0, 2.4), (1.0, 29.0, 5.1), "haze", target=source_col)
    box(f"SRC_{direction}_NearWing", (-0.65, -8.2, 2.4), (0.8, 3.4, 5.0), "plaster", target=source_col)
    box(f"SRC_{direction}_NearLintel", (-0.63, -5.9, 4.55), (0.75, 3.0, 0.38), "timber", target=source_col)
    box(f"SRC_{direction}_FarParapet", (6.7, 0.0, 5.0), (0.55, 28.0, 0.42), "roof", target=source_col)
    for i, y in enumerate((-7.1, -6.1, 5.8, 6.8)):
        box(f"SRC_{direction}_WindowGlow_{i}", (5.3, y, 2.75), (0.08, 0.75, 0.92), "warm" if warm else "mortar", target=source_col)


def resolve_kay(relative: str) -> Path:
    path = KAY_ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def resolve_ph(asset: str) -> Path:
    folder = PH_ROOT / asset
    choices = sorted(folder.glob("*.gltf"))
    if not choices:
        raise FileNotFoundError(folder)
    return choices[0]


def imported_meshes(before) -> list[bpy.types.Object]:
    return [o for o in bpy.context.selected_objects if o.name not in before and o.type == "MESH"]


def normalize_imported_materials(objects) -> None:
    for obj in objects:
        for mat in obj.data.materials:
            if not mat or not mat.use_nodes:
                continue
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Roughness"].default_value = min(0.96, max(0.72, float(bsdf.inputs["Roughness"].default_value)))
                bsdf.inputs["Metallic"].default_value = 0.0


def import_asset(path: Path, source_col: bpy.types.Collection, name: str, location, scale, rotation_z=0.0):
    before = {o.name for o in bpy.data.objects}
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.import_scene.gltf(filepath=str(path))
    objs = imported_meshes(before)
    if not objs:
        raise RuntimeError(f"No mesh imported from {path}")
    normalize_imported_materials(objs)
    for idx, obj in enumerate(objs):
        obj.name = f"SRC_{name}_{idx:02d}"
        link_only(obj, source_col)
        obj.location = Vector(location)
        obj.scale = Vector((scale, scale, scale))
        obj.rotation_euler[2] += rotation_z
    return objs


def duplicate_render_meshes(source_col, render_col, decimate=0.72):
    out = []
    for src in list(source_col.objects):
        if src.type != "MESH":
            continue
        dup = src.copy()
        dup.data = src.data.copy()
        dup.name = src.name.replace("SRC_", "RND_", 1)
        render_col.objects.link(dup)
        if len(dup.data.polygons) > 24 and decimate < 1.0:
            mod = dup.modifiers.new("coarse_runtime", "DECIMATE")
            mod.ratio = decimate
            mod.use_collapse_triangulate = True
        out.append(dup)
    return out


def apply_runtime_decimation(render_col) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in list(render_col.objects):
        if obj.type != "MESH":
            continue
        for mod in list(obj.modifiers):
            if mod.type != "DECIMATE":
                continue
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.modifier_apply(modifier=mod.name)
            obj.select_set(False)


def add_anchor(anchors, name, location, facing=1.0):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 0.55
    obj.location = location
    obj.rotation_euler[2] = 0.0 if facing >= 0 else math.pi
    anchors.objects.link(obj)
    return obj


def add_light(scene, name, location, energy, color, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((3.0, 0.0, 0.0)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def make_camera(offset_x=0.0, offset_y=0.0):
    record = copy.deepcopy(CALIBRATION)
    record["viewportCenterX"] += float(offset_x)
    record["viewportCenterY"] += float(offset_y)
    record["projectionWindowOffsetX"] = float(offset_x)
    record["projectionWindowOffsetY"] = float(offset_y)
    camera = thestra_camera.create_or_update_camera(record)
    return camera


def add_preview_actors(camera, actors_col, direction: str, add_npcs=True):
    anchors = [("spawn_player", (0.85, -3.0, 0.0), 1), ("walk_start", (0.85, -4.4, 0.0), 2), ("walk_end", (0.85, 4.4, 0.0), 3)]
    if add_npcs:
        anchors.extend([("npc_merchant", (0.9, -0.45, 0.0), 4), ("npc_watch", (0.9, 2.35, 0.0), 5)])
    for name, loc, frame in anchors:
        obj = thestra_camera.create_actor_preview(WALKER, camera, anchor=loc, frame_index=frame, name=f"ACTOR_{direction}_{name}")
        link_only(obj, actors_col)
    feet = thestra_camera.project_world_point(bpy.context.scene, camera, (0.85, -3.0, 0.0))
    head = thestra_camera.project_world_point(bpy.context.scene, camera, (0.85, -3.0, 1.75))
    second_gate_render.assert_reference_actor_height(abs(head[1] - feet[1]), tolerance_px=1.2)


def scene_setup(direction: str):
    empty_scene()
    scene = bpy.context.scene
    source = collection("TH_SOURCE")
    render = collection("TH_RENDER")
    collision = collection("TH_COLLISION")
    anchors = collection("TH_ANCHORS")
    actors = collection("TH_PREVIEW_ACTORS")
    preview = collection("TH_PREVIEW_ONLY")
    camera_col = collection("TH_CAMERA_PREVIEW")
    add_ground(source, direction)
    add_ambient_architecture(source, direction, warm=direction == "A")
    camera = make_camera()
    link_only(camera, camera_col)
    add_light(scene, "Key_Warm", (-5.0, -7.0, 10.0), 1150, (1.0, 0.57, 0.34), 7.0)
    add_light(scene, "Fill_Blue", (4.0, 8.0, 7.0), 850, (0.30, 0.48, 1.0), 9.0)
    add_light(scene, "Rim_Moon", (8.0, -1.0, 11.0), 700, (0.28, 0.42, 0.95), 5.0)
    add_preview_actors(camera, actors, direction)
    add_anchor(anchors, "spawn_player", (0.85, -3.0, 0.0))
    add_anchor(anchors, "walk_start", (0.85, -4.4, 0.0))
    add_anchor(anchors, "walk_end", (0.85, 4.4, 0.0))
    add_anchor(anchors, "doorway", (2.4, -1.95, 0.0))
    add_anchor(anchors, "npc_merchant", (0.9, -0.45, 0.0), -1)
    add_anchor(anchors, "npc_watch", (0.9, 2.35, 0.0), -1)
    box(f"COL_{direction}_WalkBounds", (0.85, 0.0, 0.55), (1.2, 10.2, 1.1), "mortar", target=collision)
    for obj in source.objects:
        if obj.type == "MESH":
            obj["thestra_source_role"] = "source"
    duplicate_render_meshes(source, render)
    # A tiny guide marks the intended walk lane in authoring view but never renders.
    guide = box(f"GUIDE_{direction}_Lane", (0.82, 0.0, 0.03), (0.12, 9.0, 0.03), "warm", target=preview)
    guide.hide_render = True
    return scene, source, render, collision, anchors, actors, preview, camera_col, camera


def place_direction_a(source, developed=True):
    # Cinderbridge Market: a gated market street, with the water edge and
    # bridge giving the side-view a strong diagonal depth cue.
    import_asset(resolve_kay("buildings/blue/building_market_blue.gltf"), source, "Market", (3.6, -2.2, 0.0), 4.4, -math.pi / 2)
    import_asset(resolve_kay("buildings/blue/building_tavern_blue.gltf"), source, "Tavern", (5.4, 2.55, 0.0), 4.2, -math.pi / 2)
    if not developed:
        import_asset(resolve_kay("buildings/neutral/fence_stone_straight_gate.gltf"), source, "StoneGate", (2.9, 4.7, 0.0), 3.3, -math.pi / 2)
        return
    import_asset(resolve_kay("buildings/blue/building_church_blue.gltf"), source, "Chapel", (6.2, -6.0, 0.0), 4.4, -math.pi / 2)
    import_asset(resolve_kay("buildings/neutral/fence_stone_straight_gate.gltf"), source, "StoneGate", (2.9, 4.7, 0.0), 3.3, -math.pi / 2)
    import_asset(resolve_kay("buildings/neutral/building_bridge_A.gltf"), source, "Bridge", (1.7, 6.7, 0.0), 3.2, 0.0)
    import_asset(resolve_kay("decoration/props/wheelbarrow.gltf"), source, "Wheelbarrow", (0.35, 1.5, 0.08), 2.3, 0.0)
    import_asset(resolve_kay("decoration/props/barrel.gltf"), source, "Barrel", (0.4, -1.3, 0.0), 2.1, 0.0)
    import_asset(resolve_kay("decoration/props/crate_A_big.gltf"), source, "Crate", (0.32, -0.6, 0.0), 2.1, 0.0)
    import_asset(resolve_ph("street_lamp_01"), source, "PH_StreetLamp", (0.25, 0.55, 0.0), 1.45, 0.0)
    import_asset(resolve_ph("wine_barrel_01"), source, "PH_WineBarrel", (0.15, -3.2, 0.0), 0.68, 0.0)
    import_asset(resolve_ph("wooden_lantern_01"), source, "PH_Lantern", (0.18, 0.9, 2.45), 0.55, 0.0)
    box("SRC_A_MarketAwning", (1.0, -2.1, 3.1), (0.75, 3.4, 0.18), "roof", target=source)
    box("SRC_A_MarketStep", (1.15, -2.1, 0.18), (1.5, 3.1, 0.24), "stone", target=source)


def place_direction_b(source, developed=True):
    # Pinewatch Court: a tighter, more vertical courtyard with a timber gate,
    # blacksmith activity, and a planted edge rather than a water street.
    import_asset(resolve_kay("buildings/green/building_blacksmith_green.gltf"), source, "Blacksmith", (3.7, -1.95, 0.0), 4.35, -math.pi / 2)
    import_asset(resolve_kay("buildings/green/building_home_A_green.gltf"), source, "HomeA", (5.3, 2.7, 0.0), 4.0, -math.pi / 2)
    if not developed:
        import_asset(resolve_kay("buildings/neutral/fence_wood_straight_gate.gltf"), source, "TimberGate", (2.4, 4.5, 0.0), 3.4, -math.pi / 2)
        return
    import_asset(resolve_kay("buildings/green/building_home_B_green.gltf"), source, "HomeB", (6.2, -5.6, 0.0), 4.2, -math.pi / 2)
    import_asset(resolve_kay("buildings/neutral/fence_wood_straight_gate.gltf"), source, "TimberGate", (2.4, 4.5, 0.0), 3.4, -math.pi / 2)
    import_asset(resolve_kay("buildings/neutral/wall_corner_A_inside.gltf"), source, "WallCorner", (3.1, -6.3, 0.0), 3.5, -math.pi / 2)
    import_asset(resolve_kay("decoration/nature/hills_A_trees.gltf"), source, "HillTrees", (7.1, 6.1, 0.0), 3.9, 0.0)
    import_asset(resolve_kay("decoration/nature/tree_single_B.gltf"), source, "Tree", (0.2, 3.0, 0.0), 3.4, 0.0)
    import_asset(resolve_kay("decoration/props/wheelbarrow.gltf"), source, "Wheelbarrow", (0.35, -0.1, 0.07), 2.4, 0.0)
    import_asset(resolve_kay("decoration/props/sack.gltf"), source, "Sack", (0.28, -1.0, 0.0), 2.0, 0.0)
    import_asset(resolve_ph("potted_plant_01"), source, "PH_Plant", (0.2, 2.15, 0.0), 0.9, 0.0)
    import_asset(resolve_ph("wooden_crate_01"), source, "PH_Crate", (0.25, -2.7, 0.0), 0.85, 0.0)
    box("SRC_B_SmithForge", (1.0, -2.1, 0.42), (1.0, 2.6, 0.7), "stone", target=source)
    box("SRC_B_SmithRoof", (1.0, -2.1, 2.85), (0.7, 3.2, 0.22), "roof", target=source)
    box("SRC_B_CourtyardBench", (0.25, 1.0, 0.45), (0.65, 1.8, 0.16), "timber", target=source)


def render(scene, path: Path, profile="cycles-lookdev", actors=True, source=True, runtime=False, offset_x=0.0):
    source_col = bpy.data.collections["TH_SOURCE"]
    render_col = bpy.data.collections["TH_RENDER"]
    actors_col = bpy.data.collections["TH_PREVIEW_ACTORS"]
    source_col.hide_render = not source
    render_col.hide_render = source and not runtime
    actors_col.hide_render = not actors
    camera = make_camera(offset_x)
    second_gate_render.apply(scene, profile, allow_expensive=profile == "beauty-selected")
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def write_camera_and_envelope():
    ensure_dir(OUT_ROOT)
    CALIBRATION_PATH.write_text(json.dumps(CALIBRATION, indent=2) + "\n", encoding="utf-8")
    envelope = {
        "samples": [
            {"name": "left_96", "projectionWindowOffsetX": -96, "weight": 1.0, "cost": 0.5},
            {"name": "nominal", "projectionWindowOffsetX": 0, "weight": 2.0, "cost": 0.0},
            {"name": "right_96", "projectionWindowOffsetX": 96, "weight": 1.0, "cost": 0.5},
        ]
    }
    (OUT_ROOT / "camera-envelope.json").write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")


def build_direction(direction: str, developed: bool, out_dir: Path):
    scene, source, render_col, collision, anchors, actors, preview, camera_col, camera = scene_setup(direction)
    (place_direction_a if direction == "A" else place_direction_b)(source, developed=developed)
    # Assets are imported after the initial runtime duplicate so repeatable
    # source/render construction happens here as one explicit boundary.
    # Rebuild render copies to include the placed sourced geometry.
    for obj in list(render_col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    duplicate_render_meshes(source, render_col)
    add_anchor(anchors, "doorway", (2.4, -2.0, 0.0))
    ensure_dir(out_dir)
    profile = "cycles-lookdev" if developed else "clay"
    render(scene, out_dir / f"{direction.lower()}_{'developed' if developed else 'early'}_426.png", profile, actors=True, source=True, runtime=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / f"direction_{direction.lower()}_{'developed' if developed else 'early'}.blend"))
    return {
        "direction": direction,
        "developed": developed,
        "blend": str(out_dir / f"direction_{direction.lower()}_{'developed' if developed else 'early'}.blend"),
        "render": str(out_dir / f"{direction.lower()}_{'developed' if developed else 'early'}_426.png"),
    }


def build_winner(out_dir: Path):
    scene, source, render_col, collision, anchors, actors, preview, camera_col, camera = scene_setup("A")
    place_direction_a(source, developed=True)
    for obj in list(render_col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    duplicate_render_meshes(source, render_col, decimate=0.10)
    apply_runtime_decimation(render_col)
    ensure_dir(out_dir)
    render(scene, out_dir / "winner_source_426.png", "cycles-candidate", actors=True, source=True, runtime=False)

    # The generic pipeline owns atlas creation and runtime export.  It receives
    # this freshly built scene and the explicit bounded camera envelope.
    import town_environment_pipeline  # noqa: E402

    package = out_dir / "runtime"
    source_blend = out_dir / "winner_source_authoring.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(source_blend))
    town_environment_pipeline.run_pipeline_in_blender(
        source_blend,
        package,
        atlas_size=1024,
        bake_samples=2,
        render_profile="cycles-candidate",
        atlas_allocation="view-weighted",
        camera_envelope=[
            {"name": "left_96", "projectionWindowOffsetX": -96, "weight": 1.0, "cost": 0.5},
            {"name": "nominal", "projectionWindowOffsetX": 0, "weight": 2.0, "cost": 0.0},
            {"name": "right_96", "projectionWindowOffsetX": 96, "weight": 1.0, "cost": 0.5},
        ],
        view_policy="bounded-camera",
        margin_px=2,
    )

    # The pipeline has replaced the runtime material with the baked atlas.
    source.hide_render = True
    render_col.hide_render = False
    actors.hide_render = True
    for offset, label in [(-96, "left_96"), (0, "nominal"), (96, "right_96")]:
        render(scene, out_dir / f"winner_runtime_{label}_426.png", "cycles-candidate", actors=False, source=False, runtime=True, offset_x=offset)
    # Also render the actual Walker over the runtime mesh for traversal review;
    # actors are excluded from the bake, then deliberately reintroduced here.
    actors.hide_render = False
    render(scene, out_dir / "winner_runtime_with_walker_426.png", "cycles-candidate", actors=True, source=False, runtime=True)
    source.hide_render = True
    render_col.hide_render = False
    actors.hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "winner.blend"))
    return {
        "blend": str(out_dir / "winner.blend"),
        "runtime": str(package),
        "source": str(out_dir / "winner_source_426.png"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("directions", "winner"), default="directions")
    parser.add_argument("--output", type=Path, default=OUT_ROOT / "evidence")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    write_camera_and_envelope()
    ensure_dir(args.output)
    if args.mode == "directions":
        rows = []
        for direction in ("A", "B"):
            rows.append(build_direction(direction, developed=False, out_dir=args.output / direction.lower()))
            rows.append(build_direction(direction, developed=True, out_dir=args.output / direction.lower()))
        (args.output / "directions.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    else:
        result = build_winner(args.output)
        (args.output / "winner.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
