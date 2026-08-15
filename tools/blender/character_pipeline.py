"""Second Rite Tiny 3D Character Authoring & Gauntlet Pipeline (24x24 pixels).

Supports:
- Procedural authoring and editing of authoritative .blend character documents.
- 3 distinct modeling/visual approaches (Volumetric Knight, Faceted Rogue, Compressed Mage).
- Hierarchical rigging & multi-action animation (Idle, Walk, Gesture).
- Supersampled orthographic rendering -> filtered 24x24 raster -> 8x enlarged inspection.
- 8-direction turnarounds, animation GIF generation, and contact sheets.
- In-place .blend source editing across gauntlet rounds.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

# Add tools/blender to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    import bpy
    import bmesh
    from mathutils import Vector, Euler, Matrix, Quaternion
    import second_rite_asset_core as asset_core
except ImportError:
    bpy = None
    bmesh = None




AUTHORING_DIR = ROOT / "assets" / "authoring" / "characters"
EXPERIMENT_DIR = ROOT / "experiments" / "tiny-character-pipeline"
RENDERS_24_DIR = EXPERIMENT_DIR / "renders" / "24x24"
RENDERS_8X_DIR = EXPERIMENT_DIR / "renders" / "enlarged_8x"
ANIMATIONS_DIR = EXPERIMENT_DIR / "renders" / "animations"
DIRECTIONS_DIR = EXPERIMENT_DIR / "renders" / "directions"
REFERENCE_DIR = EXPERIMENT_DIR / "renders" / "reference_highres"
CONTACT_DIR = EXPERIMENT_DIR / "renders" / "contact_sheets"


def ensure_directories():
    for directory in (
        AUTHORING_DIR,
        EXPERIMENT_DIR,
        RENDERS_24_DIR,
        RENDERS_8X_DIR,
        ANIMATIONS_DIR,
        DIRECTIONS_DIR,
        REFERENCE_DIR,
        CONTACT_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# BLENDER ENVIRONMENT SETUP (LIGHTS, CAMERA, SCENE, MATERIALS)
# ==============================================================================

def setup_studio_environment(scene=None):
    """Configure elevated 32° RPG camera, 3-point directional lighting, and render settings."""
    if scene is None:
        scene = bpy.context.scene

    # Set background to transparent for sprite baking / clean silhouette
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"

    # Color management: Standard / AgX / sRGB
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0

    # Optimize render engine settings for fast, high-quality supersampled sprite baking
    if hasattr(scene.render, "engine"):
        scene.render.engine = "BLENDER_EEVEE"
    if hasattr(scene, "eevee"):
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = 16
        if hasattr(scene.eevee, "use_shadows"):
            scene.eevee.use_shadows = True

    # Film pixel filter settings: eliminate film blur at source
    if hasattr(scene.render, "filter_size"):
        scene.render.filter_size = 0.5
    if hasattr(scene.render, "pixel_filter_type"):
        scene.render.pixel_filter_type = "BOX"

    # Ensure pure black world background so edge rays never pick up white/ambient bleed
    if not scene.world:
        scene.world = bpy.data.worlds.new("Studio_World")
    scene.world.use_nodes = True
    bg_node = scene.world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        bg_node.inputs["Strength"].default_value = 0.0

    # Ensure lighting collection
    light_coll = asset_core.ensure_collection("Lighting_Studio")
    
    # 1. Key Light (Sun / Strong warm directional, 45° left, 52° elevated)
    key_light = bpy.data.objects.get("Key_Light")
    if not key_light:
        key_data = bpy.data.lights.new(name="Key_Light", type="SUN")
        key_data.energy = 2.4
        key_data.color = (1.0, 0.96, 0.90)
        key_light = bpy.data.objects.new("Key_Light", key_data)
        light_coll.objects.link(key_light)
    key_light.rotation_euler = (math.radians(-52), math.radians(25), math.radians(-40))

    # 2. Fill Light (Soft cool ambient/fill, opposite side, low elevation)
    fill_light = bpy.data.objects.get("Fill_Light")
    if not fill_light:
        fill_data = bpy.data.lights.new(name="Fill_Light", type="SUN")
        fill_data.energy = 0.75
        fill_data.color = (0.65, 0.75, 0.95)
        fill_light = bpy.data.objects.new("Fill_Light", fill_data)
        light_coll.objects.link(fill_light)
    fill_light.rotation_euler = (math.radians(-20), math.radians(-45), math.radians(130))

    # 3. Rim / Kicker Light (High back-right edge accent)
    rim_light = bpy.data.objects.get("Rim_Light")
    if not rim_light:
        rim_data = bpy.data.lights.new(name="Rim_Light", type="SUN")
        rim_data.energy = 1.6
        rim_data.color = (0.95, 0.98, 1.0)
        rim_light = bpy.data.objects.new("Rim_Light", rim_data)
        light_coll.objects.link(rim_light)
    rim_light.rotation_euler = (math.radians(65), math.radians(15), math.radians(150))

    # Camera setup (Orthographic, pitched down 32° from horizontal)
    cam_obj = bpy.data.objects.get("Render_Camera")
    if not cam_obj:
        cam_data = bpy.data.cameras.new(name="Render_Camera")
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = 1.95  # Tight framing around ~1.6m tall chibi character
        cam_obj = bpy.data.objects.new("Render_Camera", cam_data)
        bpy.context.scene.collection.objects.link(cam_obj)

    # Position camera in front of character (looking along +Y towards origin, pitched down)
    pitch_angle = math.radians(60) # 60° from vertical = 30° elevation
    dist = 5.0
    cam_obj.location = (0.0, -dist * math.sin(pitch_angle), 0.75 + dist * math.cos(pitch_angle))
    cam_obj.rotation_euler = (math.radians(60), 0.0, 0.0)
    scene.camera = cam_obj

    return scene, cam_obj


def make_char_material(name, base_color, metallic=0.0, roughness=0.5, emission=None, emission_strength=1.0):
    """Helper to create Principled BSDF material with rich parameters."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*base_color[:3], 1.0)
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if emission is not None:
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (*emission[:3], 1.0)
                bsdf.inputs["Emission Strength"].default_value = emission_strength
            elif "Emission" in bsdf.inputs:
                bsdf.inputs["Emission"].default_value = (*emission[:3], 1.0)
    return mat


# ==============================================================================
# GEOMETRY HELPERS (BMESH PROCEDURAL MODELING)
# ==============================================================================

def create_primitive_mesh(name, mesh_func, collection, **kwargs):
    """Create a mesh object using bmesh primitive functions."""
    bm = bmesh.new()
    mesh_func(bm, **kwargs)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def create_cube_mesh(name, size, collection, smooth=False):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    else:
        for p in obj.data.polygons:
            p.use_smooth = False
    return obj


def create_cylinder_mesh(name, radius, depth, segments, collection, smooth=False):
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=radius,
        radius2=radius,
        depth=depth,
    )
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    else:
        for p in obj.data.polygons:
            p.use_smooth = False
    return obj


