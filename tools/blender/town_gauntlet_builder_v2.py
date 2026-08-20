"""Second Rite — Town Gauntlet Scene Builder V2 (Material & Camera Corrected).

Authors rich, textured 3D town environments in Blender matching late-1990s
pre-rendered JRPG aesthetic (Vagrant Story / FFIX style), using:
- Corrected ~43mm level side-view camera authority (PR #859 baseline)
- Rich material strategies: Procedural (A), Public CC0 (B), AI Generated (C), Hybrid
- Rich lighting: warm interior glows (5.0 strength), lantern light pools, cool twilight fill
- Character scaling: Walker 24x48 sprites in TH_PREVIEW_ACTORS
- Complete collection separation: TH_SOURCE, TH_RENDER, TH_COLLISION, TH_ANCHORS, etc.
"""
from __future__ import annotations

import io
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT / "projects" / "hichaukitoden-game"
WALKER_PATH = PROJECT_ROOT / "assets" / "character" / "walker.png"

# Default fallback calibration (overridden at runtime by thestra_camera / next authority)
CALIBRATION_RECORD = {
    "contract": "thestra.world-camera-calibration",
    "version": 1,
    "projection": "perspective",
    "eye": {"x": 0.9, "y": 5.5, "z": 0.0},
    "orientation": {
        "forwardX": 1.0, "forwardY": 0.0,
        "rightX": 0.0, "rightY": 1.0,
        "pitchRadians": 0.0
    },
    "projectionScale": {"x": 1.0, "y": 1.0},
    "fovHalfX": 0.25,
    "fovHalfY": 0.140625,
    "nearPlane": 0.05,
    "farPlane": 32.0,
    "targetWidth": 426,
    "targetHeight": 240,
    "baseViewportWidth": 256,
    "baseViewportHeight": 144,
    "viewportCenterX": 213,
    "viewportCenterY": 70,
    "projectionWindowOffsetX": 0,
    "projectionWindowOffsetY": 0,
    "coordinateSystem": {
        "handedness": "right-handed",
        "worldUp": "+Z",
        "worldHorizontal": "XY",
        "cameraForward": "+depth",
        "cameraRight": "+right",
        "screenOrigin": "top-left",
        "screenY": "+down",
        "blenderCameraForward": "-Z",
        "blenderCameraUp": "+Y"
    }
}


