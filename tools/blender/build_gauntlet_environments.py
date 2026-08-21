"""Second Gate Town Visual Gauntlet - Multi-Lineage Environment Builder.

Builds two distinct architectural directions from scratch:
- Direction A: Cinder-Quay Apothecary & Embalmers' Terrace (Waterfront / timber-framed guildhouse)
- Direction B: Bell-Weir Cloister & Copper Foundry (Industrial-monastic terraced courtyard)

Follows V0 collections contract:
- TH_SOURCE: Detailed authoritative geometry, lighting, materials.
- TH_RENDER: Simplified real-3D render mesh for baking.
- TH_COLLISION: Collision volumes.
- TH_ANCHORS: Spatial markers/empties.
- TH_PREVIEW_ACTORS: Walker preview (excluded from bake/export).
- TH_PREVIEW_ONLY: Visual guides.
- TH_CAMERA_PREVIEW: Calibrated Thestra camera.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WALKER_PATH = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"

if str(ROOT / "tools" / "blender") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools" / "blender"))


def get_camera_record(eye_y: float = -17.5, eye_z: float = 2.7, pitch: float = 0.05) -> dict:
    """Return the authoritative Second Gate side-view camera calibration record."""
    fov_x = math.tan(math.radians(14.0))  # 28 degree horizontal FOV
    fov_y = fov_x * 240.0 / 426.0
    return {
        "contract": "thestra.world-camera-calibration",
        "version": 1,
        "projection": "perspective",
        "eye": {"x": 0.0, "y": float(eye_y), "z": float(eye_z)},
        "orientation": {
            "forwardX": 0.0,
            "forwardY": 1.0,
            "rightX": 1.0,
            "rightY": 0.0,
            "pitchRadians": float(pitch),
        },
        "projectionScale": {"x": 1.0, "y": 1.0},
        "fovHalfX": fov_x,
        "fovHalfY": fov_y,
        "nearPlane": 0.05,
        "farPlane": 100.0,
        "targetWidth": 426,
        "targetHeight": 240,
        "baseViewportWidth": 256,
        "baseViewportHeight": 144,
        "viewportCenterX": 213,
        "viewportCenterY": 120,
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
            "blenderCameraUp": "+Y",
        },
    }


def get_camera_envelope() -> list[dict]:
    """Return standard 3-sample camera tracking envelope for Second Gate."""
    return [
        {
            "name": "left_m96",
            "projectionWindowOffsetX": -96.0,
            "projectionWindowOffsetY": 0.0,
            "eyeOffset": [0.0, 0.0, 0.0],
            "yawDeg": 0.0,
            "pitchDeg": 0.0,
            "weight": 1.0,
            "cost": 0.4,
        },
        {
            "name": "center_zero",
            "projectionWindowOffsetX": 0.0,
            "projectionWindowOffsetY": 0.0,
            "eyeOffset": [0.0, 0.0, 0.0],
            "yawDeg": 0.0,
            "pitchDeg": 0.0,
            "weight": 1.0,
            "cost": 0.0,
        },
        {
            "name": "right_p96",
            "projectionWindowOffsetX": 96.0,
            "projectionWindowOffsetY": 0.0,
            "eyeOffset": [0.0, 0.0, 0.0],
            "yawDeg": 0.0,
            "pitchDeg": 0.0,
            "weight": 1.0,
            "cost": 0.4,
        },
    ]


def ensure_collections():
    import bpy
    scene = bpy.context.scene
    root = scene.collection
    names = [
        "TH_SOURCE",
        "TH_RENDER",
        "TH_COLLISION",
        "TH_ANCHORS",
        "TH_PREVIEW_ACTORS",
        "TH_PREVIEW_ONLY",
        "TH_CAMERA_PREVIEW",
    ]
    cols = {}
    for name in names:
        c = bpy.data.collections.get(name)
        if not c:
            c = bpy.data.collections.new(name)
            root.children.link(c)
        cols[name] = c
    return cols


def move_to(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def create_box(name, loc, size, col, mat=None):
    import bpy
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to(obj, col)
    if mat:
        obj.data.materials.append(mat)
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")
    return obj


def create_cylinder(name, loc, radius, depth, col, vertices=16, mat=None):
    import bpy
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to(obj, col)
    if mat:
        obj.data.materials.append(mat)
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")
    return obj


def create_anchor(name, loc, forward=(0.0, 1.0, 0.0), col=None):
    import bpy
    from mathutils import Vector
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = 'ARROWS'
    obj.empty_display_size = 0.5
    obj.location = Vector(loc)
    fwd = Vector(forward).normalized()
    yaw = math.atan2(fwd.x, fwd.y)
    obj.rotation_euler = (0.0, 0.0, -yaw)
    if col:
        col.objects.link(obj)
    return obj


def create_light(name, light_type, loc, color, energy, col, radius=0.25):
    import bpy
    from mathutils import Vector
    data = bpy.data.lights.new(name=name, type=light_type)
    data.color = color
    data.energy = energy
    if light_type == 'POINT':
        data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name=name, object_data=data)
    obj.location = Vector(loc)
    if col:
        col.objects.link(obj)
    return obj


def make_material(name, base_color, roughness=0.75, metallic=0.0, emission=None, emission_strength=0.0):
    import bpy
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if emission:
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
                bsdf.inputs["Emission Strength"].default_value = emission_strength
            elif "Emission" in bsdf.inputs:
                bsdf.inputs["Emission"].default_value = (*emission, 1.0)
    return mat


def build_cinder_quay_scene(blend_path: Path):
    """Direction A: Cinder-Quay Apothecary & Embalmers' Terrace."""
    import bpy
    import thestra_camera

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    cols = ensure_collections()

    # Materials
    mat_stone_quay = make_material("MAT_StoneQuay", (0.35, 0.38, 0.40), roughness=0.85)
    mat_canal_water = make_material("MAT_CanalWater", (0.08, 0.14, 0.18), roughness=0.15, metallic=0.2)
    mat_wood_beams = make_material("MAT_WoodBeams", (0.22, 0.16, 0.11), roughness=0.80)
    mat_plaster_wall = make_material("MAT_PlasterWall", (0.65, 0.62, 0.55), roughness=0.90)
    mat_slate_roof = make_material("MAT_SlateRoof", (0.18, 0.22, 0.26), roughness=0.70)
    mat_door_wood = make_material("MAT_DoorWood", (0.18, 0.12, 0.08), roughness=0.75)
    mat_window_glass = make_material("MAT_WindowGlass", (0.85, 0.70, 0.40), roughness=0.30, emission=(0.9, 0.7, 0.3), emission_strength=2.5)
    mat_iron = make_material("MAT_Iron", (0.12, 0.12, 0.13), roughness=0.60, metallic=0.85)
    mat_bg_buildings = make_material("MAT_BgBuildings", (0.28, 0.32, 0.38), roughness=0.95)

    # 1. GROUND & QUAY
    # Main walkable promenade: X = -7.0 to +7.0, Y = -0.8 to +2.0, Z = 0.0 (height 0.8 -> top at 0.0)
    create_box("SRC_QuayPromenade", (0.0, 0.6, -0.4), (14.0, 2.8, 0.8), cols["TH_SOURCE"], mat_stone_quay)
    # Canal retaining dock wall / water basin
    create_box("SRC_DockWall", (0.0, -1.0, -0.75), (14.0, 0.4, 1.5), cols["TH_SOURCE"], mat_stone_quay)
    create_box("SRC_CanalWater", (0.0, -2.5, -0.65), (16.0, 3.0, 0.2), cols["TH_SOURCE"], mat_canal_water)

    # Foreground bollards / mooring posts
    create_cylinder("SRC_MooringPost_L", (-3.6, -1.1, 0.35), radius=0.22, depth=0.9, col=cols["TH_SOURCE"], mat=mat_wood_beams)
    create_cylinder("SRC_MooringPost_R", (3.2, -1.1, 0.35), radius=0.22, depth=0.9, col=cols["TH_SOURCE"], mat=mat_wood_beams)
    create_cylinder("SRC_IronRing_L", (-3.6, -1.1, 0.72), radius=0.12, depth=0.08, col=cols["TH_SOURCE"], mat=mat_iron)
    create_cylinder("SRC_IronRing_R", (3.2, -1.1, 0.72), radius=0.12, depth=0.08, col=cols["TH_SOURCE"], mat=mat_iron)

    # 2. PRIMARY ARCHITECTURE: APOTHECARY GUILDHOUSE (X = -2.2 to +2.8, Y = 1.2 to 4.5)
    # Ground floor stone base (Z = 0.0 to 2.8)
    create_box("SRC_Apothecary_GF_Left", (-1.35, 2.4, 1.4), (1.7, 2.4, 2.8), cols["TH_SOURCE"], mat_stone_quay)
    create_box("SRC_Apothecary_GF_Right", (1.75, 2.4, 1.4), (2.1, 2.4, 2.8), cols["TH_SOURCE"], mat_stone_quay)
    create_box("SRC_Apothecary_GF_Lintel", (0.2, 2.4, 2.5), (1.4, 2.4, 0.6), cols["TH_SOURCE"], mat_stone_quay)
    create_box("SRC_Apothecary_DoorBack", (0.2, 2.9, 1.1), (1.4, 0.2, 2.2), cols["TH_SOURCE"], mat_stone_quay)
    create_box("SRC_Apothecary_DoorLeaf", (0.2, 2.75, 1.05), (1.1, 0.1, 2.1), cols["TH_SOURCE"], mat_door_wood)
    create_box("SRC_Apothecary_CellarGrate", (-1.2, 1.1, 0.4), (0.9, 0.2, 0.6), cols["TH_SOURCE"], mat_iron)

    # First Jetty Floor (Cantilevered 2nd floor, Z = 2.8 to 5.6, overhanging to Y = 0.6)
    create_box("SRC_Apothecary_2F_Mass", (0.2, 2.2, 4.2), (5.0, 3.2, 2.8), cols["TH_SOURCE"], mat_plaster_wall)
    create_box("SRC_Apothecary_Bressummer_1", (0.2, 0.55, 2.8), (5.2, 0.25, 0.25), cols["TH_SOURCE"], mat_wood_beams)
    for x_corbel in (-2.1, -1.0, 0.2, 1.4, 2.5):
        create_box(f"SRC_Corbel_1F_{x_corbel}", (x_corbel, 0.8, 2.65), (0.22, 0.6, 0.4), cols["TH_SOURCE"], mat_wood_beams)

    # Protruding Oriel / Bay Window (X = 0.2, Z = 3.2 to 4.8, protruding to Y = 0.3)
    create_box("SRC_Apothecary_BayWindow", (0.2, 0.4, 4.0), (1.8, 0.6, 1.6), cols["TH_SOURCE"], mat_wood_beams)
    create_box("SRC_Apothecary_BayGlass", (0.2, 0.08, 4.0), (1.6, 0.05, 1.3), cols["TH_SOURCE"], mat_window_glass)
    create_box("SRC_Apothecary_SignBracket", (-0.9, 0.5, 2.6), (0.08, 0.7, 0.08), cols["TH_SOURCE"], mat_iron)
    create_box("SRC_Apothecary_SignBoard", (-0.9, 0.85, 2.3), (0.05, 0.45, 0.45), cols["TH_SOURCE"], mat_wood_beams)

    # Second Jetty Floor (Attic / 3rd floor, Z = 5.6 to 8.2, overhanging to Y = 0.3)
    create_box("SRC_Apothecary_3F_Mass", (0.2, 2.05, 6.9), (4.8, 3.5, 2.6), cols["TH_SOURCE"], mat_plaster_wall)
    create_box("SRC_Apothecary_Bressummer_2", (0.2, 0.25, 5.6), (5.0, 0.25, 0.25), cols["TH_SOURCE"], mat_wood_beams)
    for x_corbel in (-2.0, -0.6, 0.8, 2.2):
        create_box(f"SRC_Corbel_2F_{x_corbel}", (x_corbel, 0.5, 5.45), (0.22, 0.5, 0.35), cols["TH_SOURCE"], mat_wood_beams)

    for x_stud in (-1.8, -0.6, 1.0, 2.2):
        create_box(f"SRC_TimberStud_{x_stud}", (x_stud, 0.22, 6.9), (0.16, 0.1, 2.4), cols["TH_SOURCE"], mat_wood_beams)

    # Steep Gable Roof & Dormer (Z = 8.2 to 10.8)
    create_box("SRC_Apothecary_Roof", (0.2, 2.2, 9.4), (5.2, 3.8, 2.4), cols["TH_SOURCE"], mat_slate_roof)
    create_box("SRC_Apothecary_Chimney", (2.2, 2.4, 9.6), (0.8, 0.8, 3.2), cols["TH_SOURCE"], mat_stone_quay)
    create_cylinder("SRC_ChimneyPot_1", (2.05, 2.4, 11.35), radius=0.12, depth=0.4, col=cols["TH_SOURCE"], mat=mat_wood_beams)
    create_cylinder("SRC_ChimneyPot_2", (2.35, 2.4, 11.35), radius=0.12, depth=0.4, col=cols["TH_SOURCE"], mat=mat_wood_beams)

    # 3. SECONDARY ARCHITECTURE: ALLEY ARCHWAY (LEFT) & EMBALMERS' ANNEX (RIGHT)
    create_box("SRC_Alley_ArchLeftPillar", (-4.6, 2.2, 1.6), (0.8, 2.4, 3.2), cols["TH_SOURCE"], mat_stone_quay)
    create_box("SRC_Alley_ArchLintel", (-3.4, 2.2, 3.0), (1.8, 2.4, 0.8), cols["TH_SOURCE"], mat_stone_quay)
    create_box("SRC_Alley_UpperWarehouse", (-4.0, 2.4, 5.8), (2.8, 2.8, 4.8), cols["TH_SOURCE"], mat_wood_beams)
    create_box("SRC_Alley_Roof", (-4.0, 2.4, 8.6), (3.0, 3.0, 1.4), cols["TH_SOURCE"], mat_slate_roof)
    create_cylinder("SRC_Alley_Lantern", (-3.4, 1.8, 2.3), radius=0.15, depth=0.35, col=cols["TH_SOURCE"], mat=mat_window_glass)

    create_box("SRC_Annex_GF", (4.5, 2.6, 1.8), (3.2, 2.6, 3.6), cols["TH_SOURCE"], mat_stone_quay)
    create_box("SRC_Annex_Door", (3.8, 1.25, 1.0), (0.9, 0.1, 2.0), cols["TH_SOURCE"], mat_door_wood)
    create_box("SRC_Annex_Window", (5.2, 1.25, 2.2), (1.0, 0.1, 1.2), cols["TH_SOURCE"], mat_window_glass)
    create_box("SRC_Annex_ShedRoof", (4.5, 2.7, 4.1), (3.4, 3.0, 1.2), cols["TH_SOURCE"], mat_slate_roof)
    create_box("SRC_Prop_Crate_1", (5.5, 0.4, 0.35), (0.7, 0.7, 0.7), cols["TH_SOURCE"], mat_wood_beams)
    create_cylinder("SRC_Prop_Barrel_1", (4.7, 0.35, 0.45), radius=0.3, depth=0.9, col=cols["TH_SOURCE"], mat=mat_wood_beams)

    # 4. BACKGROUND SILHOUETTES & CANAL BRIDGE (Y = 8.0 to 18.0)
    create_box("SRC_BG_CanalBridge", (-3.5, 10.0, 2.5), (6.0, 2.0, 4.0), cols["TH_SOURCE"], mat_bg_buildings)
    create_box("SRC_BG_DistantTower", (-0.5, 14.0, 7.5), (3.0, 3.0, 12.0), cols["TH_SOURCE"], mat_bg_buildings)
    create_box("SRC_BG_Spire", (-0.5, 14.0, 14.5), (1.6, 1.6, 4.0), cols["TH_SOURCE"], mat_slate_roof)
    create_box("SRC_BG_TownWall", (4.5, 12.0, 4.0), (8.0, 2.0, 7.0), cols["TH_SOURCE"], mat_bg_buildings)

    # 5. LIGHTING
    create_light("SUN_Key", "SUN", (-8.0, -12.0, 15.0), (1.0, 0.88, 0.75), energy=3.5, col=cols["TH_SOURCE"])
    sun_obj = bpy.data.objects.get("SUN_Key")
    if sun_obj:
        sun_obj.rotation_euler = (math.radians(52.0), math.radians(18.0), math.radians(-32.0))

    create_light("LIGHT_DoorwayWarm", "POINT", (0.2, 2.2, 1.8), (1.0, 0.65, 0.3), energy=28.0, col=cols["TH_SOURCE"], radius=0.35)
    create_light("LIGHT_AlleyLantern", "POINT", (-3.4, 1.8, 2.1), (1.0, 0.60, 0.25), energy=22.0, col=cols["TH_SOURCE"], radius=0.3)
    create_light("LIGHT_BayWindowGlow", "POINT", (0.2, 0.6, 4.0), (1.0, 0.75, 0.4), energy=18.0, col=cols["TH_SOURCE"], radius=0.4)

    # 6. TH_RENDER (Coarse Real-3D Render Mesh)
    r_promenade = create_box("RND_Quay", (0.0, 0.6, -0.4), (14.0, 2.8, 0.8), cols["TH_RENDER"])
    r_apothecary = create_box("RND_Apothecary_Main", (0.2, 2.3, 4.6), (5.0, 3.4, 9.2), cols["TH_RENDER"])
    r_alley = create_box("RND_Alley", (-4.0, 2.3, 4.5), (3.2, 2.8, 8.0), cols["TH_RENDER"])
    r_annex = create_box("RND_Annex", (4.5, 2.6, 2.2), (3.2, 2.6, 4.4), cols["TH_RENDER"])
    r_bg = create_box("RND_BG", (0.0, 12.0, 6.0), (16.0, 4.0, 12.0), cols["TH_RENDER"])
    bpy.ops.object.select_all(action='DESELECT')
    for r_obj in (r_promenade, r_apothecary, r_alley, r_annex, r_bg):
        r_obj.select_set(True)
    scene.view_layers[0].objects.active = r_promenade
    bpy.ops.object.join()
    r_final = bpy.context.active_object
    r_final.name = "TH_RENDER_Environment"
    if not r_final.data.uv_layers:
        r_final.data.uv_layers.new(name="UVMap")

    # 7. TH_COLLISION
    create_box("COL_Walkway", (0.0, 0.6, -0.2), (13.5, 2.2, 0.4), cols["TH_COLLISION"])
    create_box("COL_BuildingWall", (0.0, 2.0, 1.5), (14.0, 0.6, 3.0), cols["TH_COLLISION"])
    create_box("COL_QuayEdge", (0.0, -0.85, 0.5), (14.0, 0.3, 1.2), cols["TH_COLLISION"])

    # 8. TH_ANCHORS
    create_anchor("spawn_player", (-4.5, 0.2, 0.0), forward=(1.0, 0.0, 0.0), col=cols["TH_ANCHORS"])
    create_anchor("walk_start", (-5.5, 0.2, 0.0), forward=(1.0, 0.0, 0.0), col=cols["TH_ANCHORS"])
    create_anchor("walk_end", (5.5, 0.2, 0.0), forward=(-1.0, 0.0, 0.0), col=cols["TH_ANCHORS"])
    create_anchor("doorway_apothecary", (0.2, 1.8, 0.0), forward=(0.0, 1.0, 0.0), col=cols["TH_ANCHORS"])
    create_anchor("doorway_annex", (3.8, 1.2, 0.0), forward=(0.0, 1.0, 0.0), col=cols["TH_ANCHORS"])
    create_anchor("npc_herbalist", (1.2, 0.5, 0.0), forward=(-0.7, -0.7, 0.0), col=cols["TH_ANCHORS"])
    create_anchor("npc_dockhand", (-2.2, -0.3, 0.0), forward=(0.7, 0.7, 0.0), col=cols["TH_ANCHORS"])

    # 9. CAMERA & WALKER PREVIEW
    cam_rec = get_camera_record(eye_y=-17.5, eye_z=2.7, pitch=0.05)
    cam_obj = thestra_camera.create_or_update_camera(cam_rec, scene=scene)
    move_to(cam_obj, cols["TH_CAMERA_PREVIEW"])

    if WALKER_PATH.is_file():
        walker = thestra_camera.create_actor_preview(WALKER_PATH, cam_obj, anchor=(-1.0, 0.1, 0.0))
        move_to(walker, cols["TH_PREVIEW_ACTORS"])

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[builder] Direction A saved to {blend_path}")