def create_uv_sphere_mesh(name, radius, segments, ring_count, collection, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm,
        u_segments=segments,
        v_segments=ring_count,
        radius=radius,
    )
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    else:
        for p in obj.data.polygons:
            p.use_smooth = False
    return obj


def create_cone_mesh(name, radius1, radius2, depth, segments, collection, smooth=False):
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=radius1,
        radius2=radius2,
        depth=depth,
    )
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    for p in obj.data.polygons:
        p.use_smooth = smooth
    return obj


def create_contact_shadow_disc(parent, collection, radius=0.45):
    """Creates a soft grounded shadow disc under the character."""
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=12, radius=radius)
    mesh = bpy.data.meshes.new("Contact_Shadow")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new("Contact_Shadow", mesh)
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = (0.0, 0.0, 0.005)
    
    mat = make_char_material("Mat_ContactShadow", (0.05, 0.04, 0.08), metallic=0.0, roughness=1.0)
    mat.diffuse_color = (0.05, 0.04, 0.08, 0.7)
    obj.data.materials.append(mat)
    return obj


# ==============================================================================
# ANIMATION ACTION CREATION HELPERS
# ==============================================================================

def add_keyframe(obj, data_path, frame, value):
    if not obj.animation_data:
        obj.animation_data_create()
    if data_path == "location":
        obj.location = value
        obj.keyframe_insert(data_path="location", frame=frame)
    elif data_path == "rotation_euler":
        obj.rotation_euler = value
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    elif data_path == "scale":
        obj.scale = value
        obj.keyframe_insert(data_path="scale", frame=frame)


def build_action_tracks(character_root, action_name, keyframes_dict, total_frames):
    """Creates an Action datablock and populates keyframes for hierarchical objects."""
    action = bpy.data.actions.get(action_name) or bpy.data.actions.new(name=action_name)
    
    for obj_name, channels in keyframes_dict.items():
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            continue
        if not obj.animation_data:
            obj.animation_data_create()
        obj.animation_data.action = action

        for path, frame_values in channels.items():
            for frame, val in frame_values:
                add_keyframe(obj, path, frame, val)
                
    return action


# ==============================================================================
# APPROACH A: VOLUMETRIC / SCULPTURAL (THE KNIGHT)
# ==============================================================================