def build_scene(attempt_id: str, blend_output: Path | None = None):
    import bpy
    from mathutils import Vector, Matrix, Euler
    sys.path.insert(0, str(ROOT / "tools" / "blender"))
    import thestra_camera
    import material_library as mat_lib

    # 1. Reset scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for light in list(bpy.data.lights):
        bpy.data.lights.remove(light)
    for img in list(bpy.data.images):
        bpy.data.images.remove(img)

    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0

    # Deep twilight world background
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.05, 0.07, 0.14, 1.0)
        bg_node.inputs["Strength"].default_value = 0.55

    # Cycles setup
    scene.render.engine = 'CYCLES'
    try:
        scene.cycles.device = 'CPU'
    except Exception:
        pass
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.film_transparent = False
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240

    # Create root contract collections
    root_col = scene.collection
    col_source = bpy.data.collections.new("TH_SOURCE")
    col_render = bpy.data.collections.new("TH_RENDER")
    col_collision = bpy.data.collections.new("TH_COLLISION")
    col_anchors = bpy.data.collections.new("TH_ANCHORS")
    col_preview_actors = bpy.data.collections.new("TH_PREVIEW_ACTORS")
    col_preview_only = bpy.data.collections.new("TH_PREVIEW_ONLY")
    col_camera = bpy.data.collections.new("TH_CAMERA_PREVIEW")

    for c in (col_source, col_render, col_collision, col_anchors, col_preview_actors, col_preview_only, col_camera):
        root_col.children.link(c)

    # Runtime / preview layers hidden during beauty render
    col_render.hide_render = True
    col_collision.hide_render = True
    col_preview_only.hide_render = True

    # 2. Materials Cache
    # Strategy A (Procedural)
    mat_proc_stone = mat_lib.create_procedural_stone("Proc_StoneWall")
    mat_proc_plaster_warm = mat_lib.create_procedural_plaster("Proc_PlasterWarm", base_color=(0.74, 0.68, 0.56))
    mat_proc_plaster_cool = mat_lib.create_procedural_plaster("Proc_PlasterCool", base_color=(0.48, 0.52, 0.58))
    mat_proc_cobble = mat_lib.create_procedural_cobblestone("Proc_Cobblestone")
    mat_proc_timber_dark = mat_lib.create_procedural_wood("Proc_TimberDark", dark=True)
    mat_proc_timber_warm = mat_lib.create_procedural_wood("Proc_TimberWarm", dark=False)
    mat_proc_roof_slate = mat_lib.create_procedural_roof_tile("Proc_RoofSlate", terracotta=False)
    mat_proc_roof_terra = mat_lib.create_procedural_roof_tile("Proc_RoofTerra", terracotta=True)
    mat_proc_iron = mat_lib.create_procedural_metal("Proc_Iron", brass=False)
    mat_proc_brass = mat_lib.create_procedural_metal("Proc_Brass", brass=True)

    # Strategy B (Public CC0)
    mat_cc0_stone = mat_lib.create_public_pbr_material("CC0_RusticStone", "rustic_stone_wall", uv_scale=1.4)
    mat_cc0_plaster = mat_lib.create_public_pbr_material("CC0_StuccoBrick", "rough_plaster_brick_04", uv_scale=1.5)
    mat_cc0_cobble = mat_lib.create_public_pbr_material("CC0_Cobblestone", "cobblestone_05", uv_scale=2.2)
    mat_cc0_timber = mat_lib.create_public_pbr_material("CC0_MedievalWood", "medieval_wood", uv_scale=1.5)
    mat_cc0_roof = mat_lib.create_public_pbr_material("CC0_ClayRoof", "clay_roof_tiles", uv_scale=2.0)
    mat_cc0_iron = mat_lib.create_public_pbr_material("CC0_RustyIron", "rusty_metal_02", uv_scale=2.0)

    # Strategy C (OpenAI Generated)
    mat_ai_stone = mat_lib.create_ai_pbr_material("AI_LimestoneAshlar", "ai_limestone_ashlar", uv_scale=1.4)
    mat_ai_plaster = mat_lib.create_ai_pbr_material("AI_AgedStucco", "ai_aged_stucco_plaster", uv_scale=1.4)
    mat_ai_cobble = mat_lib.create_ai_pbr_material("AI_TownCobble", "ai_medieval_cobblestone", uv_scale=2.0)
    mat_ai_timber = mat_lib.create_ai_pbr_material("AI_DarkTimber", "ai_weathered_dark_timber", uv_scale=1.5)
    mat_ai_roof = mat_lib.create_ai_pbr_material("AI_TerracottaRoof", "ai_terracotta_roof_tiles", uv_scale=2.0)

    # Hybrid
    mat_hybrid_facade = mat_lib.create_hybrid_stone_facade("Hybrid_StoneFacade")

    # Shared Accent Materials (Interior glow, Awning cloths)
    mat_window_glow = bpy.data.materials.new("WindowGlowWarm")
    mat_window_glow.use_nodes = True
    bsdf_glow = mat_window_glow.node_tree.nodes.get("Principled BSDF")
    if bsdf_glow:
        bsdf_glow.inputs["Base Color"].default_value = (1.0, 0.82, 0.45, 1.0)
        bsdf_glow.inputs["Roughness"].default_value = 0.2
        if "Emission Color" in bsdf_glow.inputs:
            bsdf_glow.inputs["Emission Color"].default_value = (1.0, 0.78, 0.38, 1.0)
            bsdf_glow.inputs["Emission Strength"].default_value = 5.0
        elif "Emission" in bsdf_glow.inputs:
            bsdf_glow.inputs["Emission"].default_value = (1.0, 0.78, 0.38, 1.0)

    mat_cloth_red = bpy.data.materials.new("CanopyRed")
    mat_cloth_red.use_nodes = True
    mat_cloth_red.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.68, 0.14, 0.12, 1.0)
    mat_cloth_red.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = 0.9

    mat_cloth_gold = bpy.data.materials.new("CanopyGold")
    mat_cloth_gold.use_nodes = True
    mat_cloth_gold.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.82, 0.65, 0.18, 1.0)
    mat_cloth_gold.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = 0.9

    mat_cloth_blue = bpy.data.materials.new("CanopyBlue")
    mat_cloth_blue.use_nodes = True
    mat_cloth_blue.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.18, 0.32, 0.55, 1.0)
    mat_cloth_blue.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = 0.9

    def link_obj(obj, collection):
        collection.objects.link(obj)
        if obj.name in root_col.objects:
            root_col.objects.unlink(obj)
        return obj

    def create_box(name, loc, size, mat=None, col=col_source):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = size
        bpy.ops.object.transform_apply(scale=True)
        if mat:
            obj.data.materials.append(mat)
        return link_obj(obj, col)

    def create_cylinder(name, loc, radius, depth, verts=16, mat=None, rot=(0,0,0), col=col_source):
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
        obj = bpy.context.active_object
        obj.name = name
        if mat:
            obj.data.materials.append(mat)
        return link_obj(obj, col)

    def create_point_light(name, loc, energy, color, radius=0.25):
        bpy.ops.object.light_add(type='POINT', radius=radius, location=loc)
        light = bpy.context.active_object
        light.name = name
        light.data.energy = energy
        light.data.color = color
        return link_obj(light, col_source)

    def create_sun_light(name, energy, color, rot):
        bpy.ops.object.light_add(type='SUN', location=(5, 5, 12))
        sun = bpy.context.active_object
        sun.name = name
        sun.data.energy = energy
        sun.data.color = color
        sun.rotation_euler = rot
        return link_obj(sun, col_source)

    # Reusable Architectural Modules
    def create_townhouse(prefix, loc, width, depth, height, floors=2, timber=True,
                         mat_stone=mat_cc0_stone, mat_plaster=mat_cc0_plaster,
                         mat_timber=mat_cc0_timber, mat_roof=mat_cc0_roof,
                         with_door=False, door_loc=(0,0,0), window_rows=1):
        x, y, z = loc
        # Stone Foundation
        create_box(f"{prefix}_Base", (x, y, z + 0.6), (depth, width, 1.2), mat_stone)
        # Upper Stucco
        create_box(f"{prefix}_Plaster", (x, y, z + 0.6 + height * 0.5), (depth, width, height), mat_plaster)

        # Half-Timber Framing
        if timber:
            beam_t = 0.14
            for dy in (-width*0.5 + beam_t*0.5, width*0.5 - beam_t*0.5, 0):
                create_box(f"{prefix}_BeamV_{dy}", (x - depth*0.5 - 0.03, y + dy, z + 0.6 + height*0.5), (0.1, beam_t, height + 1.2), mat_timber)
            for f in range(1, floors + 1):
                fz = z + f * (height / floors)
                create_box(f"{prefix}_BeamH_{f}", (x - depth*0.5 - 0.05, y, fz), (0.14, width + 0.15, 0.18), mat_timber)
                for cy in (-width*0.35, 0, width*0.35):
                    create_box(f"{prefix}_Corbel_{f}_{cy}", (x - depth*0.5 - 0.18, y + cy, fz - 0.16), (0.35, 0.16, 0.22), mat_timber)

        # Windows with Warm Glow
        win_w = 0.55
        win_h = 0.8
        for r in range(window_rows):
            wz = z + 1.8 + r * 1.5
            for wy in (-width*0.28, width*0.28):
                create_box(f"{prefix}_WinFrame_{r}_{wy}", (x - depth*0.5 - 0.04, y + wy, wz), (0.1, win_w + 0.12, win_h + 0.12), mat_timber)
                create_box(f"{prefix}_WinGlass_{r}_{wy}", (x - depth*0.5 - 0.02, y + wy, wz), (0.05, win_w, win_h), mat_window_glow)
                create_box(f"{prefix}_WinSill_{r}_{wy}", (x - depth*0.5 - 0.1, y + wy, wz - win_h*0.5 - 0.06), (0.18, win_w + 0.25, 0.1), mat_stone)
                # Local light spill
                create_point_light(f"{prefix}_WinSpill_{r}_{wy}", (x - depth*0.5 - 0.4, y + wy, wz), 28.0, (1.0, 0.78, 0.42), radius=0.25)

        # Roof
        roof_h = 1.8
        create_box(f"{prefix}_RoofBase", (x + 0.2, y, z + height + roof_h*0.45), (depth + 0.8, width + 0.5, roof_h), mat_roof)
        create_box(f"{prefix}_Chimney", (x + depth*0.2, y + width*0.25, z + height + roof_h + 0.5), (0.65, 0.65, 1.4), mat_stone)
        create_box(f"{prefix}_ChimneyCap", (x + depth*0.2, y + width*0.25, z + height + roof_h + 1.25), (0.8, 0.8, 0.18), mat_stone)

        # Arched Doorway
        if with_door:
            dx, dy, dz = door_loc
            create_box(f"{prefix}_DoorArchL", (dx - 0.05, dy - 0.55, dz + 1.0), (0.25, 0.25, 2.0), mat_stone)
            create_box(f"{prefix}_DoorArchR", (dx - 0.05, dy + 0.55, dz + 1.0), (0.25, 0.25, 2.0), mat_stone)
            create_box(f"{prefix}_DoorArchTop", (dx - 0.05, dy, dz + 2.1), (0.25, 1.35, 0.3), mat_stone)
            create_box(f"{prefix}_DoorPanel", (dx + 0.06, dy, dz + 1.0), (0.1, 0.95, 1.9), mat_proc_timber_warm)
            create_box(f"{prefix}_DoorStep1", (dx - 0.3, dy, dz + 0.15), (0.5, 1.5, 0.25), mat_stone)
            create_box(f"{prefix}_DoorStep2", (dx - 0.6, dy, dz - 0.05), (0.5, 1.8, 0.25), mat_stone)
            create_box(f"{prefix}_DoorLanternBody", (dx - 0.35, dy + 0.75, dz + 2.0), (0.18, 0.18, 0.35), mat_proc_brass)
            create_box(f"{prefix}_DoorLanternGlow", (dx - 0.35, dy + 0.75, dz + 2.0), (0.12, 0.12, 0.22), mat_window_glow)
            create_point_light(f"{prefix}_DoorLight", (dx - 0.5, dy + 0.75, dz + 2.0), 85.0, (1.0, 0.76, 0.42), radius=0.35)

    def create_street_lantern(prefix, loc, height=2.6, light_energy=95.0, mat_metal=mat_cc0_iron):
        x, y, z = loc
        create_cylinder(f"{prefix}_Base", (x, y, z + 0.25), 0.22, 0.5, verts=12, mat=mat_metal)
        create_cylinder(f"{prefix}_Post", (x, y, z + height*0.5), 0.08, height, verts=8, mat=mat_metal)
        create_box(f"{prefix}_Bracket", (x, y, z + height), (0.35, 0.1, 0.25), mat_metal)
        create_box(f"{prefix}_LanternHousing", (x, y, z + height - 0.12), (0.24, 0.24, 0.4), mat_proc_brass)
        create_box(f"{prefix}_LanternGlass", (x, y, z + height - 0.12), (0.16, 0.16, 0.28), mat_window_glow)
        create_point_light(f"{prefix}_Light", (x, y, z + height - 0.12), light_energy, (1.0, 0.78, 0.45), radius=0.35)

    def create_market_stall(prefix, loc, width=2.2, depth=1.3, red_gold=True, mat_wood=mat_cc0_timber):
        x, y, z = loc
        create_box(f"{prefix}_TableTop", (x, y, z + 0.75), (depth, width, 0.12), mat_proc_timber_warm)
        for dx in (-depth*0.42, depth*0.42):
            for dy in (-width*0.42, width*0.42):
                create_box(f"{prefix}_Leg_{dx}_{dy}", (x + dx, y + dy, z + 0.38), (0.1, 0.1, 0.75), mat_wood)
                create_box(f"{prefix}_Pole_{dx}_{dy}", (x + dx, y + dy, z + 1.45), (0.06, 0.06, 1.45), mat_wood)
        c_mat1 = mat_cloth_red if red_gold else mat_cloth_blue
        c_mat2 = mat_cloth_gold if red_gold else mat_proc_plaster_warm
        for s in range(5):
            sy = y - width*0.4 + s * (width * 0.2)
            c_mat = c_mat1 if s % 2 == 0 else c_mat2
            create_box(f"{prefix}_CanopyStripe_{s}", (x, sy, z + 2.25), (depth + 0.35, width*0.2, 0.14), c_mat)
        create_cylinder(f"{prefix}_Barrel1", (x - 0.25, y + width*0.5 + 0.35, z + 0.48), 0.28, 0.95, verts=12, mat=mat_wood)
        create_cylinder(f"{prefix}_Barrel2", (x + 0.25, y + width*0.5 + 0.45, z + 0.38), 0.24, 0.75, verts=12, mat=mat_proc_timber_warm)
        create_box(f"{prefix}_Crate1", (x - 0.15, y - width*0.5 - 0.4, z + 0.32), (0.55, 0.55, 0.65), mat_proc_timber_warm)
        create_cylinder(f"{prefix}_Pot1", (x, y - 0.45, z + 0.9), 0.09, 0.22, verts=8, mat=mat_proc_brass)
        create_cylinder(f"{prefix}_Pot2", (x + 0.25, y + 0.25, z + 0.9), 0.07, 0.28, verts=8, mat=mat_window_glow)

    def create_foreground_arch(prefix, loc, arch_span=3.4, arch_height=4.6, pillar_rad=0.5, mat_stone=mat_cc0_stone):
        x, y, z = loc
        create_cylinder(f"{prefix}_PillarL", (x, y - arch_span*0.5, z + arch_height*0.5), pillar_rad, arch_height, verts=16, mat=mat_stone)
        create_box(f"{prefix}_CapitalL", (x, y - arch_span*0.5, z + arch_height - 0.25), (pillar_rad*2.5, pillar_rad*2.5, 0.5), mat_stone)
        create_cylinder(f"{prefix}_PillarR", (x, y + arch_span*0.5, z + arch_height*0.5), pillar_rad, arch_height, verts=16, mat=mat_stone)
        create_box(f"{prefix}_CapitalR", (x, y + arch_span*0.5, z + arch_height - 0.25), (pillar_rad*2.5, pillar_rad*2.5, 0.5), mat_stone)
        create_box(f"{prefix}_ArchBeam", (x, y, z + arch_height + 0.35), (pillar_rad*2.3, arch_span + pillar_rad*2.2, 0.7), mat_stone)
        create_box(f"{prefix}_Keystone", (x - 0.12, y, z + arch_height + 0.4), (pillar_rad*2.6, 0.7, 0.85), mat_stone)
        create_cylinder(f"{prefix}_Chain", (x - 0.12, y, z + arch_height - 0.35), 0.03, 0.7, verts=6, mat=mat_cc0_iron)
        create_box(f"{prefix}_Lantern", (x - 0.12, y, z + arch_height - 0.8), (0.28, 0.28, 0.45), mat_cc0_iron)
        create_box(f"{prefix}_LanternGlow", (x - 0.12, y, z + arch_height - 0.8), (0.2, 0.2, 0.32), mat_window_glow)
        create_point_light(f"{prefix}_ArchLight", (x - 0.15, y, z + arch_height - 0.8), 140.0, (1.0, 0.75, 0.4), radius=0.4)

    def create_cathedral_spire(prefix, loc, height=13.0, width=4.5, mat_stone=mat_cc0_stone, mat_roof=mat_proc_roof_slate):
        x, y, z = loc
        create_box(f"{prefix}_Tower", (x, y, z + height*0.38), (width, width, height*0.75), mat_stone)
        for dy in (-width*0.5, width*0.5):
            create_box(f"{prefix}_Buttress_{dy}", (x - width*0.32, y + dy, z + height*0.28), (width*0.45, 0.7, height*0.55), mat_stone)
        create_cylinder(f"{prefix}_RoseWin", (x - width*0.5 - 0.06, y, z + height*0.55), 1.2, 0.25, verts=16, mat=mat_window_glow, rot=(0, math.radians(90), 0))
        create_cylinder(f"{prefix}_Spire", (x, y, z + height*0.75 + height*0.22), 0.06, height*0.45, verts=8, mat=mat_roof)
        create_box(f"{prefix}_CrossV", (x, y, z + height + 0.45), (0.12, 0.12, 0.9), mat_proc_brass)
        create_box(f"{prefix}_CrossH", (x, y, z + height + 0.65), (0.12, 0.6, 0.12), mat_proc_brass)

    # 3. Environment Configurations (Attempts 01 - 09)
    # Calibrated ground level: at depth 6.9m, Z = -1.65m places the street road at Screen Y = 192px
    # (lower third of 240px frame) and standing character heads (Z + 1.75m) at Screen Y = 63px (horizon level).
    ground_z = -1.65
    cam_obj = None

    # Sun & Atmosphere Lighting
    create_sun_light("Sun_TwilightRim", 1.4, (0.35, 0.50, 0.85), (0.55, 0.25, 0.75))

    if attempt_id == "01":
        # ATTEMPT 01: Procedural Guildhall Approach (Heavy Procedural Strategy)
        create_box("Road_Cobble", (7.8, 5.5, ground_z - 0.2), (3.8, 14.0, 0.4), mat_proc_cobble)
        create_box("Curb_Front", (5.8, 5.5, ground_z - 0.1), (0.4, 14.0, 0.3), mat_proc_stone)
        create_townhouse("Guildhall_Main", (10.2, 5.8, ground_z), width=4.5, depth=3.2, height=6.2, floors=3,
                         timber=True, mat_stone=mat_proc_stone, mat_plaster=mat_proc_plaster_warm,
                         mat_timber=mat_proc_timber_dark, mat_roof=mat_proc_roof_slate,
                         with_door=True, door_loc=(8.6, 5.8, ground_z), window_rows=2)
        create_townhouse("Shop_Right", (10.0, 10.2, ground_z), width=3.4, depth=2.8, height=4.8, floors=2,
                         timber=True, mat_stone=mat_proc_stone, mat_plaster=mat_proc_plaster_cool,
                         mat_timber=mat_proc_timber_warm, mat_roof=mat_proc_roof_terra,
                         with_door=True, door_loc=(8.6, 10.2, ground_z), window_rows=1)
        create_foreground_arch("Gate_Arch_Left", (6.2, 1.8, ground_z), arch_span=3.2, arch_height=4.8, pillar_rad=0.45, mat_stone=mat_proc_stone)
        create_street_lantern("Street_Lantern_Mid", (7.0, 8.5, ground_z), height=2.8, light_energy=110.0, mat_metal=mat_proc_iron)
        create_cathedral_spire("Background_Spire", (13.5, 2.0, ground_z), height=14.0, width=4.2, mat_stone=mat_proc_stone, mat_roof=mat_proc_roof_slate)

    elif attempt_id == "02":
        # ATTEMPT 02: Merchant Quarter Plaza (Heavy Public CC0 PBR Strategy)
        create_box("Road_Cobble", (7.8, 5.5, ground_z - 0.2), (4.2, 14.0, 0.4), mat_cc0_cobble)
        create_box("Curb_Front", (5.6, 5.5, ground_z - 0.1), (0.4, 14.0, 0.3), mat_cc0_stone)
        create_townhouse("Merchant_HQ", (10.4, 4.5, ground_z), width=4.8, depth=3.4, height=5.8, floors=2,
                         timber=True, mat_stone=mat_cc0_stone, mat_plaster=mat_cc0_plaster,
                         mat_timber=mat_cc0_timber, mat_roof=mat_cc0_roof,
                         with_door=True, door_loc=(8.7, 4.5, ground_z), window_rows=2)
        create_townhouse("Tavern_Right", (10.0, 9.8, ground_z), width=3.8, depth=3.0, height=5.2, floors=2,
                         timber=True, mat_stone=mat_cc0_stone, mat_plaster=mat_cc0_plaster,
                         mat_timber=mat_cc0_timber, mat_roof=mat_cc0_roof,
                         with_door=True, door_loc=(8.5, 9.8, ground_z), window_rows=1)
        create_market_stall("Market_Central", (7.2, 7.8, ground_z), width=2.4, depth=1.4, red_gold=True, mat_wood=mat_cc0_timber)
        create_street_lantern("Lantern_Post_L", (6.6, 2.4, ground_z), height=2.6, light_energy=100.0, mat_metal=mat_cc0_iron)
        create_foreground_arch("Plaza_Gate_R", (6.4, 11.5, ground_z), arch_span=2.8, arch_height=4.4, pillar_rad=0.4, mat_stone=mat_cc0_stone)

    elif attempt_id == "03":
        # ATTEMPT 03: Ancient Gate Street (Heavy AI-Generated PBR Source Strategy)
        create_box("Road_Cobble", (7.8, 5.5, ground_z - 0.2), (3.6, 14.0, 0.4), mat_ai_cobble)
        create_box("Curb_Front", (5.8, 5.5, ground_z - 0.1), (0.4, 14.0, 0.3), mat_ai_stone)
        create_townhouse("Old_Gatehouse_L", (10.2, 3.2, ground_z), width=3.8, depth=3.2, height=6.0, floors=3,
                         timber=True, mat_stone=mat_ai_stone, mat_plaster=mat_ai_plaster,
                         mat_timber=mat_ai_timber, mat_roof=mat_ai_roof,
                         with_door=True, door_loc=(8.6, 3.2, ground_z), window_rows=2)
        create_townhouse("Guard_Post_R", (10.0, 8.2, ground_z), width=4.2, depth=3.0, height=5.4, floors=2,
                         timber=True, mat_stone=mat_ai_stone, mat_plaster=mat_ai_plaster,
                         mat_timber=mat_ai_timber, mat_roof=mat_ai_roof,
                         with_door=True, door_loc=(8.5, 8.2, ground_z), window_rows=1)
        create_foreground_arch("Massive_Gate_Arch", (6.2, 5.5, ground_z), arch_span=3.6, arch_height=5.2, pillar_rad=0.55, mat_stone=mat_ai_stone)
        create_street_lantern("Lantern_L", (6.8, 1.2, ground_z), height=2.7, light_energy=95.0, mat_metal=mat_proc_iron)
        create_street_lantern("Lantern_R", (6.8, 10.2, ground_z), height=2.7, light_energy=95.0, mat_metal=mat_proc_iron)

    elif attempt_id == "04":
        # ATTEMPT 04: Cathedral Alley & Apothecary (Hybrid 1 — Warm/Cool High Contrast)
        create_box("Road_Cobble", (7.8, 5.5, ground_z - 0.2), (3.8, 14.0, 0.4), mat_cc0_cobble)
        create_box("Curb_Front", (5.8, 5.5, ground_z - 0.1), (0.4, 14.0, 0.3), mat_hybrid_facade)
        create_townhouse("Apothecary_Main", (10.2, 7.8, ground_z), width=4.4, depth=3.2, height=5.6, floors=2,
                         timber=True, mat_stone=mat_hybrid_facade, mat_plaster=mat_proc_plaster_warm,
                         mat_timber=mat_cc0_timber, mat_roof=mat_proc_roof_slate,
                         with_door=True, door_loc=(8.6, 7.8, ground_z), window_rows=2)
        create_cathedral_spire("Great_Cathedral", (12.8, 2.5, ground_z), height=15.0, width=5.0, mat_stone=mat_cc0_stone, mat_roof=mat_proc_roof_slate)
        create_foreground_arch("Alley_Arch_L", (6.2, 1.8, ground_z), arch_span=3.0, arch_height=4.6, pillar_rad=0.45, mat_stone=mat_hybrid_facade)
        create_market_stall("Herb_Stall", (7.2, 10.5, ground_z), width=2.0, depth=1.2, red_gold=False, mat_wood=mat_cc0_timber)
        create_street_lantern("Apothecary_Lantern", (6.8, 6.2, ground_z), height=2.6, light_energy=115.0, mat_metal=mat_cc0_iron)

    elif attempt_id == "05":
        # ATTEMPT 05: Riverside Tavern Wharf (Hybrid 2 — Layered Horizontal Rhythm)
        create_box("Wharf_Dock_Cobble", (7.8, 4.5, ground_z - 0.2), (4.2, 11.0, 0.4), mat_cc0_cobble)
        create_box("Water_Negative_Space", (8.5, 12.0, ground_z - 0.8), (6.0, 4.0, 0.2), mat_proc_plaster_cool)
        create_box("Wharf_Wall", (6.0, 5.5, ground_z - 0.4), (0.4, 14.0, 0.8), mat_hybrid_facade)
        create_townhouse("Tavern_Wharf", (10.5, 3.8, ground_z), width=4.8, depth=3.4, height=5.6, floors=2,
                         timber=True, mat_stone=mat_hybrid_facade, mat_plaster=mat_ai_plaster,
                         mat_timber=mat_ai_timber, mat_roof=mat_cc0_roof,
                         with_door=True, door_loc=(8.8, 3.8, ground_z), window_rows=2)
        create_townhouse("Fishmonger", (10.2, 8.2, ground_z), width=3.4, depth=2.8, height=4.6, floors=2,
                         timber=True, mat_stone=mat_cc0_stone, mat_plaster=mat_proc_plaster_warm,
                         mat_timber=mat_cc0_timber, mat_roof=mat_ai_roof,
                         with_door=True, door_loc=(8.8, 8.2, ground_z), window_rows=1)
        create_cylinder("Mooring_Post_1", (6.2, 9.8, ground_z + 0.4), 0.16, 1.2, verts=10, mat=mat_ai_timber)
        create_cylinder("Mooring_Post_2", (6.2, 11.2, ground_z + 0.4), 0.16, 1.2, verts=10, mat=mat_ai_timber)
        create_street_lantern("Wharf_Lantern", (6.6, 2.2, ground_z), height=2.6, light_energy=105.0, mat_metal=mat_cc0_iron)
        create_foreground_arch("Tavern_Corbel_Arch", (6.4, 1.0, ground_z), arch_span=2.6, arch_height=4.5, pillar_rad=0.4, mat_stone=mat_hybrid_facade)

    elif attempt_id == "06":
        # ATTEMPT 06: Sunken Market Colonnade (Hybrid 3 — Deep Foreground Archways)
        create_box("Road_Cobble", (7.8, 5.5, ground_z - 0.2), (4.0, 14.0, 0.4), mat_ai_cobble)
        create_townhouse("Market_North_1", (10.4, 3.5, ground_z), width=4.0, depth=3.2, height=5.8, floors=2,
                         timber=True, mat_stone=mat_hybrid_facade, mat_plaster=mat_cc0_plaster,
                         mat_timber=mat_cc0_timber, mat_roof=mat_cc0_roof,
                         with_door=True, door_loc=(8.8, 3.5, ground_z), window_rows=2)
        create_townhouse("Market_North_2", (10.2, 8.2, ground_z), width=4.4, depth=3.2, height=5.5, floors=2,
                         timber=True, mat_stone=mat_hybrid_facade, mat_plaster=mat_proc_plaster_warm,
                         mat_timber=mat_ai_timber, mat_roof=mat_ai_roof,
                         with_door=True, door_loc=(8.6, 8.2, ground_z), window_rows=1)
        create_market_stall("Colonnade_Stall", (7.2, 5.8, ground_z), width=2.4, depth=1.3, red_gold=True, mat_wood=mat_cc0_timber)
        # 3-Bay Continuous Foreground Colonnade
        for y_col in (1.5, 4.5, 7.5, 10.5):
            create_cylinder(f"Colonnade_Pillar_{y_col}", (5.8, y_col, ground_z + 2.2), 0.35, 4.4, verts=16, mat=mat_hybrid_facade)
            create_box(f"Colonnade_Cap_{y_col}", (5.8, y_col, ground_z + 4.2), (0.9, 0.9, 0.4), mat_hybrid_facade)
        create_box("Colonnade_Entablature", (5.8, 6.0, ground_z + 4.6), (0.85, 11.0, 0.5), mat_hybrid_facade)
        create_street_lantern("Colonnade_Lantern_L", (6.5, 2.8, ground_z), height=2.6, light_energy=100.0, mat_metal=mat_cc0_iron)
        create_street_lantern("Colonnade_Lantern_R", (6.5, 9.2, ground_z), height=2.6, light_energy=100.0, mat_metal=mat_cc0_iron)

    elif attempt_id == "07":
        # CONVERGENCE 07: Refined Guildhall Plaza (High Legibility & Balanced Warm Glow)
        # Responds to critique: rich tactile hybrid stone, clean horizontal walking lane, distinct depth layers
        create_box("Road_Cobble", (7.8, 5.5, ground_z - 0.2), (4.0, 14.0, 0.4), mat_cc0_cobble)
        create_box("Curb_Front", (5.8, 5.5, ground_z - 0.1), (0.35, 14.0, 0.25), mat_hybrid_facade)
        create_townhouse("Guild_Central", (10.4, 5.2, ground_z), width=4.6, depth=3.4, height=6.2, floors=3,
                         timber=True, mat_stone=mat_hybrid_facade, mat_plaster=mat_cc0_plaster,
                         mat_timber=mat_cc0_timber, mat_roof=mat_proc_roof_slate,
                         with_door=True, door_loc=(8.7, 5.2, ground_z), window_rows=2)
        create_townhouse("Merchant_Wing", (10.0, 10.0, ground_z), width=3.8, depth=3.0, height=5.2, floors=2,
                         timber=True, mat_stone=mat_hybrid_facade, mat_plaster=mat_proc_plaster_warm,
                         mat_timber=mat_ai_timber, mat_roof=mat_cc0_roof,
                         with_door=True, door_loc=(8.5, 10.0, ground_z), window_rows=1)
        create_cathedral_spire("Distant_Cathedral", (13.5, 1.8, ground_z), height=14.5, width=4.5, mat_stone=mat_cc0_stone, mat_roof=mat_proc_roof_slate)
        create_foreground_arch("Framing_Arch_L", (6.0, 1.5, ground_z), arch_span=3.0, arch_height=4.8, pillar_rad=0.45, mat_stone=mat_hybrid_facade)
        create_market_stall("Plaza_Stall", (7.2, 8.0, ground_z), width=2.2, depth=1.3, red_gold=True, mat_wood=mat_cc0_timber)
        create_street_lantern("Plaza_Lantern_Main", (6.8, 3.8, ground_z), height=2.7, light_energy=115.0, mat_metal=mat_cc0_iron)

    elif attempt_id == "08":
        # CONVERGENCE 08: Atmospheric Rivergate (Tactile Hybrid + Enhanced Negative Space)
        create_box("Road_Cobble", (7.8, 4.8, ground_z - 0.2), (4.2, 11.5, 0.4), mat_cc0_cobble)
        create_box("River_Negative_Space", (8.5, 12.2, ground_z - 0.7), (6.0, 3.6, 0.2), mat_proc_plaster_cool)
        create_box("River_Quay_Wall", (5.8, 5.0, ground_z - 0.35), (0.4, 12.0, 0.7), mat_hybrid_facade)
        create_townhouse("Rivergate_Tavern", (10.4, 4.2, ground_z), width=4.8, depth=3.4, height=5.8, floors=2,
                         timber=True, mat_stone=mat_hybrid_facade, mat_plaster=mat_cc0_plaster,
                         mat_timber=mat_cc0_timber, mat_roof=mat_cc0_roof,
                         with_door=True, door_loc=(8.7, 4.2, ground_z), window_rows=2)
        create_townhouse("Customs_Office", (10.0, 8.8, ground_z), width=3.6, depth=2.8, height=4.8, floors=2,
                         timber=True, mat_stone=mat_hybrid_facade, mat_plaster=mat_proc_plaster_warm,
                         mat_timber=mat_ai_timber, mat_roof=mat_ai_roof,
                         with_door=True, door_loc=(8.6, 8.8, ground_z), window_rows=1)
        create_foreground_arch("Rivergate_Arch", (6.2, 1.2, ground_z), arch_span=3.0, arch_height=4.8, pillar_rad=0.45, mat_stone=mat_hybrid_facade)
        create_cylinder("Bollard_1", (6.2, 9.8, ground_z + 0.35), 0.16, 1.1, verts=10, mat=mat_ai_timber)
        create_street_lantern("Rivergate_Lantern", (6.7, 6.5, ground_z), height=2.7, light_energy=110.0, mat_metal=mat_cc0_iron)

    elif attempt_id == "09":
        # CONVERGENCE 09: Master Town Center (Thestra Definitive Hybrid Set)
        # Optimal combination: Full Hybrid (Scanned PBR + AI Height Relief + Procedural Moss/Weathering + Theatrical Framing)
        create_box("Road_Cobble", (7.8, 5.5, ground_z - 0.2), (4.2, 14.0, 0.4), mat_cc0_cobble)
        create_box("Curb_Front", (5.6, 5.5, ground_z - 0.1), (0.38, 14.0, 0.28), mat_hybrid_facade)
        
        # Central Great Townhouse & Tavern
        create_townhouse("Master_Townhouse_Center", (10.4, 4.8, ground_z), width=5.0, depth=3.6, height=6.4, floors=3,
                         timber=True, mat_stone=mat_hybrid_facade, mat_plaster=mat_cc0_plaster,
                         mat_timber=mat_cc0_timber, mat_roof=mat_proc_roof_slate,
                         with_door=True, door_loc=(8.6, 4.8, ground_z), window_rows=2)
        
        # Right Merchant Guildhouse
        create_townhouse("Master_Guildhouse_Right", (10.0, 9.8, ground_z), width=4.2, depth=3.2, height=5.4, floors=2,
                         timber=True, mat_stone=mat_hybrid_facade, mat_plaster=mat_proc_plaster_warm,
                         mat_timber=mat_ai_timber, mat_roof=mat_cc0_roof,
                         with_door=True, door_loc=(8.4, 9.8, ground_z), window_rows=2)

        # Background Landmark Spire (Cool blue twilight silhouette)
        create_cathedral_spire("Master_Cathedral_Spire", (13.8, 1.6, ground_z), height=15.5, width=4.8,
                               mat_stone=mat_cc0_stone, mat_roof=mat_proc_roof_slate)

        # Foreground Framing Gate Arch on Left
        create_foreground_arch("Master_Gate_Arch", (6.0, 1.4, ground_z), arch_span=3.2, arch_height=5.0,
                               pillar_rad=0.5, mat_stone=mat_hybrid_facade)

        # Detailed Market Stall with Striped Canopy & Props
        create_market_stall("Master_Plaza_Stall", (7.2, 7.8, ground_z), width=2.4, depth=1.35,
                            red_gold=True, mat_wood=mat_cc0_timber)

        # Street Lanterns (Warm pools of illumination)
        create_street_lantern("Master_Lantern_Left", (6.8, 3.2, ground_z), height=2.8, light_energy=120.0, mat_metal=mat_cc0_iron)
        create_street_lantern("Master_Lantern_Right", (6.8, 11.2, ground_z), height=2.8, light_energy=110.0, mat_metal=mat_cc0_iron)

    # 4. Runtime Geometry in TH_RENDER
    # Simplified coarse watertight collision/render boxes preserving major silhouettes
    create_box("RENDER_Ground", (7.8, 5.5, ground_z - 0.2), (4.2, 14.0, 0.4), col=col_render)
    create_box("RENDER_BuildingBlock_L", (10.4, 4.5, ground_z + 3.0), (3.6, 5.2, 6.0), col=col_render)
    create_box("RENDER_BuildingBlock_R", (10.0, 9.8, ground_z + 2.6), (3.2, 4.4, 5.2), col=col_render)
    create_box("RENDER_ForegroundArch", (6.0, 1.4, ground_z + 2.5), (1.2, 4.0, 5.0), col=col_render)

    # 5. Collision in TH_COLLISION
    create_box("COL_GroundFloor", (7.8, 5.5, ground_z - 0.1), (3.8, 14.0, 0.2), col=col_collision)
    create_box("COL_WallBackdrop", (10.2, 5.5, ground_z + 3.0), (1.0, 14.0, 6.0), col=col_collision)
    create_box("COL_ArchLeft", (6.0, 1.4, ground_z + 2.5), (1.0, 3.8, 5.0), col=col_collision)

    # 6. Anchors in TH_ANCHORS
    def create_anchor(name, loc, yaw=0.0):
        empty = bpy.data.objects.new(name, None)
        empty.location = loc
        empty.rotation_euler = (0, 0, math.radians(yaw))
        empty.empty_display_size = 0.5
        empty.empty_display_type = 'ARROWS'
        return link_obj(empty, col_anchors)

    create_anchor("ANCHOR_Spawn_Default", (7.8, 5.5, ground_z), yaw=0.0)
    create_anchor("ANCHOR_Door_Guild", (8.6, 4.8, ground_z), yaw=180.0)
    create_anchor("ANCHOR_Market_Stall", (7.2, 7.8, ground_z), yaw=90.0)
    create_anchor("ANCHOR_Gate_Exit_Left", (7.8, 1.5, ground_z), yaw=270.0)
    create_anchor("ANCHOR_Road_Exit_Right", (7.8, 11.5, ground_z), yaw=90.0)

    # 7. Setup Camera
    rec = dict(CALIBRATION_RECORD)
    cam_obj = thestra_camera.create_or_update_camera(rec, scene=scene, make_active=True)

    # 8. Setup Preview Actors in TH_PREVIEW_ACTORS
    # Protagonist stand-in (Frame 0: idle stance)
    thestra_camera.create_actor_preview(
        str(WALKER_PATH), cam_obj,
        anchor=(7.8, 5.5, ground_z),
        frame_width=24, frame_height=48, frame_index=0,
        world_height=1.75, name="ACTOR_Protagonist"
    )
    # NPC 1: Merchant by stall (Frame 1)
    thestra_camera.create_actor_preview(
        str(WALKER_PATH), cam_obj,
        anchor=(8.0, 7.8, ground_z),
        frame_width=24, frame_height=48, frame_index=1,
        world_height=1.75, name="ACTOR_NPC_Merchant"
    )
    # NPC 2: Gate Guard by arch (Frame 2)
    thestra_camera.create_actor_preview(
        str(WALKER_PATH), cam_obj,
        anchor=(7.6, 3.2, ground_z),
        frame_width=24, frame_height=48, frame_index=2,
        world_height=1.75, name="ACTOR_NPC_Guard"
    )
    # NPC 3: Citizen (Frame 4)
    thestra_camera.create_actor_preview(
        str(WALKER_PATH), cam_obj,
        anchor=(8.0, 10.2, ground_z),
        frame_width=24, frame_height=48, frame_index=4,
        world_height=1.75, name="ACTOR_NPC_Citizen"
    )

    for actor_name in ["ACTOR_Protagonist", "ACTOR_NPC_Merchant", "ACTOR_NPC_Guard", "ACTOR_NPC_Citizen"]:
        act_obj = bpy.data.objects.get(actor_name)
        if act_obj:
            if act_obj.name in root_col.objects:
                root_col.objects.unlink(act_obj)
            if act_obj.name not in col_preview_actors.objects:
                col_preview_actors.objects.link(act_obj)

    # 9. Visual Guide in TH_PREVIEW_ONLY
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=10.0, location=(8.5, 5.5, ground_z + 0.01))
    grid_guide = bpy.context.active_object
    grid_guide.name = "GUIDE_GroundGrid"
    link_obj(grid_guide, col_preview_only)

    if blend_output:
        blend_output = Path(blend_output).resolve()
        blend_output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_output))
        print(f"[builder_v2] Saved {attempt_id} to {blend_output}")


