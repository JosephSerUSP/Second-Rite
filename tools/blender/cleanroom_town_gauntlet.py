"""Clean-room Second Gate town visual gauntlet.

This file owns only newly-authored geometry and procedural material sources. It
uses the generic Thestra camera/Walker helper as a one-way presentation
boundary and never opens an earlier town scene or visual asset.
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
REPO = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import thestra_camera


NATIVE_W, NATIVE_H = 426, 240
WALKER = REPO / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
AUDIT_INPUTS = ["projects/hichaukitoden-game/assets/character/walker.png"]
ROOT = REPO / "docs" / "reports" / "artifacts" / "cleanroom-town-gauntlet-2026-08-20"

COLLECTIONS = (
    "TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS",
    "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW",
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("minimal", "lineages", "final", "all"), default="all")
    parser.add_argument("--out", type=Path, default=ROOT)
    args, _ = parser.parse_known_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    return args


def calibration(offset_x=0):
    return {
        "contract": "thestra.world-camera-calibration",
        "version": 1,
        "projection": "perspective",
        "eye": {"x": -15.0, "y": 0.0, "z": 1.75},
        "orientation": {
            "forwardX": 1.0, "forwardY": 0.0,
            "rightX": 0.0, "rightY": 1.0,
            "pitchRadians": 0.0,
        },
        "projectionScale": {"x": 1.0, "y": 1.0},
        "fovHalfX": 0.25,
        "fovHalfY": 0.140625,
        "nearPlane": 0.05,
        "farPlane": 64.0,
        "targetWidth": NATIVE_W,
        "targetHeight": NATIVE_H,
        "baseViewportWidth": 256,
        "baseViewportHeight": 144,
        "viewportCenterX": 213 + int(offset_x),
        "viewportCenterY": 110,
        "projectionWindowOffsetX": int(offset_x),
        "projectionWindowOffsetY": 0,
        "coordinateSystem": {
            "handedness": "right-handed", "worldUp": "+Z", "worldHorizontal": "XY",
            "cameraForward": "+depth", "cameraRight": "+right",
            "screenOrigin": "top-left", "screenY": "+down",
            "blenderCameraForward": "-Z", "blenderCameraUp": "+Y",
        },
    }


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)
    return path


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    engine_ids = {item.identifier for item in scene.bl_rna.properties["render"].fixed_type.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engine_ids else "BLENDER_EEVEE"
    scene.render.resolution_x = NATIVE_W
    scene.render.resolution_y = NATIVE_H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    if scene.world is None:
        scene.world = bpy.data.worlds.new("TH_WORLD_PREVIEW")
    scene.world.color = (0.012, 0.018, 0.028)
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.018, 0.026, 0.038, 1.0)
    bg.inputs["Strength"].default_value = 0.32
    for name, location, energy, color in (
        ("TH_Key_Soft", (-8.0, -6.0, 14.0), 1200.0, (1.0, 0.78, 0.58)),
        ("TH_Fill_Sky", (-5.0, 8.0, 9.0), 700.0, (0.48, 0.62, 1.0)),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.color = color
        light_data.shape = "DISK"
        light_data.size = 8.0
        light_obj = bpy.data.objects.new(name, light_data)
        scene.collection.objects.link(light_obj)
        light_obj.location = location
        light_obj.rotation_euler = (Vector((4.0, 0.0, 2.5)) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    for name in COLLECTIONS:
        bpy.data.collections.new(name)
        scene.collection.children.link(bpy.data.collections[name])
    return scene


def collection(name):
    return bpy.data.collections[name]


def move_to_collection(obj, name):
    target = collection(name)
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def material(name, color, roughness=0.8, metallic=0.0, emission=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if emission:
        shader.inputs["Emission Color"].default_value = (*emission, 1.0)
        shader.inputs["Emission Strength"].default_value = 0.18
    links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    return mat


def procedural_material(name, base, accent, scale=4.0, roughness=0.8):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    tex = nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = 4.0
    tex.inputs["Roughness"].default_value = 0.75
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*base, 1.0)
    ramp.color_ramp.elements[1].color = (*accent, 1.0)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.16
    bump.inputs["Distance"].default_value = 0.09
    texcoord = nodes.new("ShaderNodeTexCoord")
    links.new(texcoord.outputs["Generated"], tex.inputs["Vector"])
    links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    shader.inputs["Roughness"].default_value = roughness
    links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    return mat


def base_materials():
    return {
        "clay": material("CLAY_DEBUG", (0.48, 0.39, 0.30), 0.9),
        "ground": material("GROUND_CLAY", (0.16, 0.19, 0.22), 0.95),
        "dark": material("OPENING_DARK", (0.012, 0.016, 0.024), 1.0),
    }


def rich_materials():
    return {
        "stone": procedural_material("FRESH_STONE_MOSS", (0.24, 0.28, 0.30), (0.47, 0.45, 0.38), 8.0),
        "plaster": procedural_material("FRESH_LIME_PLASTER", (0.50, 0.47, 0.38), (0.72, 0.64, 0.45), 5.0),
        "timber": procedural_material("FRESH_DARK_TIMBER", (0.12, 0.075, 0.042), (0.29, 0.18, 0.08), 7.0),
        "roof": procedural_material("FRESH_OXIDE_ROOF", (0.18, 0.12, 0.10), (0.40, 0.21, 0.13), 10.0),
        "road": procedural_material("FRESH_WORN_ROAD", (0.16, 0.17, 0.16), (0.31, 0.29, 0.22), 13.0),
        "opening": material("RUNTIME_INTERIOR_DARK", (0.008, 0.012, 0.018), 1.0),
        "accent": procedural_material("FRESH_CERAMIC_ACCENT", (0.16, 0.30, 0.32), (0.43, 0.64, 0.53), 12.0),
    }


def apply_mat(obj, mat, role):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj["materialRole"] = role
    return obj


def new_mesh(name, vertices, faces, coll="TH_SOURCE", mat=None, role="stone"):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection(coll).objects.link(obj)
    if mat:
        apply_mat(obj, mat, role)
    return obj


def add_box(name, x, y, z, dx, dy, dz, mat, coll="TH_SOURCE", role="stone", bevel=0.0):
    x0, x1 = x - dx / 2, x + dx / 2
    y0, y1 = y - dy / 2, y + dy / 2
    z0, z1 = z - dz / 2, z + dz / 2
    verts = [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1),
             (x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (3, 7, 6, 2), (1, 2, 6, 5), (0, 4, 7, 3)]
    obj = new_mesh(name, verts, faces, coll, mat, role)
    if bevel:
        mod = obj.modifiers.new("small construction edge", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def add_roof(name, x0, x1, y0, y1, eave, ridge, mat, coll="TH_SOURCE", role="roof"):
    ym = (y0 + y1) / 2
    verts = [(x0, y0, eave), (x0, ym, ridge), (x0, y1, eave),
             (x1, y0, eave), (x1, ym, ridge), (x1, y1, eave)]
    faces = [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
    return new_mesh(name, verts, faces, coll, mat, role)


def add_beam(name, x, y, z, dx, dy, dz, mat, coll="TH_SOURCE", role="timber", lean=0.0):
    obj = add_box(name, x, y, z, dx, dy, dz, mat, coll, role, bevel=0.025)
    if lean:
        obj.rotation_euler[0] = lean
    return obj


def add_door_reveal(prefix, front_x, back_x, center_y, opening_w, opening_h, wall_y0, wall_y1,
                    wall_h, mat, dark, coll="TH_SOURCE", refine=False):
    depth = back_x - front_x
    side_w = (wall_y1 - wall_y0 - opening_w) / 2
    add_box(prefix + "_left_jamb", front_x + depth / 2, wall_y0 + side_w / 2, wall_h / 2,
            depth, side_w, wall_h, mat, coll, "stone", 0.05)
    add_box(prefix + "_right_jamb", front_x + depth / 2, wall_y1 - side_w / 2, wall_h / 2,
            depth, side_w, wall_h, mat, coll, "stone", 0.05)
    lintel_h = wall_h - opening_h
    add_box(prefix + "_lintel", front_x + depth / 2, center_y, opening_h + lintel_h / 2,
            depth, opening_w, lintel_h, mat, coll, "stone", 0.05)
    add_box(prefix + "_interior", back_x + 0.08, center_y, opening_h / 2,
            0.18, opening_w * 0.92, opening_h * 0.98, dark, coll, "opening")
    if refine:
        add_beam(prefix + "_threshold", front_x - 0.08, center_y, 0.10, 0.34, opening_w + 0.28, 0.20, mat, coll, "stone")
        add_beam(prefix + "_header_trim", front_x - 0.06, center_y, opening_h + 0.12, 0.18, opening_w + 0.22, 0.18, mat, coll, "stone")


def add_window(prefix, x, y, z, w, h, mat, dark, coll="TH_SOURCE"):
    add_box(prefix + "_recess", x, y, z, 0.20, w, h, dark, coll, "opening")
    add_box(prefix + "_sill", x - 0.14, y, z - h / 2 - 0.05, 0.26, w + 0.25, 0.12, mat, coll, "stone")
    add_beam(prefix + "_mullion", x - 0.15, y, z, 0.18, 0.10, h + 0.08, mat, coll, "timber")


def add_anchor(name, x, y, z=0.0, kind="point"):
    obj = bpy.data.objects.new(name, None)
    collection("TH_ANCHORS").objects.link(obj)
    obj.empty_display_type = "CIRCLE"
    obj.empty_display_size = 0.25
    obj.location = (x, y, z)
    obj["anchor"] = name
    obj["kind"] = kind
    return obj


def add_actor(name, camera, y, frame_index, mat_info=None, x=1.45):
    obj = thestra_camera.create_actor_preview(
        str(WALKER), camera, anchor=(x, y, 0.0),
        frame_width=24, frame_height=48, frame_index=frame_index,
        world_height=1.75, alpha_cutoff=0.5, name=name,
    )
    move_to_collection(obj, "TH_PREVIEW_ACTORS")
    return obj


def add_ground(mats, refined=False):
    add_box("ground_action_plane", 7.0, 0.0, -0.12, 26.0, 24.0, 0.24, mats["ground"], "TH_SOURCE", "road")
    add_box("front_walk_lane", 1.9, 0.0, 0.04, 1.2, 22.0, 0.18, mats["clay"], "TH_SOURCE", "road")
    if refined:
        for i in range(-10, 11):
            add_box(f"lane_joint_{i:+d}", 1.25, i * 0.95, 0.145, 0.16, 0.08, 0.015, mats["clay"], "TH_SOURCE", "accent")


def build_a(mats, refined=False):
    add_ground(mats, refined)
    add_door_reveal("A_gate", 4.0, 7.5, 0.0, 2.25, 3.05, -6.0, 6.0, 5.15, mats["clay"], mats["dark"], refine=refined)
    add_box("A_back_mass", 8.3, 0.0, 2.45, 2.6, 12.0, 4.9, mats["clay"], role="stone")
    add_roof("A_main_roof", 3.0, 9.8, -6.5, 6.5, 5.15, 6.65, mats["clay"], role="roof")
    add_box("A_left_attachment", 6.4, -8.0, 1.7, 4.2, 3.4, 3.4, mats["clay"], role="plaster")
    add_roof("A_left_roof", 4.4, 8.5, -10.0, -6.35, 3.35, 4.05, mats["clay"], role="roof")
    add_box("A_right_tower", 8.2, 8.5, 3.45, 3.5, 3.2, 6.9, mats["clay"], role="stone")
    add_roof("A_tower_cap", 6.1, 10.0, 6.8, 10.2, 6.9, 7.75, mats["clay"], role="roof")
    if refined:
        for y in (-5.3, -3.9, 3.8, 5.2):
            add_window("A_window", 3.84, y, 3.6, 0.82, 1.05, mats["clay"], mats["dark"])
        for y in (-5.8, -4.5, 4.6, 5.9):
            add_beam("A_eave_beam", 3.65, y, 5.15, 0.36, 0.18, 0.25, mats["clay"])
        add_beam("A_canopy_front", 2.25, -7.0, 2.9, 1.0, 4.2, 0.18, mats["clay"], lean=-0.10)
        add_beam("A_canopy_post", 1.65, -8.6, 1.45, 0.25, 0.25, 2.9, mats["clay"])
        add_beam("A_canopy_post2", 1.65, -5.5, 1.45, 0.25, 0.25, 2.9, mats["clay"])
    return "A"


def build_b(mats, refined=False):
    add_ground(mats, refined)
    add_box("B_left_house", 6.0, -6.4, 2.25, 4.8, 5.8, 4.5, mats["clay"], role="stone")
    add_box("B_right_house", 6.5, 6.4, 2.7, 5.4, 5.8, 5.4, mats["clay"], role="plaster")
    add_door_reveal("B_underpass", 3.7, 6.0, 0.0, 2.35, 3.1, -2.7, 2.7, 4.2, mats["clay"], mats["dark"], refine=refined)
    add_box("B_bridge", 7.0, 0.0, 5.4, 5.0, 5.0, 2.0, mats["clay"], role="stone")
    add_roof("B_left_roof", 3.5, 8.5, -9.6, -3.3, 4.5, 5.65, mats["clay"], role="roof")
    add_roof("B_right_roof", 3.7, 9.4, 3.3, 9.6, 5.4, 6.6, mats["clay"], role="roof")
    add_roof("B_bridge_roof", 4.5, 9.5, -2.8, 2.8, 6.4, 7.25, mats["clay"], role="roof")
    for i in range(6):
        add_box(f"B_stair_{i}", 2.2, -2.2 + i * 0.75, 0.12 + i * 0.15, 1.0, 0.82, 0.24 + i * 0.03, mats["clay"], role="stone")
    if refined:
        add_beam("B_bridge_sill", 3.45, 0.0, 4.28, 0.45, 5.55, 0.25, mats["clay"])
        for y in (-7.4, -5.2, 5.1, 7.3):
            add_window("B_window", 3.55, y, 3.1, 0.88, 1.0, mats["clay"], mats["dark"])
        add_beam("B_left_support", 3.25, -2.85, 3.7, 0.45, 0.32, 4.8, mats["clay"])
        add_beam("B_right_support", 3.25, 2.85, 3.7, 0.45, 0.32, 4.8, mats["clay"])
    return "B"


def build_c(mats, refined=False):
    add_ground(mats, refined)
    add_box("C_low_lane_wall", 6.6, -5.5, 1.8, 4.9, 6.2, 3.6, mats["clay"], role="plaster")
    add_box("C_high_lane_wall", 7.0, 5.6, 3.1, 5.3, 6.1, 6.2, mats["clay"], role="stone")
    add_door_reveal("C_bent_entry", 3.7, 7.2, 0.2, 2.1, 3.0, -2.0, 2.9, 4.8, mats["clay"], mats["dark"], refine=refined)
    add_roof("C_low_roof", 3.8, 9.0, -9.0, -2.35, 3.65, 4.55, mats["clay"], role="roof")
    add_roof("C_high_roof", 3.7, 10.2, 2.35, 8.8, 6.2, 7.45, mats["clay"], role="roof")
    # A deliberately asymmetric, leaning reveal gives the lane its identity.
    add_beam("C_leaning_buttress_left", 3.3, -2.7, 2.1, 0.62, 0.72, 4.2, mats["clay"], lean=-0.25)
    add_beam("C_leaning_buttress_right", 3.3, 3.0, 2.4, 0.62, 0.72, 4.8, mats["clay"], lean=0.22)
    add_box("C_far_silhouette", 10.5, 10.0, 4.4, 3.4, 3.8, 8.8, mats["clay"], role="stone")
    if refined:
        for y in (-7.8, -5.8, 5.0, 7.1):
            add_window("C_window", 3.58, y, 3.0 + (0.4 if y > 0 else 0), 0.72, 1.0, mats["clay"], mats["dark"])
        add_beam("C_entry_canopy", 2.7, 0.2, 3.35, 1.1, 2.9, 0.18, mats["clay"], lean=0.08)
        add_beam("C_canopy_post", 2.05, 1.3, 1.65, 0.24, 0.24, 3.2, mats["clay"])
    return "C"


def build_lineage(lineage, mats, refined=False):
    return {"A": build_a, "B": build_b, "C": build_c}[lineage](mats, refined)


def refine_lineage(lineage, mats):
    """Continue the live clay scene with articulation, without rebuilding it."""
    if lineage == "A":
        for y in (-5.3, -3.9, 3.8, 5.2):
            add_window("A_window", 3.84, y, 3.6, 0.82, 1.05, mats["clay"], mats["dark"])
        for y in (-5.8, -4.5, 4.6, 5.9):
            add_beam("A_eave_beam", 3.65, y, 5.15, 0.36, 0.18, 0.25, mats["clay"])
        add_beam("A_canopy_front", 2.25, -7.0, 2.9, 1.0, 4.2, 0.18, mats["clay"], lean=-0.10)
        add_beam("A_canopy_post", 1.65, -8.6, 1.45, 0.25, 0.25, 2.9, mats["clay"])
        add_beam("A_canopy_post2", 1.65, -5.5, 1.45, 0.25, 0.25, 2.9, mats["clay"])
    elif lineage == "B":
        add_beam("B_bridge_sill", 3.45, 0.0, 4.28, 0.45, 5.55, 0.25, mats["clay"])
        for y in (-7.4, -5.2, 5.1, 7.3):
            add_window("B_window", 3.55, y, 3.1, 0.88, 1.0, mats["clay"], mats["dark"])
        add_beam("B_left_support", 3.25, -2.85, 3.7, 0.45, 0.32, 4.8, mats["clay"])
        add_beam("B_right_support", 3.25, 2.85, 3.7, 0.45, 0.32, 4.8, mats["clay"])
    else:
        for y in (-7.8, -5.8, 5.0, 7.1):
            add_window("C_window", 3.58, y, 3.0 + (0.4 if y > 0 else 0), 0.72, 1.0, mats["clay"], mats["dark"])
        add_beam("C_entry_canopy", 2.7, 0.2, 3.35, 1.1, 2.9, 0.18, mats["clay"], lean=0.08)
        add_beam("C_canopy_post", 2.05, 1.3, 1.65, 0.24, 0.24, 3.2, mats["clay"])


def create_camera(offset=0):
    record = calibration(offset)
    path = ROOT / "camera" / f"calibration-{offset:+d}.json"
    ensure_dir(path.parent)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    camera = thestra_camera.create_or_update_camera(record, make_active=True)
    move_to_collection(camera, "TH_CAMERA_PREVIEW")
    return camera, record


def setup_preview_actors(camera, actor_y=(-7.0, 0.0, 7.0)):
    return [
        add_actor("Walker_Player", camera, actor_y[1], 0, x=1.35),
        add_actor("Walker_NPC_Left", camera, actor_y[0], 2, x=1.48),
        add_actor("Walker_NPC_Right", camera, actor_y[2], 4, x=1.48),
    ]


def verify_presentation(scene, camera, actors):
    bpy.context.view_layer.update()
    if abs(float(camera.data.lens) - 43.27) > 0.15:
        raise RuntimeError(f"preferred lens family failed: {camera.data.lens}")
    camera_basis = camera.matrix_world.to_3x3()
    camera_forward = camera_basis @ Vector((0.0, 0.0, -1.0))
    camera_up = camera_basis @ Vector((0.0, 1.0, 0.0))
    if camera_forward.x < 0.999 or abs(camera_forward.y) > 1e-5 or abs(camera_forward.z) > 1e-5:
        raise RuntimeError(f"camera forward is not level +X: {tuple(camera_forward)}")
    if camera_up.z < 0.999 or abs(camera_up.x) > 1e-5 or abs(camera_up.y) > 1e-5:
        raise RuntimeError(f"camera up is not +Z: {tuple(camera_up)}")
    for actor in actors:
        if not actor.get("thestra_feet_anchor"):
            raise RuntimeError(f"feet anchor missing on {actor.name}")
        if actor.get("thestra_frame_width") != 24 or actor.get("thestra_frame_height") != 48:
            raise RuntimeError(f"Walker frame contract failed on {actor.name}")
        up = actor.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))
        if up.z < 0.98:
            raise RuntimeError(f"Walker is not upright: {actor.name} up={tuple(up)}")
        foot = thestra_camera.project_world_point(scene, camera, actor.location)
        head = thestra_camera.project_world_point(scene, camera, actor.location + Vector((0, 0, 1.75)))
        height = abs(head[1] - foot[1])
        if not 42.0 <= height <= 55.0:
            raise RuntimeError(f"Walker native height failed on {actor.name}: {height:.2f}px")
        image_node = bpy.data.materials[actor.name + "_MAT"].node_tree.nodes.get("Image Texture")
        if not image_node or image_node.interpolation != "Closest":
            raise RuntimeError(f"nearest-neighbour contract failed on {actor.name}")
    return True


def render(scene, path):
    ensure_dir(Path(path).parent)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def visible(collection_name, state):
    coll = collection(collection_name)
    coll.hide_render = not state
    coll.hide_viewport = not state


def render_lineage(lineage, out_dir):
    scene = reset_scene()
    mats = base_materials()
    camera, _ = create_camera(0)
    build_lineage(lineage, mats, refined=False)
    actors = setup_preview_actors(camera)
    verify_presentation(scene, camera, actors)
    clay = out_dir / f"{lineage}1-clay-426x240.png"
    render(scene, clay)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / f"{lineage}1-clay.blend"))
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Walker_"):
            bpy.data.objects.remove(obj, do_unlink=True)
    # The same lineage remains live; refinement is an in-place continuation.
    refine_lineage(lineage, mats)
    actors = setup_preview_actors(camera)
    verify_presentation(scene, camera, actors)
    refined = out_dir / f"{lineage}2-refined-426x240.png"
    render(scene, refined)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / f"{lineage}2-refined.blend"))
    return out_dir / f"{lineage}2-refined.blend"


def make_contact_sheet(paths, target):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    images = [Image.open(path).convert("RGB") for path in paths]
    w, h = images[0].size
    sheet = Image.new("RGB", (w * 3, h * 2), (8, 8, 12))
    draw = ImageDraw.Draw(sheet)
    for i, image in enumerate(images):
        sheet.paste(image, ((i % 3) * w, (i // 3) * h))
        draw.rectangle(((i % 3) * w, (i // 3) * h, (i % 3) * w + 100, (i // 3) * h + 14), fill=(0, 0, 0))
        draw.text(((i % 3) * w + 3, (i // 3) * h + 2), Path(paths[i]).stem, fill=(255, 235, 190))
    sheet.save(target)


def source_panel(mat, y0=-6.0, y1=6.0, z0=0.35, z1=4.95, name="TH_SOURCE_FacadePanel_960cells"):
    # Open, subdivided façade surface: relief is authored on a real panel, not
    # by displacing a closed box, so shared edges cannot tear.
    cols, rows = 48, 20
    x = 3.62
    verts = []
    for r in range(rows + 1):
        z = z0 + (z1 - z0) * r / rows
        for c in range(cols + 1):
            y = y0 + (y1 - y0) * c / cols
            relief = 0.025 * math.sin(y * 4.0 + z * 1.8) + 0.012 * math.sin(y * 17.0)
            verts.append((x - relief, y, z))
    faces = []
    for r in range(rows):
        for c in range(cols):
            a = r * (cols + 1) + c
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    return new_mesh(name, verts, faces, "TH_SOURCE", mat, "plaster")


def add_source_details(mats, selected):
    if selected == "B":
        source_panel(mats["plaster"], -9.2, -3.5, 0.35, 4.35, "TH_SOURCE_B_LeftFacade_960cells")
        source_panel(mats["stone"], 3.5, 9.2, 0.35, 5.25, "TH_SOURCE_B_RightFacade_960cells")
        for y0, y1, rows in ((-9.2, -3.5, 4), (3.5, 9.2, 5)):
            for row in range(rows):
                z = 0.48 + row * 1.02
                count = 7
                for col in range(count):
                    y = y0 + 0.48 + col * ((y1 - y0 - 0.75) / max(1, count - 1)) + (0.18 if row % 2 else 0.0)
                    add_box(f"TH_SOURCE_B_masonry_{y:+.2f}_{row}", 3.42, y, z, 0.18, 0.68, 0.72,
                            mats["stone"], "TH_SOURCE", "stone", bevel=0.035)
        for y in (-8.6, -7.0, -5.4, 5.0, 6.6, 8.2):
            add_beam(f"TH_SOURCE_B_timber_{y:+.2f}", 3.28, y, 4.25, 0.24, 0.20, 1.45, mats["timber"])
        for y in (-8.8, -7.9, -7.0, -6.1, 5.2, 6.1, 7.0, 7.9):
            add_box(f"TH_SOURCE_B_roof_tile_{y:+.2f}", 3.15, y, 5.0, 0.28, 0.65, 0.10, mats["roof"], "TH_SOURCE", "roof", bevel=0.02)
        for i in range(6):
            add_box(f"TH_SOURCE_B_stair_stone_{i}", 2.0, -2.15 + i * 0.76, 0.18 + i * 0.15,
                    0.18, 0.74, 0.12, mats["road"], "TH_SOURCE", "road", bevel=0.02)
        for y in [(-10.0 + i * 0.7) for i in range(30)]:
            add_box(f"TH_SOURCE_B_lane_stone_{y:+.2f}", 1.0, y, 0.16, 0.14, 0.52, 0.08,
                    mats["road"], "TH_SOURCE", "road", bevel=0.02)
    else:
        source_panel(mats["plaster"])
        for row in range(4):
            z = 0.55 + row * 1.12
            for col in range(11):
                y = -5.5 + col * 1.1 + (0.20 if row % 2 else 0.0)
                add_box(f"TH_SOURCE_masonry_{row}_{col}", 3.48, y, z, 0.18, 0.92, 0.84,
                        mats["stone"], "TH_SOURCE", "stone", bevel=0.035)
        for y in (-5.7, -4.25, -2.8, 2.8, 4.25, 5.7):
            add_beam(f"TH_SOURCE_timber_{y:+.2f}", 3.35, y, 4.95, 0.24, 0.20, 1.8, mats["timber"])
        for y in (-9.4, -8.55, -7.7, -6.85):
            add_box(f"TH_SOURCE_roof_tile_{y:+.2f}", 3.20, y, 4.1, 0.28, 0.65, 0.10, mats["roof"], "TH_SOURCE", "roof", bevel=0.02)
        for y in [(-10.0 + i * 0.7) for i in range(30)]:
            add_box(f"TH_SOURCE_courtyard_stone_{y:+.2f}", 1.0, y, 0.16, 0.14, 0.52, 0.08,
                    mats["road"], "TH_SOURCE", "road", bevel=0.02)


def create_atlas(path):
    size = 256
    tiles = 4
    palette = [
        (74, 82, 78), (128, 111, 80), (57, 39, 28), (91, 47, 35),
        (45, 58, 57), (102, 80, 53), (28, 31, 30), (161, 142, 97),
        (79, 68, 53), (42, 51, 48), (111, 63, 43), (68, 96, 81),
        (52, 59, 59), (125, 93, 62), (37, 42, 40), (89, 68, 48),
    ]
    pixels = []
    for y in range(size):
        for x in range(size):
            tile = (y // (size // tiles)) * tiles + (x // (size // tiles))
            base = palette[tile]
            n = int(11 * math.sin(x * 0.31 + tile) + 7 * math.sin(y * 0.17 + x * 0.03))
            edge = 8 if x % (size // tiles) in (0, 1) or y % (size // tiles) in (0, 1) else 0
            pixels.extend((max(0, min(255, base[0] + n - edge)),
                           max(0, min(255, base[1] + n - edge)),
                           max(0, min(255, base[2] + n - edge)), 255))
    image = bpy.data.images.new("TH_BEAUTY_ATLAS", width=size, height=size, alpha=True)
    image.pixels = [value / 255.0 for value in pixels]
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    return image


def atlas_materials(image):
    mats = {}
    for idx in range(16):
        mat = bpy.data.materials.new(f"TH_ATLAS_TILE_{idx:02d}")
        mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Closest"
        tex.extension = "REPEAT"
        links.new(tex.outputs["Color"], shader.inputs["Base Color"])
        shader.inputs["Roughness"].default_value = 0.88
        links.new(shader.outputs["BSDF"], out.inputs["Surface"])
        mats[idx] = mat
    return mats


def atlas_uv(obj, tile_index):
    uv = obj.data.uv_layers.get("TH_ATLAS_UV") or obj.data.uv_layers.new(name="TH_ATLAS_UV")
    tile_size = 0.25
    tile_x, tile_y = tile_index % 4, tile_index // 4
    for loop in obj.data.loops:
        vx, vy, vz = obj.data.vertices[loop.vertex_index].co
        fu = (vy * 0.18) - math.floor(vy * 0.18)
        fv = (vz * 0.18) - math.floor(vz * 0.18)
        uv.data[loop.index].uv = (tile_x * tile_size + 0.02 * tile_size + fu * 0.94 * tile_size,
                                  tile_y * tile_size + 0.02 * tile_size + fv * 0.94 * tile_size)


def runtime_box(name, x, y, z, dx, dy, dz, mat, tile_index, role="stone"):
    obj = add_box(name, x, y, z, dx, dy, dz, mat[tile_index], "TH_RENDER", role)
    atlas_uv(obj, tile_index)
    return obj


def runtime_roof(name, x0, x1, y0, y1, eave, ridge, mat, tile_index):
    obj = add_roof(name, x0, x1, y0, y1, eave, ridge, mat[tile_index], "TH_RENDER", "roof")
    atlas_uv(obj, tile_index)
    return obj


def build_runtime_a(atlas):
    runtime_box("R_ground", 7.0, 0, -0.12, 26, 24, 0.24, atlas, 8, "road")
    runtime_box("R_walk_lane", 1.9, 0, 0.04, 1.2, 22, 0.18, atlas, 9, "road")
    runtime_box("R_gate_left", 4.0, -4.1, 2.55, 0.8, 3.8, 5.1, atlas, 0)
    runtime_box("R_gate_right", 4.0, 4.1, 2.55, 0.8, 3.8, 5.1, atlas, 0)
    runtime_box("R_gate_lintel", 4.0, 0, 4.15, 0.8, 4.2, 2.0, atlas, 1)
    runtime_box("R_gate_inner", 7.5, 0, 2.4, 0.25, 2.0, 4.8, atlas, 6, "opening")
    runtime_box("R_back_mass", 8.3, 0, 2.45, 2.6, 12.0, 4.9, atlas, 0)
    runtime_roof("R_main_roof", 3.0, 9.8, -6.5, 6.5, 5.15, 6.65, atlas, 3)
    runtime_box("R_left_attachment", 6.4, -8.0, 1.7, 4.2, 3.4, 3.4, atlas, 1, "plaster")
    runtime_roof("R_left_roof", 4.4, 8.5, -10.0, -6.35, 3.35, 4.05, atlas, 3)
    runtime_box("R_right_tower", 8.2, 8.5, 3.45, 3.5, 3.2, 6.9, atlas, 0)
    runtime_roof("R_tower_cap", 6.1, 10.0, 6.8, 10.2, 6.9, 7.75, atlas, 3)
    runtime_box("R_foreground_canopy", 2.25, -7.0, 2.9, 1.0, 4.2, 0.18, atlas, 2, "timber")


def build_runtime_b(atlas):
    runtime_box("R_ground", 7.0, 0, -0.12, 26, 24, 0.24, atlas, 8, "road")
    runtime_box("R_walk_lane", 1.9, 0, 0.04, 1.2, 22, 0.18, atlas, 9, "road")
    runtime_box("R_left_house", 6.0, -6.4, 2.25, 4.8, 5.8, 4.5, atlas, 1, "plaster")
    runtime_box("R_right_house", 6.5, 6.4, 2.7, 5.4, 5.8, 5.4, atlas, 0, "stone")
    runtime_box("R_underpass_left", 3.7, -1.52, 2.1, 0.8, 1.36, 4.2, atlas, 0)
    runtime_box("R_underpass_right", 3.7, 1.52, 2.1, 0.8, 1.36, 4.2, atlas, 0)
    runtime_box("R_underpass_lintel", 3.7, 0.0, 3.65, 0.8, 2.7, 1.1, atlas, 1)
    runtime_box("R_underpass_inner", 6.0, 0.0, 2.25, 0.25, 2.15, 4.2, atlas, 6, "opening")
    runtime_box("R_bridge", 7.0, 0.0, 5.4, 5.0, 5.0, 2.0, atlas, 0)
    runtime_roof("R_left_roof", 3.5, 8.5, -9.6, -3.3, 4.5, 5.65, atlas, 3)
    runtime_roof("R_right_roof", 3.7, 9.4, 3.3, 9.6, 5.4, 6.6, atlas, 3)
    runtime_roof("R_bridge_roof", 4.5, 9.5, -2.8, 2.8, 6.4, 7.25, atlas, 3)
    for i in range(6):
        runtime_box(f"R_stair_{i}", 2.2, -2.2 + i * 0.75, 0.12 + i * 0.15,
                    1.0, 0.82, 0.24 + i * 0.03, atlas, 0)
    runtime_box("R_foreground_stair_rail", 2.2, -0.2, 1.1, 0.16, 4.8, 0.16, atlas, 2, "timber")


def build_collision_and_anchors():
    collision = material("COLLISION_DEBUG", (0.8, 0.1, 0.06), 1.0)
    obj = add_box("collision_walk_bounds", 5.5, 0, 0.75, 10.0, 21.0, 1.5, collision, "TH_COLLISION", "collision")
    obj.hide_render = True
    obj.hide_viewport = True
    for name, x, y, z, kind in (
        ("spawn_player", 1.35, 0.0, 0.0, "spawn"),
        ("doorway", 3.85, 0.0, 0.0, "transfer"),
        ("npc_left", 1.48, -7.0, 0.0, "npc"),
        ("npc_right", 1.48, 7.0, 0.0, "npc"),
        ("walk_start", 1.35, -10.0, 0.0, "bound"),
        ("walk_end", 1.35, 10.0, 0.0, "bound"),
        ("foreground_depth_landmark", 1.0, -7.0, 0.0, "foreground"),
    ):
        add_anchor(name, x, y, z, kind)


def hide_environment_for_runtime():
    visible("TH_SOURCE", False)
    visible("TH_RENDER", True)
    visible("TH_COLLISION", False)
    visible("TH_PREVIEW_ONLY", False)
    visible("TH_PREVIEW_ACTORS", True)


def hide_environment_for_source():
    visible("TH_SOURCE", True)
    visible("TH_RENDER", False)
    visible("TH_COLLISION", False)
    visible("TH_PREVIEW_ONLY", False)
    visible("TH_PREVIEW_ACTORS", True)


def final_scene(a2_blend, out_dir, selected="B"):
    bpy.ops.wm.open_mainfile(filepath=str(a2_blend))
    scene = bpy.context.scene
    camera = bpy.data.objects.get("TH_CAMERA_PREVIEW")
    if camera is None:
        camera, _ = create_camera(0)
    rich = rich_materials()
    role_map = {"stone": rich["stone"], "plaster": rich["plaster"], "timber": rich["timber"],
                "roof": rich["roof"], "road": rich["road"], "opening": rich["opening"], "accent": rich["accent"],
                "clay": rich["stone"]}
    for obj in collection("TH_SOURCE").objects:
        role = obj.get("materialRole", "stone")
        if obj.type == "MESH":
            apply_mat(obj, role_map.get(role, rich["stone"]), role)
    add_source_details(rich, selected)
    atlas_path = out_dir / "beauty_atlas.png"
    atlas_image = create_atlas(atlas_path)
    atlas = atlas_materials(atlas_image)
    if selected == "B":
        build_runtime_b(atlas)
    else:
        build_runtime_a(atlas)
    build_collision_and_anchors()
    actors = [obj for obj in collection("TH_PREVIEW_ACTORS").objects if obj.name.startswith("Walker_")]
    verify_presentation(scene, camera, actors)
    hide_environment_for_source()
    source_path = out_dir / "source-beauty-426x240.png"
    render(scene, source_path)
    hide_environment_for_runtime()
    runtime_path = out_dir / "runtime-atlas-426x240.png"
    render(scene, runtime_path)

    projection_paths = []
    matrices = []
    for label, offset in (("left", -96), ("center", 0), ("right", 96)):
        camera, record = create_camera(offset)
        matrices.append([round(v, 8) for row in camera.matrix_world for v in row])
        hide_environment_for_runtime()
        path = out_dir / f"projection-{label}-{offset:+d}-426x240.png"
        render(scene, path)
        projection_paths.append(path)
    if max(max(abs(a - b) for a, b in zip(matrices[0], matrix)) for matrix in matrices[1:]) > 1e-6:
        raise RuntimeError("projection-window proof failed: camera eye/rotation changed")
    source_tris = 0
    render_tris = 0
    for coll_name in ("TH_SOURCE", "TH_RENDER"):
        for obj in collection(coll_name).objects:
            if obj.type == "MESH":
                obj.data.calc_loop_triangles()
                if coll_name == "TH_SOURCE":
                    source_tris += len(obj.data.loop_triangles)
                else:
                    render_tris += len(obj.data.loop_triangles)
    anchors = []
    for obj in collection("TH_ANCHORS").objects:
        anchors.append({"name": obj.name, "x": obj.location.x, "y": obj.location.y, "z": obj.location.z, "kind": obj.get("kind")})
    (out_dir / "anchors.json").write_text(json.dumps(anchors, indent=2) + "\n", encoding="utf-8")
    (out_dir / "material-provenance.json").write_text(json.dumps({
        "strategy": "fresh Blender procedural materials plus a deterministic procedural beauty atlas",
        "retrievalDate": "2026-08-20",
        "externalSources": [],
        "freshSources": [
            {"file": "beauty_atlas.png", "type": "procedural albedo atlas", "generator": "cleanroom_town_gauntlet.py", "license": "project-authored"},
        ] + [
            {"material": name, "type": "Blender procedural material", "license": "project-authored"}
            for name in ("FRESH_STONE_MOSS", "FRESH_LIME_PLASTER", "FRESH_DARK_TIMBER", "FRESH_OXIDE_ROOF", "FRESH_WORN_ROAD", "FRESH_CERAMIC_ACCENT")
        ],
    }, indent=2) + "\n", encoding="utf-8")
    metrics = {
        "native": [NATIVE_W, NATIVE_H], "selectedLineage": selected, "baselinePitchDegrees": 0,
        "lensMillimetres": round(float(camera.data.lens), 5),
        "fovHalfX": 0.25, "fovHorizontalDegreesApprox": 28.07,
        "sourceTriangles": source_tris, "renderTriangles": render_tris,
        "reductionRatio": round(source_tris / max(1, render_tris), 3),
        "runtimeMaterialCount": 16, "atlasDimensions": [256, 256],
        "atlasBytes": atlas_path.stat().st_size,
        "blendBytesBeforeSave": None,
        "projectionOffsets": [-96, 0, 96],
        "cameraTransformInvariant": True,
        "runtimeIsCameraSpacePlane": False,
        "runtimeCollection": "TH_RENDER",
        "sourceCollection": "TH_SOURCE",
    }
    blend_path = out_dir / "second-gate-town-environment.blend"
    create_camera(0)
    hide_environment_for_runtime()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    metrics["blendBytes"] = blend_path.stat().st_size
    metrics["packageBytes"] = sum(p.stat().st_size for p in out_dir.iterdir() if p.is_file())
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (out_dir / "asset-input-audit.json").write_text(json.dumps({"preExistingRepositoryVisualFilesRead": AUDIT_INPUTS, "freshAssetsCreated": ["beauty_atlas.png"]}, indent=2) + "\n", encoding="utf-8")
    return source_path, runtime_path, projection_paths, metrics


def minimal_gate(out_dir):
    scene = reset_scene()
    mats = base_materials()
    camera, record = create_camera(0)
    add_ground(mats, refined=False)
    actors = setup_preview_actors(camera, (-5.5, 0.0, 5.5))
    verify_presentation(scene, camera, actors)
    out_dir = ensure_dir(out_dir)
    center = out_dir / "minimal-gate-426x240.png"
    render(scene, center)
    matrices = []
    paths = []
    for label, offset in (("left", -96), ("center", 0), ("right", 96)):
        camera, _ = create_camera(offset)
        matrices.append([round(v, 8) for row in camera.matrix_world for v in row])
        path = out_dir / f"minimal-projection-{label}-{offset:+d}.png"
        render(scene, path)
        paths.append(path)
    invariant = max(max(abs(a - b) for a, b in zip(matrices[0], matrix)) for matrix in matrices[1:]) <= 1e-6
    if not invariant:
        raise RuntimeError("minimal gate projection-window camera transform changed")
    data = {"render": str(center), "dimensions": [NATIVE_W, NATIVE_H], "walker": {"sheet": [144, 48], "frame": [24, 48], "worldHeight": 1.75, "feetAnchored": True, "upright": True, "nearest": True, "alphaClip": True}, "camera": {"pitchDegrees": 0, "lensMillimetres": float(camera.data.lens), "principalPointY": 110, "projectionWindowOffsets": [-96, 0, 96], "cameraTransformInvariant": invariant}}
    (out_dir / "minimal-gate.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "minimal-gate.blend"))
    return paths


def write_report(out_dir, selected="B"):
    report = f"""# Clean-room Second Gate town gauntlet