def build_bell_weir_scene(blend_path: Path):
    """Direction B: Bell-Weir Cloister & Copper Foundry."""
    import bpy
    import thestra_camera

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    cols = ensure_collections()

    # Materials
    mat_terrace_stone = make_material("MAT_TerraceStone", (0.38, 0.36, 0.34), roughness=0.85)
    mat_foundry_brick = make_material("MAT_FoundryBrick", (0.32, 0.22, 0.18), roughness=0.90)
    mat_soot_stone = make_material("MAT_SootStone", (0.18, 0.18, 0.19), roughness=0.92)
    mat_verdigris = make_material("MAT_VerdigrisCopper", (0.22, 0.48, 0.44), roughness=0.60, metallic=0.45)
    mat_iron_rivet = make_material("MAT_IronRivet", (0.10, 0.10, 0.11), roughness=0.55, metallic=0.90)
    mat_furnace_glow = make_material("MAT_FurnaceGlow", (1.0, 0.45, 0.1), roughness=0.20, emission=(1.0, 0.4, 0.05), emission_strength=5.0)
    mat_water_channel = make_material("MAT_WeirWater", (0.10, 0.16, 0.18), roughness=0.15)
    mat_bg_cliff = make_material("MAT_BgCliff", (0.24, 0.25, 0.28), roughness=0.95)

    # 1. GROUND & TERRACES (Z = 0.0 to 0.6)
    create_box("SRC_LowerTerrace", (-3.2, 0.9, -0.3), (7.5, 3.0, 0.6), cols["TH_SOURCE"], mat_terrace_stone)
    create_box("SRC_Step_1", (0.7, 0.9, -0.1), (0.4, 3.0, 0.4), cols["TH_SOURCE"], mat_terrace_stone)
    create_box("SRC_Step_2", (1.0, 0.9, 0.1), (0.4, 3.0, 0.4), cols["TH_SOURCE"], mat_terrace_stone)
    create_box("SRC_UpperTerrace", (4.1, 0.9, 0.0), (5.8, 3.0, 1.2), cols["TH_SOURCE"], mat_terrace_stone)

    create_box("SRC_ParapetWall", (0.0, -1.0, 0.15), (14.0, 0.35, 0.7), cols["TH_SOURCE"], mat_soot_stone)
    create_box("SRC_Brazier_Plinth", (-2.2, -0.9, 0.3), (0.6, 0.6, 0.6), cols["TH_SOURCE"], mat_soot_stone)
    create_cylinder("SRC_Brazier_Bowl", (-2.2, -0.9, 0.85), radius=0.4, depth=0.4, col=cols["TH_SOURCE"], mat=mat_iron_rivet)
    create_cylinder("SRC_Brazier_Embers", (-2.2, -0.9, 0.95), radius=0.35, depth=0.1, col=cols["TH_SOURCE"], mat=mat_furnace_glow)

    create_box("SRC_WeirChannel", (-5.5, -2.0, -0.7), (3.5, 2.0, 0.4), cols["TH_SOURCE"], mat_water_channel)

    # 2. PRIMARY ARCHITECTURE: COPPER FOUNDRY & KILN HALL (X = 0.5 to 5.5, Y = 1.8 to 5.5)
    create_box("SRC_Foundry_Base_Left", (1.8, 3.2, 2.7), (1.6, 2.8, 4.2), cols["TH_SOURCE"], mat_foundry_brick)
    create_box("SRC_Foundry_Base_Right", (4.6, 3.2, 2.7), (1.8, 2.8, 4.2), cols["TH_SOURCE"], mat_foundry_brick)
    create_box("SRC_Foundry_ArchLintel", (3.1, 3.2, 4.3), (1.8, 2.8, 1.0), cols["TH_SOURCE"], mat_foundry_brick)
    create_box("SRC_Foundry_PortalBack", (3.1, 3.8, 2.2), (1.6, 0.3, 3.2), cols["TH_SOURCE"], mat_soot_stone)
    create_box("SRC_Foundry_IronDoors", (3.1, 3.6, 2.1), (1.3, 0.1, 3.0), cols["TH_SOURCE"], mat_iron_rivet)
    create_box("SRC_Foundry_FurnaceVent", (3.1, 2.2, 1.0), (1.4, 0.3, 0.35), cols["TH_SOURCE"], mat_furnace_glow)

    create_cylinder("SRC_Foundry_CupolaDrum", (3.1, 3.5, 5.8), radius=1.8, depth=1.6, col=cols["TH_SOURCE"], vertices=12, mat=mat_foundry_brick)
    create_cylinder("SRC_Foundry_Dome", (3.1, 3.5, 7.2), radius=1.9, depth=1.2, col=cols["TH_SOURCE"], vertices=12, mat=mat_verdigris)
    create_cylinder("SRC_Foundry_DomeSpire", (3.1, 3.5, 8.4), radius=0.25, depth=1.2, col=cols["TH_SOURCE"], mat=mat_verdigris)

    create_cylinder("SRC_Foundry_FluePipe", (5.2, 3.5, 7.2), radius=0.55, depth=8.5, col=cols["TH_SOURCE"], mat=mat_iron_rivet)
    create_cylinder("SRC_Foundry_FlueCowl", (5.2, 3.5, 11.6), radius=0.8, depth=0.6, col=cols["TH_SOURCE"], mat=mat_iron_rivet)
    for z_band in (5.0, 7.5, 10.0):
        create_cylinder(f"SRC_FlueBand_{z_band}", (5.2, 3.5, z_band), radius=0.62, depth=0.15, col=cols["TH_SOURCE"], mat=mat_iron_rivet)

    # 3. SECONDARY ARCHITECTURE: ROMANESQUE CLOISTER & FLYING BUTTRESSES (X = -6.5 to 0.5)
    create_box("SRC_Cloister_RearWall", (-3.2, 3.4, 3.0), (7.0, 1.6, 6.0), cols["TH_SOURCE"], mat_soot_stone)
    create_box("SRC_Buttress_1_Base", (-4.5, 2.2, 2.2), (0.8, 2.4, 4.4), cols["TH_SOURCE"], mat_soot_stone)
    create_box("SRC_Buttress_1_Arch", (-4.5, 2.6, 5.0), (0.8, 1.6, 2.0), cols["TH_SOURCE"], mat_soot_stone)
    create_box("SRC_Buttress_2_Base", (-1.5, 2.2, 2.2), (0.8, 2.4, 4.4), cols["TH_SOURCE"], mat_soot_stone)
    create_box("SRC_Buttress_2_Arch", (-1.5, 2.6, 5.0), (0.8, 1.6, 2.0), cols["TH_SOURCE"], mat_soot_stone)

    create_box("SRC_Cloister_Niche_1", (-3.0, 2.8, 1.8), (1.4, 0.4, 2.4), cols["TH_SOURCE"], mat_foundry_brick)
    create_cylinder("SRC_Cloister_OilLamp", (-3.0, 2.6, 2.6), radius=0.15, depth=0.3, col=cols["TH_SOURCE"], mat=mat_furnace_glow)

    # 4. BACKGROUND MONUMENTAL BELL TOWER & CLIFF (Y = 7.0 to 18.0)
    create_box("SRC_BG_QuarryCliff", (0.0, 12.0, 7.0), (16.0, 3.0, 14.0), cols["TH_SOURCE"], mat_bg_cliff)
    create_box("SRC_BG_BellTower", (-3.2, 8.0, 9.5), (3.6, 3.6, 11.0), cols["TH_SOURCE"], mat_foundry_brick)
    create_box("SRC_BG_BelfryOpening", (-3.2, 6.5, 12.0), (2.0, 0.8, 3.2), cols["TH_SOURCE"], mat_soot_stone)
    create_cylinder("SRC_BG_BronzeBell", (-3.2, 6.8, 12.0), radius=0.7, depth=1.2, col=cols["TH_SOURCE"], mat=mat_verdigris)

    # 5. LIGHTING
    create_light("SUN_Key_B", "SUN", (8.0, -10.0, 16.0), (0.9, 0.92, 1.0), energy=3.0, col=cols["TH_SOURCE"])
    sun_obj = bpy.data.objects.get("SUN_Key_B")
    if sun_obj:
        sun_obj.rotation_euler = (math.radians(48.0), math.radians(-22.0), math.radians(45.0))

    create_light("LIGHT_KilnGlow", "POINT", (3.1, 2.8, 1.6), (1.0, 0.45, 0.1), energy=35.0, col=cols["TH_SOURCE"], radius=0.45)
    create_light("LIGHT_BrazierFire", "POINT", (-2.2, -0.9, 1.2), (1.0, 0.55, 0.15), energy=24.0, col=cols["TH_SOURCE"], radius=0.35)
    create_light("LIGHT_CloisterLamp", "POINT", (-3.0, 2.4, 2.5), (1.0, 0.70, 0.3), energy=16.0, col=cols["TH_SOURCE"], radius=0.3)

    # 6. TH_RENDER (Coarse Real-3D Render Mesh)
    r_lower = create_box("RND_LowerTerrace", (-3.2, 0.9, -0.3), (7.5, 3.0, 0.6), cols["TH_RENDER"])
    r_upper = create_box("RND_UpperTerrace", (4.1, 0.9, 0.0), (5.8, 3.0, 1.2), cols["TH_RENDER"])
    r_foundry = create_box("RND_Foundry", (3.2, 3.4, 4.0), (5.0, 3.2, 8.0), cols["TH_RENDER"])
    r_cloister = create_box("RND_Cloister", (-3.2, 3.0, 3.2), (6.8, 2.4, 6.4), cols["TH_RENDER"])
    r_cliff = create_box("RND_Cliff", (0.0, 10.0, 8.0), (16.0, 4.0, 14.0), cols["TH_RENDER"])
    bpy.ops.object.select_all(action='DESELECT')
    for r_obj in (r_lower, r_upper, r_foundry, r_cloister, r_cliff):
        r_obj.select_set(True)
    scene.view_layers[0].objects.active = r_lower
    bpy.ops.object.join()
    r_final = bpy.context.active_object
    r_final.name = "TH_RENDER_Environment"
    if not r_final.data.uv_layers:
        r_final.data.uv_layers.new(name="UVMap")

    # 7. TH_COLLISION
    create_box("COL_Walk_Lower", (-3.2, 0.9, -0.1), (7.2, 2.4, 0.4), cols["TH_COLLISION"])
    create_box("COL_Walk_Upper", (4.1, 0.9, 0.5), (5.6, 2.4, 0.4), cols["TH_COLLISION"])
    create_box("COL_FoundryWall", (0.0, 2.4, 2.0), (14.0, 0.8, 4.0), cols["TH_COLLISION"])
    create_box("COL_Balustrade", (0.0, -1.0, 0.4), (14.0, 0.35, 0.8), cols["TH_COLLISION"])

    # 8. TH_ANCHORS
    create_anchor("spawn_player", (-4.0, 0.5, 0.0), forward=(1.0, 0.0, 0.0), col=cols["TH_ANCHORS"])
    create_anchor("walk_start", (-5.5, 0.5, 0.0), forward=(1.0, 0.0, 0.0), col=cols["TH_ANCHORS"])
    create_anchor("walk_end", (5.5, 0.5, 0.6), forward=(-1.0, 0.0, 0.0), col=cols["TH_ANCHORS"])
    create_anchor("doorway_foundry", (3.1, 2.6, 0.6), forward=(0.0, 1.0, 0.0), col=cols["TH_ANCHORS"])
    create_anchor("npc_foundrymaster", (2.0, 0.8, 0.6), forward=(-0.7, -0.7, 0.0), col=cols["TH_ANCHORS"])
    create_anchor("npc_monk", (-2.8, 1.4, 0.0), forward=(0.5, -0.8, 0.0), col=cols["TH_ANCHORS"])

    # 9. CAMERA & WALKER PREVIEW
    cam_rec = get_camera_record(eye_y=-17.5, eye_z=2.7, pitch=0.05)
    cam_obj = thestra_camera.create_or_update_camera(cam_rec, scene=scene)
    move_to(cam_obj, cols["TH_CAMERA_PREVIEW"])

    if WALKER_PATH.is_file():
        walker = thestra_camera.create_actor_preview(WALKER_PATH, cam_obj, anchor=(-0.5, 0.3, 0.0))
        move_to(walker, cols["TH_PREVIEW_ACTORS"])

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[builder] Direction B saved to {blend_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--direction", choices=["a", "b", "all"], default="all")
    parser.add_argument("--outdir", type=Path, default=ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "second_gate_gauntlet")
    
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)

    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    if args.direction in ("a", "all"):
        build_cinder_quay_scene(outdir / "direction_a_cinder_quay.blend")
    if args.direction in ("b", "all"):
        build_bell_weir_scene(outdir / "direction_b_bell_weir.blend")


if __name__ == "__main__":
    main()
