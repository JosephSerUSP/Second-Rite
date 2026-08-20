"""Town Scene Gauntlet Builder for Second Rite (V0).

Authors rich 3D town environments in Blender matching the late-90s Square Enix
pre-rendered CG aesthetic (Vagrant Story / FFIX style), with:
- TH_SOURCE: detailed architectural geometry, lighting, materials, and props
- TH_RENDER: coarse triangulated runtime-facing geometry with UVs for atlas baking
- TH_COLLISION: simplified collision boxes/ramps
- TH_ANCHORS: named spatial markers with orientation
- TH_PREVIEW_ACTORS: unlit/emissive nearest-filtered billboard planes using walker.png
- TH_PREVIEW_ONLY: visual guides
- TH_CAMERA_PREVIEW: Thestra-calibrated camera at 426x240 (perspective, 30 deg pitch)
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

# Thestra WorldCamera calibration record for 426x240 Wide / 30 deg pitch
CALIBRATION_RECORD = {
    "contract": "thestra.world-camera-calibration",
    "version": 1,
    "projection": "perspective",
    "eye": {
        "x": 5.5,
        "y": 5.5,
        "z": 0.5
    },
    "orientation": {
        "forwardX": 1.0,
        "forwardY": 0.0,
        "rightX": 0.0,
        "rightY": 1.0,
        "pitchRadians": 0.5235987755982988
    },
    "projectionScale": {
        "x": 1.0,
        "y": 1.0
    },
    "fovHalfX": 0.75,
    "fovHalfY": 0.421875,
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

    # World background: atmospheric deep twilight gradient
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.06, 0.08, 0.16, 1.0)
        bg_node.inputs["Strength"].default_value = 0.6

    # Cycles setup
    scene.render.engine = 'CYCLES'
    try:
        scene.cycles.device = 'CPU'
    except Exception:
        pass
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.film_transparent = False

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

    # 2. Material Library Creation
    def make_material(name, base_color, roughness=0.8, metallic=0.0, emission=None, emission_strength=1.0):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*base_color, 1.0) if len(base_color) == 3 else base_color
            bsdf.inputs["Roughness"].default_value = roughness
            bsdf.inputs["Metallic"].default_value = metallic
            if emission:
                if "Emission Color" in bsdf.inputs:
                    bsdf.inputs["Emission Color"].default_value = (*emission, 1.0) if len(emission) == 3 else emission
                    bsdf.inputs["Emission Strength"].default_value = emission_strength
                elif "Emission" in bsdf.inputs:
                    bsdf.inputs["Emission"].default_value = (*emission, 1.0) if len(emission) == 3 else emission
        return mat

    # Late 90s Square Enix / Vagrant Story / FFIX palette
    mat_stone_dark = make_material("StoneDark", (0.24, 0.22, 0.20), roughness=0.9)
    mat_stone_light = make_material("StoneLight", (0.62, 0.58, 0.50), roughness=0.8)
    mat_cobble = make_material("Cobblestone", (0.32, 0.30, 0.28), roughness=0.85)
    mat_curb = make_material("StoneCurb", (0.45, 0.42, 0.38), roughness=0.8)
    mat_plaster_warm = make_material("WarmPlaster", (0.72, 0.65, 0.54), roughness=0.95)
    mat_plaster_cool = make_material("CoolPlaster", (0.48, 0.52, 0.56), roughness=0.95)
    mat_timber_dark = make_material("DarkTimber", (0.16, 0.10, 0.06), roughness=0.75)
    mat_timber_warm = make_material("WarmTimber", (0.34, 0.20, 0.12), roughness=0.7)
    mat_slate_roof = make_material("SlateRoof", (0.16, 0.18, 0.24), roughness=0.6)
    mat_terracotta_roof = make_material("TerracottaRoof", (0.58, 0.24, 0.14), roughness=0.75)
    mat_iron = make_material("WroughtIron", (0.10, 0.10, 0.12), roughness=0.4, metallic=0.9)
    mat_brass = make_material("AgedBrass", (0.78, 0.60, 0.22), roughness=0.35, metallic=0.85)
    mat_cloth_red = make_material("CanopyRed", (0.68, 0.14, 0.12), roughness=0.9)
    mat_cloth_gold = make_material("CanopyGold", (0.82, 0.65, 0.18), roughness=0.9)
    mat_cloth_blue = make_material("CanopyBlue", (0.18, 0.32, 0.55), roughness=0.9)
    mat_window_glow = make_material("WindowGlowWarm", (1.0, 0.82, 0.45), roughness=0.2, emission=(1.0, 0.78, 0.38), emission_strength=5.0)
    mat_door_oak = make_material("DoorOak", (0.24, 0.14, 0.08), roughness=0.65)
    mat_sky_backdrop = make_material("SkyBackdrop", (0.12, 0.16, 0.30), roughness=1.0, emission=(0.14, 0.18, 0.35), emission_strength=1.0)

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
        bpy.ops.object.light_add(type='SUN', location=(10, -5, 12))
        sun = bpy.context.active_object
        sun.name = name
        sun.data.energy = energy
        sun.data.color = color
        sun.rotation_euler = rot
        return link_obj(sun, col_source)

    # Architectural building block: Detailed Facade
    def create_townhouse(prefix, loc, width, depth, height, floors=2, timber=True, roof_type='slate', plaster_mat=mat_plaster_warm, with_door=False, door_loc=(0,0,0), window_rows=1):
        x, y, z = loc
        # Foundation stone base
        create_box(f"{prefix}_Base", (x, y, z + 0.6), (depth, width, 1.2), mat_stone_dark)
        # Upper stories
        create_box(f"{prefix}_Plaster", (x, y, z + 0.6 + height * 0.5), (depth, width, height), plaster_mat)
        
        # Timber framing
        if timber:
            beam_t = 0.14
            for dy in (-width*0.5 + beam_t*0.5, width*0.5 - beam_t*0.5, 0):
                create_box(f"{prefix}_BeamV_{dy}", (x - depth*0.5 - 0.03, y + dy, z + 0.6 + height*0.5), (0.1, beam_t, height + 1.2), mat_timber_dark)
            for f in range(1, floors + 1):
                fz = z + f * (height / floors)
                create_box(f"{prefix}_BeamH_{f}", (x - depth*0.5 - 0.05, y, fz), (0.14, width + 0.15, 0.18), mat_timber_dark)
                for cy in (-width*0.35, 0, width*0.35):
                    create_box(f"{prefix}_Corbel_{f}_{cy}", (x - depth*0.5 - 0.18, y + cy, fz - 0.16), (0.35, 0.16, 0.22), mat_timber_warm)

        # Windows with glow
        win_w = 0.55
        win_h = 0.8
        for r in range(window_rows):
            wz = z + 1.8 + r * 1.5
            for wy in (-width*0.28, width*0.28):
                create_box(f"{prefix}_WinFrame_{r}_{wy}", (x - depth*0.5 - 0.04, y + wy, wz), (0.1, win_w + 0.12, win_h + 0.12), mat_timber_dark)
                create_box(f"{prefix}_WinGlass_{r}_{wy}", (x - depth*0.5 - 0.02, y + wy, wz), (0.05, win_w, win_h), mat_window_glow)
                create_box(f"{prefix}_WinSill_{r}_{wy}", (x - depth*0.5 - 0.1, y + wy, wz - win_h*0.5 - 0.06), (0.18, win_w + 0.25, 0.1), mat_stone_light)
                # Small window light glow spill
                create_point_light(f"{prefix}_WinSpill_{r}_{wy}", (x - depth*0.5 - 0.4, y + wy, wz), 25.0, (1.0, 0.78, 0.4), radius=0.2)

        # Roof
        roof_mat = mat_slate_roof if roof_type == 'slate' else mat_terracotta_roof
        roof_h = 1.8
        create_box(f"{prefix}_RoofBase", (x + 0.2, y, z + height + roof_h*0.45), (depth + 0.8, width + 0.5, roof_h), roof_mat)
        create_box(f"{prefix}_Chimney", (x + depth*0.2, y + width*0.25, z + height + roof_h + 0.5), (0.65, 0.65, 1.4), mat_stone_dark)
        create_box(f"{prefix}_ChimneyCap", (x + depth*0.2, y + width*0.25, z + height + roof_h + 1.25), (0.8, 0.8, 0.18), mat_stone_light)

        # Arched doorway if specified
        if with_door:
            dx, dy, dz = door_loc
            create_box(f"{prefix}_DoorArchL", (dx - 0.05, dy - 0.55, dz + 1.0), (0.25, 0.25, 2.0), mat_stone_light)
            create_box(f"{prefix}_DoorArchR", (dx - 0.05, dy + 0.55, dz + 1.0), (0.25, 0.25, 2.0), mat_stone_light)
            create_box(f"{prefix}_DoorArchTop", (dx - 0.05, dy, dz + 2.1), (0.25, 1.35, 0.3), mat_stone_light)
            create_box(f"{prefix}_DoorPanel", (dx + 0.06, dy, dz + 1.0), (0.1, 0.95, 1.9), mat_door_oak)
            create_box(f"{prefix}_DoorStep1", (dx - 0.3, dy, dz + 0.15), (0.5, 1.5, 0.25), mat_stone_light)
            create_box(f"{prefix}_DoorStep2", (dx - 0.6, dy, dz - 0.05), (0.5, 1.8, 0.25), mat_cobble)
            create_box(f"{prefix}_DoorLanternBody", (dx - 0.35, dy + 0.75, dz + 2.0), (0.18, 0.18, 0.35), mat_brass)
            create_box(f"{prefix}_DoorLanternGlow", (dx - 0.35, dy + 0.75, dz + 2.0), (0.12, 0.12, 0.22), mat_window_glow)
            create_point_light(f"{prefix}_DoorLight", (dx - 0.5, dy + 0.75, dz + 2.0), 75.0, (1.0, 0.76, 0.42), radius=0.3)

    # Street Lantern post builder
    def create_street_lantern(prefix, loc, height=2.6, light_energy=85.0):
        x, y, z = loc
        create_cylinder(f"{prefix}_Base", (x, y, z + 0.25), 0.22, 0.5, verts=12, mat=mat_iron)
        create_cylinder(f"{prefix}_Post", (x, y, z + height*0.5), 0.08, height, verts=8, mat=mat_iron)
        create_box(f"{prefix}_Bracket", (x, y, z + height), (0.35, 0.1, 0.25), mat_iron)
        create_box(f"{prefix}_LanternHousing", (x, y, z + height - 0.12), (0.24, 0.24, 0.4), mat_brass)
        create_box(f"{prefix}_LanternGlass", (x, y, z + height - 0.12), (0.16, 0.16, 0.28), mat_window_glow)
        create_point_light(f"{prefix}_Light", (x, y, z + height - 0.12), light_energy, (1.0, 0.78, 0.45), radius=0.35)

    # Market stall builder
    def create_market_stall(prefix, loc, width=2.2, depth=1.3, red_gold=True):
        x, y, z = loc
        create_box(f"{prefix}_TableTop", (x, y, z + 0.75), (depth, width, 0.12), mat_timber_warm)
        for dx in (-depth*0.42, depth*0.42):
            for dy in (-width*0.42, width*0.42):
                create_box(f"{prefix}_Leg_{dx}_{dy}", (x + dx, y + dy, z + 0.38), (0.1, 0.1, 0.75), mat_timber_dark)
                create_box(f"{prefix}_Pole_{dx}_{dy}", (x + dx, y + dy, z + 1.45), (0.06, 0.06, 1.45), mat_timber_dark)
        c_mat1 = mat_cloth_red if red_gold else mat_cloth_blue
        c_mat2 = mat_cloth_gold if red_gold else mat_plaster_warm
        for s in range(5):
            sy = y - width*0.4 + s * (width * 0.2)
            c_mat = c_mat1 if s % 2 == 0 else c_mat2
            create_box(f"{prefix}_CanopyStripe_{s}", (x, sy, z + 2.25), (depth + 0.35, width*0.2, 0.14), c_mat)
        # Props
        create_cylinder(f"{prefix}_Barrel1", (x - 0.25, y + width*0.5 + 0.35, z + 0.48), 0.28, 0.95, verts=12, mat=mat_timber_dark)
        create_cylinder(f"{prefix}_Barrel2", (x + 0.25, y + width*0.5 + 0.45, z + 0.38), 0.24, 0.75, verts=12, mat=mat_timber_warm)
        create_box(f"{prefix}_Crate1", (x - 0.15, y - width*0.5 - 0.4, z + 0.32), (0.55, 0.55, 0.65), mat_timber_warm)
        create_cylinder(f"{prefix}_Pot1", (x, y - 0.45, z + 0.9), 0.09, 0.22, verts=8, mat=mat_brass)
        create_cylinder(f"{prefix}_Pot2", (x + 0.25, y + 0.25, z + 0.9), 0.07, 0.28, verts=8, mat=mat_window_glow)

    # Foreground Occluder Archway / Pillar builder
    def create_foreground_arch(prefix, loc, arch_span=3.4, arch_height=4.6, pillar_rad=0.5):
        x, y, z = loc
        create_cylinder(f"{prefix}_PillarL", (x, y - arch_span*0.5, z + arch_height*0.5), pillar_rad, arch_height, verts=16, mat=mat_stone_dark)
        create_box(f"{prefix}_CapitalL", (x, y - arch_span*0.5, z + arch_height - 0.25), (pillar_rad*2.5, pillar_rad*2.5, 0.5), mat_stone_light)
        create_cylinder(f"{prefix}_PillarR", (x, y + arch_span*0.5, z + arch_height*0.5), pillar_rad, arch_height, verts=16, mat=mat_stone_dark)
        create_box(f"{prefix}_CapitalR", (x, y + arch_span*0.5, z + arch_height - 0.25), (pillar_rad*2.5, pillar_rad*2.5, 0.5), mat_stone_light)
        create_box(f"{prefix}_ArchBeam", (x, y, z + arch_height + 0.35), (pillar_rad*2.3, arch_span + pillar_rad*2.2, 0.7), mat_stone_dark)
        create_box(f"{prefix}_Keystone", (x - 0.12, y, z + arch_height + 0.4), (pillar_rad*2.6, 0.7, 0.85), mat_stone_light)
        create_cylinder(f"{prefix}_Chain", (x - 0.12, y, z + arch_height - 0.35), 0.03, 0.7, verts=6, mat=mat_iron)
        create_box(f"{prefix}_Lantern", (x - 0.12, y, z + arch_height - 0.8), (0.28, 0.28, 0.45), mat_iron)
        create_box(f"{prefix}_LanternGlow", (x - 0.12, y, z + arch_height - 0.8), (0.2, 0.2, 0.32), mat_window_glow)
        create_point_light(f"{prefix}_ArchLight", (x - 0.15, y, z + arch_height - 0.8), 120.0, (1.0, 0.75, 0.4), radius=0.4)

    # Cathedral Spire / Background landmark builder
    def create_cathedral_spire(prefix, loc, height=13.0, width=4.5):
        x, y, z = loc
        create_box(f"{prefix}_Tower", (x, y, z + height*0.38), (width, width, height*0.75), mat_stone_dark)
        for dy in (-width*0.5, width*0.5):
            create_box(f"{prefix}_Buttress_{dy}", (x - width*0.32, y + dy, z + height*0.28), (width*0.45, 0.7, height*0.55), mat_stone_light)
        create_cylinder(f"{prefix}_RoseWin", (x - width*0.5 - 0.06, y, z + height*0.55), 1.2, 0.25, verts=16, mat=mat_window_glow, rot=(0, math.radians(90), 0))
        create_cylinder(f"{prefix}_Spire", (x, y, z + height*0.75 + height*0.22), 0.06, height*0.45, verts=8, mat=mat_slate_roof)
        create_box(f"{prefix}_CrossV", (x, y, z + height + 0.45), (0.12, 0.12, 0.9), mat_brass)
        create_box(f"{prefix}_CrossH", (x, y, z + height + 0.65), (0.12, 0.6, 0.12), mat_brass)

    # 4. Attempt-specific Scene Configurations (01 - 09)
    ground_z = -1.5

    # Base Cobblestone Street & Sidewalk across all variations
    create_box("SRC_MainStreet", (8.5, 5.5, ground_z - 0.1), (5.5, 22.0, 0.2), mat_cobble)
    create_box("SRC_CurbStone", (6.5, 5.5, ground_z + 0.05), (0.35, 22.0, 0.15), mat_curb)
    create_box("SRC_SkyBackdrop", (24.0, 5.5, 4.5), (0.2, 32.0, 18.0), mat_sky_backdrop)

    # Setup specific attempt geometry
    if attempt_id == "01":  # The Old Gate Alley (Dense, Romanesque arch, narrow alley)
        create_sun_light("Sun_Dusk", 2.2, (0.75, 0.8, 0.98), (math.radians(50), math.radians(15), math.radians(-40)))
        create_foreground_arch("FG_GateArch", (6.4, 2.0, ground_z), arch_span=3.4, arch_height=4.2, pillar_rad=0.48)
        create_townhouse("TH_AlleyL", (10.6, 1.0, ground_z), width=3.4, depth=3.0, height=4.8, floors=2, timber=True, roof_type='slate', with_door=True, door_loc=(9.0, 1.8, ground_z))
        create_townhouse("TH_AlleyCenter", (11.0, 5.5, ground_z), width=4.5, depth=3.2, height=5.5, floors=3, timber=True, roof_type='slate', with_door=True, door_loc=(9.3, 5.0, ground_z), window_rows=2)
        create_townhouse("TH_AlleyR", (10.6, 9.8, ground_z), width=4.0, depth=3.0, height=4.5, floors=2, timber=True, roof_type='terracotta', with_door=False)
        create_market_stall("Stall_R", (8.8, 8.2, ground_z), width=2.0, depth=1.1, red_gold=True)
        create_street_lantern("Lantern_R", (7.6, 7.0, ground_z), height=2.4, light_energy=80.0)

    elif attempt_id == "02":  # Cathedral Plaza (Open horizontal, background spire, fountain)
        create_sun_light("Sun_Moonlit", 1.8, (0.65, 0.75, 0.95), (math.radians(45), math.radians(20), math.radians(-30)))
        create_street_lantern("FG_LanternR", (6.4, 8.5, ground_z), height=2.8, light_energy=90.0)
        create_cathedral_spire("BG_Cathedral", (15.5, 4.5, ground_z), height=12.0, width=4.8)
        create_townhouse("TH_ChapelL", (11.5, 1.2, ground_z), width=4.2, depth=3.5, height=5.2, floors=2, timber=False, plaster_mat=mat_stone_light, roof_type='slate', with_door=True, door_loc=(9.6, 1.8, ground_z))
        create_townhouse("TH_InnR", (11.2, 9.5, ground_z), width=4.8, depth=3.2, height=5.0, floors=2, timber=True, roof_type='slate', with_door=True, door_loc=(9.5, 8.2, ground_z))
        create_cylinder("Fountain_Basin", (9.2, 5.5, ground_z + 0.35), 1.2, 0.7, verts=16, mat=mat_stone_dark)
        create_cylinder("Fountain_Spire", (9.2, 5.5, ground_z + 0.9), 0.28, 1.1, verts=8, mat=mat_stone_light)
        create_point_light("Fountain_Glow", (9.2, 5.5, ground_z + 1.3), 50.0, (0.85, 0.92, 1.0), radius=0.45)

    elif attempt_id == "03":  # Merchant Way (Canopy Row, warm golden hour, vibrant market)
        create_sun_light("Sun_Golden", 3.0, (1.0, 0.88, 0.65), (math.radians(40), math.radians(10), math.radians(-55)))
        create_box("FG_AwningR", (6.6, 8.8, ground_z + 2.4), (1.5, 2.2, 0.16), mat_cloth_red)
        create_box("FG_AwningPole", (6.6, 7.7, ground_z + 1.2), (0.09, 0.09, 2.4), mat_timber_dark)
        create_cylinder("FG_PillarL", (6.4, 2.2, ground_z + 2.0), 0.38, 4.0, verts=12, mat=mat_stone_dark)
        create_townhouse("TH_ShopL", (10.5, 1.5, ground_z), width=3.6, depth=2.8, height=4.5, floors=2, timber=True, roof_type='terracotta', with_door=True, door_loc=(9.0, 2.2, ground_z))
        create_townhouse("TH_GuildCenter", (10.8, 5.5, ground_z), width=4.2, depth=3.0, height=5.4, floors=3, timber=True, roof_type='slate', with_door=True, door_loc=(9.2, 5.5, ground_z), window_rows=2)
        create_townhouse("TH_ShopR", (10.5, 9.8, ground_z), width=4.0, depth=2.8, height=4.6, floors=2, timber=True, roof_type='terracotta', with_door=False)
        create_market_stall("Stall_1", (8.8, 3.8, ground_z), width=2.2, depth=1.1, red_gold=True)
        create_market_stall("Stall_2", (8.8, 7.2, ground_z), width=2.4, depth=1.2, red_gold=False)
        create_street_lantern("Lantern_Center", (8.0, 5.5, ground_z), height=2.6, light_energy=75.0)

    elif attempt_id == "04":  # The Sunken Wharf Road (Tiered promenade, bridge, cool indigo)
        create_sun_light("Sun_Indigo", 1.8, (0.55, 0.65, 0.95), (math.radians(55), math.radians(25), math.radians(-30)))
        create_box("FG_PromenadeBalustrade", (6.4, 2.2, ground_z + 1.8), (0.45, 2.8, 0.9), mat_stone_light)
        create_cylinder("FG_PromenadeCol", (6.4, 1.2, ground_z + 2.2), 0.38, 4.4, verts=12, mat=mat_stone_dark)
        create_box("Mid_BridgeArch", (10.8, 5.5, ground_z + 3.4), (1.6, 3.4, 0.7), mat_stone_dark)
        create_townhouse("TH_WharfL", (10.6, 1.2, ground_z), width=4.0, depth=3.0, height=5.8, floors=3, timber=True, roof_type='slate', with_door=True, door_loc=(9.1, 2.5, ground_z))
        create_townhouse("TH_WharfR", (10.6, 9.5, ground_z), width=4.2, depth=3.0, height=5.5, floors=3, timber=True, roof_type='slate', with_door=True, door_loc=(9.1, 8.5, ground_z))
        create_box("Retaining_Wall", (10.0, 5.5, ground_z + 1.1), (0.7, 3.8, 2.2), mat_stone_dark)
        create_box("Cellar_Door", (9.6, 5.5, ground_z + 0.8), (0.12, 1.2, 1.6), mat_door_oak)
        create_point_light("WharfTorch1", (8.5, 3.8, ground_z + 1.4), 85.0, (1.0, 0.68, 0.32), radius=0.35)
        create_point_light("WharfTorch2", (8.5, 7.2, ground_z + 1.4), 85.0, (1.0, 0.68, 0.32), radius=0.35)

    elif attempt_id == "05":  # The Rusty Anchor Tavern Crossroads (Corner tavern, diagonal massing, amber glow)
        create_sun_light("Sun_DuskWarm", 2.4, (0.9, 0.78, 0.7), (math.radians(45), math.radians(15), math.radians(-45)))
        create_box("FG_TavernSignBracket", (6.4, 7.8, ground_z + 3.0), (0.12, 0.9, 0.12), mat_iron)
        create_box("FG_TavernSignBoard", (6.4, 7.8, ground_z + 2.45), (0.06, 0.65, 0.55), mat_timber_dark)
        create_street_lantern("FG_CrossroadLantern", (6.4, 2.5, ground_z), height=2.6, light_energy=90.0)
        create_townhouse("TH_TavernMain", (10.8, 5.5, ground_z), width=5.2, depth=3.8, height=5.8, floors=3, timber=True, roof_type='slate', with_door=True, door_loc=(8.9, 5.5, ground_z), window_rows=2)
        create_townhouse("TH_SideL", (10.4, 1.0, ground_z), width=3.6, depth=2.8, height=4.5, floors=2, timber=True, roof_type='terracotta', with_door=False)
        create_townhouse("TH_SideR", (10.4, 10.0, ground_z), width=3.8, depth=2.8, height=4.6, floors=2, timber=True, roof_type='terracotta', with_door=False)
        create_box("TavernPorch", (8.5, 5.5, ground_z + 0.18), (0.9, 2.4, 0.35), mat_timber_warm)
        create_cylinder("AleBarrel1", (8.2, 4.2, ground_z + 0.5), 0.3, 0.95, verts=12, mat=mat_timber_dark)
        create_cylinder("AleBarrel2", (8.2, 6.8, ground_z + 0.42), 0.26, 0.85, verts=12, mat=mat_timber_dark)

    elif attempt_id == "06":  # The Watchtower Promenade (Fortified ashlar, portcullis gate, sunset)
        create_sun_light("Sun_SunsetCrimson", 2.6, (1.0, 0.65, 0.45), (math.radians(35), math.radians(5), math.radians(-70)))
        create_foreground_arch("FG_FortArch", (6.3, 2.0, ground_z), arch_span=3.2, arch_height=4.4, pillar_rad=0.58)
        create_cylinder("Tower_Base", (11.2, 9.2, ground_z + 4.2), 2.4, 8.5, verts=16, mat=mat_stone_dark)
        create_box("Tower_Crenels", (11.2, 9.2, ground_z + 8.6), (5.0, 5.0, 0.65), mat_stone_light)
        create_cylinder("Tower_Roof", (11.2, 9.2, ground_z + 10.0), 0.1, 2.8, verts=8, mat=mat_slate_roof)
        create_box("GarrisonWall", (11.0, 4.5, ground_z + 2.8), (2.2, 6.5, 5.5), mat_stone_dark)
        create_box("GarrisonDoorArch", (9.8, 4.5, ground_z + 1.3), (0.35, 1.8, 2.6), mat_stone_light)
        create_box("GarrisonDoorPanel", (9.9, 4.5, ground_z + 1.2), (0.12, 1.4, 2.2), mat_iron)
        create_point_light("GateTorch", (8.6, 3.5, ground_z + 2.0), 95.0, (1.0, 0.72, 0.35), radius=0.4)

    # 5. Convergence Attempts (07 - 09) - Refined syntheses fixing weaknesses
    elif attempt_id == "07":  # Refined Merchant Archway (Synthesis of 01 + 03: dramatic arch framing + clear traversal & doorway)
        create_sun_light("Sun_WarmDusk", 2.6, (0.98, 0.84, 0.68), (math.radians(45), math.radians(12), math.radians(-50)))
        create_foreground_arch("FG_MerchantArch", (6.4, 1.8, ground_z), arch_span=3.6, arch_height=4.4, pillar_rad=0.5)
        create_street_lantern("FG_StreetlampR", (6.4, 9.2, ground_z), height=2.6, light_energy=85.0)
        create_townhouse("TH_ApothecaryL", (10.6, 1.5, ground_z), width=3.6, depth=2.8, height=4.8, floors=2, timber=True, roof_type='slate', with_door=False)
        create_townhouse("TH_GuildHallCenter", (10.8, 5.5, ground_z), width=4.8, depth=3.4, height=5.6, floors=3, timber=True, roof_type='slate', with_door=True, door_loc=(9.0, 5.2, ground_z), window_rows=2)
        create_townhouse("TH_BakehouseR", (10.6, 9.8, ground_z), width=3.8, depth=2.8, height=4.6, floors=2, timber=True, roof_type='terracotta', with_door=False)
        create_market_stall("Stall_Refined", (8.8, 7.8, ground_z), width=2.2, depth=1.1, red_gold=True)
        create_box("BG_AqueductArch", (16.5, 5.5, ground_z + 4.2), (0.9, 15.0, 1.3), mat_stone_light)
        for ay in (-4.5, 0.0, 4.5):
            create_cylinder(f"BG_AqueductPillar_{ay}", (16.5, 5.5 + ay, ground_z + 2.1), 0.65, 4.2, verts=12, mat=mat_stone_dark)

    elif attempt_id == "08":  # Grand Spire Promenade (Synthesis of 02 + 05: Cathedral spire depth + rich tavern crossroad)
        create_sun_light("Sun_TwilightRim", 2.2, (0.72, 0.80, 0.98), (math.radians(48), math.radians(18), math.radians(-35)))
        create_street_lantern("FG_PromenadeLampL", (6.4, 2.2, ground_z), height=2.7, light_energy=90.0)
        create_box("FG_TavernSignBracket", (6.4, 8.2, ground_z + 2.9), (0.12, 0.8, 0.12), mat_iron)
        create_box("FG_TavernSignBoard", (6.4, 8.2, ground_z + 2.35), (0.06, 0.6, 0.5), mat_timber_dark)
        create_cathedral_spire("BG_CathedralSpire", (16.5, 3.5, ground_z), height=12.5, width=4.5)
        create_townhouse("TH_InnLeft", (10.8, 1.2, ground_z), width=4.0, depth=3.2, height=5.0, floors=2, timber=True, roof_type='slate', with_door=False)
        create_townhouse("TH_CentralTavern", (11.0, 5.8, ground_z), width=5.2, depth=3.6, height=5.8, floors=3, timber=True, roof_type='slate', with_door=True, door_loc=(9.1, 5.5, ground_z), window_rows=2)
        create_townhouse("TH_TownhouseR", (10.7, 10.2, ground_z), width=4.0, depth=3.2, height=4.8, floors=2, timber=True, roof_type='terracotta', with_door=False)
        create_cylinder("WineBarrelCluster1", (8.4, 4.2, ground_z + 0.48), 0.3, 0.95, verts=12, mat=mat_timber_dark)
        create_cylinder("WineBarrelCluster2", (8.4, 7.5, ground_z + 0.42), 0.26, 0.85, verts=12, mat=mat_timber_warm)
        create_box("StoneBench", (8.5, 2.5, ground_z + 0.32), (0.55, 1.5, 0.42), mat_stone_light)

    elif attempt_id == "09":  # The Definitive Bellroot Quarter (Master synthesis: arch occluder, cathedral skyline, rich tavern portal, perfect traversal)
        create_sun_light("Sun_DuskMaster", 2.6, (0.95, 0.82, 0.70), (math.radians(46), math.radians(14), math.radians(-48)))
        create_foreground_arch("FG_BellrootArch", (6.4, 1.8, ground_z), arch_span=3.4, arch_height=4.5, pillar_rad=0.52)
        create_street_lantern("FG_BellrootLampR", (6.4, 9.4, ground_z), height=2.7, light_energy=90.0)
        create_cathedral_spire("BG_Spire", (17.0, 3.5, ground_z), height=12.5, width=4.2)
        create_box("BG_AqueductSpans", (17.5, 8.5, ground_z + 4.0), (0.9, 8.5, 1.2), mat_stone_light)
        for ay in (6.0, 9.0, 12.0):
            create_cylinder(f"BG_AqueductPillar_{ay}", (17.5, ay, ground_z + 2.0), 0.6, 4.0, verts=12, mat=mat_stone_dark)
        create_townhouse("TH_AlchemistL", (10.8, 1.2, ground_z), width=3.8, depth=3.2, height=5.0, floors=2, timber=True, roof_type='slate', with_door=False)
        create_townhouse("TH_BellrootTavern", (11.0, 5.5, ground_z), width=5.0, depth=3.6, height=5.8, floors=3, timber=True, roof_type='slate', with_door=True, door_loc=(9.1, 5.2, ground_z), window_rows=2)
        create_townhouse("TH_MerchantR", (10.7, 9.8, ground_z), width=4.0, depth=3.2, height=4.8, floors=2, timber=True, roof_type='terracotta', with_door=True, door_loc=(9.0, 9.0, ground_z))
        create_market_stall("Stall_Bellroot", (8.8, 7.8, ground_z), width=2.0, depth=1.1, red_gold=True)
        create_cylinder("BarrelsL", (8.4, 3.6, ground_z + 0.48), 0.3, 0.95, verts=12, mat=mat_timber_dark)
        create_cylinder("BarrelsR", (8.4, 9.8, ground_z + 0.42), 0.25, 0.85, verts=12, mat=mat_timber_warm)
        create_box("CratesR", (8.5, 7.0, ground_z + 0.32), (0.5, 0.5, 0.65), mat_timber_warm)

    # 6. Build Coarse Runtime-Facing Mesh in TH_RENDER
    rnd_floor = create_box("RND_Floor", (8.5, 5.5, ground_z - 0.05), (5.5, 22.0, 0.1), col=col_render)
    rnd_wall = create_box("RND_BackdropWall", (11.5, 5.5, ground_z + 3.0), (1.0, 22.0, 6.0), col=col_render)
    
    rnd_b1 = create_box("RND_BuildingL", (10.8, 1.5, ground_z + 2.5), (3.5, 4.0, 5.0), col=col_render)
    rnd_b2 = create_box("RND_BuildingCenter", (11.0, 5.5, ground_z + 2.9), (3.6, 5.2, 5.8), col=col_render)
    rnd_b3 = create_box("RND_BuildingR", (10.7, 9.8, ground_z + 2.4), (3.5, 4.0, 4.8), col=col_render)
    
    rnd_fg_pillar = create_box("RND_FGOccluderPillar", (6.4, 1.8, ground_z + 2.25), (1.0, 1.0, 4.5), col=col_render)
    rnd_fg_lamp = create_box("RND_FGOccluderLamp", (6.4, 9.2, ground_z + 1.35), (0.35, 0.35, 2.7), col=col_render)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in [rnd_floor, rnd_wall, rnd_b1, rnd_b2, rnd_b3, rnd_fg_pillar, rnd_fg_lamp]:
        obj.select_set(True)
    scene.view_layers[0].objects.active = rnd_floor
    bpy.ops.object.join()
    render_mesh_obj = bpy.context.active_object
    render_mesh_obj.name = "RND_Environment_Mesh"

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.04)
    bpy.ops.object.mode_set(mode='OBJECT')

    mat_baked = bpy.data.materials.new("EnvironmentBakedAtlas")
    mat_baked.use_nodes = True
    render_mesh_obj.data.materials.clear()
    render_mesh_obj.data.materials.append(mat_baked)

    # 7. Geometry in TH_COLLISION (Simplified collision bounds)
    create_box("COL_Street_Bounds", (8.5, 5.5, ground_z - 0.1), (4.5, 22.0, 0.2), col=col_collision)
    create_box("COL_Building_BlockL", (10.8, 1.5, ground_z + 1.5), (3.5, 4.0, 3.0), col=col_collision)
    create_box("COL_Building_BlockCenter", (11.0, 5.5, ground_z + 1.5), (3.6, 5.2, 3.0), col=col_collision)
    create_box("COL_Building_BlockR", (10.7, 9.8, ground_z + 1.5), (3.5, 4.0, 3.0), col=col_collision)
    create_box("COL_FGPillar_Bounds", (6.4, 1.8, ground_z + 1.5), (1.1, 1.1, 3.0), col=col_collision)

    # 8. Anchors in TH_ANCHORS (Spatial markers)
    def create_anchor(name, loc, rot_z_deg):
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = 'ARROWS'
        empty.empty_display_size = 0.5
        empty.location = loc
        empty.rotation_euler = (0, 0, math.radians(rot_z_deg))
        col_anchors.objects.link(empty)
        return empty

    create_anchor("spawn_player", (7.8, 5.5, ground_z), 0.0)
    create_anchor("npc_merchant", (8.0, 7.8, ground_z), 45.0)
    create_anchor("npc_guard", (7.6, 3.2, ground_z), -30.0)
    create_anchor("npc_citizen", (8.0, 10.2, ground_z), 180.0)
    create_anchor("door_tavern", (9.1, 5.2, ground_z), 0.0)
    create_anchor("torch_arch", (6.4, 1.8, ground_z + 2.0), 90.0)

    # 9. Camera setup in TH_CAMERA_PREVIEW via thestra_camera
    cam_obj = thestra_camera.create_or_update_camera(CALIBRATION_RECORD, scene=scene, make_active=True)
    if cam_obj.name in root_col.objects:
        root_col.objects.unlink(cam_obj)
    if cam_obj.name not in col_camera.objects:
        col_camera.objects.link(cam_obj)

    # 10. Preview Actors in TH_PREVIEW_ACTORS using walker.png
    # Positioned at X = 7.6 - 8.0 (walkable lane in front of all walls and props)
    if WALKER_PATH.is_file():
        # Protagonist stand-in (Frame 0: idle stance)
        thestra_camera.create_actor_preview(
            str(WALKER_PATH), cam_obj,
            anchor=(7.8, 5.5, ground_z),
            frame_width=24, frame_height=48, frame_index=0,
            world_height=1.0, name="ACTOR_Protagonist"
        )
        # NPC 1: Merchant by stall (Frame 1)
        thestra_camera.create_actor_preview(
            str(WALKER_PATH), cam_obj,
            anchor=(8.0, 7.8, ground_z),
            frame_width=24, frame_height=48, frame_index=1,
            world_height=1.0, name="ACTOR_NPC_Merchant"
        )
        # NPC 2: Gate Guard by arch (Frame 2)
        thestra_camera.create_actor_preview(
            str(WALKER_PATH), cam_obj,
            anchor=(7.6, 3.2, ground_z),
            frame_width=24, frame_height=48, frame_index=2,
            world_height=1.0, name="ACTOR_NPC_Guard"
        )
        # NPC 3: Citizen (Frame 4)
        thestra_camera.create_actor_preview(
            str(WALKER_PATH), cam_obj,
            anchor=(8.0, 10.2, ground_z),
            frame_width=24, frame_height=48, frame_index=4,
            world_height=1.0, name="ACTOR_NPC_Citizen"
        )
        for actor_name in ["ACTOR_Protagonist", "ACTOR_NPC_Merchant", "ACTOR_NPC_Guard", "ACTOR_NPC_Citizen"]:
            act_obj = bpy.data.objects.get(actor_name)
            if act_obj:
                if act_obj.name in root_col.objects:
                    root_col.objects.unlink(act_obj)
                if act_obj.name not in col_preview_actors.objects:
                    col_preview_actors.objects.link(act_obj)

    # 11. Visual Guide in TH_PREVIEW_ONLY
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=10.0, location=(8.5, 5.5, ground_z + 0.01))
    grid_guide = bpy.context.active_object
    grid_guide.name = "GUIDE_GroundGrid"
    link_obj(grid_guide, col_preview_only)

    if blend_output:
        blend_output = Path(blend_output).resolve()
        blend_output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_output))
        print(f"[builder] Saved {attempt_id} to {blend_output}")


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

    print(f"[builder] Rendering attempt {attempt_id} (offset_x={projection_offset_x}) to {output_png}...")
    bpy.ops.render.render(write_still=True)
    print(f"[builder] Render complete: {output_png}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Town Gauntlet Scene Builder & Renderer")
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