def build_knight_volumetric():
    """Build Approach A: Volumetric Chibi Knight with large curved forms, visor gleam, and pauldrons."""
    asset_core.reset_scene()
    setup_studio_environment()
    
    coll = asset_core.ensure_collection("Knight_Model")

    # Materials
    mat_steel = make_char_material("Mat_Steel", (0.55, 0.60, 0.68), metallic=0.85, roughness=0.28)
    mat_dark_steel = make_char_material("Mat_DarkSteel", (0.22, 0.24, 0.28), metallic=0.75, roughness=0.45)
    mat_gold = make_char_material("Mat_Gold", (0.85, 0.68, 0.20), metallic=0.9, roughness=0.25)
    mat_tunic = make_char_material("Mat_NavyTunic", (0.12, 0.16, 0.28), metallic=0.0, roughness=0.85)
    mat_visor = make_char_material("Mat_VisorGleam", (0.05, 0.08, 0.12), metallic=0.1, roughness=0.1, emission=(0.4, 0.7, 0.9), emission_strength=1.5)
    mat_leather = make_char_material("Mat_Leather", (0.35, 0.22, 0.14), metallic=0.0, roughness=0.7)

    # 1. Root and Hip Controller
    root = bpy.data.objects.new("Knight_Root", None)
    root.empty_display_type = "ARROWS"
    coll.objects.link(root)
    asset_core.tag_asset_target(
        root,
        asset_id="knight_volumetric",
        representation="full_model",
        role="preview_only",
        authoring_space="item_display",
        placement_frame="floor_center",
        states=["default", "idle", "walk", "gesture"],
        default_state="default",
    )
    root["sr_source_authority"] = "blend"
    root["character_archetype"] = "volumetric_sculptural"

    create_contact_shadow_disc(root, coll, radius=0.42)

    # Pelvis / Hips
    hips = bpy.data.objects.new("Hips", None)
    hips.parent = root
    hips.location = (0.0, 0.0, 0.52)
    coll.objects.link(hips)

    # 2. Torso (Solid rounded cylinder/egg with navy tunic and gold chest crest)
    torso_obj = create_cylinder_mesh("Torso_Mesh", radius=0.28, depth=0.36, segments=10, collection=coll, smooth=True)
    torso_obj.parent = hips
    torso_obj.location = (0.0, 0.0, 0.16)
    torso_obj.data.materials.append(mat_tunic)

    # Breastplate / Chest Armor Plate
    breastplate = create_uv_sphere_mesh("Breastplate_Mesh", radius=0.25, segments=8, ring_count=6, collection=coll, smooth=True)
    breastplate.parent = torso_obj
    breastplate.location = (0.0, -0.10, 0.04)
    breastplate.scale = (0.95, 0.6, 0.85)
    breastplate.data.materials.append(mat_steel)

    # Gold Cross Crest
    crest = create_cube_mesh("Chest_Crest", size=(0.14, 0.04, 0.14), collection=coll, smooth=False)
    crest.parent = breastplate
    crest.location = (0.0, -0.22, 0.02)
    crest.data.materials.append(mat_gold)

    # Belt
    belt = create_cylinder_mesh("Belt_Mesh", radius=0.30, depth=0.08, segments=10, collection=coll, smooth=False)
    belt.parent = hips
    belt.location = (0.0, 0.0, -0.02)
    belt.data.materials.append(mat_leather)
    
    buckle = create_cube_mesh("Belt_Buckle", size=(0.08, 0.04, 0.08), collection=coll, smooth=False)
    buckle.parent = belt
    buckle.location = (0.0, -0.30, 0.0)
    buckle.data.materials.append(mat_gold)

    # 3. Head & Helmet (Large spherical helm with visor slit, crest, and cheekplates)
    head_joint = bpy.data.objects.new("Head_Joint", None)
    head_joint.parent = torso_obj
    head_joint.location = (0.0, 0.0, 0.32)
    coll.objects.link(head_joint)

    # Helmet Dome (Major volume)
    helmet_dome = create_uv_sphere_mesh("Helmet_Dome", radius=0.36, segments=12, ring_count=8, collection=coll, smooth=True)
    helmet_dome.parent = head_joint
    helmet_dome.location = (0.0, 0.0, 0.22)
    helmet_dome.scale = (0.98, 1.05, 1.02)
    helmet_dome.data.materials.append(mat_steel)

    # Visor Slit (Dark aperture with high-specular / subtle gleam)
    visor = create_cube_mesh("Visor_Slit", size=(0.36, 0.08, 0.07), collection=coll, smooth=False)
    visor.parent = helmet_dome
    visor.location = (0.0, -0.32, -0.02)
    visor.data.materials.append(mat_visor)

    # Helmet Top Crest / Ridge (Gold fin)
    crest_ridge = create_cube_mesh("Helmet_Crest", size=(0.06, 0.42, 0.16), collection=coll, smooth=False)
    crest_ridge.parent = helmet_dome
    crest_ridge.location = (0.0, -0.02, 0.34)
    crest_ridge.data.materials.append(mat_gold)

    # Helmet Cheekguards / Cowl
    cheek_l = create_cube_mesh("Cheek_L", size=(0.08, 0.18, 0.20), collection=coll, smooth=True)
    cheek_l.parent = helmet_dome
    cheek_l.location = (-0.32, -0.12, -0.12)
    cheek_l.rotation_euler = (0.0, math.radians(15), math.radians(-10))
    cheek_l.data.materials.append(mat_dark_steel)

    cheek_r = create_cube_mesh("Cheek_R", size=(0.08, 0.18, 0.20), collection=coll, smooth=True)
    cheek_r.parent = helmet_dome
    cheek_r.location = (0.32, -0.12, -0.12)
    cheek_r.rotation_euler = (0.0, math.radians(-15), math.radians(10))
    cheek_r.data.materials.append(mat_dark_steel)

    # 4. Shoulders & Arms
    shoulder_l = bpy.data.objects.new("Shoulder_L", None)
    shoulder_l.parent = torso_obj
    shoulder_l.location = (-0.36, 0.0, 0.18)
    coll.objects.link(shoulder_l)

    pauldron_l = create_uv_sphere_mesh("Pauldron_L_Mesh", radius=0.18, segments=8, ring_count=6, collection=coll, smooth=True)
    pauldron_l.parent = shoulder_l
    pauldron_l.scale = (1.1, 1.1, 0.85)
    pauldron_l.data.materials.append(mat_steel)

    arm_l = create_cylinder_mesh("Arm_L_Mesh", radius=0.09, depth=0.22, segments=6, collection=coll, smooth=True)
    arm_l.parent = shoulder_l
    arm_l.location = (-0.04, 0.0, -0.16)
    arm_l.data.materials.append(mat_tunic)

    hand_l = create_uv_sphere_mesh("Hand_L_Mesh", radius=0.10, segments=6, ring_count=5, collection=coll, smooth=True)
    hand_l.parent = arm_l
    hand_l.location = (0.0, 0.0, -0.14)
    hand_l.data.materials.append(mat_dark_steel)

    shield = create_cylinder_mesh("Shield_Mesh", radius=0.24, depth=0.05, segments=10, collection=coll, smooth=True)
    shield.parent = hand_l
    shield.location = (-0.12, -0.06, 0.04)
    shield.rotation_euler = (math.radians(20), math.radians(75), math.radians(10))
    shield.data.materials.append(mat_steel)

    shield_boss = create_uv_sphere_mesh("Shield_Boss", radius=0.08, segments=6, ring_count=5, collection=coll, smooth=True)
    shield_boss.parent = shield
    shield_boss.location = (0.0, 0.0, 0.04)
    shield_boss.data.materials.append(mat_gold)

    shoulder_r = bpy.data.objects.new("Shoulder_R", None)
    shoulder_r.parent = torso_obj
    shoulder_r.location = (0.36, 0.0, 0.18)
    coll.objects.link(shoulder_r)

    pauldron_r = create_uv_sphere_mesh("Pauldron_R_Mesh", radius=0.18, segments=8, ring_count=6, collection=coll, smooth=True)
    pauldron_r.parent = shoulder_r
    pauldron_r.scale = (1.1, 1.1, 0.85)
    pauldron_r.data.materials.append(mat_steel)

    arm_r = create_cylinder_mesh("Arm_R_Mesh", radius=0.09, depth=0.22, segments=6, collection=coll, smooth=True)
    arm_r.parent = shoulder_r
    arm_r.location = (0.04, 0.0, -0.16)
    arm_r.data.materials.append(mat_tunic)

    hand_r = create_uv_sphere_mesh("Hand_R_Mesh", radius=0.10, segments=6, ring_count=5, collection=coll, smooth=True)
    hand_r.parent = arm_r
    hand_r.location = (0.0, 0.0, -0.14)
    hand_r.data.materials.append(mat_dark_steel)

    sword_hilt = create_cylinder_mesh("Sword_Hilt", radius=0.03, depth=0.16, segments=6, collection=coll, smooth=False)
    sword_hilt.parent = hand_r
    sword_hilt.location = (0.04, -0.06, -0.02)
    sword_hilt.rotation_euler = (math.radians(65), math.radians(10), math.radians(-25))
    sword_hilt.data.materials.append(mat_gold)

    sword_cross = create_cube_mesh("Sword_Cross", size=(0.20, 0.05, 0.05), collection=coll, smooth=False)
    sword_cross.parent = sword_hilt
    sword_cross.location = (0.0, 0.0, 0.08)
    sword_cross.data.materials.append(mat_gold)

    sword_blade = create_cube_mesh("Sword_Blade", size=(0.10, 0.03, 0.46), collection=coll, smooth=False)
    sword_blade.parent = sword_cross
    sword_blade.location = (0.0, 0.0, 0.24)
    sword_blade.data.materials.append(mat_steel)

    # 5. Legs & Boots
    leg_l = bpy.data.objects.new("Leg_L", None)
    leg_l.parent = hips
    leg_l.location = (-0.16, 0.0, -0.08)
    coll.objects.link(leg_l)

    boot_l = create_uv_sphere_mesh("Boot_L_Mesh", radius=0.15, segments=8, ring_count=6, collection=coll, smooth=True)
    boot_l.parent = leg_l
    boot_l.location = (0.0, -0.04, -0.26)
    boot_l.scale = (0.9, 1.35, 0.95)
    boot_l.data.materials.append(mat_dark_steel)

    toe_l = create_cube_mesh("Toe_L_Mesh", size=(0.14, 0.16, 0.10), collection=coll, smooth=True)
    toe_l.parent = boot_l
    toe_l.location = (0.0, -0.12, -0.06)
    toe_l.data.materials.append(mat_steel)

    leg_r = bpy.data.objects.new("Leg_R", None)
    leg_r.parent = hips
    leg_r.location = (0.16, 0.0, -0.08)
    coll.objects.link(leg_r)

    boot_r = create_uv_sphere_mesh("Boot_R_Mesh", radius=0.15, segments=8, ring_count=6, collection=coll, smooth=True)
    boot_r.parent = leg_r
    boot_r.location = (0.0, -0.04, -0.26)
    boot_r.scale = (0.9, 1.35, 0.95)
    boot_r.data.materials.append(mat_dark_steel)

    toe_r = create_cube_mesh("Toe_R_Mesh", size=(0.14, 0.16, 0.10), collection=coll, smooth=True)
    toe_r.parent = boot_r
    toe_r.location = (0.0, -0.12, -0.06)
    toe_r.data.materials.append(mat_steel)

    # 6. Author Animation Actions
    idle_keys = {
        "Hips": {
            "location": [
                (1, Vector((0.0, 0.0, 0.52))),
                (16, Vector((0.0, 0.0, 0.50))),
                (32, Vector((0.0, 0.0, 0.52))),
            ]
        },
        "Head_Joint": {
            "rotation_euler": [
                (1, Euler((0.0, 0.0, 0.0))),
                (16, Euler((math.radians(3), 0.0, 0.0))),
                (32, Euler((0.0, 0.0, 0.0))),
            ]
        },
        "Shoulder_L": {
            "rotation_euler": [
                (1, Euler((math.radians(-5), math.radians(5), 0.0))),
                (16, Euler((math.radians(-2), math.radians(8), 0.0))),
                (32, Euler((math.radians(-5), math.radians(5), 0.0))),
            ]
        },
        "Shoulder_R": {
            "rotation_euler": [
                (1, Euler((math.radians(5), math.radians(-5), 0.0))),
                (16, Euler((math.radians(2), math.radians(-8), 0.0))),
                (32, Euler((math.radians(5), math.radians(-5), 0.0))),
            ]
        },
    }
    build_action_tracks(root, "Knight_Idle", idle_keys, 32)

    walk_keys = {
        "Hips": {
            "location": [
                (1, Vector((0.0, 0.0, 0.52))),
                (5, Vector((0.0, 0.0, 0.55))),
                (9, Vector((0.0, 0.0, 0.52))),
                (13, Vector((0.0, 0.0, 0.55))),
                (17, Vector((0.0, 0.0, 0.52))),
            ],
            "rotation_euler": [
                (1, Euler((0.0, 0.0, math.radians(6)))),
                (9, Euler((0.0, 0.0, math.radians(-6)))),
                (17, Euler((0.0, 0.0, math.radians(6)))),
            ],
        },
        "Leg_L": {
            "rotation_euler": [
                (1, Euler((math.radians(28), 0.0, 0.0))),
                (5, Euler((math.radians(0), 0.0, 0.0))),
                (9, Euler((math.radians(-28), 0.0, 0.0))),
                (13, Euler((math.radians(0), 0.0, 0.0))),
                (17, Euler((math.radians(28), 0.0, 0.0))),
            ],
            "location": [
                (1, Vector((-0.16, -0.06, -0.08))),
                (5, Vector((-0.16, 0.0, -0.04))),
                (9, Vector((-0.16, 0.08, -0.08))),
                (13, Vector((-0.16, 0.0, -0.06))),
                (17, Vector((-0.16, -0.06, -0.08))),
            ],
        },
        "Leg_R": {
            "rotation_euler": [
                (1, Euler((math.radians(-28), 0.0, 0.0))),
                (5, Euler((math.radians(0), 0.0, 0.0))),
                (9, Euler((math.radians(28), 0.0, 0.0))),
                (13, Euler((math.radians(0), 0.0, 0.0))),
                (17, Euler((math.radians(-28), 0.0, 0.0))),
            ],
            "location": [
                (1, Vector((0.16, 0.08, -0.08))),
                (5, Vector((0.16, 0.0, -0.06))),
                (9, Vector((0.16, -0.06, -0.08))),
                (13, Vector((0.16, 0.0, -0.04))),
                (17, Vector((0.16, 0.08, -0.08))),
            ],
        },
        "Shoulder_L": {
            "rotation_euler": [
                (1, Euler((math.radians(-22), 0.0, 0.0))),
                (9, Euler((math.radians(18), 0.0, 0.0))),
                (17, Euler((math.radians(-22), 0.0, 0.0))),
            ]
        },
        "Shoulder_R": {
            "rotation_euler": [
                (1, Euler((math.radians(24), 0.0, 0.0))),
                (9, Euler((math.radians(-20), 0.0, 0.0))),
                (17, Euler((math.radians(24), 0.0, 0.0))),
            ]
        },
    }
    build_action_tracks(root, "Knight_Walk", walk_keys, 16)

    gesture_keys = {
        "Head_Joint": {
            "rotation_euler": [
                (1, Euler((0.0, 0.0, 0.0))),
                (8, Euler((math.radians(-8), 0.0, math.radians(-10)))),
                (16, Euler((math.radians(5), 0.0, math.radians(5)))),
                (24, Euler((0.0, 0.0, 0.0))),
            ]
        },
        "Shoulder_R": {
            "rotation_euler": [
                (1, Euler((0.0, 0.0, 0.0))),
                (8, Euler((math.radians(-55), math.radians(20), math.radians(35)))),
                (16, Euler((math.radians(-70), math.radians(30), math.radians(45)))),
                (24, Euler((0.0, 0.0, 0.0))),
            ]
        },
    }
    build_action_tracks(root, "Knight_Gesture", gesture_keys, 24)

    out_blend = AUTHORING_DIR / "knight_volumetric.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    print(f"SAVED: {out_blend}")
    return out_blend


