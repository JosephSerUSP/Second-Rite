#!/usr/bin/env python3
"""Author two Second Gate side-view town directions from empty Blender scenes.

This is the focused 2026-08-21 art gauntlet.  It deliberately delegates camera,
render profiles, facade projection, and runtime baking to the #881 tooling.  The
builder owns only the scene composition and the authored source geometry.
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
CAMERA_RECORD = ROOT / "tools" / "blender" / "tests" / "fixtures" / "thestra_camera_calibration.json"
WALKER = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
ART_ROOT = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "second_gate_side_view_20260821"
GENERATED = ART_ROOT / "generated"


def rgba(value: str, alpha: float = 1.0):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (alpha,)


def fresh_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.engine = "BLENDER_EEVEE"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    world = bpy.data.worlds.new("SecondGateSideViewWorld")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = rgba("#0d1822")
        background.inputs["Strength"].default_value = 0.18
    return scene


def make_collections():
    names = (
        "TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS",
        "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW",
    )
    result = {}
    for name in names:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
        result[name] = col
    return result


def move_to(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def set_material(obj, mat):
    if obj.type == "MESH":
        obj.data.materials.clear()
        obj.data.materials.append(mat)


def principled(name, color, roughness=0.8, metallic=0.0, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if emission is not None:
            if bsdf.inputs.get("Emission Color"):
                bsdf.inputs["Emission Color"].default_value = emission
                bsdf.inputs["Emission Strength"].default_value = strength
            elif bsdf.inputs.get("Emission"):
                bsdf.inputs["Emission"].default_value = emission
    return mat


def image_material(name, image_path: Path, tint=(1.0, 1.0, 1.0, 1.0)):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    tex = nodes.new("ShaderNodeTexImage")
    tex.name = "GeneratedFacadeImage"
    tex.image = bpy.data.images.load(str(image_path.resolve()), check_existing=True)
    tex.interpolation = "Linear"
    tex.image.colorspace_settings.name = "sRGB"
    bsdf.inputs["Roughness"].default_value = 0.84
    links.new(texcoord.outputs["UV"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat["sr_material_strategy"] = "image_assisted_projected_surface"
    mat["sr_material_source"] = image_path.relative_to(ROOT).as_posix()
    mat["sr_material_provider"] = "OpenAI built-in image generation"
    mat["sr_material_tint"] = list(tint)
    return mat


def cube(name, loc, scale, mat, col, bevel=0.0, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat is not None:
        set_material(obj, mat)
    if bevel:
        mod = obj.modifiers.new("AuthoringBevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
    return move_to(obj, col)


def cylinder(name, loc, radius, depth, mat, col, rotation=(0.0, 0.0, 0.0), vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    set_material(obj, mat)
    return move_to(obj, col)


def sphere(name, loc, radius, mat, col):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=radius, location=loc)
    obj = bpy.context.object
    obj.name = name
    set_material(obj, mat)
    return move_to(obj, col)


def panel(name, x, y0, y1, z0, z1, mat, col):
    """Camera-facing panel with an ordinary UVMap and normal toward -X."""
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata([
        (x, y0, z0), (x, y0, z1), (x, y1, z1), (x, y1, z0),
    ], [], [(0, 1, 2, 3)])
    mesh.update()
    uv = mesh.uv_layers.new(name="UVMap")
    for loop in mesh.loops:
        uv.data[loop.index].uv = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))[loop.vertex_index]
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    set_material(obj, mat)
    obj["sr_projection_target"] = True
    return obj


def anchor(name, loc, col, forward=(0.0, 1.0, 0.0)):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 0.35
    obj.location = loc
    obj.rotation_euler[2] = math.atan2(forward[1], forward[0]) - math.pi * 0.5
    col.objects.link(obj)
    return obj


def add_window(prefix, y, z, theme, mats, source_col, refined):
    x = 9.18
    dark = cube(prefix + "_Recess", (x, y, z), (0.16, 0.42, 0.68), mats["dark"], source_col, bevel=0.05)
    trim = mats["trim"]
    cube(prefix + "_Sill", (x - 0.06, y, z - 0.78), (0.18, 0.55, 0.09), trim, source_col, bevel=0.03)
    cube(prefix + "_Header", (x - 0.06, y, z + 0.78), (0.18, 0.55, 0.09), trim, source_col, bevel=0.03)
    for offset in (-0.46, 0.46):
        cube(prefix + "_Jamb_" + str(offset), (x - 0.06, y + offset, z), (0.18, 0.08, 0.76), trim, source_col, bevel=0.02)
    if theme == "aqueduct":
        cube(prefix + "_Glow", (x - 0.18, y, z), (0.03, 0.28, 0.54), mats["glow"], source_col)
    else:
        cube(prefix + "_Glow", (x - 0.18, y, z), (0.03, 0.28, 0.54), mats["glow"], source_col)
    return dark


def add_pipe(prefix, y, z0, z1, mats, source_col):
    cylinder(prefix + "_Vertical", (9.05, y, (z0 + z1) * 0.5), 0.075, z1 - z0, mats["metal"], source_col)
    cylinder(prefix + "_Elbow", (9.05, y + 0.35, z0), 0.10, 0.7, mats["metal"], source_col, rotation=(math.pi * 0.5, 0.0, 0.0))


def add_doorway(prefix, y, mats, source_col, render_col, refined):
    # The gap is left open through both source and runtime massing; this dark
    # interior is a real recessed volume, not a painted doorway card.
    cube(prefix + "_Interior", (10.05, y, -0.22), (1.18, 0.62, 1.32), mats["dark"], source_col, bevel=0.05)
    cube(prefix + "_InteriorFloor", (10.0, y, -1.34), (1.2, 0.62, 0.10), mats["ground"], source_col)
    for dy in (-0.78, 0.78):
        cube(prefix + "_Jamb_" + str(dy), (9.10, y + dy, -0.08), (0.20, 0.13, 1.45), mats["trim"], source_col, bevel=0.05)
    cube(prefix + "_Lintel", (9.10, y, 1.34), (0.20, 0.95, 0.18), mats["trim"], source_col, bevel=0.06)
    cube(prefix + "_Step", (8.98, y, -1.42), (0.35, 0.96, 0.10), mats["stone"], source_col, bevel=0.03)
    # Runtime keeps the same void and its interior silhouette.
    cube(prefix + "_RuntimeInterior", (10.05, y, -0.22), (1.18, 0.62, 1.32), mats["dark"], render_col, bevel=0.05)
    cube(prefix + "_RuntimeFloor", (10.0, y, -1.34), (1.2, 0.62, 0.10), mats["ground"], render_col)


def add_archway(prefix, y, mats, source_col, height=4.3):
    # A shallow triangular pediment reads as an arch at native size while the
    # usable doorway below remains a genuine gap in the massing.
    cube(prefix + "_Pediment", (9.05, y, height), (0.24, 1.25, 0.16), mats["trim"], source_col, bevel=0.08)
    cube(prefix + "_Crest", (8.88, y, height + 0.42), (0.10, 0.30, 0.30), mats["accent"], source_col, bevel=0.04)


def build_direction(direction: str, refined: bool, output_blend: Path, output_render: Path):
    scene = fresh_scene()
    cols = make_collections()
    source_col = cols["TH_SOURCE"]
    render_col = cols["TH_RENDER"]
    collision_col = cols["TH_COLLISION"]
    anchors_col = cols["TH_ANCHORS"]
    preview_col = cols["TH_PREVIEW_ACTORS"]
    guide_col = cols["TH_PREVIEW_ONLY"]
    camera_col = cols["TH_CAMERA_PREVIEW"]

    if direction == "aqueduct":
        palette = {
            "ground": principled("A_Ground", rgba("#41585a"), 0.95, emission=rgba("#1e2d30"), strength=0.18),
            "stone": principled("A_Riverstone", rgba("#8c8a7d"), 0.90),
            "trim": principled("A_TealTrim", rgba("#345e66"), 0.70, 0.15),
            "wood": principled("A_Wood", rgba("#3a302c"), 0.80),
            "roof": principled("A_Roof", rgba("#1e3441"), 0.86),
            "metal": principled("A_Copper", rgba("#765b43"), 0.35, 0.62),
            "dark": principled("A_Recess", rgba("#0b171d"), 0.98),
            "glow": principled("A_WarmWindow", rgba("#c77b35"), 0.38, emission=rgba("#e29a4c"), strength=3.2),
            "accent": principled("A_WaterAccent", rgba("#4ca0ab"), 0.32, emission=rgba("#4bc0cb"), strength=1.2),
        }
        generated_path = GENERATED / "ashglass_aqueduct_facade.png"
        title = "Ashglass Aqueduct Quarter"
    else:
        palette = {
            "ground": principled("B_Ground", rgba("#3d3b3d"), 0.95, emission=rgba("#211c1d"), strength=0.18),
            "stone": principled("B_Basalt", rgba("#343238"), 0.92),
            "trim": principled("B_CopperTrim", rgba("#9b6046"), 0.45, 0.50),
            "wood": principled("B_Timber", rgba("#2d1c1a"), 0.86),
            "roof": principled("B_CopperRoof", rgba("#4f6f69"), 0.42, 0.55),
            "metal": principled("B_Iron", rgba("#15191c"), 0.42, 0.82),
            "dark": principled("B_Recess", rgba("#090a0d"), 0.98),
            "glow": principled("B_FurnaceGlow", rgba("#d25424"), 0.36, emission=rgba("#ff702c"), strength=4.4),
            "accent": principled("B_Banner", rgba("#8b3f4b"), 0.88),
        }
        generated_path = GENERATED / "ember_bell_foundry_facade.png"
        title = "Ember Bell Foundry Lane"

    clay = principled(direction.upper() + "_Clay", rgba("#9b9b98"), 0.96)
    render_mat = principled(direction.upper() + "_RenderProxy", rgba("#777a7b"), 0.96)
    facade = image_material(direction.upper() + "_GeneratedFacade", generated_path) if refined else clay

    # Continuous ground and a readable near-to-far route.  Camera looks +X;
    # the screen's horizontal axis is world Y.
    cube("SRC_ContinuousGround", (11.2, 5.5, -1.62), (7.5, 7.2, 0.18), palette["ground"], source_col)
    cube("RND_ContinuousGround", (11.2, 5.5, -1.62), (7.5, 7.2, 0.18), render_mat, render_col)
    cube("COL_WalkBounds", (11.6, 5.5, -1.42), (5.4, 1.65, 0.18), palette["ground"], collision_col)
    cube("SRC_WalkLane", (10.8, 5.5, -1.38), (4.9, 1.45, 0.08), palette["stone"], source_col)

    # Deep structures extend behind the view and beyond both frame edges.
    for index, y in enumerate((0.2, 2.0, 8.9, 10.8)):
        depth_mat = palette["stone"] if index % 2 else palette["roof"]
        cube(f"SRC_DeepBlock_{index}", (13.4 + (index % 2) * 0.8, y, 1.3 + (index % 3) * 0.4), (2.1, 1.0, 2.8 + (index % 2) * 0.8), depth_mat, source_col, bevel=0.10)
        cube(f"RND_DeepBlock_{index}", (13.4 + (index % 2) * 0.8, y, 1.3 + (index % 3) * 0.4), (2.1, 1.0, 2.8 + (index % 2) * 0.8), render_mat, render_col)

    # Primary inhabited architecture is split around a true doorway gap.
    left_y0, left_y1 = 1.0, 4.36
    right_y0, right_y1 = 5.24, 9.95
    for suffix, y0, y1 in (("Left", left_y0, left_y1), ("Right", right_y0, right_y1)):
        cube(f"SRC_PrimaryMass_{suffix}", (10.15, (y0 + y1) * 0.5, 1.65), (1.28, (y1 - y0) * 0.5, 3.15), palette["stone"], source_col, bevel=0.12)
        cube(f"RND_PrimaryMass_{suffix}", (10.15, (y0 + y1) * 0.5, 1.65), (1.28, (y1 - y0) * 0.5, 3.15), render_mat, render_col)
        panel(f"SRC_{direction.upper()}_Facade_{suffix}", 9.31, y0, y1, -1.42, 4.72, facade, source_col)

    cube("SRC_PrimaryHeader", (10.15, 4.80, 4.55), (1.28, 0.48, 0.72), palette["stone"], source_col, bevel=0.10)
    cube("RND_PrimaryHeader", (10.15, 4.80, 4.55), (1.28, 0.48, 0.72), render_mat, render_col)
    panel(f"SRC_{direction.upper()}_Facade_Header", 9.31, 4.36, 5.24, 3.95, 5.22, facade, source_col)

    add_doorway("SRC_MainDoor", 4.80, palette, source_col, render_col, refined)
    add_archway("SRC_MainArch", 4.80, palette, source_col, 4.45)

    # Windows and trim establish inhabitation at a 426x240 read.
    for i, y in enumerate((1.55, 2.75, 6.05, 7.25, 8.55, 9.35)):
        add_window(f"SRC_Window_{i}", y, 2.55 + (0.35 if i % 2 else 0.0), direction, palette, source_col, refined)
    for y in (1.25, 3.65, 6.55, 8.15, 9.55):
        add_pipe("SRC_Pipe_" + str(y), y, -1.28, 4.28, palette, source_col)

    # Direction-specific landmark geometry.
    if direction == "aqueduct":
        for y in (1.25, 9.55):
            cube("SRC_AqueductChannel_" + str(y), (9.02, y, 0.18), (0.24, 0.62, 0.10), palette["trim"], source_col, bevel=0.04)
            cube("SRC_AqueductWater_" + str(y), (8.88, y, 0.38), (0.08, 0.42, 0.95), palette["accent"], source_col)
        for y in (2.0, 3.15, 7.0, 8.25):
            cube("SRC_BalconyDeck_" + str(y), (8.95, y, 3.56), (0.42, 0.62, 0.10), palette["wood"], source_col, bevel=0.04)
            for dy in (-0.48, 0.48):
                cylinder("SRC_BalconyRail_" + str(y) + str(dy), (8.82, y + dy, 3.94), 0.035, 0.72, palette["metal"], source_col)
        cube("SRC_AqueductCrown", (10.0, 5.5, 5.35), (1.3, 5.4, 0.18), palette["trim"], source_col, bevel=0.06)
        cube("SRC_AqueductRoof", (10.45, 5.5, 5.82), (1.0, 5.2, 0.32), palette["roof"], source_col, bevel=0.12, rotation=(0.0, math.radians(5.0), 0.0))
        for y in (2.5, 7.8):
            cube("SRC_AqueductBanner_" + str(y), (8.92, y, 3.75), (0.08, 0.30, 0.75), palette["accent"], source_col, bevel=0.03)
    else:
        # Central bell tower is real geometry, not just a texture motif.
        for y in (4.22, 6.38):
            cube("SRC_BellTowerPost_" + str(y), (8.92, y, 2.85), (0.23, 0.18, 3.10), palette["trim"], source_col, bevel=0.06)
        cube("SRC_BellTowerBeam", (8.92, 5.30, 5.65), (0.23, 1.26, 0.18), palette["trim"], source_col, bevel=0.05)
        sphere("SRC_Bell", (8.68, 5.30, 4.05), 0.58, palette["roof"], source_col)
        cylinder("SRC_BellClapper", (8.52, 5.30, 3.42), 0.08, 0.80, palette["metal"], source_col)
        for y in (2.0, 8.35):
            cube("SRC_FoundryAwning_" + str(y), (8.75, y, 0.82), (0.64, 0.92, 0.12), palette["roof"], source_col, bevel=0.05, rotation=(0.0, math.radians(-12), 0.0))
            cube("SRC_FoundryCounter_" + str(y), (8.92, y, -0.18), (0.24, 0.82, 0.46), palette["wood"], source_col, bevel=0.05)
        for y in (2.25, 8.10):
            cylinder("SRC_Chain_" + str(y), (8.82, y, 3.0), 0.035, 3.8, palette["metal"], source_col)
        cube("SRC_FoundryRoof", (10.18, 5.5, 5.55), (1.42, 5.45, 0.28), palette["roof"], source_col, bevel=0.10, rotation=(0.0, math.radians(-4), 0.0))
        for y in (2.85, 7.45):
            cube("SRC_FoundryBanner_" + str(y), (8.86, y, 3.1), (0.08, 0.30, 0.80), palette["accent"], source_col, bevel=0.03)

    # Foreground depth: a near arcade, hanging beam, and an important occluder.
    for y in (0.85, 10.15):
        cube("SRC_ForegroundPillar_" + str(y), (7.55, y, 0.65), (0.45, 0.34, 2.2), palette["wood"], source_col, bevel=0.12)
        cube("RND_ForegroundPillar_" + str(y), (7.55, y, 0.65), (0.45, 0.34, 2.2), render_mat, render_col)
    cube("SRC_ForegroundBeam", (7.55, 1.35, 2.78), (0.45, 1.55, 0.24), palette["wood"], source_col, bevel=0.10)
    cube("RND_ForegroundBeam", (7.55, 1.35, 2.78), (0.45, 1.55, 0.24), render_mat, render_col)
    cube("SRC_ForegroundBeamB", (7.55, 9.75, 2.58), (0.45, 1.05, 0.22), palette["wood"], source_col, bevel=0.10)
    cube("RND_ForegroundBeamB", (7.55, 9.75, 2.58), (0.45, 1.05, 0.22), render_mat, render_col)
    cube("SRC_ForegroundLantern", (7.05, 4.7, 1.15), (0.12, 0.20, 0.30), palette["glow"], source_col, bevel=0.04)

    # Runtime proxy intentionally retains silhouette, doorway void, route and
    # foreground depth but leaves out the small windows, pipes, and ornament.
    cube("RND_RuntimeDoorwayHeader", (9.55, 4.80, 1.34), (0.42, 0.95, 0.18), render_mat, render_col)

    # Collision and authoring anchors are kept out of every visual bake.
    cube("COL_OuterWalkLimit", (11.7, 3.2, -1.10), (4.8, 0.18, 0.34), palette["ground"], collision_col)
    cube("COL_OuterWalkLimitB", (11.7, 7.8, -1.10), (4.8, 0.18, 0.34), palette["ground"], collision_col)
    for name, loc in (
        ("spawn_player", (8.55, 4.0, -1.42)),
        ("walk_start", (8.95, 3.55, -1.42)),
        ("walk_end", (13.4, 7.3, -1.42)),
        ("doorway", (9.05, 4.80, -1.42)),
        ("npc_waterwright", (9.05, 2.35, -1.42)),
        ("npc_bellkeeper", (9.05, 7.65, -1.42)),
        ("foreground_occlusion", (7.55, 5.5, 0.0)),
    ):
        anchor(name, loc, anchors_col)
    guide = cube("GUIDE_Route", (10.9, 5.5, -1.18), (4.5, 1.45, 0.03), palette["accent"], guide_col)
    guide.hide_render = True

    record = json.loads(CAMERA_RECORD.read_text(encoding="utf-8"))
    camera = sys.modules["thestra_camera"].create_or_update_camera(record, scene=scene)
    move_to(camera, camera_col)
    # Preview actors are deliberately shown in refined evidence but are not a
    # part of the source/render contract.
    actor = sys.modules["thestra_camera"].create_actor_preview(WALKER, camera, anchor=(9.0, 4.0, -1.42), name="TH_WALKER_PREVIEW")
    move_to(actor, preview_col)

    # The #881 calibration is deliberately wide and keeps its principal point
    # high in the native frame.  Lower and vertically compress the authored
    # town as a whole so the route occupies the lower third while a 1.75-unit
    # Walker remains the human-scale ruler.  The camera itself is never edited.
    for obj in scene.objects:
        if obj is not camera:
            obj.location.z -= 1.0
    world_floor = -2.42
    vertical_scale = 0.42
    world_scale = bpy.data.objects.new("SECOND_GATE_AUTHORED_WORLD_SCALE", None)
    scene.collection.objects.link(world_scale)
    world_scale.location.z = world_floor * (1.0 - vertical_scale)
    world_scale.scale.z = vertical_scale
    for collection_name in ("TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_PREVIEW_ONLY"):
        for obj in list(cols[collection_name].objects):
            if obj.type != "LIGHT":
                obj.parent = world_scale

    # A soft key plus a warm facade-side fill keeps clay readable and the rich
    # source pass dimensional without making the generated image a flat card.
    bpy.ops.object.light_add(type="AREA", location=(6.5, 3.0, 7.2))
    key = bpy.context.object
    key.name = "SRC_KeyLight"
    key.data.energy = 920.0 if refined else 700.0
    key.data.shape = "RECTANGLE"
    key.data.size = 6.0
    key.data.size_y = 4.0
    move_to(key, source_col)
    bpy.ops.object.light_add(type="AREA", location=(8.0, 8.6, 2.2))
    fill = bpy.context.object
    fill.name = "SRC_WarmFill"
    fill.data.energy = 360.0
    fill.data.color = (1.0, 0.48, 0.25)
    fill.data.size = 4.0
    move_to(fill, source_col)

    scene["second_gate_direction"] = direction
    scene["second_gate_title"] = title
    scene["second_gate_camera_authority"] = "#881 thestra.world-camera-calibration"
    scene["second_gate_native_review"] = "426x240"
    scene["second_gate_generated_surface"] = generated_path.relative_to(ROOT).as_posix()
    scene["second_gate_stage"] = "refined" if refined else "clay"
    scene["second_gate_collection_contract"] = "TH_SOURCE,TH_RENDER,TH_COLLISION,TH_ANCHORS,TH_PREVIEW_ACTORS,TH_PREVIEW_ONLY,TH_CAMERA_PREVIEW"

    output_blend.parent.mkdir(parents=True, exist_ok=True)
    output_render.parent.mkdir(parents=True, exist_ok=True)
    profile = "cycles-lookdev" if refined else "clay"
    sys.modules["second_gate_render"].apply(scene, profile)
    scene.render.filepath = str(output_render)
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    print(f"SIDE_VIEW_BUILT {direction} {'refined' if refined else 'clay'} {output_blend}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--direction", choices=("aqueduct", "foundry", "both"), default="both")
    parser.add_argument("--stage", choices=("initial", "refined", "both"), default="both")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    # Blender imports the #881 modules through this script's directory.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import second_gate_render  # noqa: F401
    import thestra_camera  # noqa: F401
    for direction in (("aqueduct", "foundry") if args.direction == "both" else (args.direction,)):
        for refined in ((False, True) if args.stage == "both" else (args.stage == "refined",)):
            stage = "refined" if refined else "initial"
            stem = "ashglass_aqueduct" if direction == "aqueduct" else "ember_bell_foundry"
            output_blend = ART_ROOT / "directions" / direction / f"{stem}_{stage}.blend"
            output_render = ART_ROOT / "renders" / stage / f"{direction}.png"
            build_direction(direction, refined, output_blend, output_render)


if __name__ == "__main__":
    main()