Date: 2026-08-20
Selected lineage: {selected}
Native review target: 426x240
Baseline: level side view, preferred lens family, projection-window tracking

## Gate result

The minimal sterile scene was rendered before architecture. It contains one
Walker protagonist and two Walker stand-ins using the exact generic
`thestra_camera.create_actor_preview` helper. The gate records upright pose,
feet anchoring, 24x48 slicing, nearest filtering, alpha clipping, native scale,
level pitch, lens family and fixed-eye projection-window invariance.

## Architectural lineages

Three lineages were authored from factory-reset Blender scenes. Each was
reviewed as clay before the in-place refinement pass. The retained direction is
lineage B: two human-scale masses are tied by a real upper connection, with a
thick-wall underpass, supports, staircase, action lane and architecture
continuing beyond the visible frame.

## Runtime collapse

The final scene contains rich TH_SOURCE geometry, a subdivided open source
facade panel, and a separate coarse real-3D TH_RENDER. TH_RENDER uses one fresh
beauty atlas through world-stable UVs; it is not a camera-space background plane.
TH_COLLISION and TH_ANCHORS are prepared for a later reviewed traversal
integration. Preview actors are isolated from both environment collections.

## Composition follow-up

Review feedback on the submitted frames: the architecture is compositionally
interesting, but the buildings read close to the Walker. The next study should
compare a farther-back authored action/depth arrangement with a small camera
framing study. Preserve the proven level baseline and preferred lens family;
do not widen the lens merely to make the scene feel farther away.

