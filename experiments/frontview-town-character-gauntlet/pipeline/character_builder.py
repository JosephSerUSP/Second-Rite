"""Blender 5.1 procedural authoring, rigging, posing and rendering pipeline for
Second Gate 128x128 front-view town character sprites (Celina, Agnes, Gambler).
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

import bpy
import bmesh
from mathutils import Vector, Euler, Matrix, Quaternion


def clean_scene():
    """Wipe all existing objects, meshes, materials, and collections for a clean build."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.cameras, bpy.data.lights):
        for item in list(block):
            block.remove(item)


def setup_studio_environment(scene=None):
    """Configure front-view camera, 3-point lighting, transparent film, and EEVEE settings."""
    if scene is None:
        scene = bpy.context.scene

    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"

    # Color Management: Standard sRGB
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0

    # Engine
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in dir(bpy.types.RenderSettings) else "BLENDER_EEVEE"

    # Eliminate film Gaussian blur at source
    if hasattr(scene.render, "filter_size"):
        scene.render.filter_size = 0.5
    if hasattr(scene.render, "pixel_filter_type"):
        scene.render.pixel_filter_type = "BOX"

    # Black world background so escaping rays never pick up white/ambient bleed
    if not scene.world:
        scene.world = bpy.data.worlds.new("BlackWorld")
    scene.world.use_nodes = True
    bg_node = scene.world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        bg_node.inputs["Strength"].default_value = 0.0

    # Camera: Front-view, level eye/chest height, orthographic or long-lens
    cam_data = bpy.data.cameras.new("FrontViewCamera")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 1.90  # Frames full-body 1.6-1.75m figure to ~110-116px in 128 canvas
    cam_data.clip_start = 0.1
    cam_data.clip_end = 50.0

    cam_obj = bpy.data.objects.new("Camera_Front", cam_data)
    # Character centered around z=0.85 (mid-torso). Camera positioned at eye level z=0.88, looking straight +Y
    cam_obj.location = (0.0, -3.5, 0.88)
    cam_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # 3-Point Front-View Lighting
    # 1. Key Light: Warm neutral, upper-front-right
    key_data = bpy.data.lights.new("KeyLight", type="SUN")
    key_data.energy = 2.8
    key_data.color = (1.0, 0.96, 0.90)
    key_obj = bpy.data.objects.new("KeyLight", key_data)
    key_obj.rotation_euler = (math.radians(55.0), math.radians(15.0), math.radians(-30.0))
    scene.collection.objects.link(key_obj)

    # 2. Fill Light: Cool soft, lower-front-left (prevents crushed shadows)
    fill_data = bpy.data.lights.new("FillLight", type="SUN")
    fill_data.energy = 1.1
    fill_data.color = (0.85, 0.90, 1.0)
    fill_obj = bpy.data.objects.new("FillLight", fill_data)
    fill_obj.rotation_euler = (math.radians(35.0), math.radians(-20.0), math.radians(45.0))
    scene.collection.objects.link(fill_obj)

    # 3. Rim Light: Subtle high rear rim for silhouette separation against dark dungeon tiles
    rim_data = bpy.data.lights.new("RimLight", type="SUN")
    rim_data.energy = 1.4
    rim_data.color = (0.95, 0.95, 1.0)
    rim_obj = bpy.data.objects.new("RimLight", rim_data)
    rim_obj.rotation_euler = (math.radians(-60.0), 0.0, math.radians(180.0))
    scene.collection.objects.link(rim_obj)