# ==============================================================================
# APPROACH B: GRAPHIC / FACETED (THE ROGUE)
# ==============================================================================

def build_rogue_faceted():
    """Build Approach B: Graphic/Faceted Rogue with sharp planes, asymmetrical cowl, and crisp light breaks."""
    asset_core.reset_scene()
    setup_studio_environment()

    coll = asset_core.ensure_collection("Rogue_Model")

    # Materials
    mat_cloak = make_char_material("Mat_ShadowCloak", (0.10, 0.09, 0.14), metallic=0.0, roughness=0.92)
    mat_inner_cloak = make_char_material("Mat_InnerCloak", (0.32, 0.12, 0.16), metallic=0.0, roughness=0.88)
    mat_leather = make_char_material("Mat_RogueLeather", (0.42, 0.26, 0.16), metallic=0.0, roughness=0.65)
    mat_dark_leather = make_char_material("Mat_DarkLeather", (0.18, 0.14, 0.12), metallic=0.0, roughness=0.75)
    mat_skin = make_char_material("Mat_FaceSkin", (0.88, 0.72, 0.62), metallic=0.0, roughness=0.55)
    mat_gold_accent = make_char_material("Mat_RogueGold", (0.88, 0.70, 0.18), metallic=0.92, roughness=0.22)
    mat_dagger_steel = make_char_material("Mat_DaggerSteel", (0.75, 0.80, 0.88), metallic=0.95, roughness=0.15)
    mat_eye_glow = make_char_material("Mat_EyeGlow", (0.2, 0.9, 0.7), metallic=0.0, roughness=0.2, emission=(0.2, 1.0, 0.8), emission_strength=2.0)

    # 1. Root & Hips
    root = bpy.data.objects.new("Rogue_Root", None)
    root.empty_display_type = "ARROWS"
    coll.objects.link(root)
    asset_core.tag_asset_target(
        root,
        asset_id="rogue_faceted",
        representation="full_model",
        role="preview_only",
        authoring_space="item_display",
        placement_frame="floor_center",
        states=["default", "idle", "walk", "gesture"],
        default_state="default",
    )
    root["sr_source_authority"] = "blend"
    root["character_archetype"] = "graphic_faceted"

    create_contact_shadow_disc(root, coll, radius=0.38)

    hips = bpy.data.objects.new("Hips", None)
    hips.parent = root
    hips.location = (0.0, 0.0, 0.48)
    coll.objects.link(hips)

    # 2. Torso
    torso_obj = create_cylinder_mesh("Torso_Mesh", radius=0.22, depth=0.34, segments=6, collection=coll, smooth=False)
    torso_obj.parent = hips
    torso_obj.location = (0.0, 0.0, 0.15)
    torso_obj.data.materials.append(mat_leather)

    chest_strap = create_cube_mesh("Chest_Strap", size=(0.26, 0.06, 0.06), collection=coll, smooth=False)
    chest_strap.parent = torso_obj
    chest_strap.location = (0.0, -0.16, 0.04)
    chest_strap.rotation_euler = (0.0, 0.0, math.radians(-35))
    chest_strap.data.materials.append(mat_dark_leather)

    buckle = create_cube_mesh("Chest_Buckle", size=(0.06, 0.04, 0.06), collection=coll, smooth=False)
    buckle.parent = chest_strap
    buckle.location = (0.0, -0.04, 0.0)
    buckle.data.materials.append(mat_gold_accent)

    belt = create_cylinder_mesh("Belt_Mesh", radius=0.24, depth=0.06, segments=6, collection=coll, smooth=False)
    belt.parent = hips
    belt.location = (0.0, 0.0, -0.02)
    belt.data.materials.append(mat_dark_leather)

    # 3. Head & Hood
    head_joint = bpy.data.objects.new("Head_Joint", None)
    head_joint.parent = torso_obj
    head_joint.location = (0.0, 0.0, 0.30)
    coll.objects.link(head_joint)

    face_mesh = create_cube_mesh("Face_Plane", size=(0.22, 0.12, 0.20), collection=coll, smooth=False)
    face_mesh.parent = head_joint
    face_mesh.location = (0.0, -0.12, 0.16)
    face_mesh.data.materials.append(mat_skin)

    eye_l = create_cube_mesh("Eye_L", size=(0.04, 0.02, 0.03), collection=coll, smooth=False)
    eye_l.parent = face_mesh
    eye_l.location = (-0.06, -0.07, 0.02)
    eye_l.data.materials.append(mat_eye_glow)

    eye_r = create_cube_mesh("Eye_R", size=(0.04, 0.02, 0.03), collection=coll, smooth=False)
    eye_r.parent = face_mesh
    eye_r.location = (0.06, -0.07, 0.02)
    eye_r.data.materials.append(mat_eye_glow)

    hood = create_cone_mesh("Hood_Peaked", radius1=0.34, radius2=0.04, depth=0.48, segments=7, collection=coll, smooth=False)
    hood.parent = head_joint
    hood.location = (0.0, 0.04, 0.24)
    hood.rotation_euler = (math.radians(-15), math.radians(8), 0.0)
    hood.data.materials.append(mat_cloak)

    collar_l = create_cube_mesh("Collar_Wing_L", size=(0.08, 0.22, 0.20), collection=coll, smooth=False)
    collar_l.parent = head_joint
    collar_l.location = (-0.24, -0.06, 0.08)
    collar_l.rotation_euler = (math.radians(10), math.radians(-25), math.radians(15))
    collar_l.data.materials.append(mat_inner_cloak)

    collar_r = create_cube_mesh("Collar_Wing_R", size=(0.08, 0.16, 0.14), collection=coll, smooth=False)
    collar_r.parent = head_joint
    collar_r.location = (0.22, -0.04, 0.06)
    collar_r.rotation_euler = (math.radians(10), math.radians(20), math.radians(-10))
    collar_r.data.materials.append(mat_cloak)

    # 4. Cape & Arms
    cape_root = bpy.data.objects.new("Cape_Root", None)
    cape_root.parent = torso_obj
    cape_root.location = (0.0, 0.14, 0.22)
    coll.objects.link(cape_root)

    cape_panel = create_cube_mesh("Cape_Panel", size=(0.38, 0.04, 0.52), collection=coll, smooth=False)
    cape_panel.parent = cape_root
    cape_panel.location = (-0.08, 0.06, -0.22)
    cape_panel.rotation_euler = (math.radians(12), math.radians(-10), math.radians(5))
    cape_panel.data.materials.append(mat_cloak)

    shoulder_l = bpy.data.objects.new("Shoulder_L", None)
    shoulder_l.parent = torso_obj
    shoulder_l.location = (-0.28, 0.0, 0.16)
    coll.objects.link(shoulder_l)

    arm_l = create_cylinder_mesh("Arm_L_Mesh", radius=0.07, depth=0.22, segments=5, collection=coll, smooth=False)
    arm_l.parent = shoulder_l
    arm_l.location = (-0.04, 0.0, -0.14)
    arm_l.data.materials.append(mat_cloak)

    hand_l = create_cube_mesh("Hand_L_Mesh", size=(0.10, 0.10, 0.10), collection=coll, smooth=False)
    hand_l.parent = arm_l
    hand_l.location = (0.0, 0.0, -0.14)
    hand_l.data.materials.append(mat_dark_leather)

    dagger_l = create_cube_mesh("Dagger_Blade_L", size=(0.04, 0.02, 0.32), collection=coll, smooth=False)
    dagger_l.parent = hand_l
    dagger_l.location = (0.02, -0.06, -0.08)
    dagger_l.rotation_euler = (math.radians(-65), math.radians(15), 0.0)
    dagger_l.data.materials.append(mat_dagger_steel)

    shoulder_r = bpy.data.objects.new("Shoulder_R", None)
    shoulder_r.parent = torso_obj
    shoulder_r.location = (0.28, 0.0, 0.16)
    coll.objects.link(shoulder_r)

    arm_r = create_cylinder_mesh("Arm_R_Mesh", radius=0.07, depth=0.22, segments=5, collection=coll, smooth=False)
    arm_r.parent = shoulder_r
    arm_r.location = (0.04, 0.0, -0.14)
    arm_r.data.materials.append(mat_leather)

    hand_r = create_cube_mesh("Hand_R_Mesh", size=(0.10, 0.10, 0.10), collection=coll, smooth=False)
    hand_r.parent = arm_r
    hand_r.location = (0.0, 0.0, -0.14)
    hand_r.data.materials.append(mat_dark_leather)

    # 5. Legs & Boots
    leg_l = bpy.data.objects.new("Leg_L", None)
    leg_l.parent = hips
    leg_l.location = (-0.14, 0.0, -0.06)
    coll.objects.link(leg_l)

    boot_l = create_cube_mesh("Boot_L_Mesh", size=(0.14, 0.22, 0.26), collection=coll, smooth=False)
    boot_l.parent = leg_l
    boot_l.location = (0.0, -0.04, -0.22)
    boot_l.data.materials.append(mat_dark_leather)

    leg_r = bpy.data.objects.new("Leg_R", None)
    leg_r.parent = hips
    leg_r.location = (0.14, 0.0, -0.06)
    coll.objects.link(leg_r)

    boot_r = create_cube_mesh("Boot_R_Mesh", size=(0.14, 0.22, 0.26), collection=coll, smooth=False)
    boot_r.parent = leg_r
    boot_r.location = (0.0, -0.04, -0.22)
    boot_r.data.materials.append(mat_dark_leather)

    # 6. Actions
    idle_keys = {
        "Hips": {
            "location": [
                (1, Vector((0.0, 0.0, 0.48))),
                (16, Vector((0.0, 0.0, 0.46))),
                (32, Vector((0.0, 0.0, 0.48))),
            ],
            "rotation_euler": [
                (1, Euler((0.0, 0.0, math.radians(-5)))),
                (16, Euler((0.0, 0.0, math.radians(-3)))),
                (32, Euler((0.0, 0.0, math.radians(-5)))),
            ]
        },
        "Cape_Root": {
            "rotation_euler": [
                (1, Euler((0.0, 0.0, 0.0))),
                (16, Euler((math.radians(6), math.radians(-4), 0.0))),
                (32, Euler((0.0, 0.0, 0.0))),
            ]
        },
        "Shoulder_L": {
            "rotation_euler": [
                (1, Euler((math.radians(10), math.radians(5), 0.0))),
                (16, Euler((math.radians(15), math.radians(8), 0.0))),
                (32, Euler((math.radians(10), math.radians(5), 0.0))),
            ]
        },
    }
    build_action_tracks(root, "Rogue_Idle", idle_keys, 32)

    walk_keys = {
        "Hips": {
            "location": [
                (1, Vector((0.0, 0.0, 0.48))),
                (5, Vector((0.0, 0.0, 0.51))),
                (9, Vector((0.0, 0.0, 0.48))),
                (13, Vector((0.0, 0.0, 0.51))),
                (17, Vector((0.0, 0.0, 0.48))),
            ],
            "rotation_euler": [
                (1, Euler((0.0, 0.0, math.radians(-8)))),
                (9, Euler((0.0, 0.0, math.radians(8)))),
                (17, Euler((0.0, 0.0, math.radians(-8)))),
            ],
        },
        "Leg_L": {
            "rotation_euler": [
                (1, Euler((math.radians(32), 0.0, 0.0))),
                (9, Euler((math.radians(-30), 0.0, 0.0))),
                (17, Euler((math.radians(32), 0.0, 0.0))),
            ],
            "location": [
                (1, Vector((-0.14, -0.08, -0.06))),
                (9, Vector((-0.14, 0.08, -0.06))),
                (17, Vector((-0.14, -0.08, -0.06))),
            ],
        },
        "Leg_R": {
            "rotation_euler": [
                (1, Euler((math.radians(-30), 0.0, 0.0))),
                (9, Euler((math.radians(32), 0.0, 0.0))),
                (17, Euler((math.radians(-30), 0.0, 0.0))),
            ],
            "location": [
                (1, Vector((0.14, 0.08, -0.06))),
                (9, Vector((0.14, -0.08, -0.06))),
                (17, Vector((0.14, 0.08, -0.06))),
            ],
        },
        "Cape_Root": {
            "rotation_euler": [
                (1, Euler((math.radians(15), math.radians(-10), 0.0))),
                (9, Euler((math.radians(20), math.radians(10), 0.0))),
                (17, Euler((math.radians(15), math.radians(-10), 0.0))),
            ]
        },
        "Shoulder_L": {
            "rotation_euler": [
                (1, Euler((math.radians(-25), 0.0, 0.0))),
                (9, Euler((math.radians(25), 0.0, 0.0))),
                (17, Euler((math.radians(-25), 0.0, 0.0))),
            ]
        },
        "Shoulder_R": {
            "rotation_euler": [
                (1, Euler((math.radians(25), 0.0, 0.0))),
                (9, Euler((math.radians(-25), 0.0, 0.0))),
                (17, Euler((math.radians(25), 0.0, 0.0))),
            ]
        },
    }
    build_action_tracks(root, "Rogue_Walk", walk_keys, 16)

    gesture_keys = {
        "Shoulder_L": {
            "rotation_euler": [
                (1, Euler((0.0, 0.0, 0.0))),
                (8, Euler((math.radians(-65), math.radians(25), math.radians(-20)))),
                (16, Euler((math.radians(-85), math.radians(35), math.radians(-30)))),
                (24, Euler((0.0, 0.0, 0.0))),
            ]
        },
        "Head_Joint": {
            "rotation_euler": [
                (1, Euler((0.0, 0.0, 0.0))),
                (8, Euler((math.radians(10), 0.0, math.radians(-15)))),
                (16, Euler((math.radians(12), 0.0, math.radians(-20)))),
                (24, Euler((0.0, 0.0, 0.0))),
            ]
        },
    }
    build_action_tracks(root, "Rogue_Gesture", gesture_keys, 24)

    out_blend = AUTHORING_DIR / "rogue_faceted.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    print(f"SAVED: {out_blend}")
    return out_blend


