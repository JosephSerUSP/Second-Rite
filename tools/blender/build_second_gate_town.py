#!/usr/bin/env python3
"""Author a clean-room Second Gate side-view town environment in Blender.

This is deliberately an art-gauntlet builder, not a runtime exporter.  It
creates three independent architectural propositions from empty Blender
state, renders clay/refined checkpoints, and saves the winning source scene.
The final bake/export is performed by ``town_environment_pipeline.py`` so the
existing selected-to-active beauty-atlas boundary remains the authority.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
WALKER = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"


def rgba(hex_value: str, alpha: float = 1.0):
    value = hex_value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (alpha,)


def fresh_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    world = bpy.data.worlds.new("SecondGateWorld")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = rgba("#101b24")
        bg.inputs["Strength"].default_value = 0.26
    return scene


def collection(name: str):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def layer_collections():
    return {name: collection(name) for name in (
        "TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS",
        "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW",
    )}


def move_to(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def set_material(obj, mat):
    if obj.type in {"MESH", "CURVE", "SURFACE"}:
        obj.data.materials.clear()
        obj.data.materials.append(mat)


def principled(name, color, roughness=0.8, metallic=0.0, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if "Emission Color" in bsdf.inputs and emission:
            bsdf.inputs["Emission Color"].default_value = emission
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def textured(name, colors, roughness, pattern="noise", scale=4.0, bump=0.16, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (540, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-760, 0)
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-160, 90)
    ramp.color_ramp.elements[0].color = colors[0]
    ramp.color_ramp.elements[1].color = colors[1]
    if len(colors) > 2:
        e = ramp.color_ramp.elements.new(0.52)
        e.color = colors[2]
    bump_node = nodes.new("ShaderNodeBump")
    bump_node.location = (60, -170)
    bump_node.inputs["Strength"].default_value = bump
    bump_node.inputs["Distance"].default_value = 0.08

    if pattern == "brick":
        pattern_node = nodes.new("ShaderNodeTexBrick")
        pattern_node.offset = 0.5
        pattern_node.offset_frequency = 2
        pattern_node.squash = 1.0
        if "Mortar Size" in pattern_node.inputs:
            pattern_node.inputs["Mortar Size"].default_value = 0.035
        if "Mortar Smooth" in pattern_node.inputs:
            pattern_node.inputs["Mortar Smooth"].default_value = 0.01
        pattern_node.inputs["Scale"].default_value = scale
        pattern_node.inputs["Color1"].default_value = colors[0]
        pattern_node.inputs["Color2"].default_value = colors[-1]
        pattern_node.inputs["Mortar"].default_value = rgba("#24282c")
        links.new(texcoord.outputs["Generated"], pattern_node.inputs["Vector"])
        links.new(pattern_node.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(pattern_node.outputs["Fac"], bump_node.inputs["Height"])
    elif pattern == "wave":
        pattern_node = nodes.new("ShaderNodeTexWave")
        pattern_node.wave_type = "BANDS"
        pattern_node.bands_direction = "X"
        pattern_node.inputs["Scale"].default_value = scale
        pattern_node.inputs["Distortion"].default_value = 4.0
        pattern_node.inputs["Detail"].default_value = 5.0
        links.new(texcoord.outputs["Generated"], pattern_node.inputs["Vector"])
        links.new(pattern_node.outputs["Color"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(pattern_node.outputs["Fac"], bump_node.inputs["Height"])
    elif pattern == "voronoi":
        pattern_node = nodes.new("ShaderNodeTexVoronoi")
        pattern_node.distance = "EUCLIDEAN"
        pattern_node.feature = "DISTANCE_TO_EDGE"
        pattern_node.inputs["Scale"].default_value = scale
        links.new(texcoord.outputs["Generated"], pattern_node.inputs["Vector"])
        links.new(pattern_node.outputs["Distance"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(pattern_node.outputs["Distance"], bump_node.inputs["Height"])
    else:
        pattern_node = nodes.new("ShaderNodeTexNoise")
        pattern_node.inputs["Scale"].default_value = scale
        pattern_node.inputs["Detail"].default_value = 5.0
        pattern_node.inputs["Roughness"].default_value = 0.72
        links.new(texcoord.outputs["Generated"], pattern_node.inputs["Vector"])
        links.new(pattern_node.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(pattern_node.outputs["Fac"], bump_node.inputs["Height"])

    links.new(bump_node.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def materials():
    return {
        "clay": principled("Clay_Review", rgba("#a59b91"), 1.0),
        "stone": textured("Ashwater_Coursed_Stone", [rgba("#8c8580"), rgba("#4d5658"), rgba("#c0a897")], 0.88, "brick", 5.2, 0.28),
        "plaster": textured("Limewash_Worn_Plaster", [rgba("#b7aa9a"), rgba("#5d6670"), rgba("#d3c5af")], 0.92, "noise", 6.0, 0.22),
        "paving": textured("Wet_Cobbled_Paving", [rgba("#5e6868"), rgba("#222f35"), rgba("#8d8173")], 0.82, "voronoi", 11.0, 0.34),
        "wood": textured("Tarred_Oak_Grain", [rgba("#533c2e"), rgba("#1e2224"), rgba("#8a6143")], 0.76, "wave", 8.0, 0.2),
        "roof": textured("Handcut_Slate_Roof", [rgba("#303f48"), rgba("#111a21"), rgba("#59666b")], 0.9, "brick", 10.0, 0.2),
        "tile": textured("Bellmaker_Terracotta", [rgba("#7e4a3d"), rgba("#38272a"), rgba("#b37558")], 0.82, "brick", 12.0, 0.18),
        "metal": principled("Blackened_Bell_Bronze", rgba("#5a4738"), 0.3, 0.76),
        "iron": principled("Forged_Iron", rgba("#1d2529"), 0.47, 0.84),
        "water": textured("Cold_Canal_Water", [rgba("#1b3b45"), rgba("#07161f")], 0.2, "noise", 5.0, 0.08, 0.15),
        "dark": principled("Unlit_Door_Recess", rgba("#071017"), 0.96),
        "warm": principled("Doorway_Warmth", rgba("#c06a37"), 0.48, 0.0, rgba("#d78049"), 2.4),
        "blue": principled("Shrine_Cool_Light", rgba("#4f9db0"), 0.42, 0.0, rgba("#79d3df"), 3.2),
        "paper": textured("Weathered_Paper_Sign", [rgba("#c0a980"), rgba("#4c392f")], 0.93, "noise", 12.0, 0.08),
    }


def cube(name, loc, scale, mat, col, bevel=0.0, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("Softened_Edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    set_material(obj, mat)
    return move_to(obj, col)


def cylinder(name, loc, radius, depth, mat, col, vertices=16, rotation=(0.0, 0.0, 0.0), bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    set_material(obj, mat)
    if bevel:
        mod = obj.modifiers.new("Softened_Edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return move_to(obj, col)


def sphere(name, loc, radius, mat, col, segments=20, rings=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=loc)
    obj = bpy.context.object
    obj.name = name
    set_material(obj, mat)
    return move_to(obj, col)


def torus(name, loc, major, minor, mat, col, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=24, minor_segments=8, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    set_material(obj, mat)
    return move_to(obj, col)


def prism_xz(name, points, y0, y1, mat, col, bevel=0.0):
    n = len(points)
    verts = [(x, y0, z) for x, z in points] + [(x, y1, z) for x, z in points]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    set_material(obj, mat)
    if bevel:
        mod = obj.modifiers.new("Softened_Edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def plane_xz(name, points, y, mat, col):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata([(x, y, z) for x, z in points], [], [tuple(range(len(points)))])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    set_material(obj, mat)
    return obj


def curve_arc(name, x, y, z, radius, mat, col, bevel=0.09):
    curve = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = bevel
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    points = [(x + radius * math.cos(math.pi * i / 16.0), y, z + radius * math.sin(math.pi * i / 16.0), 1.0) for i in range(17)]
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = co
    obj = bpy.data.objects.new(name, curve)
    col.objects.link(obj)
    set_material(obj, mat)
    return obj


def add_displaced_relief(name, x, y, z, width, height, mat, col):
    # Open, subdivided source-only relief surface: no closed-box edge tearing.
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=24, y_subdivisions=16, size=2.0, location=(x, y, z), rotation=(math.pi / 2.0, 0.0, 0.0))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (width / 2.0, height / 2.0, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    set_material(obj, mat)
    tex = bpy.data.textures.new(name + "_Height_Source", type="CLOUDS")
    tex.noise_scale = 0.24
    tex.noise_depth = 3
    mod = obj.modifiers.new("TH_SOURCE_Rich_Displacement", "DISPLACE")
    mod.texture = tex
    mod.strength = 0.055
    mod.mid_level = 0.5
    return move_to(obj, col)


def arch_points(open_width, spring_z, radius=None):
    radius = radius if radius is not None else open_width / 2.0
    pts = [(-open_width / 2.0, 0.0), (open_width / 2.0, 0.0), (open_width / 2.0, spring_z)]
    for i in range(1, 13):
        theta = math.pi * i / 12.0
        pts.append((radius * math.cos(theta), spring_z + radius * math.sin(theta)))
    return pts


def add_arch_facade(prefix, x, y, width, height, depth, open_width, mat, render_mat, source_col, render_col, recess_mat, ring_mat, z0=0.0):
    side_w = max(0.25, (width - open_width) / 2.0)
    spring = min(height - 0.65, max(2.1, height * 0.62))
    radius = open_width / 2.0
    cube(prefix + "_SRC_LeftJamb", (x - (width - side_w) / 2.0, y, z0 + height / 2.0), (side_w, depth, height), mat, source_col, 0.08)
    cube(prefix + "_SRC_RightJamb", (x + (width - side_w) / 2.0, y, z0 + height / 2.0), (side_w, depth, height), mat, source_col, 0.08)
    top_start = z0 + spring + radius
    if top_start < z0 + height:
        cube(prefix + "_SRC_ArchSpandrel", (x, y, (top_start + z0 + height) / 2.0), (width, depth, z0 + height - top_start), mat, source_col, 0.08)
    cube(prefix + "_RND_LeftJamb", (x - (width - side_w) / 2.0, y, z0 + height / 2.0), (side_w, depth, height), render_mat, render_col)
    cube(prefix + "_RND_RightJamb", (x + (width - side_w) / 2.0, y, z0 + height / 2.0), (side_w, depth, height), render_mat, render_col)
    if top_start < z0 + height:
        cube(prefix + "_RND_ArchSpandrel", (x, y, (top_start + z0 + height) / 2.0), (width, depth, z0 + height - top_start), render_mat, render_col)

    front_y = y - depth / 2.0 - 0.012
    back_y = y + depth / 2.0 + 0.012
    pts = [(px + x, pz + z0) for px, pz in arch_points(open_width, spring, radius)]
    plane_xz(prefix + "_SRC_Deep_Arch_Recess", pts, back_y, recess_mat, source_col)
    plane_xz(prefix + "_RND_Deep_Arch_Recess", pts, back_y, render_mat, render_col)
    cube(prefix + "_SRC_DoorThreshold", (x, front_y - 0.06, 0.06), (open_width + 0.5, depth + 0.12, 0.12), ring_mat, source_col, 0.04)
    cube(prefix + "_RND_DoorThreshold", (x, front_y - 0.06, 0.06), (open_width + 0.5, depth + 0.12, 0.12), render_mat, render_col)
    curve_arc(prefix + "_SRC_Arch_Ring", x, front_y - 0.055, z0 + spring, radius + 0.24, ring_mat, source_col, 0.12)
    cube(prefix + "_SRC_Arch_Left_Pier", (x - open_width / 2.0 - 0.18, front_y - 0.055, z0 + spring / 2.0), (0.36, 0.16, spring), ring_mat, source_col, 0.05)
    cube(prefix + "_SRC_Arch_Right_Pier", (x + open_width / 2.0 + 0.18, front_y - 0.055, z0 + spring / 2.0), (0.36, 0.16, spring), ring_mat, source_col, 0.05)
    return {"front_y": front_y, "spring": spring, "radius": radius, "back_y": back_y}


def add_window(prefix, x, y, z, width, height, depth, wall_mat, frame_mat, source_col, render_col, render_mat):
    # The facade remains real volume; the window is a recessed dark panel with
    # a projecting sill and frame rather than a painted rectangle.
    back_y = y + depth / 2.0 + 0.02
    plane_xz(prefix + "_SRC_Recess", [(x - width / 2, z - height / 2), (x + width / 2, z - height / 2), (x + width / 2, z + height / 2), (x - width / 2, z + height / 2)], back_y, wall_mat, source_col)
    plane_xz(prefix + "_RND_Recess", [(x - width / 2, z - height / 2), (x + width / 2, z - height / 2), (x + width / 2, z + height / 2), (x - width / 2, z + height / 2)], back_y, render_mat, render_col)
    front = y - depth / 2.0 - 0.03
    for dx, dz, sx, sz in ((-(width + 0.18) / 2, 0, 0.14, height + 0.24), ((width + 0.18) / 2, 0, 0.14, height + 0.24), (0, -(height + 0.18) / 2, width + 0.24, 0.14), (0, (height + 0.18) / 2, width + 0.24, 0.14)):
        cube(prefix + "_SRC_Frame", (x + dx, front, z + dz), (sx, 0.16, sz), frame_mat, source_col, 0.035)
    cube(prefix + "_SRC_Sill", (x, front - 0.08, z - height / 2 - 0.12), (width + 0.35, 0.32, 0.16), frame_mat, source_col, 0.04)


def roof_gable(prefix, x, y, width, depth, z, rise, mat, render_mat, source_col, render_col):
    points = [(-width / 2.0, z), (0.0, z + rise), (width / 2.0, z)]
    prism_xz(prefix + "_SRC_GableRoof", [(x + px, pz) for px, pz in points], y - depth / 2.0, y + depth / 2.0, mat, source_col, 0.05)
    prism_xz(prefix + "_RND_GableRoof", [(x + px, pz) for px, pz in points], y - depth / 2.0, y + depth / 2.0, render_mat, render_col)


def awning(prefix, x, y, z, width, depth, mat, render_mat, source_col, render_col, angle=-0.12):
    cube(prefix + "_SRC_Awning", (x, y, z), (width, depth, 0.16), mat, source_col, 0.05, rotation=(0.0, angle, 0.0))
    cube(prefix + "_RND_Awning", (x, y, z), (width, depth, 0.16), render_mat, render_col, 0.0, rotation=(0.0, angle, 0.0))


def add_ground(cols, mats, style="stone"):
    src, rnd, col = cols["TH_SOURCE"], cols["TH_RENDER"], cols["TH_COLLISION"]
    paving = mats["paving"] if style != "terrace" else mats["stone"]
    cube("SRC_Ground_Continuous_Paving", (0.0, 5.0, -0.16), (18.0, 18.0, 0.32), paving, src)
    cube("RND_Ground_Continuous_Paving", (0.0, 5.0, -0.18), (18.0, 18.0, 0.28), mats["clay"], rnd)
    cube("COL_Ground_WalkBounds", (0.0, 5.0, -0.16), (18.0, 18.0, 0.32), mats["clay"], col)
    # Dense source-only fitted slabs establish scale and a material-specific
    # paving read; the coarse runtime plane retains the continuous floor.
    row_y = [-2.0 + i * 1.5 for i in range(9)]
    for row, y in enumerate(row_y):
        x = -13.0 + (0.38 if row % 2 else 0.0)
        i = 0
        while x < 13.0:
            width = 1.06 + 0.15 * ((row * 7 + i * 3) % 4)
            slab = cube(f"SRC_Paving_Slab_{row:02d}_{i:02d}", (x + width / 2.0, y, 0.035), (width, 1.25, 0.065), paving, src)
            slab["bake_exclude"] = True
            x += width + 0.06
            i += 1
    # Continuous drain/canal, with source stones and a coarse runtime trough.
    cube("SRC_Drain_Water", (-3.0, 3.8, 0.028), (0.95, 16.0, 0.035), mats["water"], src)
    cube("RND_Drain_Water", (-3.0, 3.8, 0.02), (0.84, 16.0, 0.025), mats["clay"], rnd)
    for y in [i * 1.8 - 2.0 for i in range(10)]:
        cube(f"SRC_Drain_LeftEdge_{y:.1f}", (-4.0, y, 0.08), (0.16, 0.72, 0.12), mats["stone"], src, 0.03)
        cube(f"SRC_Drain_RightEdge_{y:.1f}", (-2.0, y, 0.08), (0.16, 0.72, 0.12), mats["stone"], src, 0.03)
    # A threshold strip gives the player a readable action plane.
    cube("SRC_Action_Lane_Threshold", (3.8, 2.0, 0.07), (10.0, 0.22, 0.12), mats["stone"], src, 0.03)
    cube("RND_Action_Lane_Threshold", (3.8, 2.0, 0.07), (10.0, 0.20, 0.10), mats["clay"], rnd)


def add_background(cols, mats, style="stone"):
    src, rnd = cols["TH_SOURCE"], cols["TH_RENDER"]
    wall_mat = mats["stone"] if style != "plaster" else mats["plaster"]
    roof_mat = mats["roof"] if style != "tile" else mats["tile"]
    # Segmented skyline: it continues beyond every projection window without
    # becoming one photographed slab.
    segments = [(-14.0, 4.0, 6.0), (-7.5, 4.7, 7.0), (0.0, 4.2, 6.0), (7.2, 4.9, 7.2), (14.2, 3.9, 5.5)]
    for i, (x, h, w) in enumerate(segments):
        cube(f"SRC_Background_Block_{i}", (x, 10.5 + (i % 2) * 0.35, h / 2.0), (w, 0.9, h), wall_mat, src, 0.08)
        cube(f"RND_Background_Block_{i}", (x, 10.5 + (i % 2) * 0.35, h / 2.0), (w, 0.85, h), mats["clay"], rnd)
        roof_gable(f"BACKGROUND_{i}", x, 10.5 + (i % 2) * 0.35, w + 0.5, 1.2, h, 0.9 + 0.12 * (i % 3), roof_mat, mats["clay"], src, rnd)
    # Distant tower and water tank provide a readable depth landmark.
    cube("SRC_Distant_Bell_Tower", (-9.4, 11.3, 5.0), (1.5, 1.0, 5.0), wall_mat, src, 0.08)
    cube("RND_Distant_Bell_Tower", (-9.4, 11.3, 5.0), (1.4, 0.95, 5.0), mats["clay"], rnd)
    roof_gable("DISTANT_TOWER", -9.4, 11.3, 3.6, 1.3, 10.0, 1.3, roof_mat, mats["clay"], src, rnd)
    cylinder("SRC_Distant_Tower_Bell", (-9.4, 10.7, 6.8), 0.42, 0.8, mats["metal"], src, 18, rotation=(math.pi / 2.0, 0.0, 0.0))
    cylinder("RND_Distant_Tower_Bell", (-9.4, 10.7, 6.8), 0.36, 0.7, mats["clay"], rnd, 10, rotation=(math.pi / 2.0, 0.0, 0.0))


def add_direction_a(cols, mats, refined=False):
    src, rnd, col = cols["TH_SOURCE"], cols["TH_RENDER"], cols["TH_COLLISION"]
    add_ground(cols, mats, "stone")
    add_background(cols, mats, "stone")
    # Canal arcade: a deep continuous colonnade sits behind the action lane.
    for i, x in enumerate([-8.8, -5.8, -2.8, 0.2, 3.2, 6.2, 9.2]):
        cylinder(f"SRC_Arcade_Column_{i}", (x, 4.9, 2.2), 0.42, 4.4, mats["stone"], src, 18, bevel=0.04)
        cube(f"RND_Arcade_Column_{i}", (x, 4.9, 2.2), (0.38, 0.42, 2.2), mats["clay"], rnd)
    cube("SRC_Arcade_Entablature", (0.2, 4.9, 4.65), (11.7, 0.7, 0.42), mats["stone"], src, 0.06)
    cube("RND_Arcade_Entablature", (0.2, 4.9, 4.65), (11.7, 0.65, 0.4), mats["clay"], rnd)
    for x in [-7.3, -1.3, 4.7]:
        add_arch_facade(f"ARCADE_{x}", x, 5.25, 2.8, 3.2, 0.7, 1.7, mats["plaster"], mats["clay"], src, rnd, mats["dark"], mats["stone"], 0.0)
    # Near-side bridge and a roofed foreground threshold give real occlusion.
    for x in [-9.8, -7.8]:
        cylinder(f"SRC_Foreground_Arcade_Pier_{x}", (x, 0.15, 2.0), 0.55, 4.0, mats["stone"], src, 16, bevel=0.05)
        cube(f"RND_Foreground_Arcade_Pier_{x}", (x, 0.15, 2.0), (0.55, 0.62, 2.0), mats["clay"], rnd)
    cube("SRC_Foreground_Arcade_Beam", (-8.8, 0.15, 4.15), (2.0, 0.7, 0.45), mats["wood"], src, 0.08)
    cube("RND_Foreground_Arcade_Beam", (-8.8, 0.15, 4.15), (2.0, 0.64, 0.42), mats["clay"], rnd)
    roof_gable("FORE_ARCADE_ROOF", -8.8, 0.15, 3.6, 1.7, 4.38, 0.85, mats["roof"], mats["clay"], src, rnd)
    add_arch_facade("CANAL_GATE", 4.9, 6.2, 4.5, 5.1, 0.95, 2.1, mats["stone"], mats["clay"], src, rnd, mats["dark"], mats["metal"], 0.0)
    cube("COL_Canal_Gate", (4.9, 6.2, 2.45), (2.2, 0.9, 2.45), mats["clay"], col)
    cube("COL_Arcade_BackWall", (0.0, 6.0, 2.5), (12.0, 0.8, 2.5), mats["clay"], col)


def add_direction_b(cols, mats, refined=False):
    src, rnd, col = cols["TH_SOURCE"], cols["TH_RENDER"], cols["TH_COLLISION"]
    add_ground(cols, mats, "terrace")
    add_background(cols, mats, "plaster")
    # Terraced rookery: staggered floor plates, stairs and projecting timber.
    for i, (x, y, z, w, h) in enumerate([(-8.0, 6.0, 2.0, 4.0, 4.0), (-3.3, 6.7, 2.8, 4.4, 5.6), (1.7, 6.2, 2.2, 3.6, 4.4), (6.0, 6.9, 3.0, 4.8, 6.0), (10.3, 6.0, 2.0, 3.6, 4.0)]):
        cube(f"SRC_Terrace_Block_{i}", (x, y, h / 2.0), (w, 1.35, h), mats["plaster"] if i % 2 else mats["stone"], src, 0.08)
        cube(f"RND_Terrace_Block_{i}", (x, y, h / 2.0), (w, 1.25, h), mats["clay"], rnd)
        roof_gable(f"TERRACE_ROOF_{i}", x, y, w + 0.5, 2.0, h, 1.0 + 0.16 * (i % 2), mats["tile"], mats["clay"], src, rnd)
        add_window(f"TERRACE_WINDOW_{i}", x, y - 0.73, 2.5 + (i % 2) * 1.5, 0.9, 1.2, 0.12, mats["dark"], mats["wood"], src, rnd, mats["clay"])
    # Central stepped route reads as traversable architecture, not a pasted strip.
    for i in range(5):
        x = -1.0 + i * 0.55
        y = 4.0 + i * 0.42
        z = 0.08 + i * 0.18
        cube(f"SRC_Central_Step_{i}", (x, y, z), (3.8 - i * 0.28, 1.0, 0.16), mats["stone"], src, 0.04)
        cube(f"RND_Central_Step_{i}", (x, y, z), (3.8 - i * 0.28, 0.95, 0.15), mats["clay"], rnd)
    add_arch_facade("ROOKERY_ENTRY", 2.9, 7.8, 4.1, 5.6, 1.0, 2.0, mats["stone"], mats["clay"], src, rnd, mats["dark"], mats["wood"], 0.2)
    # Foreground timber balcony overlaps the lane with a believable house mass.
    cube("SRC_Foreground_TimberHouse", (8.4, 0.6, 2.3), (3.0, 1.5, 2.3), mats["wood"], src, 0.08)
    cube("RND_Foreground_TimberHouse", (8.4, 0.6, 2.3), (2.9, 1.35, 2.3), mats["clay"], rnd)
    for x in [6.1, 10.7]:
        cube(f"SRC_Timber_Post_{x}", (x, -0.05, 2.5), (0.18, 0.22, 2.5), mats["wood"], src, 0.03)
    awning("ROOKERY_FORE_AWNING", 8.4, 0.0, 4.8, 6.2, 2.3, mats["tile"], mats["clay"], src, rnd, -0.15)
    cube("COL_Rookery_Foreground_House", (8.4, 0.6, 2.3), (3.0, 1.5, 2.3), mats["clay"], col)
    cube("COL_Rookery_BackWall", (0.0, 7.8, 3.0), (12.0, 0.9, 3.0), mats["clay"], col)


def add_direction_c(cols, mats, refined=False):
    src, rnd, col = cols["TH_SOURCE"], cols["TH_RENDER"], cols["TH_COLLISION"]
    add_ground(cols, mats, "stone")
    add_background(cols, mats, "stone")
    # Final lineage: a bell-foundry gate joining a covered market, a deep portal,
    # an open service bay and a naturally necessary foreground arcade.
    add_arch_facade("FOUNDRY_PORTAL", 1.9, 6.65, 5.5, 6.0, 1.25, 2.45, mats["stone"], mats["clay"], src, rnd, mats["dark"], mats["metal"], 0.0)
    cube("SRC_Foundry_Portal_Cap", (1.9, 6.65, 6.18), (5.9, 1.45, 0.42), mats["stone"], src, 0.08)
    cube("RND_Foundry_Portal_Cap", (1.9, 6.65, 6.18), (5.7, 1.36, 0.38), mats["clay"], rnd)
    add_displaced_relief("SRC_Foundry_Relief_Panel", 1.9, 5.98, 4.9, 2.9, 1.25, mats["stone"], src)
    # Warm playable doorway inset, kept distinct from the cool shrine light.
    door_pts = [(1.9 - 1.02, 0.08), (1.9 + 1.02, 0.08), (1.9 + 1.02, 2.65)]
    for i in range(1, 13):
        theta = math.pi * i / 12.0
        door_pts.append((1.9 + 1.02 * math.cos(theta), 2.65 + 1.02 * math.sin(theta)))
    plane_xz("SRC_Foundry_Door_Leaf", door_pts, 7.30, mats["warm"], src)
    plane_xz("RND_Foundry_Door_Leaf", door_pts, 7.30, mats["clay"], rnd)
    # The bell hangs in the portal's upper void, a landmark visible at native size.
    torus("SRC_Foundry_Bell_Rim", (1.9, 6.00, 4.65), 0.48, 0.12, mats["metal"], src, rotation=(math.pi / 2.0, 0.0, 0.0))
    sphere("SRC_Foundry_Bell", (1.9, 6.00, 4.55), 0.42, mats["metal"], src, 20, 12)
    cylinder("SRC_Foundry_Bell_Clapper", (1.9, 6.00, 4.05), 0.08, 0.65, mats["iron"], src, 10)
    cylinder("RND_Foundry_Bell", (1.9, 6.00, 4.55), 0.38, 0.5, mats["clay"], rnd, 10)
    # Left guild hall: layered walls, windows, and an overhanging roof.
    add_arch_facade("GUILDHALL_ENTRY", -5.1, 6.2, 4.9, 4.9, 1.0, 1.75, mats["plaster"], mats["clay"], src, rnd, mats["dark"], mats["wood"], 0.0)
    add_window("GUILDHALL_WINDOW_A", -6.5, 5.65, 3.25, 0.95, 1.3, 0.14, mats["blue"], mats["wood"], src, rnd, mats["clay"])
    add_window("GUILDHALL_WINDOW_B", -3.8, 5.65, 3.25, 0.95, 1.3, 0.14, mats["blue"], mats["wood"], src, rnd, mats["clay"])
    roof_gable("GUILDHALL_ROOF", -5.1, 6.2, 5.5, 1.8, 4.92, 1.15, mats["roof"], mats["clay"], src, rnd)
    awning("GUILDHALL_AWNING", -5.1, 5.25, 2.55, 4.3, 1.0, mats["wood"], mats["clay"], src, rnd, -0.1)
    # Right workshop is open to the lane: a recessed service bay with real
    # depth, counter, hanging fabric and stacked crates.
    cube("SRC_MARKET_Workshop_Left", (6.0, 6.35, 2.4), (1.2, 1.0, 2.4), mats["stone"], src, 0.08)
    cube("SRC_MARKET_Workshop_Right", (10.0, 6.35, 2.4), (1.0, 1.0, 2.4), mats["stone"], src, 0.08)
    cube("SRC_MARKET_Workshop_Top", (8.0, 6.35, 4.65), (3.2, 1.0, 0.55), mats["stone"], src, 0.08)
    cube("RND_MARKET_Workshop_Left", (6.0, 6.35, 2.4), (1.1, 0.92, 2.4), mats["clay"], rnd)
    cube("RND_MARKET_Workshop_Right", (10.0, 6.35, 2.4), (0.92, 0.92, 2.4), mats["clay"], rnd)
    cube("RND_MARKET_Workshop_Top", (8.0, 6.35, 4.65), (3.1, 0.88, 0.5), mats["clay"], rnd)
    plane_xz("SRC_MARKET_Service_Recess", [(6.4, 0.7), (9.6, 0.7), (9.6, 4.2), (6.4, 4.2)], 6.88, mats["dark"], src)
    plane_xz("RND_MARKET_Service_Recess", [(6.4, 0.7), (9.6, 0.7), (9.6, 4.2), (6.4, 4.2)], 6.88, mats["clay"], rnd)
    cube("SRC_MARKET_Counter", (8.0, 5.55, 1.18), (3.0, 1.0, 0.18), mats["wood"], src, 0.04)
    cube("RND_MARKET_Counter", (8.0, 5.55, 1.18), (2.9, 0.9, 0.16), mats["clay"], rnd)
    awning("MARKET_AWNING", 8.0, 5.0, 4.0, 4.0, 1.9, mats["tile"], mats["clay"], src, rnd, 0.1)
    for i, (x, z) in enumerate([(6.6, 0.45), (7.2, 0.42), (9.8, 0.5), (10.4, 0.45)]):
        cube(f"SRC_Market_Crate_{i}", (x, 4.95, z), (0.48, 0.48, 0.45), mats["wood"], src, 0.04)
        cube(f"RND_Market_Crate_{i}", (x, 4.95, z), (0.44, 0.44, 0.4), mats["clay"], rnd)
    roof_gable("MARKET_ROOF", 8.0, 6.35, 5.0, 1.8, 5.1, 1.15, mats["roof"], mats["clay"], src, rnd)
    # Genuine near foreground: a covered bell-maker's arcade, with columns,
    # roof mass and a bridge rail that can occlude the action lane.
    for i, x in enumerate([-10.3, -8.0, 10.6]):
        cylinder(f"SRC_FOREGROUND_Arcade_Pier_{i}", (x, 0.05, 2.15), 0.48, 4.3, mats["stone"], src, 18, bevel=0.05)
        cube(f"RND_FOREGROUND_Arcade_Pier_{i}", (x, 0.05, 2.15), (0.46, 0.58, 2.15), mats["clay"], rnd)
    # Visible supports bring the near arcade into the native frame.  The
    # bellmaker anchor sits just behind the left one, proving real overlap.
    for i, x in enumerate([-5.4, 3.6]):
        cylinder(f"SRC_FOREGROUND_Visible_Pier_{i}", (x, 0.05, 2.15), 0.46, 4.3, mats["stone"], src, 18, bevel=0.05)
        cube(f"RND_FOREGROUND_Visible_Pier_{i}", (x, 0.05, 2.15), (0.44, 0.58, 2.15), mats["clay"], rnd)
    cube("SRC_FOREGROUND_Arcade_Beam", (-1.0, 0.05, 4.45), (9.6, 0.72, 0.42), mats["wood"], src, 0.08)
    cube("RND_FOREGROUND_Arcade_Beam", (-1.0, 0.05, 4.45), (9.5, 0.64, 0.38), mats["clay"], rnd)
    roof_gable("FOREGROUND_ARCADE_ROOF", -1.0, 0.05, 11.0, 1.9, 4.75, 0.85, mats["roof"], mats["clay"], src, rnd)
    # A second middle-depth canopy catches the projection-window pans.
    awning("MID_CANOPY", -9.0, 2.7, 3.35, 3.5, 1.2, mats["tile"], mats["clay"], src, rnd, -0.12)
    cube("SRC_Mid_Canopy_Post", (-9.0, 2.7, 1.6), (0.18, 0.18, 1.6), mats["wood"], src, 0.03)
    cube("RND_Mid_Canopy_Post", (-9.0, 2.7, 1.6), (0.16, 0.16, 1.6), mats["clay"], rnd)
    # Colliders are intentionally a small authored set, not a copy of render.
    cube("COL_Foreground_Arcade_Occluder", (-1.0, 0.05, 2.2), (10.0, 0.75, 2.2), mats["clay"], col)
    cube("COL_Foreground_Visible_Pier_Left", (-5.4, 0.05, 2.15), (0.5, 0.65, 2.15), mats["clay"], col)
    cube("COL_Foreground_Visible_Pier_Right", (3.6, 0.05, 2.15), (0.5, 0.65, 2.15), mats["clay"], col)
    cube("COL_Foundry_BackWall", (1.9, 6.65, 3.0), (2.75, 1.3, 3.0), mats["clay"], col)
    cube("COL_Guildhall_BackWall", (-5.1, 6.2, 2.45), (2.45, 1.1, 2.45), mats["clay"], col)
    cube("COL_Market_RightWall", (10.0, 6.35, 2.4), (1.0, 1.0, 2.4), mats["clay"], col)


def anchor(name, loc, rot_z, col):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 0.55
    obj.location = loc
    obj.rotation_euler[2] = math.radians(rot_z)
    col.objects.link(obj)
    return obj


def add_anchors(cols):
    col = cols["TH_ANCHORS"]
    anchor("spawn_player", (-7.0, 2.0, 0.0), 0.0, col)
    anchor("walk_start", (-10.0, 2.0, 0.0), 0.0, col)
    anchor("walk_end", (11.5, 2.0, 0.0), 0.0, col)
    anchor("doorway", (1.9, 7.2, 0.0), 0.0, col)
    anchor("npc_bellmaker", (-5.1, 2.0, 0.0), 0.0, col)
    anchor("npc_vendor", (7.9, 2.0, 0.0), 180.0, col)
    anchor("npc_archivist", (4.1, 4.6, 0.0), 180.0, col)
    anchor("foreground_occluder", (-1.0, 0.05, 0.0), 0.0, col)
    anchor("doorway_interaction", (1.9, 7.05, 1.0), 0.0, col)


def add_lights(cols, mats):
    src = cols["TH_SOURCE"]
    def area(name, loc, energy, size, color, target=(0.0, 5.0, 1.5)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.data.color = color
        direction = Vector(target) - light.location
        light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        move_to(light, src)
    area("SRC_Soft_Dawn", (-2.0, -2.0, 11.0), 950.0, 10.0, (0.86, 0.91, 1.0), (0.0, 5.0, 0.0))
    area("SRC_Warm_Foundry", (1.9, 5.0, 3.0), 450.0, 3.0, (1.0, 0.46, 0.22), (1.9, 6.6, 2.0))
    area("SRC_Cool_Door_Light", (1.9, 7.0, 2.0), 220.0, 1.4, (0.25, 0.68, 0.82), (1.9, 6.0, 1.4))
    area("SRC_Market_Fill", (8.0, 3.0, 6.0), 260.0, 4.0, (0.94, 0.66, 0.38), (8.0, 6.0, 2.0))


def setup_camera(record, cols, actor=False):
    sys.path.insert(0, str(ROOT / "tools" / "blender"))
    from thestra_camera import create_actor_preview, create_or_update_camera

    cam = create_or_update_camera(record, name="TH_CAMERA_PREVIEW", make_active=True)
    move_to(cam, cols["TH_CAMERA_PREVIEW"])
    if actor:
        actor_specs = [
            ("PREVIEW_Walker_Player", 0, (-7.0, 2.0, 0.0)),
            ("PREVIEW_Walker_Bellmaker", 2, (-5.1, 2.0, 0.0)),
            ("PREVIEW_Walker_Vendor", 4, (7.9, 2.0, 0.0)),
        ]
        for name, frame, loc in actor_specs:
            obj = create_actor_preview(WALKER, cam, anchor=loc, frame_width=24, frame_height=48, frame_index=frame, world_height=1.75, name=name)
            move_to(obj, cols["TH_PREVIEW_ACTORS"])
    return cam


def record():
    return {
        "contract": "thestra.world-camera-calibration",
        "version": 1,
        "projection": "perspective",
        "targetWidth": 426,
        "targetHeight": 240,
        "baseViewportWidth": 256,
        "baseViewportHeight": 144,
        "projectionScale": {"x": 1.0, "y": 1.0},
        "fovHalfX": 0.25,
        "fovHalfY": 0.140625,
        "viewportCenterX": 213.0,
        "viewportCenterY": 110.0,
        "projectionWindowOffsetX": 0.0,
        "projectionWindowOffsetY": 0.0,
        "eye": {"x": 0.0, "y": -16.5, "z": 2.65},
        "orientation": {"forwardX": 0.0, "forwardY": 1.0, "rightX": 1.0, "rightY": 0.0, "pitchRadians": 0.0},
        "coordinateSystem": {
            "handedness": "right-handed", "worldUp": "+Z", "worldHorizontal": "XY",
            "cameraForward": "+depth", "cameraRight": "+right", "screenOrigin": "top-left",
            "screenY": "+down", "blenderCameraForward": "-Z", "blenderCameraUp": "+Y",
        },
        "nearPlane": 0.05,
        "farPlane": 80.0,
        "lensMm": 43.27,
        "pitchDegrees": 0.0,
        "walkerWorldHeight": 1.75,
        "walkerTargetPixels": 48.0,
    }


def join_render_mesh(cols, mats):
    render_col = cols["TH_RENDER"]
    meshes = [obj for obj in render_col.objects if obj.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    target = bpy.context.object
    target.name = "RND_Environment_Mesh"
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.025)
    bpy.ops.object.mode_set(mode="OBJECT")
    set_material(target, mats["clay"])
    target["second_gate_role"] = "coarse_real_3d_runtime_depth_and_silhouette"
    return target


def set_stage(scene, cols, mats, stage):
    clay = mats["clay"]
    for col_name in ("TH_SOURCE", "TH_RENDER"):
        for obj in cols[col_name].objects:
            if obj.type in {"MESH", "CURVE", "SURFACE"} and stage == "clay":
                set_material(obj, clay)
    # Keep source lights available for clay/runtime previews while hiding the
    # source meshes when the coarse render layer is the subject.
    cols["TH_SOURCE"].hide_render = False
    cols["TH_RENDER"].hide_render = stage != "refined_source" and stage != "final_source"
    cols["TH_PREVIEW_ACTORS"].hide_render = stage != "final_source"
    cols["TH_COLLISION"].hide_render = True
    cols["TH_ANCHORS"].hide_render = True
    cols["TH_PREVIEW_ONLY"].hide_render = True
    cols["TH_CAMERA_PREVIEW"].hide_render = True
    for name in ("TH_SOURCE", "TH_RENDER", "TH_PREVIEW_ACTORS", "TH_COLLISION", "TH_ANCHORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW"):
        for obj in cols[name].objects:
            obj.hide_render = cols[name].hide_render
    if stage == "clay":
        for obj in cols["TH_SOURCE"].objects:
            obj.hide_render = obj.type != "LIGHT"
    elif stage in {"refined_source", "final_source"}:
        for obj in cols["TH_SOURCE"].objects:
            obj.hide_render = False
    if stage in {"refined_source", "final_source"}:
        cols["TH_SOURCE"].hide_render = False
        for obj in cols["TH_SOURCE"].objects:
            obj.hide_render = False
    elif stage == "clay":
        cols["TH_RENDER"].hide_render = False
        for obj in cols["TH_RENDER"].objects:
            obj.hide_render = False


def render_to(path):
    scene = bpy.context.scene
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def build_scene(direction, stage, blend_path, render_path=None, final=False):
    scene = fresh_scene()
    cols = layer_collections()
    mats = materials()
    if direction == "A":
        add_direction_a(cols, mats)
    elif direction == "B":
        add_direction_b(cols, mats)
    elif direction == "C":
        add_direction_c(cols, mats)
    else:
        raise ValueError(direction)
    add_anchors(cols)
    add_lights(cols, mats)
    # Keep source appearance spatially authoritative while giving the
    # selected-to-active bake a deterministic outward shell.  The visible
    # source beauty changes by less than a pixel at the review camera, but
    # coplanar source/render faces no longer starve the bake rays.
    for obj in cols["TH_SOURCE"].objects:
        if obj.type in {"MESH", "CURVE", "SURFACE"}:
            obj.location.y -= 0.06
            obj["source_bake_shell_offset_y"] = -0.06
    join_render_mesh(cols, mats)
    cam_record = record()
    setup_camera(cam_record, cols, actor=final)
    scene["second_gate_environment_id"] = "ashwater_bellfoundry_lane"
    scene["architectural_direction"] = direction
    scene["authoring_stage"] = stage
    scene["native_resolution"] = "426x240"
    scene["camera_contract"] = "Thestra WorldCamera; 43.27mm equivalent; pitch 0 degrees"
    scene["walker_contract"] = "24x48 frame; 1.75 world units; feet anchored"
    scene["beauty_atlas_authority"] = "TH_SOURCE selected-to-active bake onto TH_RENDER UVs"
    scene["material_provenance"] = "Original procedural Blender node materials; no external environment images"
    set_stage(scene, cols, mats, stage)
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    if render_path:
        render_to(render_path)
    return scene


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--winning-only", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def main():
    args = parse_args()
    out_root = Path(args.out_root).resolve()
    (out_root / "renders" / "clay").mkdir(parents=True, exist_ok=True)
    (out_root / "renders" / "refined").mkdir(parents=True, exist_ok=True)
    (out_root / "renders" / "final").mkdir(parents=True, exist_ok=True)

    # Each proposition is reset to a truly empty Blender scene before build.
    directions = ("C",) if args.winning_only else ("A", "B", "C")
    for direction in directions:
        build_scene(direction, "clay", out_root / f"direction_{direction.lower()}_initial.blend", out_root / "renders" / "clay" / f"direction_{direction.lower()}_initial.png")
        build_scene(direction, "refined_source", out_root / f"direction_{direction.lower()}_refined.blend", out_root / "renders" / "refined" / f"direction_{direction.lower()}_refined.png")

    camera_path = out_root / "camera_record.json"
    camera_path.write_text(json.dumps(record(), indent=2) + "\n", encoding="utf-8")
    final_blend = out_root / "second_gate_ashwater_bellfoundry.blend"
    build_scene("C", "final_source", final_blend, out_root / "renders" / "final" / "th_source_rich.png", final=True)
    print(f"SECOND_GATE_BUILD_OK {out_root}")


if __name__ == "__main__":
    main()