def get_or_create_material(name: str, color: Tuple[float, float, float, float], roughness: float = 0.8, specular: float = 0.1) -> bpy.types.Material:
    """Create a stylized low-specular material with clean diffuse response."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = color
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = roughness
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = specular
            elif "Specular" in bsdf.inputs:
                bsdf.inputs["Specular"].default_value = specular
    return mat


# ==============================================================================
# MESH GEOMETRY HELPERS
# ==============================================================================

def create_cube(name: str, size: Tuple[float, float, float], loc: Tuple[float, float, float], rot: Tuple[float, float, float] = (0, 0, 0), mat=None) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    obj.scale = size
    obj.location = loc
    obj.rotation_euler = (math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2]))
    if mat:
        obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def create_cylinder(name: str, radius: float, depth: float, loc: Tuple[float, float, float], rot: Tuple[float, float, float] = (0, 0, 0), segments: int = 10, mat=None) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=radius, radius2=radius, depth=depth)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = (math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2]))
    if mat:
        obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def create_uv_sphere(name: str, radius: float, loc: Tuple[float, float, float], scale: Tuple[float, float, float] = (1, 1, 1), rot: Tuple[float, float, float] = (0, 0, 0), segments: int = 12, rings: int = 8, mat=None) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    obj.scale = scale
    obj.location = loc
    obj.rotation_euler = (math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2]))
    if mat:
        obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def create_tapered_box(name: str, bottom_w: float, bottom_d: float, top_w: float, top_d: float, height: float, loc: Tuple[float, float, float], rot: Tuple[float, float, float] = (0, 0, 0), mat=None) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    # 8 vertices
    hw_b, hd_b = bottom_w / 2.0, bottom_d / 2.0
    hw_t, hd_t = top_w / 2.0, top_d / 2.0
    hh = height / 2.0

    v0 = bm.verts.new((-hw_b, -hd_b, -hh))
    v1 = bm.verts.new(( hw_b, -hd_b, -hh))
    v2 = bm.verts.new(( hw_b,  hd_b, -hh))
    v3 = bm.verts.new((-hw_b,  hd_b, -hh))
    v4 = bm.verts.new((-hw_t, -hd_t,  hh))
    v5 = bm.verts.new(( hw_t, -hd_t,  hh))
    v6 = bm.verts.new(( hw_t,  hd_t,  hh))
    v7 = bm.verts.new((-hw_t,  hd_t,  hh))

    bm.faces.new((v0, v1, v2, v3)) # bottom
    bm.faces.new((v7, v6, v5, v4)) # top
    bm.faces.new((v0, v4, v5, v1)) # front
    bm.faces.new((v1, v5, v6, v2)) # right
    bm.faces.new((v2, v6, v7, v3)) # back
    bm.faces.new((v3, v7, v4, v0)) # left

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = (math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2]))
    if mat:
        obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# ==============================================================================
# CHARACTER BUILDERS
# ==============================================================================

def build_registrar_celina(pose: str = "idle") -> List[bpy.types.Object]:
    """Build Registrar Celina: severe, watchful, vertical, formal Portuguese-colonial tailoring.
    Proportions: ~5.6 heads, ~116px height in 128 canvas.
    """
    clean_scene()
    setup_studio_environment()

    # Materials
    mat_skin = get_or_create_material("Celina_Skin", (0.86, 0.76, 0.68, 1.0), roughness=0.75)
    mat_hair = get_or_create_material("Celina_Hair", (0.12, 0.10, 0.11, 1.0), roughness=0.85)
    mat_coat = get_or_create_material("Celina_Coat", (0.16, 0.18, 0.22, 1.0), roughness=0.70) # Dark tailored slate navy
    mat_cravat = get_or_create_material("Celina_Cravat", (0.92, 0.90, 0.84, 1.0), roughness=0.60) # Crisp ivory collar
    mat_skirt = get_or_create_material("Celina_Skirt", (0.13, 0.14, 0.17, 1.0), roughness=0.75)
    mat_boots = get_or_create_material("Celina_Boots", (0.08, 0.08, 0.09, 1.0), roughness=0.40) # Polished dark boots
    mat_ledger = get_or_create_material("Celina_Ledger", (0.42, 0.22, 0.14, 1.0), roughness=0.65) # Dark reddish-brown leather
    mat_paper = get_or_create_material("Celina_Paper", (0.88, 0.85, 0.75, 1.0), roughness=0.90)
    mat_metal = get_or_create_material("Celina_Metal", (0.75, 0.68, 0.45, 1.0), roughness=0.35, specular=0.6) # Brass clasp/brooch

    parts = []

    # Head inclination & facial planes
    # Celina tilts chin slightly downward (-5 to -8 deg) to give that assessing, inspecting glance
    head_tilt_x = -7.0 if pose in ("idle", "request_seal") else -2.0
    head_rot_z = 4.0 if pose == "request_seal" else 2.0

    # 1. Head & Hair Bun
    head = create_uv_sphere("Head", radius=0.12, loc=(0.01, -0.02, 1.48), scale=(0.95, 1.05, 1.15), rot=(head_tilt_x, 0, head_rot_z), mat=mat_skin)
    # Severe high swept hair bun
    hair_base = create_uv_sphere("HairBase", radius=0.13, loc=(0.01, 0.02, 1.51), scale=(1.02, 1.05, 1.10), rot=(head_tilt_x, 0, head_rot_z), mat=mat_hair)
    hair_bun = create_uv_sphere("HairBun", radius=0.075, loc=(0.01, 0.11, 1.57), scale=(1.1, 0.9, 1.1), rot=(15, 0, 0), mat=mat_hair)
    hair_pin = create_cylinder("HairPin", radius=0.008, depth=0.18, loc=(0.01, 0.11, 1.57), rot=(10, 75, 0), mat=mat_metal)
    parts.extend([head, hair_base, hair_bun, hair_pin])

    # 2. High Collar & Cravat
    collar = create_tapered_box("Collar", bottom_w=0.11, bottom_d=0.11, top_w=0.14, top_d=0.13, height=0.09, loc=(0.01, -0.01, 1.37), rot=(0, 0, 0), mat=mat_cravat)
    cravat_fold = create_cube("CravatFold", size=(0.05, 0.02, 0.08), loc=(0.01, -0.07, 1.34), rot=(-5, 0, 0), mat=mat_cravat)
    brooch = create_uv_sphere("Brooch", radius=0.016, loc=(0.01, -0.08, 1.36), scale=(1.0, 0.5, 1.0), mat=mat_metal)
    parts.extend([collar, cravat_fold, brooch])

    # 3. Torso & Fitted Jacket (Asymmetrical posture: right shoulder slightly back, left forward)
    torso_top = create_tapered_box("TorsoTop", bottom_w=0.24, bottom_d=0.14, top_w=0.31, top_d=0.17, height=0.22, loc=(0.0, 0.0, 1.23), rot=(1.0, 1.5, -3.0), mat=mat_coat)
    torso_waist = create_tapered_box("TorsoWaist", bottom_w=0.25, bottom_d=0.15, top_w=0.24, top_d=0.14, height=0.16, loc=(0.0, 0.0, 1.05), rot=(0, 1.0, -2.0), mat=mat_coat)
    coat_peplum = create_tapered_box("CoatPeplum", bottom_w=0.29, bottom_d=0.18, top_w=0.25, top_d=0.15, height=0.14, loc=(0.0, 0.0, 0.91), rot=(0, 0, -2.0), mat=mat_coat)
    parts.extend([torso_top, torso_waist, coat_peplum])

    # 4. Long Tailored Pleated Skirt (extends down to 0.18m)
    skirt_upper = create_tapered_box("SkirtUpper", bottom_w=0.33, bottom_d=0.21, top_w=0.28, top_d=0.17, height=0.36, loc=(0.0, 0.01, 0.69), rot=(0, -1.0, 0), mat=mat_skirt)
    skirt_lower = create_tapered_box("SkirtLower", bottom_w=0.38, bottom_d=0.24, top_w=0.33, top_d=0.21, height=0.40, loc=(0.0, 0.01, 0.33), rot=(0, -1.0, 0), mat=mat_skirt)
    parts.extend([skirt_upper, skirt_lower])

    # 5. Grounded Polished Boots
    boot_left = create_cube("BootL", size=(0.085, 0.16, 0.12), loc=(-0.08, -0.01, 0.06), rot=(0, 0, 8), mat=mat_boots)
    boot_right = create_cube("BootR", size=(0.085, 0.16, 0.12), loc=(0.08, 0.03, 0.06), rot=(0, 0, -12), mat=mat_boots)
    parts.extend([boot_left, boot_right])

    # 6. Left Arm: Holds Ledger firmly in crook against ribs
    shoulder_l = create_uv_sphere("ShoulderL", radius=0.055, loc=(-0.17, -0.01, 1.30), mat=mat_coat)
    upperarm_l = create_cylinder("UpperArmL", radius=0.045, depth=0.22, loc=(-0.18, 0.01, 1.18), rot=(15, -12, 0), mat=mat_coat)
    forearm_l = create_cylinder("ForeArmL", radius=0.042, depth=0.22, loc=(-0.14, -0.08, 1.07), rot=(75, 25, -20), mat=mat_coat)
    hand_l = create_cube("HandL", size=(0.045, 0.07, 0.05), loc=(-0.07, -0.15, 1.08), rot=(10, 30, -15), mat=mat_skin)
    # Narrow Ledger
    ledger = create_cube("Ledger", size=(0.05, 0.18, 0.26), loc=(-0.08, -0.14, 1.12), rot=(18, 28, -25), mat=mat_ledger)
    ledger_pages = create_cube("LedgerPages", size=(0.038, 0.165, 0.245), loc=(-0.075, -0.14, 1.12), rot=(18, 28, -25), mat=mat_paper)
    stylus = create_cylinder("Stylus", radius=0.006, depth=0.15, loc=(-0.05, -0.18, 1.14), rot=(45, 30, 0), mat=mat_metal)
    parts.extend([shoulder_l, upperarm_l, forearm_l, hand_l, ledger, ledger_pages, stylus])

    # 7. Right Arm & Hand (Posed per state)
    shoulder_r = create_uv_sphere("ShoulderR", radius=0.055, loc=(0.17, 0.01, 1.30), mat=mat_coat)
    parts.append(shoulder_r)

    if pose == "idle":
        # Economical resting posture: right arm down along hip, hand slightly curved inward
        upperarm_r = create_cylinder("UpperArmR", radius=0.045, depth=0.23, loc=(0.18, 0.0, 1.17), rot=(-8, 10, 0), mat=mat_coat)
        forearm_r = create_cylinder("ForeArmR", radius=0.042, depth=0.22, loc=(0.17, -0.04, 0.98), rot=(20, 5, 0), mat=mat_coat)
        hand_r = create_cube("HandR", size=(0.05, 0.07, 0.04), loc=(0.16, -0.07, 0.86), rot=(20, 0, 10), mat=mat_skin)
        parts.extend([upperarm_r, forearm_r, hand_r])

    elif pose == "request_seal":
        # Signature acting pose: Right arm extended forward/center, palm open upward ("Your Summoner's seal...")
        upperarm_r = create_cylinder("UpperArmR", radius=0.045, depth=0.23, loc=(0.16, -0.08, 1.19), rot=(45, 5, -15), mat=mat_coat)
        forearm_r = create_cylinder("ForeArmR", radius=0.042, depth=0.24, loc=(0.12, -0.25, 1.14), rot=(82, 0, -28), mat=mat_coat)
        # Open hand extended toward player
        hand_palm = create_cube("HandPalm", size=(0.055, 0.075, 0.025), loc=(0.07, -0.38, 1.15), rot=(85, 0, -30), mat=mat_skin)
        hand_fingers = create_cube("HandFingers", size=(0.05, 0.06, 0.02), loc=(0.05, -0.44, 1.16), rot=(75, 0, -30), mat=mat_skin)
        hand_thumb = create_cube("HandThumb", size=(0.025, 0.04, 0.02), loc=(0.10, -0.37, 1.17), rot=(45, 0, -10), mat=mat_skin)
        parts.extend([upperarm_r, forearm_r, hand_palm, hand_fingers, hand_thumb])

    elif pose == "dry_warning":
        # Dry warning: Right elbow bent, forefinger raised/warning gesture, head held high
        upperarm_r = create_cylinder("UpperArmR", radius=0.045, depth=0.22, loc=(0.18, -0.03, 1.18), rot=(25, 8, -5), mat=mat_coat)
        forearm_r = create_cylinder("ForeArmR", radius=0.042, depth=0.22, loc=(0.15, -0.15, 1.18), rot=(85, 30, -35), mat=mat_coat)
        hand_palm = create_cube("HandPalm", size=(0.045, 0.05, 0.04), loc=(0.12, -0.24, 1.28), rot=(45, 20, -20), mat=mat_skin)
        index_finger = create_cylinder("IndexFinger", radius=0.010, depth=0.08, loc=(0.11, -0.26, 1.34), rot=(-35, 15, 0), mat=mat_skin)
        parts.extend([upperarm_r, forearm_r, hand_palm, index_finger])

    return parts


def build_sister_agnes(pose: str = "idle_working") -> List[bpy.types.Object]:
    """Build Sister Agnes: calm, patient, physically grounded chapel caretaker.
    Proportions: ~5.3 heads, ~112px height in 128 canvas.
    """
    clean_scene()
    setup_studio_environment()

    # Materials
    mat_skin = get_or_create_material("Agnes_Skin", (0.88, 0.77, 0.69, 1.0), roughness=0.80)
    mat_habit = get_or_create_material("Agnes_Habit", (0.18, 0.17, 0.19, 1.0), roughness=0.85) # Muted charcoal dark wool
    mat_cowl = get_or_create_material("Agnes_Cowl", (0.84, 0.81, 0.74, 1.0), roughness=0.85) # Warm natural unbleached linen
    mat_apron = get_or_create_material("Agnes_Apron", (0.68, 0.64, 0.58, 1.0), roughness=0.90) # Working canvas apron
    mat_dust = get_or_create_material("Agnes_Dust", (0.76, 0.74, 0.70, 1.0), roughness=0.95) # Stone dust highlights on fabric
    mat_belt = get_or_create_material("Agnes_Belt", (0.40, 0.32, 0.22, 1.0), roughness=0.90) # Hemp cord
    mat_shoes = get_or_create_material("Agnes_Shoes", (0.16, 0.13, 0.11, 1.0), roughness=0.80)
    mat_trowel = get_or_create_material("Agnes_Trowel", (0.55, 0.53, 0.50, 1.0), roughness=0.45, specular=0.5) # Steel blade
    mat_wood = get_or_create_material("Agnes_Wood", (0.35, 0.22, 0.12, 1.0), roughness=0.75) # Ash wood handle

    parts = []

    # 1. Hood / Wimple & Calm Head (gentle forward inclination)
    head_lean_x = 8.0 if pose == "idle_working" else (14.0 if pose == "brush_dust" else 2.0)
    head_tilt_z = 3.0 if pose != "brush_dust" else -6.0

    head = create_uv_sphere("Head", radius=0.125, loc=(0.0, -0.03, 1.42), scale=(0.95, 1.02, 1.10), rot=(head_lean_x, 0, head_tilt_z), mat=mat_skin)
    # Soft cowl/wimple framing face
    wimple_hood = create_uv_sphere("WimpleHood", radius=0.145, loc=(0.0, 0.01, 1.44), scale=(1.02, 1.10, 1.15), rot=(head_lean_x, 0, head_tilt_z), mat=mat_habit)
    wimple_drape = create_tapered_box("WimpleDrape", bottom_w=0.30, bottom_d=0.20, top_w=0.22, top_d=0.16, height=0.20, loc=(0.0, 0.0, 1.30), rot=(head_lean_x * 0.6, 0, head_tilt_z * 0.5), mat=mat_cowl)
    parts.extend([head, wimple_hood, wimple_drape])

    # 2. Torso & Chapel Habit (Grounded, relaxed shoulders lower than Celina's)
    torso_lean = 6.0 if pose == "idle_working" else (10.0 if pose == "brush_dust" else 0.0)
    torso = create_tapered_box("Torso", bottom_w=0.28, bottom_d=0.18, top_w=0.30, top_d=0.18, height=0.32, loc=(0.0, -0.01, 1.15), rot=(torso_lean, 0, 0), mat=mat_habit)
    apron_chest = create_cube("ApronChest", size=(0.20, 0.02, 0.26), loc=(0.0, -0.11, 1.14), rot=(torso_lean, 0, 0), mat=mat_apron)
    belt_cord = create_cylinder("BeltCord", radius=0.155, depth=0.03, loc=(0.0, -0.01, 0.98), rot=(90, 0, 0), mat=mat_belt)
    bead_drop = create_cylinder("BeadDrop", radius=0.012, depth=0.25, loc=(-0.10, -0.10, 0.86), rot=(0, 0, 5), mat=mat_wood)
    parts.extend([torso, apron_chest, belt_cord, bead_drop])

    # 3. Grounded Skirt & Working Apron (wide, comfortable, stone dust on hem)
    skirt_top = create_tapered_box("SkirtTop", bottom_w=0.36, bottom_d=0.25, top_w=0.29, top_d=0.19, height=0.38, loc=(0.0, 0.0, 0.78), rot=(torso_lean * 0.3, 0, 0), mat=mat_habit)
    skirt_bottom = create_tapered_box("SkirtBottom", bottom_w=0.42, bottom_d=0.30, top_w=0.36, top_d=0.25, height=0.44, loc=(0.0, 0.01, 0.38), rot=(0, 0, 0), mat=mat_habit)
    apron_skirt = create_cube("ApronSkirt", size=(0.24, 0.02, 0.46), loc=(0.0, -0.14, 0.68), rot=(torso_lean * 0.3, 0, 0), mat=mat_apron)
    dust_patch = create_cube("DustPatch", size=(0.14, 0.015, 0.12), loc=(0.06, -0.15, 0.52), rot=(0, 0, 10), mat=mat_dust)
    parts.extend([skirt_top, skirt_bottom, apron_skirt, dust_patch])

    # 4. Work Shoes
    shoe_l = create_cube("ShoeL", size=(0.09, 0.17, 0.10), loc=(-0.10, 0.0, 0.05), rot=(0, 0, 12), mat=mat_shoes)
    shoe_r = create_cube("ShoeR", size=(0.09, 0.17, 0.10), loc=(0.10, -0.02, 0.05), rot=(0, 0, -8), mat=mat_shoes)
    parts.extend([shoe_l, shoe_r])

    # 5. Shoulders
    sh_l = create_uv_sphere("ShoulderL", radius=0.06, loc=(-0.17, -0.01, 1.25), mat=mat_habit)
    sh_r = create_uv_sphere("ShoulderR", radius=0.06, loc=(0.17, -0.01, 1.25), mat=mat_habit)
    parts.extend([sh_l, sh_r])

    # 6. Arms & Hands per Pose
    if pose == "idle_working":
        # Agnes is repairing steps: right sleeve pushed up, right hand holding masonry trowel low, left hand resting on knee/hip
        # Left Arm (habit sleeve down)
        up_arm_l = create_cylinder("UpArmL", radius=0.05, depth=0.22, loc=(-0.18, 0.0, 1.14), rot=(10, -10, 0), mat=mat_habit)
        fore_arm_l = create_cylinder("ForeArmL", radius=0.045, depth=0.22, loc=(-0.16, -0.08, 0.97), rot=(55, 15, -15), mat=mat_habit)
        hand_l = create_cube("HandL", size=(0.05, 0.07, 0.04), loc=(-0.12, -0.14, 0.86), rot=(45, 10, -10), mat=mat_skin)
        parts.extend([up_arm_l, fore_arm_l, hand_l])

        # Right Arm (sleeve rolled up to forearm, exposing bare working forearm & trowel)
        up_arm_r = create_cylinder("UpArmR", radius=0.05, depth=0.16, loc=(0.18, -0.03, 1.16), rot=(20, 8, -5), mat=mat_habit)
        sleeve_cuff_r = create_cylinder("SleeveCuffR", radius=0.055, depth=0.06, loc=(0.19, -0.06, 1.05), rot=(25, 8, -5), mat=mat_habit)
        bare_forearm_r = create_cylinder("BareForearmR", radius=0.038, depth=0.24, loc=(0.17, -0.16, 0.92), rot=(60, 5, -20), mat=mat_skin)
        hand_r = create_cube("HandR", size=(0.05, 0.07, 0.04), loc=(0.14, -0.26, 0.79), rot=(65, 0, -25), mat=mat_skin)
        # Masonry Trowel
        trowel_handle = create_cylinder("TrowelHandle", radius=0.012, depth=0.12, loc=(0.14, -0.28, 0.79), rot=(45, 30, 0), mat=mat_wood)
        trowel_blade = create_tapered_box("TrowelBlade", bottom_w=0.01, bottom_d=0.07, top_w=0.06, top_d=0.08, height=0.12, loc=(0.12, -0.34, 0.75), rot=(45, 30, 0), mat=mat_trowel)
        parts.extend([up_arm_r, sleeve_cuff_r, bare_forearm_r, hand_r, trowel_handle, trowel_blade])

    elif pose == "brush_dust":
        # Agnes brushes stone dust from her left sleeve with her right hand
        # Left Arm held out slightly
        up_arm_l = create_cylinder("UpArmL", radius=0.05, depth=0.22, loc=(-0.17, -0.04, 1.14), rot=(25, -15, 0), mat=mat_habit)
        fore_arm_l = create_cylinder("ForeArmL", radius=0.045, depth=0.22, loc=(-0.10, -0.16, 1.04), rot=(75, 40, -45), mat=mat_habit)
        hand_l = create_cube("HandL", size=(0.05, 0.07, 0.04), loc=(-0.04, -0.22, 1.06), rot=(45, 30, -30), mat=mat_skin)
        parts.extend([up_arm_l, fore_arm_l, hand_l])

        # Right Arm reaching across to brush left forearm
        up_arm_r = create_cylinder("UpArmR", radius=0.05, depth=0.22, loc=(0.15, -0.06, 1.15), rot=(40, 10, -30), mat=mat_habit)
        fore_arm_r = create_cylinder("ForeArmR", radius=0.045, depth=0.22, loc=(0.04, -0.19, 1.08), rot=(70, -25, 40), mat=mat_skin)
        hand_r = create_cube("HandR", size=(0.05, 0.07, 0.03), loc=(-0.07, -0.19, 1.09), rot=(50, -20, 35), mat=mat_skin)
        parts.extend([up_arm_r, fore_arm_r, hand_r])

    elif pose == "quiet_welcome":
        # Open conversational posture: both hands open, low and grounded (hospitality without preaching)
        # Left Arm
        up_arm_l = create_cylinder("UpArmL", radius=0.05, depth=0.22, loc=(-0.18, -0.02, 1.15), rot=(20, -18, 0), mat=mat_habit)
        fore_arm_l = create_cylinder("ForeArmL", radius=0.045, depth=0.22, loc=(-0.16, -0.15, 1.02), rot=(65, 15, -25), mat=mat_habit)
        hand_l = create_cube("HandL", size=(0.05, 0.07, 0.03), loc=(-0.14, -0.25, 0.98), rot=(75, 10, -20), mat=mat_skin)
        # Right Arm
        up_arm_r = create_cylinder("UpArmR", radius=0.05, depth=0.22, loc=(0.18, -0.02, 1.15), rot=(20, 18, 0), mat=mat_habit)
        fore_arm_r = create_cylinder("ForeArmR", radius=0.045, depth=0.22, loc=(0.16, -0.15, 1.02), rot=(65, -15, 25), mat=mat_habit)
        hand_r = create_cube("HandR", size=(0.05, 0.07, 0.03), loc=(0.14, -0.25, 0.98), rot=(75, -10, 20), mat=mat_skin)
        parts.extend([up_arm_l, fore_arm_l, hand_l, up_arm_r, fore_arm_r, hand_r])

    return parts


def build_gambler_concept_1(pose: str = "idle") -> List[bpy.types.Object]:
    """Concept 1: Outwardly Ordinary Local ("Local Regular")
    Plain tavern silhouette, concealing playing cards inside wide left cuff.
    """
    clean_scene()
    setup_studio_environment()

    mat_skin = get_or_create_material("G1_Skin", (0.84, 0.74, 0.65, 1.0))
    mat_hair = get_or_create_material("G1_Hair", (0.24, 0.18, 0.14, 1.0))
    mat_coat = get_or_create_material("G1_Coat", (0.35, 0.25, 0.18, 1.0), roughness=0.85) # Brown wool
    mat_shirt = get_or_create_material("G1_Shirt", (0.75, 0.72, 0.65, 1.0))
    mat_pants = get_or_create_material("G1_Pants", (0.18, 0.18, 0.20, 1.0))
    mat_boots = get_or_create_material("G1_Boots", (0.12, 0.09, 0.07, 1.0))
    mat_card = get_or_create_material("G1_Card", (0.92, 0.90, 0.80, 1.0))
    mat_coin = get_or_create_material("G1_Coin", (0.85, 0.72, 0.25, 1.0), roughness=0.3, specular=0.7)

    parts = []
    # Head & hair
    head = create_uv_sphere("Head", radius=0.12, loc=(0.0, -0.02, 1.44), scale=(0.95, 1.0, 1.1), rot=(-4, 0, 5), mat=mat_skin)
    hair = create_uv_sphere("Hair", radius=0.13, loc=(0.0, 0.0, 1.47), scale=(1.02, 1.04, 1.05), rot=(-4, 0, 5), mat=mat_hair)
    parts.extend([head, hair])

    # Torso & Tavern Coat
    torso = create_tapered_box("Torso", bottom_w=0.28, bottom_d=0.17, top_w=0.32, top_d=0.18, height=0.34, loc=(0.0, 0.0, 1.20), rot=(0, 2, -3), mat=mat_coat)
    shirt = create_cube("Shirt", size=(0.12, 0.02, 0.20), loc=(0.01, -0.09, 1.22), rot=(0, 2, -3), mat=mat_shirt)
    coat_tails = create_tapered_box("CoatTails", bottom_w=0.32, bottom_d=0.20, top_w=0.28, top_d=0.17, height=0.24, loc=(0.0, 0.0, 0.95), rot=(0, 2, -3), mat=mat_coat)
    parts.extend([torso, shirt, coat_tails])

    # Legs & Boots
    leg_l = create_cylinder("LegL", radius=0.065, depth=0.46, loc=(-0.09, 0.0, 0.60), rot=(0, 0, 4), mat=mat_pants)
    leg_r = create_cylinder("LegR", radius=0.065, depth=0.46, loc=(0.09, 0.0, 0.60), rot=(0, 0, -6), mat=mat_pants)
    boot_l = create_cube("BootL", size=(0.08, 0.16, 0.12), loc=(-0.10, -0.01, 0.06), rot=(0, 0, 8), mat=mat_boots)
    boot_r = create_cube("BootR", size=(0.08, 0.16, 0.12), loc=(0.10, 0.01, 0.06), rot=(0, 0, -10), mat=mat_boots)
    parts.extend([leg_l, leg_r, boot_l, boot_r])

    # Arms: Left arm hides card in cuff; right arm holds coin
    up_l = create_cylinder("UpArmL", radius=0.05, depth=0.22, loc=(-0.18, 0.0, 1.16), rot=(15, -8, 0), mat=mat_coat)
    fore_l = create_cylinder("ForeArmL", radius=0.052, depth=0.22, loc=(-0.14, -0.08, 1.02), rot=(65, 20, -15), mat=mat_coat)
    cuff_l = create_cylinder("CuffL", radius=0.06, depth=0.06, loc=(-0.10, -0.14, 0.96), rot=(65, 20, -15), mat=mat_coat)
    hand_l = create_cube("HandL", size=(0.045, 0.07, 0.04), loc=(-0.08, -0.17, 0.94), rot=(45, 10, -10), mat=mat_skin)
    card_peek = create_cube("CardPeek", size=(0.04, 0.06, 0.01), loc=(-0.09, -0.14, 0.98), rot=(45, 15, -10), mat=mat_card)

    up_r = create_cylinder("UpArmR", radius=0.05, depth=0.22, loc=(0.18, 0.0, 1.16), rot=(10, 8, 0), mat=mat_coat)
    fore_r = create_cylinder("ForeArmR", radius=0.048, depth=0.22, loc=(0.16, -0.07, 0.99), rot=(45, -10, 10), mat=mat_coat)
    hand_r = create_cube("HandR", size=(0.05, 0.07, 0.04), loc=(0.14, -0.15, 0.88), rot=(45, -10, 10), mat=mat_skin)
    coin = create_cylinder("Coin", radius=0.02, depth=0.008, loc=(0.14, -0.18, 0.89), rot=(45, 0, 0), mat=mat_coin)
    parts.extend([up_l, fore_l, cuff_l, hand_l, card_peek, up_r, fore_r, hand_r, coin])

    return parts


def build_gambler_concept_2(pose: str = "idle") -> List[bpy.types.Object]:
    """Concept 2: Wiry Number Obsessive ("The Counter")
    Angular, forward-hunched stature (~5.2 heads, ~108px), narrow shoulders,
    spindly fingers spread in counting postures, multiple-pocketed waistcoat, brass tokens.
    """
    clean_scene()
    setup_studio_environment()

    mat_skin = get_or_create_material("G2_Skin", (0.83, 0.73, 0.64, 1.0))
    mat_hair = get_or_create_material("G2_Hair", (0.16, 0.14, 0.13, 1.0))
    mat_vest = get_or_create_material("G2_Vest", (0.22, 0.26, 0.24, 1.0), roughness=0.75) # Faded olive/slate vest
    mat_shirt = get_or_create_material("G2_Shirt", (0.78, 0.76, 0.70, 1.0))
    mat_pants = get_or_create_material("G2_Pants", (0.15, 0.15, 0.16, 1.0))
    mat_boots = get_or_create_material("G2_Boots", (0.10, 0.08, 0.07, 1.0))
    mat_token = get_or_create_material("G2_Token", (0.82, 0.68, 0.28, 1.0), roughness=0.35, specular=0.6) # Brass counters/dice
    mat_pocket = get_or_create_material("G2_Pocket", (0.17, 0.20, 0.18, 1.0))

    parts = []

    # Head: Sharp profile, angular, tilted forward in calculating focus
    head_rot_x = 10.0 if pose == "idle" else (14.0 if pose == "offer_game" else 4.0)
    head_rot_z = -4.0 if pose != "win_or_reveal" else 8.0

    head = create_uv_sphere("Head", radius=0.115, loc=(0.0, -0.06, 1.40), scale=(0.90, 1.05, 1.15), rot=(head_rot_x, 0, head_rot_z), mat=mat_skin)
    nose = create_tapered_box("Nose", bottom_w=0.015, bottom_d=0.04, top_w=0.01, top_d=0.01, height=0.04, loc=(0.0, -0.16, 1.39), rot=(head_rot_x, 0, head_rot_z), mat=mat_skin)
    hair = create_uv_sphere("Hair", radius=0.12, loc=(0.0, -0.04, 1.44), scale=(0.96, 1.06, 1.10), rot=(head_rot_x, 0, head_rot_z), mat=mat_hair)
    parts.extend([head, nose, hair])

    # Torso: Wiry, narrow shoulders, hunched forward
    torso_lean = 10.0 if pose in ("idle", "offer_game") else 2.0
    torso = create_tapered_box("Torso", bottom_w=0.24, bottom_d=0.15, top_w=0.26, top_d=0.15, height=0.32, loc=(0.0, -0.03, 1.14), rot=(torso_lean, 0, 0), mat=mat_vest)
    shirt_collar = create_tapered_box("ShirtCollar", bottom_w=0.10, bottom_d=0.08, top_w=0.12, top_d=0.10, height=0.08, loc=(0.0, -0.08, 1.30), rot=(torso_lean, 0, 0), mat=mat_shirt)
    pocket1 = create_cube("Pocket1", size=(0.06, 0.015, 0.05), loc=(-0.07, -0.12, 1.16), rot=(torso_lean, 0, 0), mat=mat_pocket)
    pocket2 = create_cube("Pocket2", size=(0.06, 0.015, 0.05), loc=(0.07, -0.12, 1.16), rot=(torso_lean, 0, 0), mat=mat_pocket)
    pocket3 = create_cube("Pocket3", size=(0.06, 0.015, 0.05), loc=(-0.07, -0.12, 1.06), rot=(torso_lean, 0, 0), mat=mat_pocket)
    pocket4 = create_cube("Pocket4", size=(0.06, 0.015, 0.05), loc=(0.07, -0.12, 1.06), rot=(torso_lean, 0, 0), mat=mat_pocket)
    parts.extend([torso, shirt_collar, pocket1, pocket2, pocket3, pocket4])

    # Legs & Boots: Thin, slightly crouched
    leg_l = create_cylinder("LegL", radius=0.052, depth=0.48, loc=(-0.08, 0.0, 0.58), rot=(4, 0, 2), mat=mat_pants)
    leg_r = create_cylinder("LegR", radius=0.052, depth=0.48, loc=(0.08, -0.02, 0.58), rot=(-6, 0, -4), mat=mat_pants)
    boot_l = create_cube("BootL", size=(0.075, 0.15, 0.10), loc=(-0.08, 0.0, 0.05), rot=(0, 0, 4), mat=mat_boots)
    boot_r = create_cube("BootR", size=(0.075, 0.15, 0.10), loc=(0.08, -0.03, 0.05), rot=(0, 0, -10), mat=mat_boots)
    parts.extend([leg_l, leg_r, boot_l, boot_r])

    # Arms & Spindly Hands per Pose
    sh_l = create_uv_sphere("ShoulderL", radius=0.05, loc=(-0.15, -0.03, 1.25), mat=mat_vest)
    sh_r = create_uv_sphere("ShoulderR", radius=0.05, loc=(0.15, -0.03, 1.25), mat=mat_vest)
    parts.extend([sh_l, sh_r])

    if pose == "idle":
        # Idle: Fingers splayed in counting configuration holding brass tokens
        up_l = create_cylinder("UpArmL", radius=0.042, depth=0.22, loc=(-0.16, -0.04, 1.13), rot=(20, -10, 0), mat=mat_shirt)
        fore_l = create_cylinder("ForeArmL", radius=0.038, depth=0.22, loc=(-0.11, -0.16, 1.02), rot=(75, 30, -35), mat=mat_shirt)
        hand_l = create_cube("HandL", size=(0.045, 0.075, 0.03), loc=(-0.06, -0.22, 1.04), rot=(55, 20, -25), mat=mat_skin)
        token1 = create_cylinder("Token1", radius=0.016, depth=0.008, loc=(-0.05, -0.24, 1.06), rot=(55, 20, -25), mat=mat_token)

        up_r = create_cylinder("UpArmR", radius=0.042, depth=0.22, loc=(0.16, -0.04, 1.13), rot=(20, 10, 0), mat=mat_shirt)
        fore_r = create_cylinder("ForeArmR", radius=0.038, depth=0.22, loc=(0.11, -0.16, 1.02), rot=(75, -30, 35), mat=mat_shirt)
        hand_r = create_cube("HandR", size=(0.045, 0.075, 0.03), loc=(0.06, -0.22, 1.04), rot=(55, -20, 25), mat=mat_skin)
        token2 = create_cylinder("Token2", radius=0.016, depth=0.008, loc=(0.05, -0.24, 1.06), rot=(55, -20, 25), mat=mat_token)
        token3 = create_cylinder("Token3", radius=0.016, depth=0.008, loc=(0.07, -0.21, 1.08), rot=(45, -15, 20), mat=mat_token)
        parts.extend([up_l, fore_l, hand_l, token1, up_r, fore_r, hand_r, token2, token3])

    elif pose == "offer_game":
        # Signature acting: Leaning forward offering numbered token between spread fingers
        up_l = create_cylinder("UpArmL", radius=0.042, depth=0.22, loc=(-0.16, -0.04, 1.13), rot=(25, -12, 0), mat=mat_shirt)
        fore_l = create_cylinder("ForeArmL", radius=0.038, depth=0.22, loc=(-0.12, -0.16, 1.01), rot=(60, 20, -20), mat=mat_shirt)
        hand_l = create_cube("HandL", size=(0.045, 0.07, 0.03), loc=(-0.08, -0.22, 0.98), rot=(50, 10, -15), mat=mat_skin)

        up_r = create_cylinder("UpArmR", radius=0.042, depth=0.24, loc=(0.14, -0.10, 1.17), rot=(50, 8, -20), mat=mat_shirt)
        fore_r = create_cylinder("ForeArmR", radius=0.038, depth=0.26, loc=(0.08, -0.28, 1.13), rot=(85, 0, -32), mat=mat_shirt)
        hand_r = create_cube("HandR", size=(0.055, 0.08, 0.025), loc=(0.03, -0.42, 1.14), rot=(85, 0, -30), mat=mat_skin)
        offered_token = create_cylinder("OfferedToken", radius=0.022, depth=0.01, loc=(0.01, -0.47, 1.15), rot=(90, 0, -30), mat=mat_token)
        parts.extend([up_l, fore_l, hand_l, up_r, fore_r, hand_r, offered_token])

    elif pose == "win_or_reveal":
        # Wry reveal: One hand flipped open displaying result, other tucked in pocket
        up_l = create_cylinder("UpArmL", radius=0.042, depth=0.22, loc=(-0.16, -0.02, 1.13), rot=(10, -8, 0), mat=mat_shirt)
        fore_l = create_cylinder("ForeArmL", radius=0.038, depth=0.20, loc=(-0.12, -0.10, 0.98), rot=(45, 15, -15), mat=mat_shirt)
        hand_l = create_cube("HandL", size=(0.04, 0.06, 0.03), loc=(-0.08, -0.12, 1.02), rot=(20, 0, 0), mat=mat_skin)

        up_r = create_cylinder("UpArmR", radius=0.042, depth=0.22, loc=(0.16, -0.06, 1.16), rot=(35, 15, -10), mat=mat_shirt)
        fore_r = create_cylinder("ForeArmR", radius=0.038, depth=0.24, loc=(0.12, -0.22, 1.18), rot=(80, 25, -25), mat=mat_shirt)
        hand_r = create_cube("HandR", size=(0.055, 0.08, 0.025), loc=(0.08, -0.32, 1.25), rot=(45, 20, -20), mat=mat_skin)
        revealed_die = create_cube("RevealedDie", size=(0.03, 0.03, 0.03), loc=(0.08, -0.34, 1.30), rot=(25, 35, 15), mat=mat_token)
        parts.extend([up_l, fore_l, hand_l, up_r, fore_r, hand_r, revealed_die])

    return parts


def build_gambler_concept_3(pose: str = "idle") -> List[bpy.types.Object]:
    """Concept 3: Relaxed Sleight-of-Hand Socialite ("The Deceiver")
    Asymmetric leaning stance, loose open vest, tilted hair across forehead,
    fluid sleight-of-hand gestures displaying fanned cards/coins.
    """
    clean_scene()
    setup_studio_environment()

    mat_skin = get_or_create_material("G3_Skin", (0.86, 0.76, 0.67, 1.0))
    mat_hair = get_or_create_material("G3_Hair", (0.18, 0.12, 0.10, 1.0))
    mat_vest = get_or_create_material("G3_Vest", (0.28, 0.16, 0.18, 1.0)) # Burgundy open vest
    mat_shirt = get_or_create_material("G3_Shirt", (0.85, 0.82, 0.76, 1.0)) # Loose ruffled shirt
    mat_pants = get_or_create_material("G3_Pants", (0.14, 0.14, 0.16, 1.0))
    mat_boots = get_or_create_material("G3_Boots", (0.12, 0.09, 0.08, 1.0))
    mat_card = get_or_create_material("G3_Card", (0.94, 0.92, 0.85, 1.0))
    mat_gold = get_or_create_material("G3_Gold", (0.85, 0.70, 0.25, 1.0), roughness=0.3, specular=0.7)

    parts = []

    # Head: Tilted cocky head with fringe
    head = create_uv_sphere("Head", radius=0.12, loc=(0.02, -0.02, 1.46), scale=(0.95, 1.02, 1.12), rot=(-2, -6, 8), mat=mat_skin)
    hair = create_uv_sphere("Hair", radius=0.13, loc=(0.02, 0.01, 1.49), scale=(1.02, 1.08, 1.08), rot=(-2, -6, 8), mat=mat_hair)
    fringe = create_cube("Fringe", size=(0.08, 0.04, 0.06), loc=(0.05, -0.12, 1.48), rot=(15, -15, 20), mat=mat_hair)
    parts.extend([head, hair, fringe])

    # Torso: Relaxed asymmetric posture, weight on left hip
    torso = create_tapered_box("Torso", bottom_w=0.27, bottom_d=0.16, top_w=0.30, top_d=0.17, height=0.34, loc=(0.0, 0.0, 1.20), rot=(0, -4, 5), mat=mat_shirt)
    vest_l = create_cube("VestL", size=(0.08, 0.03, 0.32), loc=(-0.11, -0.08, 1.20), rot=(0, -4, 5), mat=mat_vest)
    vest_r = create_cube("VestR", size=(0.08, 0.03, 0.32), loc=(0.11, -0.08, 1.20), rot=(0, -4, 5), mat=mat_vest)
    parts.extend([torso, vest_l, vest_r])

    # Legs & Boots (Asymmetric contrapposto)
    leg_l = create_cylinder("LegL", radius=0.06, depth=0.50, loc=(-0.08, 0.02, 0.60), rot=(0, 2, 4), mat=mat_pants)
    leg_r = create_cylinder("LegR", radius=0.06, depth=0.48, loc=(0.10, -0.02, 0.59), rot=(-8, -8, -12), mat=mat_pants)
    boot_l = create_cube("BootL", size=(0.08, 0.16, 0.12), loc=(-0.08, 0.01, 0.06), rot=(0, 0, 5), mat=mat_boots)
    boot_r = create_cube("BootR", size=(0.08, 0.16, 0.12), loc=(0.12, -0.05, 0.06), rot=(0, 0, -20), mat=mat_boots)
    parts.extend([leg_l, leg_r, boot_l, boot_r])

    # Arms: Left elbow cocked out on hip; right hand fanning cards
    up_l = create_cylinder("UpArmL", radius=0.05, depth=0.22, loc=(-0.18, 0.0, 1.18), rot=(20, -35, 0), mat=mat_shirt)
    fore_l = create_cylinder("ForeArmL", radius=0.045, depth=0.22, loc=(-0.16, -0.06, 1.02), rot=(60, 40, -40), mat=mat_shirt)
    hand_l = create_cube("HandL", size=(0.05, 0.07, 0.04), loc=(-0.10, -0.08, 0.98), rot=(20, 10, -10), mat=mat_skin)

    up_r = create_cylinder("UpArmR", radius=0.05, depth=0.22, loc=(0.18, -0.02, 1.18), rot=(25, 15, -10), mat=mat_shirt)
    fore_r = create_cylinder("ForeArmR", radius=0.045, depth=0.24, loc=(0.14, -0.16, 1.10), rot=(75, 10, -25), mat=mat_shirt)
    hand_r = create_cube("HandR", size=(0.05, 0.07, 0.03), loc=(0.09, -0.26, 1.12), rot=(65, 10, -20), mat=mat_skin)
    # Fanned cards
    card1 = create_cube("Card1", size=(0.04, 0.07, 0.005), loc=(0.07, -0.28, 1.15), rot=(65, 0, -10), mat=mat_card)
    card2 = create_cube("Card2", size=(0.04, 0.07, 0.005), loc=(0.08, -0.29, 1.16), rot=(65, 15, -25), mat=mat_card)
    card3 = create_cube("Card3", size=(0.04, 0.07, 0.005), loc=(0.06, -0.27, 1.14), rot=(65, -15, 5), mat=mat_card)
    parts.extend([up_l, fore_l, hand_l, up_r, fore_r, hand_r, card1, card2, card3])

    return parts


def render_scene_to_file(filepath: Path, resolution: int = 256):
    """Render the active Blender scene to a PNG file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.filepath = str(filepath)
    bpy.ops.render.render(write_still=True)


def save_blend_file(filepath: Path):
    """Save the active Blender scene to a .blend file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(filepath))