# ==============================================================================
# APPROACH C: RENDERED-SPRITE / COMPRESSED DEPTH (THE MAGE)
# ==============================================================================

def build_mage_planar():
    """Build Approach C: Mage optimized for elevated camera with wide hat brim, floating focus orb, and detached pieces."""
    asset_core.reset_scene()
    setup_studio_environment()

    coll = asset_core.ensure_collection("Mage_Model")

    # Materials
    mat_robe = make_char_material("Mat_IndigoRobe", (0.14, 0.12, 0.32), metallic=0.0, roughness=0.85)
    mat_gold_trim = make_char_material("Mat_MageGold", (0.92, 0.75, 0.22), metallic=0.88, roughness=0.25)
    mat_skin = make_char_material("Mat_MageSkin", (0.90, 0.78, 0.70), metallic=0.0, roughness=0.6)
    mat_orb_glow = make_char_material("Mat_OrbGlow", (0.1, 0.8, 1.0), metallic=0.1, roughness=0.1, emission=(0.15, 0.9, 1.2), emission_strength=2.8)
    mat_staff_wood = make_char_material("Mat_StaffWood", (0.28, 0.18, 0.12), metallic=0.0, roughness=0.8)

    # 1. Root & Hips
    root = bpy.data.objects.new("Mage_Root", None)
    root.empty_display_type = "ARROWS"
    coll.objects.link(root)
    asset_core.tag_asset_target(
        root,
        asset_id="mage_planar",
        representation="full_model",
        role="preview_only",
        authoring_space="item_display",
        placement_frame="floor_center",
        states=["default", "idle", "walk", "gesture"],
        default_state="default",
    )
    root["sr_source_authority"] = "blend"
    root["character_archetype"] = "rendered_sprite_compressed"

    create_contact_shadow_disc(root, coll, radius=0.44)

    hips = bpy.data.objects.new("Hips", None)
    hips.parent = root
    hips.location = (0.0, 0.0, 0.44)
    coll.objects.link(hips)

    # 2. Robe Cone & Mantle
    robe_skirt = create_cone_mesh("Robe_Skirt", radius1=0.34, radius2=0.18, depth=0.48, segments=10, collection=coll, smooth=True)
    robe_skirt.parent = hips
    robe_skirt.location = (0.0, 0.0, -0.06)
    robe_skirt.data.materials.append(mat_robe)

    skirt_trim = create_cylinder_mesh("Skirt_GoldTrim", radius=0.35, depth=0.06, segments=10, collection=coll, smooth=True)
    skirt_trim.parent = robe_skirt
    skirt_trim.location = (0.0, 0.0, -0.22)
    skirt_trim.data.materials.append(mat_gold_trim)

    torso_obj = create_cylinder_mesh("Torso_Mesh", radius=0.20, depth=0.28, segments=8, collection=coll, smooth=True)
    torso_obj.parent = hips
    torso_obj.location = (0.0, 0.0, 0.18)
    torso_obj.data.materials.append(mat_robe)

    mantle = create_cylinder_mesh("Mantle_Layer", radius=0.38, depth=0.06, segments=10, collection=coll, smooth=True)
    mantle.parent = torso_obj
    mantle.location = (0.0, 0.0, 0.12)
    mantle.scale = (1.1, 0.85, 1.0)
    mantle.data.materials.append(mat_gold_trim)

    # 3. Head & Wizard Hat
    head_joint = bpy.data.objects.new("Head_Joint", None)
    head_joint.parent = torso_obj
    head_joint.location = (0.0, 0.0, 0.26)
    coll.objects.link(head_joint)

    face_sphere = create_uv_sphere_mesh("Face_Sphere", radius=0.18, segments=8, ring_count=6, collection=coll, smooth=True)
    face_sphere.parent = head_joint
    face_sphere.location = (0.0, -0.06, 0.08)
    face_sphere.data.materials.append(mat_skin)

    hat_brim = create_cylinder_mesh("Hat_Brim", radius=0.48, depth=0.04, segments=12, collection=coll, smooth=True)
    hat_brim.parent = head_joint
    hat_brim.location = (0.0, 0.0, 0.18)
    hat_brim.rotation_euler = (math.radians(12), 0.0, 0.0)
    hat_brim.data.materials.append(mat_robe)

    hat_brim_gold = create_cylinder_mesh("Hat_Brim_GoldEdge", radius=0.49, depth=0.02, segments=12, collection=coll, smooth=True)
    hat_brim_gold.parent = hat_brim
    hat_brim_gold.location = (0.0, 0.0, 0.0)
    hat_brim_gold.data.materials.append(mat_gold_trim)

    hat_crown = create_cone_mesh("Hat_Crown", radius1=0.26, radius2=0.03, depth=0.44, segments=8, collection=coll, smooth=True)
    hat_crown.parent = hat_brim
    hat_crown.location = (0.0, 0.04, 0.22)
    hat_crown.rotation_euler = (math.radians(-18), math.radians(6), 0.0)
    hat_crown.data.materials.append(mat_robe)

    hat_band = create_cylinder_mesh("Hat_Band", radius=0.27, depth=0.06, segments=8, collection=coll, smooth=True)
    hat_band.parent = hat_brim
    hat_band.location = (0.0, 0.02, 0.05)
    hat_band.data.materials.append(mat_gold_trim)

    # 4. Detached Floating Hands & Floating Orb
    hand_l_joint = bpy.data.objects.new("Hand_L_Joint", None)
    hand_l_joint.parent = torso_obj
    hand_l_joint.location = (-0.32, -0.18, 0.06)
    coll.objects.link(hand_l_joint)

    sleeve_l = create_cylinder_mesh("Sleeve_L", radius=0.12, depth=0.18, segments=6, collection=coll, smooth=True)
    sleeve_l.parent = hand_l_joint
    sleeve_l.rotation_euler = (math.radians(45), 0.0, math.radians(-20))
    sleeve_l.data.materials.append(mat_robe)

    hand_l = create_uv_sphere_mesh("Hand_L_Mesh", radius=0.08, segments=6, ring_count=5, collection=coll, smooth=True)
    hand_l.parent = sleeve_l
    hand_l.location = (0.0, 0.0, -0.10)
    hand_l.data.materials.append(mat_skin)

    orb_joint = bpy.data.objects.new("Orb_Joint", None)
    orb_joint.parent = hand_l_joint
    orb_joint.location = (-0.06, -0.14, 0.16)
    coll.objects.link(orb_joint)

    orb_mesh = create_uv_sphere_mesh("Orb_Core", radius=0.12, segments=8, ring_count=6, collection=coll, smooth=True)
    orb_mesh.parent = orb_joint
    orb_mesh.data.materials.append(mat_orb_glow)

    orb_ring = create_cylinder_mesh("Orb_Ring", radius=0.16, depth=0.02, segments=10, collection=coll, smooth=True)
    orb_ring.parent = orb_mesh
    orb_ring.rotation_euler = (math.radians(35), math.radians(45), 0.0)
    orb_ring.data.materials.append(mat_gold_trim)

    hand_r_joint = bpy.data.objects.new("Hand_R_Joint", None)
    hand_r_joint.parent = torso_obj
    hand_r_joint.location = (0.32, -0.12, 0.04)
    coll.objects.link(hand_r_joint)

    sleeve_r = create_cylinder_mesh("Sleeve_R", radius=0.12, depth=0.18, segments=6, collection=coll, smooth=True)
    sleeve_r.parent = hand_r_joint
    sleeve_r.rotation_euler = (math.radians(35), 0.0, math.radians(20))
    sleeve_r.data.materials.append(mat_robe)

    hand_r = create_uv_sphere_mesh("Hand_R_Mesh", radius=0.08, segments=6, ring_count=5, collection=coll, smooth=True)
    hand_r.parent = sleeve_r
    hand_r.location = (0.0, 0.0, -0.10)
    hand_r.data.materials.append(mat_skin)

    staff_shaft = create_cylinder_mesh("Staff_Shaft", radius=0.03, depth=1.10, segments=6, collection=coll, smooth=False)
    staff_shaft.parent = hand_r
    staff_shaft.location = (0.04, -0.04, 0.12)
    staff_shaft.rotation_euler = (math.radians(15), math.radians(-10), 0.0)
    staff_shaft.data.materials.append(mat_staff_wood)

    staff_head = create_uv_sphere_mesh("Staff_Crystal", radius=0.09, segments=6, ring_count=5, collection=coll, smooth=True)
    staff_head.parent = staff_shaft
    staff_head.location = (0.0, 0.0, 0.54)
    staff_head.data.materials.append(mat_orb_glow)

    # 5. Actions
    idle_keys = {
        "Hips": {
            "location": [
                (1, Vector((0.0, 0.0, 0.44))),
                (16, Vector((0.0, 0.0, 0.42))),
                (32, Vector((0.0, 0.0, 0.44))),
            ]
        },
        "Orb_Joint": {
            "location": [
                (1, Vector((-0.06, -0.14, 0.16))),
                (16, Vector((-0.06, -0.14, 0.22))),
                (32, Vector((-0.06, -0.14, 0.16))),
            ],
            "rotation_euler": [
                (1, Euler((0.0, 0.0, 0.0))),
                (16, Euler((0.0, math.radians(90), math.radians(45)))),
                (32, Euler((0.0, math.radians(180), math.radians(90)))),
            ]
        },
        "Hand_L_Joint": {
            "location": [
                (1, Vector((-0.32, -0.18, 0.06))),
                (16, Vector((-0.32, -0.18, 0.09))),
                (32, Vector((-0.32, -0.18, 0.06))),
            ]
        },
    }
    build_action_tracks(root, "Mage_Idle", idle_keys, 32)

    walk_keys = {
        "Hips": {
            "location": [
                (1, Vector((0.0, 0.0, 0.44))),
                (5, Vector((0.0, 0.0, 0.47))),
                (9, Vector((0.0, 0.0, 0.44))),
                (13, Vector((0.0, 0.0, 0.47))),
                (17, Vector((0.0, 0.0, 0.44))),
            ],
            "rotation_euler": [
                (1, Euler((0.0, math.radians(4), math.radians(-5)))),
                (9, Euler((0.0, math.radians(-4), math.radians(5)))),
                (17, Euler((0.0, math.radians(4), math.radians(-5)))),
            ],
        },
        "Robe_Skirt": {
            "rotation_euler": [
                (1, Euler((math.radians(-6), 0.0, math.radians(-8)))),
                (9, Euler((math.radians(6), 0.0, math.radians(8)))),
                (17, Euler((math.radians(-6), 0.0, math.radians(-8)))),
            ]
        },
        "Orb_Joint": {
            "location": [
                (1, Vector((-0.06, -0.14, 0.15))),
                (9, Vector((-0.06, -0.14, 0.24))),
                (17, Vector((-0.06, -0.14, 0.15))),
            ]
        },
        "Hand_R_Joint": {
            "rotation_euler": [
                (1, Euler((math.radians(18), 0.0, 0.0))),
                (9, Euler((math.radians(-18), 0.0, 0.0))),
                (17, Euler((math.radians(18), 0.0, 0.0))),
            ]
        },
    }
    build_action_tracks(root, "Mage_Walk", walk_keys, 16)

    gesture_keys = {
        "Orb_Joint": {
            "location": [
                (1, Vector((-0.06, -0.14, 0.16))),
                (10, Vector((-0.10, -0.26, 0.38))),
                (18, Vector((-0.12, -0.30, 0.42))),
                (24, Vector((-0.06, -0.14, 0.16))),
            ],
            "scale": [
                (1, Vector((1.0, 1.0, 1.0))),
                (14, Vector((1.45, 1.45, 1.45))),
                (24, Vector((1.0, 1.0, 1.0))),
            ]
        },
        "Hand_L_Joint": {
            "location": [
                (1, Vector((-0.32, -0.18, 0.06))),
                (10, Vector((-0.34, -0.24, 0.22))),
                (24, Vector((-0.32, -0.18, 0.06))),
            ]
        },
        "Head_Joint": {
            "rotation_euler": [
                (1, Euler((0.0, 0.0, 0.0))),
                (10, Euler((math.radians(-12), 0.0, 0.0))),
                (24, Euler((0.0, 0.0, 0.0))),
            ]
        },
    }
    build_action_tracks(root, "Mage_Gesture", gesture_keys, 24)

    out_blend = AUTHORING_DIR / "mage_planar.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    print(f"SAVED: {out_blend}")
    return out_blend


