"""Author the V0 Second Gate town gauntlet in Blender.

This is a disposable, deterministic authoring harness for the first town scene.
The semantic camera authority remains Thestra: every scene calls
``thestra_camera.create_or_update_camera`` with a calibration record emitted by
the real WorldCamera resolver.  The Blender camera is a preview derivative.

The script intentionally keeps the scene in the V0 collection contract:
TH_SOURCE, TH_RENDER, TH_COLLISION, TH_ANCHORS, TH_PREVIEW_ACTORS,
TH_PREVIEW_ONLY and TH_CAMERA_PREVIEW.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]
BLENDER_TOOLS = REPO_ROOT / "tools" / "blender"
sys.path.insert(0, str(BLENDER_TOOLS))

import bpy  # type: ignore
from mathutils import Vector  # type: ignore

import thestra_camera  # type: ignore


TARGET_W = 426
TARGET_H = 240
FRAME_W = 24
FRAME_H = 48
WALKER_PATH = REPO_ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
DEFAULT_CALIBRATION = HERE / "thestra-town-camera.json"
DEFAULT_OUTPUT = HERE / "renders"


MATERIAL_COLORS = {
    "stone_cream": (0.56, 0.48, 0.38, 1.0),
    "stone_rose": (0.42, 0.25, 0.22, 1.0),
    "stone_blue": (0.22, 0.30, 0.36, 1.0),
    "stone_ochre": (0.52, 0.35, 0.18, 1.0),
    "stone_pale": (0.68, 0.59, 0.45, 1.0),
    "stone_shadow": (0.12, 0.12, 0.15, 1.0),
    "wood_dark": (0.16, 0.085, 0.045, 1.0),
    "wood_warm": (0.34, 0.16, 0.07, 1.0),
    "roof_umber": (0.19, 0.10, 0.07, 1.0),
    "roof_blue": (0.08, 0.14, 0.18, 1.0),
    "cloth_red": (0.45, 0.09, 0.07, 1.0),
    "cloth_teal": (0.06, 0.28, 0.27, 1.0),
    "cloth_ochre": (0.55, 0.29, 0.08, 1.0),
    "copper": (0.48, 0.20, 0.08, 1.0),
    "lantern": (0.95, 0.43, 0.10, 1.0),
    "street": (0.17, 0.16, 0.16, 1.0),
    "street_light": (0.27, 0.24, 0.20, 1.0),
    "water": (0.04, 0.16, 0.22, 1.0),
    "sky_warm": (0.11, 0.07, 0.09, 1.0),
    "sky_cool": (0.035, 0.07, 0.12, 1.0),
    "sky_neutral": (0.07, 0.08, 0.09, 1.0),
}


ATTEMPTS = [
    {
        "id": 1,
        "name": "Lantern Row",
        "seed": 11,
        "door_y": 5.7,
        "foreground_y": -2.2,
        "foreground_side": "left",
        "street_width": 4.4,
        "building_pattern": [(-5.5, 3.0, 3.6, "stone_rose", "roof_umber"),
                              (-1.7, 2.6, 4.2, "stone_cream", "roof_umber"),
                              (2.1, 3.2, 3.3, "stone_ochre", "roof_blue"),
                              (6.2, 3.0, 4.6, "stone_blue", "roof_blue"),
                              (10.5, 4.4, 3.0, "stone_pale", "roof_umber")],
        "npc_positions": [(0.0, 1.9, 1), (1.0, 2.0, 2), (7.2, 1.85, 4)],
        "lanterns": [-4.2, -0.8, 4.5, 8.4],
        "mood": "warm",
        "note": "Strong lantern rhythm and centered doorway; dense but readable street theatre.",
    },
    {
        "id": 2,
        "name": "Quiet Shrine",
        "seed": 22,
        "door_y": 9.2,
        "foreground_y": 5.6,
        "foreground_side": "right",
        "street_width": 5.8,
        "building_pattern": [(-7.0, 3.5, 4.8, "stone_blue", "roof_blue"),
                              (-2.7, 2.5, 3.4, "stone_pale", "roof_umber"),
                              (2.0, 2.7, 3.1, "stone_cream", "roof_umber"),
                              (8.6, 5.0, 4.8, "stone_rose", "roof_blue"),
                              (14.0, 3.3, 3.6, "stone_blue", "roof_blue")],
        "npc_positions": [(-3.7, 1.75, 3), (8.0, 1.85, 1), (10.0, 1.8, 4)],
        "lanterns": [-6.0, 0.0, 8.7, 13.7],
        "mood": "cool",
        "shrine": True,
        "note": "Large negative-space lane and shrine focal point; quiet enough for a return-state read.",
    },
    {
        "id": 3,
        "name": "Market Turn",
        "seed": 33,
        "door_y": 1.5,
        "foreground_y": 8.2,
        "foreground_side": "right",
        "street_width": 6.7,
        "building_pattern": [(-8.5, 4.2, 3.4, "stone_ochre", "roof_umber"),
                              (-3.0, 2.6, 3.7, "stone_cream", "roof_blue"),
                              (1.5, 4.2, 4.0, "stone_rose", "roof_umber"),
                              (7.0, 2.8, 3.5, "stone_pale", "roof_blue"),
                              (11.8, 4.8, 4.8, "stone_blue", "roof_blue")],
        "npc_positions": [(-1.1, 1.8, 2), (0.2, 1.9, 1), (3.1, 1.75, 4)],
        "lanterns": [-7.3, -2.2, 2.0, 7.0, 11.8],
        "mood": "warm",
        "awnings": [-5.4, 3.1, 9.3],
        "note": "Broad market lane with a right-hand awning; high story density but less quiet space.",
    },
    {
        "id": 4,
        "name": "Twin Gables",
        "seed": 44,
        "door_y": 4.0,
        "foreground_y": -6.2,
        "foreground_side": "left",
        "street_width": 4.9,
        "building_pattern": [(-8.4, 4.8, 5.1, "stone_cream", "roof_umber"),
                              (-2.5, 2.4, 2.9, "stone_blue", "roof_blue"),
                              (2.2, 2.5, 3.2, "stone_pale", "roof_umber"),
                              (7.7, 4.8, 5.3, "stone_rose", "roof_umber"),
                              (13.4, 3.8, 3.0, "stone_blue", "roof_blue")],
        "npc_positions": [(-3.0, 1.8, 4), (5.8, 1.8, 1), (7.3, 1.8, 2)],
        "lanterns": [-8.0, -2.8, 4.0, 8.0, 13.0],
        "mood": "neutral",
        "gables": True,
        "note": "Tall twin silhouettes make a memorable frame, but the doorway competes with vertical massing.",
    },
    {
        "id": 5,
        "name": "Canal Edge",
        "seed": 55,
        "door_y": -1.5,
        "foreground_y": 6.6,
        "foreground_side": "right",
        "street_width": 5.2,
        "building_pattern": [(-9.0, 3.4, 3.2, "stone_blue", "roof_blue"),
                              (-5.0, 3.0, 3.8, "stone_rose", "roof_umber"),
                              (-0.5, 3.0, 4.3, "stone_cream", "roof_umber"),
                              (4.2, 3.5, 3.4, "stone_ochre", "roof_blue"),
                              (9.5, 4.4, 4.1, "stone_pale", "roof_umber")],
        "npc_positions": [(-4.0, 1.8, 3), (2.2, 1.85, 1), (8.5, 1.8, 4)],
        "lanterns": [-8.0, -3.0, 2.2, 6.5, 10.0],
        "mood": "cool",
        "water": True,
        "note": "A cool canal edge gives strong depth separation, though the water competes with protagonist contrast.",
    },
    {
        "id": 6,
        "name": "Gatehouse",
        "seed": 66,
        "door_y": 7.0,
        "foreground_y": 10.0,
        "foreground_side": "right",
        "street_width": 4.6,
        "building_pattern": [(-9.5, 4.6, 3.5, "stone_pale", "roof_umber"),
                              (-4.2, 2.8, 4.2, "stone_rose", "roof_blue"),
                              (0.0, 2.4, 3.0, "stone_blue", "roof_blue"),
                              (4.7, 3.4, 3.6, "stone_cream", "roof_umber"),
                              (9.0, 5.6, 5.0, "stone_ochre", "roof_umber")],
        "npc_positions": [(-4.0, 1.85, 2), (4.5, 1.9, 1), (6.0, 1.8, 3)],
        "lanterns": [-8.6, -3.6, 1.5, 6.5, 10.0],
        "mood": "warm",
        "gatehouse": True,
        "note": "Excellent foreground portal and termination tower; hero lane narrows at the right edge.",
    },
    {
        "id": 7,
        "name": "Shrine Return",
        "seed": 77,
        "door_y": 7.9,
        "foreground_y": 5.8,
        "foreground_side": "right",
        "street_width": 5.4,
        "building_pattern": [(-7.3, 3.2, 4.4, "stone_blue", "roof_blue"),
                              (-3.0, 2.7, 3.2, "stone_pale", "roof_umber"),
                              (1.2, 2.7, 3.3, "stone_cream", "roof_umber"),
                              (7.5, 4.6, 4.4, "stone_rose", "roof_blue"),
                              (13.0, 3.2, 3.4, "stone_blue", "roof_blue")],
        "npc_positions": [(-3.7, 1.8, 3), (5.2, 1.85, 1), (8.4, 1.8, 4)],
        "lanterns": [-6.0, -0.2, 7.6, 12.5],
        "mood": "cool",
        "shrine": True,
        "return_state": True,
        "note": "Refines 02: keeps the quiet lane, moves the doorway toward the optical center, and separates the NPC beats.",
    },
    {
        "id": 8,
        "name": "Lantern Threshold",
        "seed": 88,
        "door_y": 5.5,
        "foreground_y": -2.8,
        "foreground_side": "left",
        "street_width": 5.0,
        "building_pattern": [(-6.2, 3.2, 3.5, "stone_rose", "roof_umber"),
                              (-2.2, 2.5, 3.8, "stone_cream", "roof_umber"),
                              (2.0, 3.0, 3.2, "stone_ochre", "roof_blue"),
                              (6.3, 3.3, 4.4, "stone_blue", "roof_blue"),
                              (11.2, 4.0, 3.2, "stone_pale", "roof_umber")],
        "npc_positions": [(-0.2, 1.95, 1), (1.4, 1.85, 2), (7.5, 1.85, 4)],
        "lanterns": [-4.8, -0.8, 4.5, 8.2],
        "mood": "warm",
        "return_state": True,
        "note": "Refines 01: preserves the strong lantern rhythm, opens the middle lane, and gives the doorway more breathing room.",
    },
    {
        "id": 9,
        "name": "Market Reprise",
        "seed": 99,
        "door_y": 2.2,
        "foreground_y": 8.6,
        "foreground_side": "right",
        "street_width": 5.8,
        "building_pattern": [(-8.0, 3.8, 3.3, "stone_ochre", "roof_umber"),
                              (-3.0, 2.6, 3.5, "stone_cream", "roof_blue"),
                              (1.0, 3.8, 4.1, "stone_rose", "roof_umber"),
                              (6.2, 3.0, 3.4, "stone_pale", "roof_blue"),
                              (11.4, 4.6, 4.6, "stone_blue", "roof_blue")],
        "npc_positions": [(-1.8, 1.85, 2), (0.2, 1.9, 1), (4.0, 1.85, 4)],
        "lanterns": [-7.0, -2.0, 2.4, 6.9, 11.2],
        "mood": "warm",
        "awnings": [-4.7, 3.3, 9.1],
        "return_state": True,
        "note": "Refines 03: keeps a market story beat while recovering a clear quiet slice around the protagonist.",
    },
]


def ensure_collection(name: str):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj, collection):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def reset_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    collections = {name: ensure_collection(name) for name in (
        "TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS",
        "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW",
    )}
    return scene, collections


def make_material(name, color, *, roughness=0.72, metallic=0.0, emission=None, strength=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if emission is not None and "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = emission
            bsdf.inputs["Emission Strength"].default_value = strength
    return material


def add_box(name, location, dimensions, material, collection, *, bevel=0.0, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    move_to_collection(obj, collection)
    if bevel:
        modifier = obj.modifiers.new("controlled_edge_softness", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    return obj


def add_cylinder(name, location, radius, depth, material, collection, *, vertices=12, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                        location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj


def add_uv_sphere(name, location, radius, material, collection, *, segments=16, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius,
                                         location=location)
    obj = bpy.context.object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj


def add_prism_roof(name, y, width, x, depth, z_base, height, material, collection):
    # A triangular prism whose visible silhouette is a deliberate low-poly gable.
    x0, x1 = x - depth * 0.5, x + depth * 0.5
    y0, y1 = y - width * 0.5, y + width * 0.5
    ym = (y0 + y1) * 0.5
    z0, z1 = z_base, z_base + height
    vertices = [
        (x0, y0, z0), (x0, y1, z0), (x0, ym, z1),
        (x1, y0, z0), (x1, y1, z0), (x1, ym, z1),
    ]
    faces = [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2),
             (2, 5, 3, 0)]
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if material:
        mesh.materials.append(material)
    return obj


def add_arch_ring(name, x, y, z, width, height, thickness, material, collection):
    # Extruded segmented arch in the camera-facing Y/Z plane.
    segments = 10
    outer_r = width * 0.5
    inner_r = max(outer_r - thickness, 0.08)
    cx, cz = y, z + height - outer_r
    verts = []
    for depth in (-0.5, 0.5):
        xd = x + depth * 0.12
        for radius in (outer_r, inner_r):
            for index in range(segments + 1):
                theta = math.pi * index / segments
                verts.append((xd, cx + math.cos(theta) * radius,
                              cz + math.sin(theta) * radius))
    faces = []
    # two front/back half-ring strips
    for side in (0, 1):
        base = side * (segments + 1) * 2
        for index in range(segments):
            a = base + index * 2
            faces.append((a, a + 1, a + 3, a + 2))
    # connect the two depths on both curved boundaries
    front = 0
    back = 2 * (segments + 1)
    for index in range(segments + 1):
        faces.append((front + index * 2, back + index * 2,
                      back + index * 2 + 1, front + index * 2 + 1))
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if material:
        mesh.materials.append(material)
    return obj


def add_anchor(name, location, collection, *, rotation_z=0.0):
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "ARROWS"
    empty.empty_display_size = 0.45
    empty.location = location
    empty.rotation_euler[2] = math.radians(rotation_z)
    collection.objects.link(empty)
    return empty


def configure_render(scene, mood):
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = TARGET_W
    scene.render.resolution_y = TARGET_H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "Standard"
    try:
        scene.view_settings.look = "Medium High Contrast"
    except Exception:
        pass
    world = scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        sky = MATERIAL_COLORS["sky_" + ("warm" if mood == "warm" else "cool" if mood == "cool" else "neutral")]
        bg.inputs["Color"].default_value = sky
        bg.inputs["Strength"].default_value = 0.22 if mood == "cool" else 0.28


def setup_lights(collections, mood):
    source = collections["TH_SOURCE"]
    warm = mood == "warm"
    key_color = (1.0, 0.64, 0.35) if warm else (0.46, 0.66, 1.0) if mood == "cool" else (0.78, 0.84, 1.0)
    bpy.ops.object.light_add(type="AREA", location=(6.8, 4.5, 4.8))
    key = bpy.context.object
    key.name = "SRC_Key_Softbox"
    key.data.energy = 950 if warm else 760
    key.data.color = key_color
    key.data.shape = "RECTANGLE"
    key.data.size = 7.0
    key.data.size_y = 4.0
    key.rotation_euler = (math.radians(58), 0, math.radians(12))
    move_to_collection(key, source)

    bpy.ops.object.light_add(type="AREA", location=(10.2, -5.5, 2.6))
    fill = bpy.context.object
    fill.name = "SRC_Fill_Bounce"
    fill.data.energy = 430
    fill.data.color = (0.26, 0.42, 0.52) if warm else (0.33, 0.50, 0.65)
    fill.data.size = 5.0
    fill.rotation_euler = (math.radians(76), 0, math.radians(-14))
    move_to_collection(fill, source)


def add_facade_details(prefix, x, y, width, height, z_ground, mats, source, *, seed=0,
                        doorway=False, door_y=None, window_count=2, gable=False):
    front_x = x - 0.52
    trim = mats["stone_pale"]
    dark = mats["wood_dark"]
    glass = mats["stone_shadow"]
    # Vertical pilasters establish an architectural rhythm.
    for side in (-1, 1):
        add_box(f"SRC_{prefix}_Pilaster_{side}", (front_x - 0.04, y + side * (width * 0.46),
                                                     z_ground + height * 0.52),
                (0.16, 0.18, height * 1.04), trim, source, bevel=0.03)
    if doorway and door_y is not None:
        add_box(f"SRC_{prefix}_Door", (front_x - 0.11, door_y, z_ground + 0.94),
                (0.12, 1.15, 1.88), dark, source)
        add_box(f"SRC_{prefix}_DoorLintel", (front_x - 0.16, door_y, z_ground + 1.96),
                (0.18, 1.52, 0.18), trim, source, bevel=0.05)
        add_box(f"SRC_{prefix}_DoorStep", (front_x - 0.22, door_y, z_ground + 0.07),
                (0.28, 1.48, 0.14), mats["street_light"], source, bevel=0.03)
        add_arch_ring(f"SRC_{prefix}_DoorArch", front_x - 0.18, door_y, z_ground + 0.15,
                      1.52, 1.88, 0.16, trim, source)
    for index in range(window_count):
        frac = (index + 1) / (window_count + 1)
        wy = y - width * 0.5 + frac * width
        if doorway and door_y is not None and abs(wy - door_y) < 1.15:
            continue
        wz = z_ground + min(2.35, height * 0.62)
        add_box(f"SRC_{prefix}_Window_{index}", (front_x - 0.12, wy, wz),
                (0.10, 0.72, 0.86), glass, source, bevel=0.03)
        add_box(f"SRC_{prefix}_WindowTop_{index}", (front_x - 0.17, wy, wz + 0.52),
                (0.16, 0.88, 0.12), trim, source, bevel=0.02)
        add_box(f"SRC_{prefix}_WindowSill_{index}", (front_x - 0.18, wy, wz - 0.51),
                (0.18, 0.92, 0.12), trim, source, bevel=0.02)
    if gable:
        add_prism_roof(f"SRC_{prefix}_Gable", y, width * 0.95, x, 1.05,
                       z_ground + height - 0.05, 1.05, mats["roof_umber"], source)


def add_building(prefix, y, width, height, color_name, roof_name, mats, source, render,
                 z_ground, *, door_y=None, gable=False, source_only=False):
    x = 9.35
    facade = mats[color_name]
    roof = mats[roof_name]
    add_box(f"SRC_{prefix}_Mass", (x, y, z_ground + height * 0.5),
            (1.25, width, height), facade, source, bevel=0.08)
    add_box(f"SRC_{prefix}_RoofBand", (x - 0.08, y, z_ground + height + 0.10),
            (1.38, width + 0.18, 0.22), roof, source, bevel=0.04)
    add_facade_details(prefix, x, y, width, height, z_ground, mats, source,
                       doorway=door_y is not None, door_y=door_y, window_count=2,
                       gable=gable)
    if not source_only:
        # Coarse proxy is intentionally a single mass; the baked atlas carries detail.
        add_box(f"RND_{prefix}_Proxy", (x, y, z_ground + height * 0.5),
                (1.30, width + 0.06, height + 0.12), facade, render)
        if gable:
            add_prism_roof(f"RND_{prefix}_RoofProxy", y, width + 0.06, x, 1.32,
                           z_ground + height, 0.92, roof, render)


def add_street_details(mats, source, render, z_ground, street_width, *, water=False):
    add_box("SRC_StreetBase", (10.0, 4.0, z_ground - 0.10),
            (7.2, 34.0, 0.20), mats["street"], source)
    add_box("SRC_StreetLightBand", (9.15, 4.0, z_ground + 0.015),
            (0.18, 34.0, 0.04), mats["street_light"], source)
    # Sparse source cobbles add texture without turning the scene into random clutter.
    for index, y in enumerate(range(-11, 27, 2)):
        offset = 0.18 if index % 2 else -0.12
        add_box(f"SRC_Cobble_{index:02d}", (8.92, y + offset, z_ground + 0.035),
                (0.08, 1.22, 0.07), mats["street_light"], source, bevel=0.02)
    if water:
        add_box("SRC_Canal", (8.85, -1.7, z_ground + 0.02),
                (0.10, 33.0, 0.56), mats["water"], source)
        add_box("SRC_CanalRim", (8.72, -1.7, z_ground + 0.30),
                (0.22, 33.0, 0.16), mats["stone_pale"], source)
    # Runtime-facing street proxy is one broad coarse slab.
    add_box("RND_StreetProxy", (10.0, 4.0, z_ground - 0.10),
            (7.2, 34.0, 0.20), mats["street"], render)
    if water:
        add_box("RND_CanalProxy", (8.85, -1.7, z_ground + 0.02),
                (0.10, 33.0, 0.56), mats["water"], render)


def add_foreground_frame(config, mats, source, render, collision, z_ground):
    y = config["foreground_y"]
    sign = -1 if config["foreground_side"] == "left" else 1
    # A readable partial occluder: it frames a third of the picture, never the lane.
    add_box("SRC_Foreground_Occluder", (7.20, y, z_ground + 2.15),
            (0.72, 0.76, 4.3), mats["stone_shadow"], source, bevel=0.10)
    add_box("SRC_Foreground_OccluderCap", (7.15, y, z_ground + 4.28),
            (0.90, 1.05, 0.22), mats["stone_pale"], source, bevel=0.05)
    add_box("RND_Foreground_Occluder", (7.20, y, z_ground + 2.15),
            (0.78, 0.80, 4.3), mats["stone_shadow"], render)
    add_box("COL_Foreground_Occluder", (7.20, y, z_ground + 2.15),
            (0.84, 0.86, 4.3), mats["stone_shadow"], collision)
    # A low beam on the same side makes depth explicit, but leaves a sightline.
    beam_y = y + sign * 1.35
    add_box("SRC_Foreground_Beam", (7.25, beam_y, z_ground + 3.92),
            (0.64, 1.75, 0.36), mats["stone_rose"], source, bevel=0.06)
    add_box("RND_Foreground_Beam", (7.25, beam_y, z_ground + 3.92),
            (0.68, 1.78, 0.38), mats["stone_rose"], render)


def add_doorway(config, mats, source, render, z_ground):
    y = config["door_y"]
    add_box("SRC_FocalDoorShadow", (8.63, y, z_ground + 1.05),
            (0.16, 1.55, 2.10), mats["wood_dark"], source)
    add_arch_ring("SRC_FocalDoorArch", 8.52, y, z_ground + 0.15,
                  1.82, 2.12, 0.18, mats["stone_pale"], source)
    add_box("SRC_FocalDoorThreshold", (8.42, y, z_ground + 0.12),
            (0.30, 2.0, 0.18), mats["street_light"], source, bevel=0.04)
    add_box("RND_FocalDoorProxy", (8.66, y, z_ground + 1.05),
            (0.18, 1.72, 2.14), mats["wood_dark"], render)
    add_box("RND_FocalDoorHeader", (8.56, y, z_ground + 2.18),
            (0.20, 1.95, 0.18), mats["stone_pale"], render)


def add_shrine(config, mats, source, render, z_ground):
    y = config["door_y"] - 2.5
    add_box("SRC_ShrineBackplate", (8.95, y, z_ground + 1.45),
            (0.22, 2.8, 2.9), mats["stone_blue"], source, bevel=0.07)
    add_cylinder("SRC_ShrineBasin", (8.20, y, z_ground + 0.48), 0.86, 0.56,
                 mats["stone_pale"], source, vertices=16)
    add_cylinder("SRC_ShrinePillar", (8.1, y, z_ground + 1.5), 0.18, 1.9,
                 mats["stone_pale"], source, vertices=8)
    add_uv_sphere("SRC_ShrineLight", (7.82, y, z_ground + 2.42), 0.28,
                  mats["lantern"], source, segments=12, rings=6)
    add_box("RND_ShrineProxy", (8.98, y, z_ground + 1.45),
            (0.25, 2.9, 2.9), mats["stone_blue"], render)
    add_box("RND_ShrineBasinProxy", (8.22, y, z_ground + 0.48),
            (0.48, 1.72, 0.56), mats["stone_pale"], render)


def add_awning(y, mats, source, render, z_ground):
    add_box(f"SRC_Awning_{y:+.1f}", (8.25, y, z_ground + 2.2),
            (1.65, 2.2, 0.16), mats["cloth_red"], source,
            rotation=(0, math.radians(-10), 0), bevel=0.03)
    add_box(f"RND_Awning_{y:+.1f}", (8.25, y, z_ground + 2.2),
            (1.70, 2.2, 0.18), mats["cloth_red"], render)


def add_gatehouse(config, mats, source, render, collision, z_ground):
    y = config["foreground_y"]
    # A near frame and distant tower make the projection window's travel legible.
    add_box("SRC_GatehouseLeft", (10.7, y - 1.7, z_ground + 2.6),
            (2.0, 1.0, 5.2), mats["stone_ochre"], source, bevel=0.10)
    add_box("SRC_GatehouseRight", (10.7, y + 1.7, z_ground + 2.6),
            (2.0, 1.0, 5.2), mats["stone_ochre"], source, bevel=0.10)
    add_box("SRC_GatehouseLintel", (10.7, y, z_ground + 5.0),
            (2.0, 4.4, 0.8), mats["stone_rose"], source, bevel=0.10)
    for side in (-1, 1):
        add_box("RND_Gatehouse_" + str(side), (10.7, y + side * 1.7, z_ground + 2.6),
                (2.1, 1.05, 5.2), mats["stone_ochre"], render)
    add_box("RND_Gatehouse_Lintel", (10.7, y, z_ground + 5.0),
            (2.1, 4.5, 0.82), mats["stone_rose"], render)
    add_box("COL_GatehouseLeft", (10.7, y - 1.7, z_ground + 2.6),
            (2.1, 1.1, 5.2), mats["stone_ochre"], collision)
    add_box("COL_GatehouseRight", (10.7, y + 1.7, z_ground + 2.6),
            (2.1, 1.1, 5.2), mats["stone_ochre"], collision)


def add_background_termination(config, mats, source, render, z_ground):
    y = 17.0 if config["id"] not in (2, 5) else 19.0
    add_box("SRC_Background_Termination", (13.2, y, z_ground + 2.1),
            (1.6, 4.5, 4.2), mats["stone_shadow"], source)
    add_prism_roof("SRC_Background_TerminationRoof", y, 4.8, 13.2, 1.7,
                   z_ground + 4.2, 1.2, mats["roof_blue"], source)
    add_box("RND_Background_Termination", (13.2, y, z_ground + 2.1),
            (1.7, 4.7, 4.2), mats["stone_shadow"], render)
    add_prism_roof("RND_Background_TerminationRoof", y, 4.9, 13.2, 1.8,
                   z_ground + 4.2, 1.2, mats["roof_blue"], render)


def add_lantern(y, mats, source, render, z_ground, index):
    add_box(f"SRC_LanternPost_{index}", (8.32, y, z_ground + 1.18),
            (0.10, 0.10, 2.35), mats["wood_dark"], source)
    add_uv_sphere(f"SRC_LanternGlow_{index}", (8.18, y, z_ground + 2.34), 0.18,
                  mats["lantern"], source, segments=12, rings=6)
    add_box(f"RND_LanternPost_{index}", (8.32, y, z_ground + 1.18),
            (0.12, 0.12, 2.35), mats["wood_dark"], render)
    add_box(f"RND_LanternGlow_{index}", (8.18, y, z_ground + 2.34),
            (0.22, 0.22, 0.35), mats["lantern"], render)


def add_actor(image_path, camera, collection, name, anchor, frame_index, height):
    actor = thestra_camera.create_actor_preview(
        image_path, camera, anchor=anchor, frame_width=FRAME_W, frame_height=FRAME_H,
        frame_index=frame_index, world_height=height, alpha_cutoff=0.5, name=name)
    move_to_collection(actor, collection)
    actor["thestra_actor_role"] = "protagonist" if "Protagonist" in name else "npc"
    actor["thestra_bake_excluded"] = True
    return actor


def create_camera(record, collections, *, offset=0.0):
    camera_record = copy.deepcopy(record)
    camera_record["viewportCenterX"] = float(record["viewportCenterX"]) + float(offset)
    camera_record["projectionWindowOffsetX"] = float(offset)
    scene = bpy.context.scene
    camera = thestra_camera.create_or_update_camera(
        camera_record, scene=scene, name="TH_CAMERA_PREVIEW", make_active=True)
    move_to_collection(camera, collections["TH_CAMERA_PREVIEW"])
    camera["thestra_calibration_source"] = "runtime/presentation/world_camera.lua via world_camera_calibration.lua"
    camera["thestra_preview_contract"] = "thestra.world-camera-calibration"
    camera["thestra_target_resolution"] = f"{TARGET_W}x{TARGET_H}"
    camera["thestra_projection_window_offset_x"] = float(offset)
    bpy.context.view_layer.update()
    return camera


def build_scene(config, calibration, *, render=True, save_path=None, render_path=None):
    scene, collections = reset_scene()
    configure_render(scene, config["mood"])
    mats = {name: make_material(name, color) for name, color in MATERIAL_COLORS.items()}
    # Lanterns are intentionally self-lit so the warm/cool staging survives the
    # baked proof as a readable color note.
    mats["lantern"] = make_material("lantern", MATERIAL_COLORS["lantern"],
                                    emission=MATERIAL_COLORS["lantern"], strength=2.4)
    mats["water"] = make_material("water", MATERIAL_COLORS["water"], roughness=0.32)
    setup_lights(collections, config["mood"])
    source = collections["TH_SOURCE"]
    render_col = collections["TH_RENDER"]
    collision = collections["TH_COLLISION"]
    anchors = collections["TH_ANCHORS"]
    preview = collections["TH_PREVIEW_ACTORS"]
    guides = collections["TH_PREVIEW_ONLY"]

    # The camera fixture is the real first-person WorldCamera calibration. Its
    # resolved optical center sits below the street, so the authored town uses
    # the same world space with a negative ground datum rather than moving the eye.
    z_ground = -2.0
    add_street_details(mats, source, render_col, z_ground, config["street_width"],
                       water=config.get("water", False))
    for index, (y, width, height, color_name, roof_name) in enumerate(config["building_pattern"]):
        door_y = config["door_y"] if index == 3 else None
        add_building(f"Building_{index:02d}", y, width, height, color_name, roof_name,
                     mats, source, render_col, z_ground, door_y=door_y,
                     gable=config.get("gables", False) and index in (0, 4))
    add_doorway(config, mats, source, render_col, z_ground)
    if config.get("shrine"):
        add_shrine(config, mats, source, render_col, z_ground)
    for index, y in enumerate(config.get("awnings", [])):
        add_awning(y, mats, source, render_col, z_ground)
    add_foreground_frame(config, mats, source, render_col, collision, z_ground)
    add_background_termination(config, mats, source, render_col, z_ground)
    if config.get("gatehouse"):
        add_gatehouse(config, mats, source, render_col, collision, z_ground)
    for index, y in enumerate(config["lanterns"]):
        add_lantern(y, mats, source, render_col, z_ground, index)

    # A few meaningful anchors, never actor geometry and never exported into
    # the render mesh.
    add_anchor("spawn_player", (8.22, -3.6, z_ground), anchors, rotation_z=0)
    add_anchor("focal_doorway", (8.50, config["door_y"], z_ground), anchors, rotation_z=0)
    add_anchor("street_midpoint", (9.0, 3.0, z_ground), anchors, rotation_z=0)
    add_anchor("foreground_occluder", (7.2, config["foreground_y"], z_ground), anchors, rotation_z=0)
    add_anchor("town_exit", (12.5, 17.0, z_ground), anchors, rotation_z=0)

    # Preview-only guides document the composition without affecting render or export.
    add_box("GUIDE_StreetLane", (7.0, 3.0, z_ground + 0.015),
            (0.02, config["street_width"], 0.02), mats["lantern"], guides)
    guide = bpy.data.objects.new("GUIDE_ProjectionWindowAxis", None)
    guide.empty_display_type = "SINGLE_ARROW"
    guide.empty_display_size = 4.0
    guide.location = (7.0, 3.0, z_ground + 0.1)
    guides.objects.link(guide)

    camera = create_camera(calibration, collections)
    actor_z = z_ground
    # The calibrated camera's target is centered near world Y=5.5. Keep the
    # preview stand-ins inside that native projection window while retaining
    # the deliberate composition differences in the surrounding architecture.
    def visible_y(value):
        return max(2.45, min(8.55, float(value)))

    protagonist_y = visible_y(config["door_y"] - 1.15)
    npc_y = [visible_y(row[0]) for row in config["npc_positions"]]
    add_actor(WALKER_PATH, camera, preview, "ACTOR_Protagonist_WalkerFrame0",
              (8.15, protagonist_y, actor_z), 0, 1.75)
    add_actor(WALKER_PATH, camera, preview, "ACTOR_NPC_WalkerFrame2",
              (8.05, npc_y[0], actor_z), config["npc_positions"][0][2], 1.55)
    add_actor(WALKER_PATH, camera, preview, "ACTOR_NPC_WalkerFrame4",
              (8.00, npc_y[1], actor_z), config["npc_positions"][1][2], 1.50)
    add_actor(WALKER_PATH, camera, preview, "ACTOR_NPC_WalkerFrame5",
              (8.10, npc_y[2], actor_z), config["npc_positions"][2][2], 1.60)
    bpy.context.view_layer.update()

    # Give every runtime-facing proxy a real UV island before the shared V0
    # bake/export pipeline joins TH_RENDER. Source detail remains untouched.
    for obj in [o for o in render_col.objects if o.type == "MESH"]:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.03)
        bpy.ops.object.mode_set(mode="OBJECT")

    # The camera preview is the only active camera; all non-source collections
    # stay visible in authoring but are hidden from beauty renders as needed.
    collections["TH_RENDER"].hide_render = True
    collections["TH_COLLISION"].hide_render = True
    collections["TH_ANCHORS"].hide_render = True
    collections["TH_PREVIEW_ONLY"].hide_render = True
    collections["TH_CAMERA_PREVIEW"].hide_render = True
    collections["TH_PREVIEW_ACTORS"].hide_render = False
    collections["TH_SOURCE"].hide_render = False
    scene["thestra_camera_contract"] = "thestra.world-camera-calibration"
    scene["thestra_camera_authority"] = "presentation.world_camera.resolve"
    scene["town_attempt_id"] = int(config["id"])
    scene["town_attempt_name"] = config["name"]
    scene["walker_asset"] = "projects/hichaukitoden-game/assets/character/walker.png"
    scene["walker_sheet_dimensions"] = "144x48"
    scene["walker_frame_dimensions"] = "24x48"
    scene["walker_preview_frames"] = "0,2,4,5"
    scene["composition_resolution"] = "426x240"
    scene["composition_note"] = config["note"]
    if render:
        scene.render.filepath = str(Path(render_path).resolve())
        bpy.ops.render.render(write_still=True)
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(save_path).resolve()))
    return {
        "config": config,
        "camera": camera,
        "scene": scene,
        "collections": collections,
    }


def build_attempts(calibration_path, output_dir, *, only=None):
    calibration = thestra_camera.load_calibration(str(calibration_path))
    if not WALKER_PATH.is_file():
        raise FileNotFoundError(f"walker.png is required but missing: {WALKER_PATH}")
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for config in ATTEMPTS:
        if only is not None and config["id"] != only:
            continue
        render_path = output_dir / f"attempt-{config['id']:02d}.png"
        build_scene(config, calibration, render=True, render_path=render_path)
        records.append({
            "id": config["id"], "name": config["name"],
            "image": str(render_path), "note": config["note"],
        })
        print(json.dumps({"attempt": config["id"], "name": config["name"],
                          "image": str(render_path)}, sort_keys=True))
    (output_dir / "attempts.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def build_final(calibration_path, output_dir, final_id):
    calibration = thestra_camera.load_calibration(str(calibration_path))
    config = next(item for item in ATTEMPTS if item["id"] == final_id)
    blend_path = output_dir / "town-pilot.blend"
    final_image = output_dir / f"attempt-{final_id:02d}.png"
    build_scene(config, calibration, render=True, render_path=final_image, save_path=blend_path)
    print(json.dumps({"final": final_id, "blend": str(blend_path),
                      "image": str(final_image)}, sort_keys=True))


def build_projection_strip(calibration_path, output_dir, final_id):
    calibration = thestra_camera.load_calibration(str(calibration_path))
    config = next(item for item in ATTEMPTS if item["id"] == final_id)
    built = build_scene(config, calibration, render=False)
    scene = built["scene"]
    camera = built["camera"]
    strip_dir = output_dir / "projection-window"
    strip_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for label, offset in (("left", -96), ("center", 0), ("right", 96)):
        camera_record = copy.deepcopy(calibration)
        camera_record["viewportCenterX"] = float(calibration["viewportCenterX"]) + offset
        camera_record["projectionWindowOffsetX"] = offset
        camera = thestra_camera.create_or_update_camera(
            camera_record, scene=scene, name="TH_CAMERA_PREVIEW", make_active=True)
        move_to_collection(camera, built["collections"]["TH_CAMERA_PREVIEW"])
        scene.render.filepath = str((strip_dir / f"{label}.png").resolve())
        bpy.ops.render.render(write_still=True)
        rows.append({"label": label, "offset": offset, "image": scene.render.filepath})
        print(json.dumps({"projection": label, "offset": offset,
                          "image": scene.render.filepath}, sort_keys=True))
    # The authored file is saved with the center camera, never with a shifted eye.
    create_camera(calibration, built["collections"], offset=0)
    bpy.ops.wm.save_as_mainfile(filepath=str((output_dir / "town-pilot.blend").resolve()))
    (strip_dir / "projection-window.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", default=str(DEFAULT_CALIBRATION))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--mode", choices=("attempts", "final", "strip"), default="attempts")
    parser.add_argument("--final-id", type=int, default=8)
    parser.add_argument("--only", type=int)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def main():
    args = parse_args()
    calibration_path = Path(args.calibration).resolve()
    output_dir = Path(args.output).resolve()
    if not calibration_path.is_file():
        raise FileNotFoundError(f"Calibration record missing: {calibration_path}")
    if args.mode == "attempts":
        build_attempts(calibration_path, output_dir, only=args.only)
    elif args.mode == "final":
        build_final(calibration_path, output_dir, args.final_id)
    else:
        build_projection_strip(calibration_path, output_dir, args.final_id)


if __name__ == "__main__":
    main()