def render_attempt(attempt_id: str, output_png: Path, projection_offset_x: float = 0.0, samples: int = 64):
    import bpy
    sys.path.insert(0, str(ROOT / "tools" / "blender"))
    import thestra_camera

    build_scene(attempt_id)
    scene = bpy.context.scene
    scene.cycles.samples = samples

    rec = dict(CALIBRATION_RECORD)
    rec["projectionWindowOffsetX"] = projection_offset_x
    cam_obj = thestra_camera.create_or_update_camera(rec, scene=scene, make_active=True)

    output_png = Path(output_png).resolve()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(output_png)
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    print(f"[builder_v2] Rendering attempt {attempt_id} (offset_x={projection_offset_x}) to {output_png}...")
    bpy.ops.render.render(write_still=True)
    print(f"[builder_v2] Render complete: {output_png}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Town Gauntlet V2 Scene Builder & Renderer")
    parser.add_argument("attempt", help="Attempt ID (01-09)")
    parser.add_argument("--blend", "-b", default=None, help="Save output .blend path")
    parser.add_argument("--render", "-r", default=None, help="Render output PNG path")
    parser.add_argument("--offset-x", type=float, default=0.0, help="Projection window offset X in pixels")
    parser.add_argument("--samples", type=int, default=64, help="Cycles render samples")
    
    if "--" in sys.argv:
        args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    else:
        args = parser.parse_args()

    if args.render:
        render_attempt(args.attempt, Path(args.render), projection_offset_x=args.offset_x, samples=args.samples)
    elif args.blend:
        build_scene(args.attempt, Path(args.blend))
    else:
        build_scene(args.attempt)
    sys.exit(0)


if __name__ == "__main__":
    main()