# ==============================================================================
# RENDERING, DOWNSAMPLING & DERIVATIVE PIPELINE
# ==============================================================================

DIRECTIONS = [
    ("south", 0.0),
    ("south_east", 45.0),
    ("east", 90.0),
    ("north_east", 135.0),
    ("north", 180.0),
    ("north_west", 225.0),
    ("west", 270.0),
    ("south_west", 315.0),
]


def render_viewport_frame(output_path, res_x=48, res_y=48):
    """Render the current Blender frame to a temporary supersampled PNG."""
    scene = bpy.context.scene
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    return Path(output_path)





def render_character_suite(blend_path, archetype_id):
    """Renders raw supersampled frames (stills, 8 directions, animations, and high-res references) for host postprocessing."""
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    setup_studio_environment()
    root = (
        bpy.data.objects.get(f"{archetype_id.split('_')[0].capitalize()}_Root")
        or bpy.data.objects.get("Knight_Root")
        or bpy.data.objects.get("Rogue_Root")
        or bpy.data.objects.get("Mage_Root")
    )
    
    raw_char_dir = EXPERIMENT_DIR / "raw_frames" / archetype_id
    raw_char_dir.mkdir(parents=True, exist_ok=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. High-Res 512x512 Reference
    highres_path = REFERENCE_DIR / f"{archetype_id}_512.png"
    render_viewport_frame(highres_path, res_x=512, res_y=512)

    # 2. Directional 8-angle Stills (at frame 1 of Idle)
    action_name = f"{archetype_id.split('_')[0].capitalize()}_Idle"
    action = bpy.data.actions.get(action_name)
    if action:
        for obj in bpy.data.objects:
            if obj.animation_data:
                obj.animation_data.action = action
        bpy.context.scene.frame_set(1)

    for dir_name, angle_deg in DIRECTIONS:
        if root:
            root.rotation_euler = (0.0, 0.0, math.radians(angle_deg))
        bpy.context.view_layer.update()
        raw_out = raw_char_dir / f"dir_{dir_name}_raw.png"
        render_viewport_frame(raw_out, res_x=48, res_y=48)

    if root:
        root.rotation_euler = (0.0, 0.0, 0.0)

    # 3. Animation Sequences (Idle, Walk, Gesture)
    actions = [
        ("idle", f"{archetype_id.split('_')[0].capitalize()}_Idle", 32, 2),
        ("walk", f"{archetype_id.split('_')[0].capitalize()}_Walk", 16, 1),
        ("gesture", f"{archetype_id.split('_')[0].capitalize()}_Gesture", 24, 1),
    ]

    for anim_name, act_name, frame_count, frame_step in actions:
        act = bpy.data.actions.get(act_name)
        if not act:
            continue
        for obj in bpy.data.objects:
            if obj.animation_data:
                obj.animation_data.action = act

        for f in range(1, frame_count + 1, frame_step):
            bpy.context.scene.frame_set(f)
            bpy.context.view_layer.update()
            raw_f_path = raw_char_dir / f"{anim_name}_f{f:02d}_raw.png"
            render_viewport_frame(raw_f_path, res_x=48, res_y=48)

    print(f"COMPLETED RAW RENDERS FOR: {archetype_id}")


# ==============================================================================
# MAIN CLI ENTRY POINT
# ==============================================================================

def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Tiny 3D Character Authoring & Rendering")
    parser.add_argument("--build-all", action="store_true", help="Scaffold all 3 initial character .blend sources")
    parser.add_argument("--render-all", action="store_true", help="Render raw derivative frames for all 3 characters")
    args = parser.parse_args(argv)

    ensure_directories()

    if args.build_all:
        print("=== BUILDING CHARACTER .BLEND SOURCES ===")
        build_knight_volumetric()
        build_rogue_faceted()
        build_mage_planar()

    if args.render_all:
        print("=== RENDERING RAW DERIVATIVE FRAMES ===")
        render_character_suite(AUTHORING_DIR / "knight_volumetric.blend", "knight_volumetric")
        render_character_suite(AUTHORING_DIR / "rogue_faceted.blend", "rogue_faceted")
        render_character_suite(AUTHORING_DIR / "mage_planar.blend", "mage_planar")

    return 0


if __name__ == "__main__":
    if bpy is not None:
        raise SystemExit(main())
