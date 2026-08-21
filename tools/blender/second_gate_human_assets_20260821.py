"""Fresh Second Gate town gauntlet using human-made CC0 low-poly assets.

This is intentionally a disposable experiment driver.  It starts every town
direction from an empty Blender scene, imports only public source assets, and
keeps the authoring collections explicit so the generic town environment
pipeline can export the selected winner later.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSET_ROOT = ROOT / "out" / "blender" / "second-gate-human-assets-20260821"
MEDIEVAL = ASSET_ROOT / "KayKit-Medieval-Hexagon-Pack-1.0" / "addons" / "kaykit_medieval_hexagon_pack" / "Assets" / "gltf"
CITY = ASSET_ROOT / "KayKit-City-Builder-Bits-1.0" / "addons" / "kaykit_city_builder_bits" / "Assets" / "gltf"
WALKER = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
SKY_HDRI = ASSET_ROOT / "industrial_sunset_puresky_2k.hdr"

sys.path.insert(0, str(HERE))
import second_gate_render  # noqa: E402
import thestra_camera  # noqa: E402


OUT = ROOT / "out" / "blender" / "second-gate-human-assets-20260821" / "evidence"
PACK_URL_MEDIEVAL = "https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0"
PACK_URL_CITY = "https://github.com/KayKit-Game-Assets/KayKit-City-Builder-Bits-1.0"


def calibration_record():
    half_x = math.tan(math.radians(14.0))
    half_y = math.tan(math.atan(half_x) * 240.0 / 426.0)
    return {
        "contract": "thestra.world-camera-calibration",
        "version": 1,
        "projection": "perspective",
        "eye": {"x": 0.0, "y": -31.0, "z": 4.5},
        "orientation": {
            "forwardX": 0.0, "forwardY": 1.0,
            "rightX": 1.0, "rightY": 0.0,
            "pitchRadians": 0.0,
        },
        "projectionScale": {"x": 1.0, "y": 1.0},
        "fovHalfX": half_x,
        "fovHalfY": half_y,
        "nearPlane": 0.1,
        "farPlane": 60.0,
        "targetWidth": 426,
        "targetHeight": 240,
        "baseViewportWidth": 256,
        "baseViewportHeight": 144,
        "viewportCenterX": 213,
        "viewportCenterY": 110,
        "projectionWindowOffsetX": 0,
        "projectionWindowOffsetY": 0,
        "coordinateSystem": {
            "handedness": "right-handed", "worldUp": "+Z", "worldHorizontal": "XY",
            "cameraForward": "+depth", "cameraRight": "+right",
            "screenOrigin": "top-left", "screenY": "+down",
            "blenderCameraForward": "-Z", "blenderCameraUp": "+Y",
        },
    }


def fresh_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    # Blender 5.1 in this environment exposes the legacy enum name; the
    # shared profile helper resolves Eevee/Cycles for the actual render.
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.color_mode = "RGBA"
    scene.world = bpy.data.worlds.new("TH_WORLD_SKYBOX")
    scene.world.use_nodes = True
    world_nodes, world_links = scene.world.node_tree.nodes, scene.world.node_tree.links
    world_nodes.clear()
    out = world_nodes.new("ShaderNodeOutputWorld")
    bg = world_nodes.new("ShaderNodeBackground")
    env = world_nodes.new("ShaderNodeTexEnvironment")
    coords = world_nodes.new("ShaderNodeTexCoord")
    if SKY_HDRI.is_file():
        env.image = bpy.data.images.load(str(SKY_HDRI), check_existing=True)
        env.image.name = "industrial_sunset_puresky_2k.hdr"
        world_links.new(coords.outputs["Normal"], env.inputs["Vector"])
        world_links.new(env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 0.24
    else:
        bg.inputs["Color"].default_value = (0.07, 0.12, 0.20, 1.0)
        bg.inputs["Strength"].default_value = 0.55
    world_links.new(bg.outputs[0], out.inputs["Surface"])
    try:
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "Medium High Contrast"
    except (TypeError, ValueError):
        pass
    cols = {}
    for name in (
        "TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS",
        "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW",
    ):
        cols[name] = bpy.data.collections.new(name)
        scene.collection.children.link(cols[name])
    return scene, cols


def move_to(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)


def material(name, color, roughness=0.8, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def structured_material(name, kind, base, accent=None):
    mat = material(name, base, 0.88)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.5 if kind == "plaster" else 7.0
    noise.inputs["Detail"].default_value = 4.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15 if kind != "wood" else 0.2
    bump.inputs["Distance"].default_value = 0.08
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if kind == "stone":
        brick = nodes.new("ShaderNodeTexBrick")
        brick.inputs["Scale"].default_value = 2.8
        brick.inputs["Mortar Size"].default_value = 0.035
        brick.inputs["Color1"].default_value = (*base, 1)
        brick.inputs["Color2"].default_value = (*(accent or tuple(min(1, c * 1.18) for c in base)), 1)
        brick.inputs["Mortar"].default_value = (0.08, 0.065, 0.05, 1)
        links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])
    elif kind == "wood":
        wave = nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = "X"
        wave.inputs["Scale"].default_value = 5.0
        wave.inputs["Distortion"].default_value = 4.0
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*base, 1)
        ramp.color_ramp.elements[1].color = (*(accent or (0.18, 0.08, 0.03)), 1)
        links.new(wave.outputs["Color"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    elif kind == "plaster":
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*base, 1)
        ramp.color_ramp.elements[1].color = (*(accent or (0.64, 0.32, 0.17)), 1)
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def sky_material(name="Sky_Gradient_Backed"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    tex = nodes.new("ShaderNodeTexCoord")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.16, 0.28, 0.46, 1.0)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.015, 0.035, 0.08, 1.0)
    links.new(tex.outputs["Generated"], separate.inputs[0])
    links.new(separate.outputs[2], ramp.inputs[0])
    links.new(ramp.outputs["Color"], emission.inputs["Color"])
    emission.inputs["Strength"].default_value = 0.55
    links.new(emission.outputs[0], out.inputs["Surface"])
    return mat


def add_cube(name, location, dimensions, col, mat=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to(obj, col)
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Softened edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def add_cylinder(name, location, radius, depth, col, mat, vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    move_to(obj, col)
    obj.data.materials.append(mat)
    return obj


def import_asset(path, col, location, scale=1.0, rotation_z=0.0, role="set dressing", source_pack="medieval"):
    path = Path(path).resolve()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    if not imported:
        raise RuntimeError(f"asset importer produced no objects: {path}")
    for obj in imported:
        move_to(obj, col)
        obj.location = location
        obj.scale = (scale, scale, scale)
        obj.rotation_euler[2] = math.radians(rotation_z)
        obj["source_creator"] = "Kay Lousberg"
        obj["source_license"] = "CC0-1.0"
        obj["source_url"] = PACK_URL_MEDIEVAL if source_pack == "medieval" else PACK_URL_CITY
        obj["source_asset"] = path.stem
        obj["local_role"] = role
    return imported


def asset(pack, relative):
    base = MEDIEVAL if pack == "medieval" else CITY
    return base / Path(relative)


def add_asset(rec, pack, relative, location, scale, rotation=0, role="set dressing", col=None):
    path = asset(pack, relative)
    rec.append({
        "creator": "Kay Lousberg", "sourceUrl": PACK_URL_MEDIEVAL if pack == "medieval" else PACK_URL_CITY,
        "license": "CC0-1.0", "originalAsset": Path(relative).stem,
        "localRole": role, "localPath": str(path.relative_to(ASSET_ROOT)),
    })
    return import_asset(path, col, location, scale, rotation, role, pack)


def add_architectural_glue(col, source_mats, direction):
    stone = source_mats["stone"]
    plaster = source_mats["plaster"]
    wood = source_mats["wood"]
    # Overscanned ground, action lane, terrace edge and a handful of authored
    # masonry pieces.  These are glue geometry around the sourced set dressing.
    add_cube("SRC_Ground_Continuous", (0, 17.0, -0.22), (40, 70, 0.44), col, stone, 0.05)
    add_cube("SRC_Action_Lane", (0, 0.15, 0.055), (24, 2.5, 0.11), col, structured_material("PavingStructured", "stone", (0.24, 0.20, 0.17), (0.38, 0.30, 0.22)), 0.02)
    add_cube("SRC_Back_Terrace", (0, 5.6, 0.35), (27, 3.0, 0.7), col, stone, 0.05)
    add_cube("SRC_Back_Parapet", (0, 4.1, 0.75), (18, 0.35, 0.6), col, stone, 0.04)
    if direction == "A":
        # A rising stair cuts through the market block toward the gate.
        for i in range(6):
            add_cube(f"SRC_RisingStep_{i}", (-5.6 + i * 0.72, 1.9, 0.16 + i * 0.16), (0.85, 2.0, 0.32 + i * 0.02), col, stone, 0.025)
        # Visible doorway thickness at the action plane.
        add_cube("SRC_Doorway_Left", (3.85, 1.25, 1.15), (0.45, 0.7, 2.3), col, stone, 0.04)
        add_cube("SRC_Doorway_Right", (5.15, 1.25, 1.15), (0.45, 0.7, 2.3), col, stone, 0.04)
        add_cube("SRC_Doorway_Lintel", (4.5, 1.25, 2.25), (1.75, 0.7, 0.45), col, stone, 0.04)
        add_cube("SRC_Door_Recess", (4.5, 1.18, 1.05), (0.85, 0.08, 1.8), col, wood, 0.02)
    else:
        # A narrow elevated lane and a broken retaining wall create a different
        # spatial proposition from direction A.
        add_cube("SRC_RidgeWalk", (0, 1.8, 0.8), (19, 2.0, 1.6), col, stone, 0.05)
        add_cube("SRC_RidgeFace", (0, 0.8, 1.8), (19, 0.35, 2.0), col, stone, 0.04)
        add_cube("SRC_RidgeDoorway_Left", (1.4, 0.45, 2.7), (0.42, 0.6, 2.5), col, stone, 0.04)
        add_cube("SRC_RidgeDoorway_Right", (2.8, 0.45, 2.7), (0.42, 0.6, 2.5), col, stone, 0.04)
        add_cube("SRC_RidgeDoorway_Lintel", (2.1, 0.45, 3.9), (1.8, 0.6, 0.45), col, stone, 0.04)
        add_cube("SRC_RidgeDoor", (2.1, 0.38, 2.65), (0.9, 0.08, 1.9), col, wood, 0.02)
    # A crooked timber canopy is deliberate foreground occlusion.
    add_cube("SRC_CanopyBeam", (-0.5, -3.1, 3.2), (8.0, 0.35, 0.35), col, wood, 0.05)
    add_cube("SRC_CanopyPost", (3.15, -3.1, 1.7), (0.35, 0.35, 3.2), col, wood, 0.05)
    add_cube("SRC_CanopyCloth", (-0.5, -3.05, 2.75), (8.0, 1.1, 0.10), col, plaster, 0.02)


def place_direction(scene, cols, direction, polished=True):
    src = cols["TH_SOURCE"]
    rec = []
    mats = {
        "stone": structured_material("Masonry_Courses", "stone", (0.30, 0.25, 0.20), (0.48, 0.39, 0.30)),
        "plaster": structured_material("Weathered_Plaster", "plaster", (0.62, 0.36, 0.18), (0.32, 0.18, 0.12)),
        "wood": structured_material("Directional_Wood", "wood", (0.36, 0.16, 0.07), (0.12, 0.045, 0.02)),
        "dark": material("Iron_Dark", (0.055, 0.045, 0.04), 0.54, 0.25),
        "lantern": material("Lantern_Amber", (0.95, 0.28, 0.06), 0.28, 0.1),
    }
    add_architectural_glue(src, mats, direction)

    if direction == "A":
        # Market landing: an open stair, a gate, and a low cluster of homes.
        add_asset(rec, "medieval", "buildings/yellow/building_church_yellow.gltf", (-5.8, 7.0, 0), 3.7, 0, "civic landmark", src)
        add_asset(rec, "medieval", "buildings/blue/building_market_blue.gltf", (0.5, 5.7, 0), 4.5, 0, "primary market hall", src)
        add_asset(rec, "medieval", "buildings/red/building_home_A_red.gltf", (4.8, 6.3, 0), 3.8, 0, "inhabited facade", src)
        add_asset(rec, "medieval", "buildings/green/building_tavern_green.gltf", (7.7, 7.5, 0), 2.2, 0, "deep continuation", src)
        add_asset(rec, "medieval", "buildings/neutral/building_bridge_A.gltf", (-8.2, 2.0, 0.2), 4.1, 0, "foreground bridge crop", src)
        add_asset(rec, "medieval", "buildings/neutral/wall_straight_gate.gltf", (4.5, 1.6, 0.1), 4.0, 0, "usable doorway and gate", src)
        add_asset(rec, "medieval", "buildings/neutral/wall_straight.gltf", (8.2, 1.7, 0.1), 4.0, 0, "continuing wall", src)
        if polished:
            add_asset(rec, "medieval", "decoration/nature/hill_single_A.gltf", (-8.6, 12.0, 0), 4.6, 0, "distant landscape continuation", src)
            add_asset(rec, "medieval", "decoration/nature/mountain_B_grass.gltf", (9.2, 12.5, 0), 5.0, 0, "distant landscape continuation", src)
            add_asset(rec, "medieval", "decoration/nature/tree_single_A.gltf", (-9.2, 3.2, 0), 3.3, 0, "natural foreground frame", src)
            add_asset(rec, "medieval", "decoration/props/wheelbarrow.gltf", (-1.5, -0.2, 0.1), 4.0, -8, "market clutter", src)
            add_asset(rec, "medieval", "decoration/props/barrel.gltf", (1.9, -0.55, 0.1), 4.3, 0, "market clutter", src)
            add_asset(rec, "medieval", "decoration/props/crate_long_A.gltf", (2.8, -0.35, 0.1), 4.0, 3, "market clutter", src)
            add_asset(rec, "medieval", "decoration/props/flag_red.gltf", (4.8, 2.0, 0.1), 4.0, 0, "wayfinding accent", src)
            add_asset(rec, "city", "bench.gltf", (-3.0, -0.55, 0.1), 3.0, 0, "neutral resting place", src)
            add_asset(rec, "city", "box_A.gltf", (3.9, -0.4, 0.1), 3.2, 0, "neutral cargo clutter", src)
    else:
        # Ridge alley: a raised lane, civic bell silhouette, and a broken edge.
        add_asset(rec, "medieval", "buildings/blue/building_church_blue.gltf", (-6.5, 7.3, 0), 3.8, 0, "civic landmark", src)
        add_asset(rec, "medieval", "buildings/red/building_tower_A_red.gltf", (-0.5, 7.2, 0), 4.0, 0, "vertical landmark", src)
        add_asset(rec, "medieval", "buildings/green/building_home_B_green.gltf", (4.4, 6.7, 0), 4.3, 0, "inhabited facade", src)
        add_asset(rec, "medieval", "buildings/yellow/building_home_A_yellow.gltf", (8.5, 6.9, 0), 4.0, 0, "deep continuation", src)
        add_asset(rec, "medieval", "buildings/neutral/building_bridge_B.gltf", (-7.4, 2.4, 0.3), 4.3, 0, "foreground bridge crop", src)
        add_asset(rec, "medieval", "buildings/neutral/wall_corner_A_gate.gltf", (2.2, 1.2, 1.6), 4.0, 0, "usable ridge doorway", src)
        add_asset(rec, "medieval", "buildings/neutral/building_destroyed.gltf", (7.8, 1.3, 0.1), 4.2, 0, "broken retaining edge", src)
        if polished:
            add_asset(rec, "medieval", "decoration/nature/hill_single_B.gltf", (-8.8, 12.0, 0), 4.8, 0, "distant landscape continuation", src)
            add_asset(rec, "medieval", "decoration/nature/mountain_A_grass.gltf", (9.0, 12.2, 0), 5.0, 0, "distant landscape continuation", src)
            add_asset(rec, "medieval", "decoration/nature/trees_A_medium.gltf", (-9.0, 2.8, 0), 3.2, 0, "natural foreground frame", src)
            add_asset(rec, "medieval", "decoration/nature/rock_single_C.gltf", (8.5, -2.4, 0), 3.3, 0, "natural foreground frame", src)
            add_asset(rec, "medieval", "decoration/props/barrel.gltf", (-2.0, -0.55, 0.1), 4.1, 0, "ridge clutter", src)
            add_asset(rec, "medieval", "decoration/props/sack.gltf", (-0.8, -0.5, 0.1), 4.3, 0, "ridge clutter", src)
            add_asset(rec, "medieval", "decoration/props/crate_A_big.gltf", (3.5, -0.5, 0.1), 4.0, 12, "ridge clutter", src)
            add_asset(rec, "medieval", "decoration/props/flag_yellow.gltf", (0.4, 2.4, 1.5), 4.3, 0, "wayfinding accent", src)
            add_asset(rec, "city", "bench.gltf", (5.3, -0.45, 0.1), 3.0, 0, "neutral resting place", src)
            add_asset(rec, "city", "box_B.gltf", (6.0, -0.4, 0.1), 3.2, 0, "neutral cargo clutter", src)

    # Local material accents on the glue architecture; imported materials keep
    # their original meshes/UVs and are unified by lighting and scene grade.
    for obj in src.objects:
        if obj.type == "MESH" and obj.name.startswith("SRC_") and not obj.data.materials:
            obj.data.materials.append(mats["stone"])

    # Scene lights: a warm, low sun plus cool ambient fill and a small lantern
    # incident at the action plane.
    bpy.ops.object.light_add(type="AREA", location=(-3, -7, 11))
    key = bpy.context.object
    key.name = "SRC_Key_Sunlit"
    key.data.energy = 950
    key.data.shape = "RECTANGLE"
    key.data.size = 12
    key.data.color = (1.0, 0.52, 0.24)
    key.rotation_euler = (math.radians(18), 0, math.radians(10))
    move_to(key, src)
    bpy.ops.object.light_add(type="AREA", location=(5, -4, 6))
    fill = bpy.context.object
    fill.name = "SRC_Fill_Moon"
    fill.data.energy = 700
    fill.data.size = 10
    fill.data.color = (0.22, 0.42, 1.0)
    fill.rotation_euler = (math.radians(34), 0, math.radians(150))
    move_to(fill, src)
    bpy.ops.object.light_add(type="POINT", location=(1.7, -1.6, 2.0))
    lamp = bpy.context.object
    lamp.name = "SRC_Lantern_Incident"
    lamp.data.energy = 180
    lamp.data.color = (1.0, 0.20, 0.04)
    lamp.data.shadow_soft_size = 0.8
    move_to(lamp, src)
    bpy.ops.object.light_add(type="SUN", location=(0, -4, 10))
    sun = bpy.context.object
    sun.name = "SRC_Sun_Fill"
    sun.data.energy = 2.4
    sun.data.color = (1.0, 0.78, 0.62)
    sun.rotation_euler = (math.radians(28), math.radians(-18), math.radians(-22))
    move_to(sun, src)

    return rec, mats


def add_proxies(scene, cols, direction, source_mats):
    render = cols["TH_RENDER"]
    col = cols["TH_COLLISION"]
    stone = source_mats["stone"]
    # The runtime mesh is a decimated copy of the actual fresh source set.
    # This preserves the authored depth/silhouette and gives selected-to-active
    # baking a measured receiving surface instead of a distant box guess.
    source_meshes = [obj for obj in cols["TH_SOURCE"].objects if obj.type == "MESH"]
    for index, original in enumerate(source_meshes):
        proxy = original.copy()
        proxy.data = original.data.copy()
        proxy.name = f"RND_{index:03d}_{original.name}"
        render.objects.link(proxy)
        if len(proxy.data.vertices) > 80:
            bpy.context.view_layer.objects.active = proxy
            proxy.select_set(True)
            decimate = proxy.modifiers.new("Coarse silhouette", "DECIMATE")
            decimate.ratio = 0.42
            try:
                bpy.ops.object.modifier_apply(modifier=decimate.name)
            except RuntimeError:
                pass
            proxy.select_set(False)
    # Simple collision lane and architecture blockers.
    add_cube("COL_WalkBounds", (0, 0.2, 0.08), (18.0, 1.2, 0.16), col, stone)
    add_cube("COL_BackEdge", (0, 1.3, 1.0), (18.0, 0.5, 2.0), col, stone)
    add_cube("COL_Doorway", (4.5 if direction == "A" else 2.1, 1.2 if direction == "A" else 0.45, 1.0), (1.0, 0.8, 2.0), col, stone)

    render_meshes = [o for o in render.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in render_meshes:
        obj.select_set(True)
    scene.view_layers[0].objects.active = render_meshes[0]
    bpy.ops.object.join()
    render_mesh = bpy.context.object
    render_mesh.name = "RND_Environment_Mesh"
    bpy.context.view_layer.objects.active = render_mesh
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.04)
    bpy.ops.object.mode_set(mode="OBJECT")
    return render_mesh


def add_anchors_and_actor(scene, cols, direction):
    anchors = cols["TH_ANCHORS"]
    def anchor(name, loc, rot=0):
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "ARROWS"
        empty.empty_display_size = 0.5
        empty.location = loc
        empty.rotation_euler[2] = math.radians(rot)
        anchors.objects.link(empty)
        return empty
    anchor("spawn_player", (-5.5, 0.0, 0.0), 0)
    anchor("walk_start", (-7.5, 0.0, 0.0), 0)
    anchor("walk_end", (7.5, 0.0, 0.0), 180)
    anchor("doorway", (4.5 if direction == "A" else 2.1, 0.5, 0.0), 0)
    anchor("npc_anchor_01", (-1.6, 0.0, 0.0), 0)
    anchor("npc_anchor_02", (3.0, 0.0, 0.0), 180)
    anchor("foreground_occluder", (-0.5, -3.1, 0.0), 0)
    actor_col = cols["TH_PREVIEW_ACTORS"]
    cam = thestra_camera.create_or_update_camera(calibration_record(), scene=scene)
    move_to(cam, cols["TH_CAMERA_PREVIEW"])
    for i, loc in enumerate(((-5.5, 0.0, 0.0), (-1.6, 0.0, 0.0), (3.0, 0.0, 0.0))):
        walker = thestra_camera.create_actor_preview(WALKER, cam, anchor=loc, frame_index=i, name=f"TH_WALKER_{i}")
        move_to(walker, actor_col)
        walker.hide_render = False
    return cam


def set_source_visibility(cols, source=True, render=False, actors=True):
    cols["TH_SOURCE"].hide_render = not source
    cols["TH_RENDER"].hide_render = not render
    cols["TH_PREVIEW_ACTORS"].hide_render = not actors
    cols["TH_COLLISION"].hide_render = True
    cols["TH_PREVIEW_ONLY"].hide_render = True
    for name in ("TH_SOURCE", "TH_RENDER", "TH_PREVIEW_ACTORS"):
        for obj in cols[name].objects:
            obj.hide_render = not {"TH_SOURCE": source, "TH_RENDER": render, "TH_PREVIEW_ACTORS": actors}[name]


def clay_material():
    return material("EARLY_CLAY", (0.36, 0.40, 0.46), 0.94)


def render_to(scene, path, profile="cycles-draft", allow_expensive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    second_gate_render.apply(scene, profile, allow_expensive=allow_expensive)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_clay(scene, cols, path):
    clay = clay_material()
    stored = []
    for obj in cols["TH_SOURCE"].objects:
        if obj.type == "MESH":
            slots = list(obj.data.materials)
            stored.append((obj, slots))
            obj.data.materials.clear()
            obj.data.materials.append(clay)
    try:
        set_source_visibility(cols, source=True, render=False, actors=True)
        render_to(scene, path, "clay")
    finally:
        for obj, slots in stored:
            obj.data.materials.clear()
            for slot in slots:
                obj.data.materials.append(slot)


def render_camera_extremes(scene, cam, cols, out_dir):
    base_shift = float(cam.data.shift_x)
    rows = []
    for offset, label in ((-96.0, "left"), (0.0, "center"), (96.0, "right")):
        cam.data.shift_x = base_shift - offset / 426.0
        transform = tuple(round(v, 8) for row in cam.matrix_world for v in row)
        set_source_visibility(cols, source=True, render=False, actors=True)
        path = out_dir / f"winner_{label}.png"
        render_to(scene, path, "cycles-candidate")
        rows.append({"offset": offset, "path": path.name, "cameraTransform": transform})
    cam.data.shift_x = base_shift
    return rows


def build_direction(direction, polished, out_dir):
    scene, cols = fresh_scene()
    records, mats = place_direction(scene, cols, direction, polished=polished)
    render_mesh = add_proxies(scene, cols, direction, mats)
    cam = add_anchors_and_actor(scene, cols, direction)
    set_source_visibility(cols, source=True, render=False, actors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    render_clay(scene, cols, out_dir / f"early_{direction}.png")
    render_to(scene, out_dir / f"developed_{direction}.png", "cycles-lookdev")
    # Source-side final named separately for the selected winner handoff.
    if polished:
        render_to(scene, out_dir / f"source_{direction}_center.png", "cycles-candidate")
    scene["gauntlet_direction"] = direction
    scene["human_asset_count"] = len(records)
    scene["th_source_to_th_render"] = "source appearance baked through coarse proxy UVs"
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / f"town_{direction}.blend"))
    return {
        "direction": direction,
        "polished": polished,
        "assetRecords": records,
        "assetCount": len(records),
        "renderMeshTriangles": len(render_mesh.data.polygons),
        "blend": str(out_dir / f"town_{direction}.blend"),
    }


def build_asset_board(out_dir):
    scene, cols = fresh_scene()
    src = cols["TH_SOURCE"]
    board = [
        ("medieval", "buildings/yellow/building_church_yellow.gltf", -4.5, 3.8, 3.0),
        ("medieval", "buildings/blue/building_market_blue.gltf", -1.5, 3.8, 3.0),
        ("medieval", "buildings/neutral/building_bridge_A.gltf", 1.6, 3.8, 3.0),
        ("medieval", "buildings/neutral/wall_straight_gate.gltf", 4.6, 3.8, 3.0),
        ("medieval", "decoration/nature/tree_single_A.gltf", -4.5, 0.2, 3.0),
        ("medieval", "decoration/props/wheelbarrow.gltf", -1.5, 0.2, 3.0),
        ("medieval", "decoration/props/barrel.gltf", 1.5, 0.2, 3.5),
        ("medieval", "decoration/props/crate_long_A.gltf", 4.5, 0.2, 3.2),
        ("city", "bench.gltf", -1.5, -2.3, 3.0),
        ("city", "box_A.gltf", 1.5, -2.3, 3.0),
    ]
    for pack, rel, x, y, scale in board:
        import_asset(asset(pack, rel), src, (x, y, 0), scale, 0, "audition board", pack)
    add_cube("BoardFloor", (0, 1.0, -0.2), (14, 9, 0.4), src, structured_material("BoardStone", "stone", (0.25, 0.20, 0.16)))
    cam = thestra_camera.create_or_update_camera(calibration_record(), scene=scene)
    move_to(cam, cols["TH_CAMERA_PREVIEW"])
    set_source_visibility(cols, source=True, render=False, actors=False)
    render_to(scene, out_dir / "asset-board.png", "cycles-lookdev")


def write_manifest(payload, out_dir):
    (out_dir / "gauntlet-manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--direction", choices=("A", "B", "both", "board"), default="both")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "camera_calibration.json").write_text(json.dumps(calibration_record(), indent=2), encoding="utf-8")
    payload = {
        "experiment": "Second Gate human-made public low-poly town gauntlet 2026-08-21",
        "assetSources": [
            {"creator": "Kay Lousberg", "sourceUrl": PACK_URL_MEDIEVAL, "license": "CC0-1.0", "retrieval": "2026-08-21", "packRole": "architecture, roads, walls, vegetation, props"},
            {"creator": "Kay Lousberg", "sourceUrl": PACK_URL_CITY, "license": "CC0-1.0", "retrieval": "2026-08-21", "packRole": "neutral benches and cargo clutter"},
            {"creator": "Sergej Majboroda; Jarod Guest (sky edits)", "sourceUrl": "https://polyhaven.com/a/industrial_sunset_puresky", "license": "CC0-1.0", "retrieval": "2026-08-21", "originalAsset": "industrial_sunset_puresky_2k.hdr", "packRole": "outdoor skybox / world lighting"},
        ],
        "calibration": calibration_record(),
        "directions": [],
        "candidatePacksDownloaded": 2,
        "selectionMethod": "native 426x240 camera review; two independent empty-scene lineages",
    }
    if args.direction in ("A", "both"):
        payload["directions"].append(build_direction("A", False, args.output / "direction-A"))
        payload["directions"].append(build_direction("A", True, args.output / "direction-A"))
    if args.direction in ("B", "both"):
        payload["directions"].append(build_direction("B", False, args.output / "direction-B"))
        payload["directions"].append(build_direction("B", True, args.output / "direction-B"))
    if args.direction in ("board", "both"):
        build_asset_board(args.output)
    write_manifest(payload, args.output)
    print(json.dumps({"directions": len(payload["directions"]), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