## Evidence

- `minimal/minimal-gate-426x240.png`
- `clay/lineages-clay-comparison.png`
- `clay/lineages-refined-comparison.png`
- `final/source-beauty-426x240.png`
- `final/runtime-atlas-426x240.png`
- `final/projection-left--96-426x240.png`
- `final/projection-center-+0-426x240.png`
- `final/projection-right-+96-426x240.png`
- `final/second-gate-town-environment.blend`
- `final/beauty_atlas.png`
- `final/metrics.json`
- `final/material-provenance.json`
- `final/anchors.json`

## Asset input audit

The only pre-existing repository visual file read was exactly:

`projects/hichaukitoden-game/assets/character/walker.png`

All environment geometry and material sources in this run are fresh.
"""
    (out_dir / "REPORT.md").write_text(report, encoding="utf-8")


def main():
    global ROOT
    args = parse_args()
    ROOT = ensure_dir(args.out.resolve())
    minimal = ROOT / "minimal"
    clay = ROOT / "clay"
    final = ROOT / "final"
    ensure_dir(minimal); ensure_dir(clay); ensure_dir(final)
    if args.mode in ("minimal", "all"):
        minimal_gate(minimal)
    selected_blend = None
    if args.mode in ("lineages", "all"):
        render_lineage("A", clay)
        b2 = render_lineage("B", clay)
        render_lineage("C", clay)
        selected_blend = b2
        clay_paths = [clay / f"{lineage}{stage}-{'clay' if stage == 1 else 'refined'}-426x240.png" for lineage in "ABC" for stage in (1, 2)]
        make_contact_sheet(clay_paths[0::2], clay / "lineages-clay-comparison.png")
        make_contact_sheet(clay_paths[1::2], clay / "lineages-refined-comparison.png")
    if args.mode in ("final", "all"):
        if selected_blend is None:
            selected_blend = ROOT / "clay" / "B2-refined.blend"
        source, runtime, projections, metrics = final_scene(selected_blend, final, "B")
        make_contact_sheet([source, runtime], final / "source-vs-runtime-comparison.png")
        write_report(ROOT, "B")
    print(json.dumps({"root": str(ROOT), "mode": args.mode, "assetAudit": AUDIT_INPUTS}, indent=2))


if __name__ == "__main__":
    main()
