"""Fresh Second Gate side-view town visual gauntlet.

This file is intentionally self-contained and starts every lineage from an
empty Blender file.  It uses the generic ``thestra_camera`` helper for camera
and Walker previews; it does not introduce runtime or Map architecture.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import thestra_camera  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
WALKER = ROOT / "projects/hichaukitoden-game/assets/character/walker.png"


def parse_args():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--phase", choices=("acceptance", "clay", "winner"), required=True)
    parser.add_argument("--generated-albedo", default="")
    parser.add_argument("--public-dir", default="")
    return parser.parse_args(raw)


def ensure_collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def setup_collections():
    return {name: ensure_collection(name) for name in (
        "TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS",
        "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW",
    )}


def move_to_collection(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)


def clear_materials(obj):
    if getattr(obj, "data", None) and hasattr(obj.data, "materials"):
        obj.data.materials.clear()


def make_simple_material(name, color, roughness=0.82, metallic=0.0, emission=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 1.4
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.diffuse_color = (*color, 1.0)
    return mat


def image_node(nodes, image_path, name, non_color=False):
    image = bpy.data.images.load(str(Path(image_path).resolve()), check_existing=True)
    if non_color:
        try:
            image.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
    node = nodes.new("ShaderNodeTexImage")
    node.name = name
    node.image = image
    node.interpolation = "Linear"
    node.extension = "REPEAT"
    return node


def world_surface_vector(nodes, links, scale=0.5):
    geo = nodes.new("ShaderNodeNewGeometry")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    comb = nodes.new("ShaderNodeCombineXYZ")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    # Use shared world position, with world Z mapped to image V.  This keeps
    # the same source scale on walls, jambs and towers.
    links.new(geo.outputs["Position"], sep.inputs["Vector"])
    links.new(sep.outputs["X"], comb.inputs["X"])
    links.new(sep.outputs["Z"], comb.inputs["Y"])
    links.new(comb.outputs["Vector"], mapping.inputs["Vector"])
    return mapping.outputs["Vector"]


def make_public_stone(public_dir):
    public_dir = Path(public_dir)
    mat = bpy.data.materials.new("MAT_PUBLIC_STONE_BRICK_001")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    diff = image_node(nodes, public_dir / "stone_brick_wall_001_diff_1k.png", "PublicDiffuse")
    disp = image_node(nodes, public_dir / "stone_brick_wall_001_disp_1k.png", "PublicDisplacement", True)
    rough = image_node(nodes, public_dir / "stone_brick_wall_001_rough_1k.png", "PublicRoughness", True)
    uv = world_surface_vector(nodes, links, 0.42)
    for tex in (diff, disp, rough):
        links.new(uv, tex.inputs["Vector"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.24
    bump.inputs["Distance"].default_value = 0.075
    links.new(disp.outputs["Color"], bump.inputs["Height"])
    links.new(diff.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.18
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_generated_plaster(albedo_path):
    mat = bpy.data.materials.new("MAT_GENERATED_LIME_PLASTER_ALBEDO")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    albedo = image_node(nodes, albedo_path, "GeneratedAlbedo")
    uv = world_surface_vector(nodes, links, 0.32)
    links.new(uv, albedo.inputs["Vector"])
    bw = nodes.new("ShaderNodeRGBToBW")
    links.new(albedo.outputs["Color"], bw.inputs["Color"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.16
    bump.inputs["Distance"].default_value = 0.045
    links.new(bw.outputs["Val"], bump.inputs["Height"])
    links.new(albedo.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.88
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_procedural_wood():
    mat = bpy.data.materials.new("MAT_PROCEDURAL_DARK_TIMBER")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 3.5
    wave.inputs["Distortion"].default_value = 4.0
    wave.inputs["Detail"].default_value = 3.0
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 5.0
    noise.inputs["Detail"].default_value = 4.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.018, 0.009, 0.004, 1)
    ramp.color_ramp.elements[1].color = (0.18, 0.055, 0.018, 1)
    uv = world_surface_vector(nodes, links, 0.6)
    links.new(uv, wave.inputs["Vector"])
    links.new(uv, noise.inputs["Vector"])
    links.new(wave.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bsdf.inputs["Roughness"])
    bsdf.inputs["Roughness"].default_value = 0.68
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_roof():
    mat = bpy.data.materials.new("MAT_PROCEDURAL_ROOF_TILE")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 8.0
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2.7
    noise.inputs["Detail"].default_value = 2.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.035, 0.012, 0.006, 1)
    ramp.color_ramp.elements[1].color = (0.28, 0.07, 0.02, 1)
    uv = world_surface_vector(nodes, links, 0.72)
    links.new(uv, wave.inputs["Vector"])
    links.new(uv, noise.inputs["Vector"])
    links.new(wave.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bsdf.inputs["Roughness"])
    bsdf.inputs["Roughness"].default_value = 0.76
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_materials(args, textured=False):
    if not textured:
        return {
            "stone": make_simple_material("MAT_CLAY_STONE", (0.44, 0.47, 0.46)),
            "plaster": make_simple_material("MAT_CLAY_PLASTER", (0.62, 0.64, 0.60)),
            "wood": make_simple_material("MAT_CLAY_TIMBER", (0.28, 0.29, 0.27)),
            "roof": make_simple_material("MAT_CLAY_ROOF", (0.38, 0.39, 0.36)),
            "ground": make_simple_material("MAT_CLAY_GROUND", (0.31, 0.34, 0.33)),
            "dark": make_simple_material("MAT_CLAY_DARK", (0.055, 0.07, 0.07)),
            "distant": make_simple_material("MAT_CLAY_DISTANT", (0.27, 0.31, 0.31)),
        }
    public_stone = make_public_stone(args.public_dir)
    generated_plaster = make_generated_plaster(args.generated_albedo)
    return {
        "stone": public_stone,
        "plaster": generated_plaster,
        "wood": make_procedural_wood(),
        "roof": make_roof(),
        "ground": public_stone,
        "dark": make_simple_material("MAT_INTERIOR_DARK", (0.012, 0.009, 0.007), 1.0),
        "distant": make_simple_material("MAT_HAZED_DISTANT", (0.18, 0.25, 0.27), 0.95),
        "warm": make_simple_material("MAT_WARM_INTERIOR", (0.24, 0.045, 0.012), 0.6, emission=(0.8, 0.16, 0.025)),
    }


def cube(name, loc, dims, mat, col, rotation=(0.0, 0.0, 0.0), role=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, col)
    clear_materials(obj)
    if mat:
        obj.data.materials.append(mat)
    if role:
        obj["town_material_role"] = role
    if bevel:
        mod = obj.modifiers.new("SoftConstructionEdges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def gable_roof(name, x, y, eave_z, width, depth, rise, mat, col, role="roof"):
    angle = math.atan2(rise, width * 0.5)
    slab_len = math.sqrt((width * 0.5) ** 2 + rise ** 2)
    left = cube(name + "_L", (x - width * 0.25, y, eave_z + rise * 0.5),
                (slab_len, depth, 0.22), mat, col, rotation=(0, -angle, 0), role=role, bevel=0.025)
    right = cube(name + "_R", (x + width * 0.25, y, eave_z + rise * 0.5),
                 (slab_len, depth, 0.22), mat, col, rotation=(0, angle, 0), role=role, bevel=0.025)
    cube(name + "_ridge", (x, y, eave_z + rise), (0.24, depth, 0.26), mat, col, role=role, bevel=0.025)
    return left, right


def facade(name, x, y, width, height, depth, door_x, mats, col, role="plaster", roof=True, timber=False):
    door_w, door_h = 1.35, 2.15
    side_w = max(0.35, (width - door_w) * 0.5)
    cube(name + "_left", (x - (door_w + side_w) * 0.5, y, height * 0.5),
         (side_w, depth, height), mats[role], col, role=role, bevel=0.04)
    cube(name + "_right", (x + (door_w + side_w) * 0.5, y, height * 0.5),
         (side_w, depth, height), mats[role], col, role=role, bevel=0.04)
    cube(name + "_lintel", (x, y, door_h + (height - door_h) * 0.5),
         (door_w, depth, height - door_h), mats[role], col, role=role, bevel=0.04)
    cube(name + "_door_recess", (x + door_x, y - depth * 0.52, door_h * 0.5),
         (door_w * 0.9, 0.12, door_h), mats["dark"], col, role="dark", bevel=0.02)
    cube(name + "_threshold", (x + door_x, y - depth * 0.55, 0.06),
         (door_w * 1.2, 0.42, 0.12), mats["stone"], col, role="stone", bevel=0.03)
    # Recessed upper windows with structural surrounds.
    for i, wx in enumerate((-width * 0.26, width * 0.26)):
        wz = min(height - 1.0, 3.5)
        cube(f"{name}_win_{i}_dark", (x + wx, y - depth * 0.53, wz), (0.75, 0.12, 0.85), mats["dark"], col, role="dark")
        cube(f"{name}_win_{i}_top", (x + wx, y - depth * 0.61, wz + 0.52), (1.05, 0.22, 0.16), mats["stone"], col, role="stone", bevel=0.02)
        cube(f"{name}_win_{i}_sill", (x + wx, y - depth * 0.61, wz - 0.52), (1.05, 0.22, 0.16), mats["stone"], col, role="stone", bevel=0.02)
    if timber:
        for z in (2.55, 4.15):
            cube(f"{name}_timber_{z}", (x, y - depth * 0.59, z), (width * 0.96, 0.18, 0.18), mats["wood"], col, role="wood")
        for tx in (-width * 0.36, -width * 0.12, width * 0.12, width * 0.36):
            cube(f"{name}_beam_{tx}", (x + tx, y - depth * 0.61, 3.35), (0.14, 0.2, 2.25), mats["wood"], col, role="wood")
    if roof:
        gable_roof(name + "_roof", x, y, height, width + 0.55, depth + 0.55, 1.05, mats["roof"], col)


def window_tower(name, x, y, width, height, depth, mats, col, role="stone"):
    cube(name + "_body", (x, y, height * 0.5), (width, depth, height), mats[role], col, role=role, bevel=0.06)
    for z in (2.1, 4.4, 6.6):
        cube(name + f"_slot_{z}", (x, y - depth * 0.54, z), (0.48, 0.13, 1.0), mats["dark"], col, role="dark")
        cube(name + f"_slot_sill_{z}", (x, y - depth * 0.62, z - 0.6), (0.78, 0.24, 0.14), mats["stone"], col, role="stone")
    gable_roof(name + "_roof", x, y, height, width + 0.55, depth + 0.5, 1.5, mats["roof"], col)


def archway(name, x, y, width, height, depth, mats, col, roof=True):
    opening_w, opening_h = width * 0.42, height * 0.65
    pier_w = (width - opening_w) * 0.5
    cube(name + "_left_pier", (x - (opening_w + pier_w) * 0.5, y, height * 0.5), (pier_w, depth, height), mats["stone"], col, role="stone", bevel=0.05)
    cube(name + "_right_pier", (x + (opening_w + pier_w) * 0.5, y, height * 0.5), (pier_w, depth, height), mats["stone"], col, role="stone", bevel=0.05)
    cube(name + "_arch_mass", (x, y, opening_h + (height - opening_h) * 0.5), (opening_w, depth, height - opening_h), mats["stone"], col, role="stone", bevel=0.05)
    cube(name + "_deep_void", (x, y - depth * 0.54, opening_h * 0.5), (opening_w * 0.88, 0.12, opening_h), mats["dark"], col, role="dark")
    cube(name + "_keystone", (x, y - depth * 0.62, opening_h + 0.3), (0.46, 0.18, 0.42), mats["stone"], col, role="stone", bevel=0.03)
    if roof:
        cube(name + "_cap", (x, y, height + 0.22), (width + 0.5, depth + 0.45, 0.42), mats["stone"], col, role="stone", bevel=0.04)


def stairs(name, x0, x1, y, z0, count, width, mats, col, role="stone"):
    for i in range(count):
        t = (i + 1) / count
        x = x0 + (x1 - x0) * t
        z = z0 + i * 0.22
        cube(f"{name}_{i:02d}", (x, y, z * 0.5 + 0.02), (abs(x1 - x0) / count + 0.24, width, max(0.12, z + 0.12)), mats[role], col, role=role, bevel=0.025)


def add_ground(mats, col):
    cube("ground_continuity_mass", (0.0, 6.0, -1.98), (56.0, 10.0, 4.15), mats["ground"], col, role="ground", bevel=0.04)
    cube("ground_front_stone_band", (0.0, 0.68, -0.25), (56.0, 0.55, 0.62), mats["stone"], col, role="stone", bevel=0.03)
    cube("walkway_cap", (0.0, 0.0, 0.10), (56.0, 5.2, 0.20), mats["ground"], col, role="ground", bevel=0.02)
    for x in (-22, -15, -8, 0, 8, 15, 22):
        cube(f"ground_buttress_{x}", (x, -0.6, -0.72), (0.52, 0.9, 1.7), mats["stone"], col, role="stone", bevel=0.05)
    # Continuous lower arcades make the below-route volume read as a place,
    # not as a platform edge, while remaining outside the actor lane. They
    # sit in front of the mass so their actual openings remain visible.
    for x in (-18, -11, -4, 4, 11, 18):
        before = set(bpy.data.objects)
        archway(f"lower_arch_{x}", x, -1.65, 6.2, 3.2, 1.2, mats, col, roof=False)
        for obj in set(bpy.data.objects) - before:
            obj.location.z -= 3.10
    for z in (-0.65, -1.55, -2.45):
        cube(f"ground_course_{z}", (0.0, -2.28, z), (56.0, 0.16, 0.12), mats["stone"], col, role="stone", bevel=0.02)


def add_distant(mats, col, variant):
    heights = {
        "A": [3.8, 5.2, 4.2, 6.8, 4.6, 5.6, 4.0],
        "B": [5.4, 4.1, 6.2, 5.0, 7.6, 4.4, 5.5],
        "C": [4.0, 5.7, 4.5, 8.5, 4.8, 6.0, 4.2],
    }[variant]
    for i, h in enumerate(heights):
        x = -22 + i * 7.2
        window_tower(f"distant_{variant}_{i}", x, 8.5, 4.0 + (i % 2) * 0.5, h, 1.8, mats, col, role="distant")
    cube(f"distant_horizon_{variant}", (0, 12.0, 5.5), (84, 1.0, 16.0), mats["distant"], col, role="distant")


def build_A(mats, cols):
    r = cols["TH_RENDER"]
    facade("A_central_house", -1.5, 3.0, 7.0, 5.8, 2.6, 0.0, mats, r, role="plaster", roof=True, timber=False)
    facade("A_timber_house", 6.6, 3.5, 7.2, 5.6, 2.8, 0.0, mats, r, role="plaster", roof=True, timber=True)
    archway("A_water_arcade", -10.0, 2.7, 9.5, 4.3, 2.2, mats, r)
    cube("A_water_channel", (-10.0, 1.5, -0.15), (9.0, 2.2, 0.25), mats["dark"], r, role="dark")
    stairs("A_canal_stairs", -13.2, -9.5, -0.2, 0.0, 6, 1.8, mats, r)
    facade("A_left_house", -17.0, 4.0, 6.3, 5.2, 2.5, 0.0, mats, r, role="stone", roof=True, timber=True)
    window_tower("A_rear_tower", -20.5, 6.0, 3.6, 7.1, 2.2, mats, r, role="stone")
    # Genuine near foreground: a canal-side roof/arcade connected to the
    # lower structure, with posts and a continuous return off screen.
    for x in (-22, -16, -10, -4, 2):
        cube(f"A_foreground_post_{x}", (x, -3.2, 0.45), (0.28, 0.7, 2.0), mats["wood"], r, role="wood")
    cube("A_foreground_roof", (-10.0, -3.4, 1.55), (25.0, 1.8, 0.34), mats["roof"], r, role="roof", bevel=0.04)
    cube("A_foreground_return", (3.0, -2.5, 2.0), (4.0, 1.5, 0.22), mats["wood"], r, role="wood")
    add_distant(mats, r, "A")


def build_B(mats, cols):
    r = cols["TH_RENDER"]
    window_tower("B_civic_tower", -8.5, 3.7, 4.6, 8.2, 2.8, mats, r, role="stone")
    archway("B_civic_gate", -4.0, 3.2, 5.4, 5.2, 2.6, mats, r)
    facade("B_stepped_house", -14.0, 4.2, 7.5, 5.5, 2.8, 0.0, mats, r, role="plaster", roof=True, timber=True)
    stairs("B_civic_stairs", -12.8, -5.2, -0.1, 0.0, 9, 2.5, mats, r)
    facade("B_market_house", 5.7, 3.2, 8.4, 5.7, 3.0, 0.0, mats, r, role="plaster", roof=True, timber=False)
    # Connected covered market passage.
    for x in (1.0, 5.0, 9.0, 13.0):
        cube(f"B_market_post_{x}", (x, 1.5, 2.0), (0.22, 1.2, 4.0), mats["wood"], r, role="wood")
    cube("B_market_canopy", (7.0, 1.55, 4.2), (14.0, 2.0, 0.3), mats["roof"], r, role="roof", rotation=(0, 0.06, 0), bevel=0.04)
    stairs("B_market_ramp", 9.5, 14.2, -0.1, 0.0, 6, 2.0, mats, r)
    # Near foreground balcony/awning with real supports.
    for x in (-8, -2, 5, 12, 18):
        cube(f"B_foreground_support_{x}", (x, -3.0, 1.2), (0.28, 0.9, 2.8), mats["wood"], r, role="wood")
    cube("B_foreground_balcony", (5.0, -3.2, 2.25), (31.0, 1.6, 0.34), mats["roof"], r, role="roof")
    cube("B_foreground_rail", (5.0, -2.3, 0.95), (30.0, 0.16, 0.72), mats["wood"], r, role="wood")
    add_distant(mats, r, "B")


def build_C(mats, cols):
    r = cols["TH_RENDER"]
    window_tower("C_bell_tower", 0.0, 3.6, 4.5, 9.0, 3.2, mats, r, role="stone")
    # Tower bell opening: actual deep dark aperture framed by thick masonry.
    cube("C_bell_void", (0.0, 1.82, 7.25), (1.45, 0.16, 1.7), mats["dark"], r, role="dark")
    cube("C_bell_crossbar", (0.0, 1.68, 6.95), (1.75, 0.2, 0.16), mats["wood"], r, role="wood")
    archway("C_gate_passage", 4.3, 3.1, 5.4, 5.6, 2.8, mats, r)
    facade("C_left_residence", -8.0, 3.5, 8.0, 5.4, 2.8, 0.0, mats, r, role="plaster", roof=True, timber=True)
    facade("C_right_shop", 11.0, 3.7, 8.0, 5.1, 2.8, 0.0, mats, r, role="plaster", roof=True, timber=False)
    # Diagonal covered passage and stair: structural, not decorative trim.
    cube("C_diagonal_canopy", (7.5, 2.0, 3.55), (8.3, 2.4, 0.34), mats["roof"], r, rotation=(0, -0.22, 0), role="roof", bevel=0.04)
    cube("C_canopy_beam", (7.5, 1.7, 2.15), (8.3, 0.24, 0.32), mats["wood"], r, rotation=(0, -0.22, 0), role="wood")
    stairs("C_gate_stairs", 4.6, 8.0, -0.15, 0.0, 7, 2.0, mats, r)
    # Real near foreground bridge/roof layer, visually continuous left/right.
    for x in (-21, -15, -9, -3, 3, 9, 15, 21):
        cube(f"C_foreground_arch_pier_{x}", (x, -3.6, 0.9), (0.3, 1.0, 2.6), mats["stone"], r, role="stone")
    cube("C_foreground_bridge_roof", (0.0, -3.7, 2.25), (52.0, 1.7, 0.36), mats["roof"], r, role="roof", bevel=0.04)
    cube("C_foreground_bridge_return", (-18.0, -2.9, 1.1), (7.0, 1.0, 0.22), mats["wood"], r, role="wood")
    add_distant(mats, r, "C")


def add_collision_and_anchors(cols, variant):
    c = cols["TH_COLLISION"]
    cube(f"{variant}_walk_bounds", (0, 0.2, 0.5), (46.0, 0.55, 1.0), None, c, role="collision")
    a = cols["TH_ANCHORS"]
    anchors = {
        "spawn_player": (-11.5, 0.0, 0.0),
        "walk_start": (-21.0, 0.0, 0.0),
        "walk_end": (21.0, 0.0, 0.0),
        "doorway": (4.3, 0.0, 0.0),
        "npc_anchor_01": (-5.0, 0.0, 0.0),
        "npc_anchor_02": (12.0, 0.0, 0.0),
        "foreground_landmark": (-9.0, -3.5, 1.8),
    }
    for name, loc in anchors.items():
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_type = "PLAIN_AXES"
        obj.location = loc
        a.objects.link(obj)
        obj["anchor_id"] = name
        obj["variant"] = variant


def add_lights(mats, cols):
    def area(name, loc, energy, size, color):
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.data.color = color
        light.rotation_euler = (Vector((0, 2.5, 1.8)) - light.location).to_track_quat("-Z", "Y").to_euler()
        move_to_collection(light, cols["TH_PREVIEW_ONLY"])
        light.hide_render = False
        return light
    area("Key_Soft_Overcast", (-5, -8, 12), 950, 10.0, (1.0, 0.84, 0.68))
    area("Fill_Cool_Sky", (14, -5, 7), 380, 12.0, (0.38, 0.58, 1.0))
    area("Rim_Back", (-14, 7, 8), 520, 8.0, (0.48, 0.72, 0.78))
    area("Low_Street_Fill", (0, -11, 2.0), 420, 9.0, (0.70, 0.78, 0.92))
    for x in (-11, 0, 7, 13):
        bpy.ops.object.light_add(type="POINT", location=(x, 1.3, 2.1))
        light = bpy.context.object
        light.name = f"InteriorGlow_{x}"
        light.data.energy = 38
        light.data.color = (1.0, 0.18, 0.035)
        light.data.shadow_soft_size = 0.55
        move_to_collection(light, cols["TH_PREVIEW_ONLY"])


def configure_render(scene, filepath):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 4
    scene.cycles.preview_samples = 2
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 2
    scene.cycles.diffuse_bounces = 1
    scene.cycles.glossy_bounces = 1
    scene.cycles.transmission_bounces = 0
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(Path(filepath).resolve())
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("TH_PREVIEW_WORLD")
    scene.world.use_nodes = False
    scene.world.color = (0.045, 0.075, 0.095)
    try:
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "None"
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
    except Exception:
        pass


def camera_record(offset=0.0):
    return {
        "contract": "thestra.world-camera-calibration",
        "version": 1,
        "projection": "perspective",
        "targetWidth": 426,
        "targetHeight": 240,
        "baseViewportWidth": 256,
        "baseViewportHeight": 144,
        "nearPlane": 0.05,
        "farPlane": 96.0,
        "viewportCenterX": 213.0 + float(offset),
        "viewportCenterY": 110.0,
        "projectionWindowOffsetX": float(offset),
        "projectionWindowOffsetY": 0.0,
        "projectionScale": {"x": 1.0, "y": 1.0},
        "fovHalfX": 0.25,
        "fovHalfY": 0.140625,
        "orthoHalfX": 1.0,
        "orthoHalfY": 1.0,
        "eye": {"x": 0.0, "y": -37.333333, "z": 1.0},
        "orientation": {
            "forwardX": 0.0, "forwardY": 1.0,
            "rightX": 1.0, "rightY": 0.0,
            "pitchRadians": 0.0,
        },
        "coordinateSystem": {
            "handedness": "right-handed", "worldUp": "+Z", "worldHorizontal": "XY",
            "cameraForward": "+depth", "cameraRight": "+right",
            "screenOrigin": "top-left", "screenY": "+down",
            "blenderCameraForward": "-Z", "blenderCameraUp": "+Y",
        },
    }


def add_actors(cols, cam, names=("Walker_A", "Walker_B", "Walker_C")):
    anchors = [(-13.0, 0.0, 0.0), (-2.0, 0.0, 0.0), (9.5, 0.0, 0.0)]
    for i, (name, anchor) in enumerate(zip(names, anchors)):
        obj = thestra_camera.create_actor_preview(
            WALKER, cam, anchor=anchor, frame_width=24, frame_height=48,
            frame_index=i, world_height=1.75, alpha_cutoff=0.5, name=name,
        )
        move_to_collection(obj, cols["TH_PREVIEW_ACTORS"])


def render_views(scene, cols, out_dir, label, actors=True):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    center_lens = None
    eye = None
    for offset, suffix in ((-96.0, "-096"), (0.0, "center"), (96.0, "+096")):
        record = camera_record(offset)
        cam = thestra_camera.create_or_update_camera(record, scene=scene, name="TH_CAMERA_PREVIEW", make_active=True)
        move_to_collection(cam, cols["TH_CAMERA_PREVIEW"])
        if actors:
            for obj in cols["TH_PREVIEW_ACTORS"].objects:
                obj.rotation_mode = "QUATERNION"
                obj.rotation_quaternion = cam.matrix_world.to_quaternion()
        if center_lens is None:
            center_lens = cam.data.lens
            eye = tuple(round(v, 6) for v in cam.location)
        else:
            assert abs(cam.data.lens - center_lens) < 1e-6
            assert tuple(round(v, 6) for v in cam.location) == eye
        path = out_dir / f"{label}_{suffix}.png"
        configure_render(scene, path)
        bpy.ops.render.render(write_still=True)
    (out_dir / f"{label}_camera_checks.json").write_text(json.dumps({
        "target": [426, 240], "lensMm": center_lens, "eye": eye,
        "pitchDegrees": 0.0, "projectionWindowOffsets": [-96, 0, 96],
        "actorFrame": [24, 48], "actorWorldHeight": 1.75,
    }, indent=2), encoding="utf-8")


def add_source_displaced_panel(cols, mats):
    # A separate, subdivided source panel is the real-displacement test. It is
    # deliberately source-only and does not alter the runtime silhouette.
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=48, y_subdivisions=32, size=2.0, location=(-8.0, 2.03, 3.2), rotation=(math.pi * 0.5, 0.0, 0.0))
    panel = bpy.context.object
    panel.name = "SRC_C_generated_plaster_displacement_panel"
    panel.scale = (1.5, 1.15, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(panel, cols["TH_SOURCE"])
    clear_materials(panel)
    panel.data.materials.append(mats["plaster"])
    tex = bpy.data.textures.new("SRC_PublicDisplacementTexture", type="IMAGE")
    disp = mats["stone"].node_tree.nodes.get("PublicDisplacement")
    if disp and disp.image:
        tex.image = disp.image
    mod = panel.modifiers.new("RealSourceDisplacement", "DISPLACE")
    mod.texture = tex
    mod.texture_coords = "UV"
    mod.strength = 0.055
    mod.mid_level = 0.5
    bevel = panel.modifiers.new("SourcePanelEdge", "SOLIDIFY")
    bevel.thickness = 0.025
    panel["source_detail"] = "actual_public_displacement_panel"
    return panel


def duplicate_render_to_source(cols, mats):
    source = cols["TH_SOURCE"]
    for obj in list(cols["TH_RENDER"].objects):
        if obj.type != "MESH":
            continue
        dup = obj.copy()
        dup.data = obj.data.copy()
        source.objects.link(dup)
        dup.name = "SRC_" + obj.name
        role = obj.get("town_material_role", "stone")
        if role not in mats:
            role = "stone"
        clear_materials(dup)
        dup.data.materials.append(mats[role])
        mod = dup.modifiers.new("SourceEdgeSoftening", "BEVEL")
        mod.width = 0.035
        mod.segments = 2
    add_source_displaced_panel(cols, mats)


def hide_collection(col, hidden):
    col.hide_render = hidden
    for obj in col.objects:
        obj.hide_render = hidden


def build_variant(variant, args, textured=False, winner=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cols = setup_collections()
    mats = make_materials(args, textured=textured)
    add_ground(mats, cols["TH_RENDER"])
    if variant == "A":
        build_A(mats, cols)
    elif variant == "B":
        build_B(mats, cols)
    else:
        build_C(mats, cols)
    add_collision_and_anchors(cols, variant)
    add_lights(mats, cols)
    scene = bpy.context.scene
    configure_render(scene, Path(args.out) / variant / "bootstrap.png")
    record = camera_record(0.0)
    cam = thestra_camera.create_or_update_camera(record, scene=scene, name="TH_CAMERA_PREVIEW", make_active=True)
    move_to_collection(cam, cols["TH_CAMERA_PREVIEW"])
    add_actors(cols, cam)
    if winner:
        duplicate_render_to_source(cols, mats)
    return scene, cols


def acceptance(args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cols = setup_collections()
    mats = make_materials(args, textured=False)
    cube("acceptance_ground", (0, 2.0, -0.3), (40, 10, 0.6), mats["ground"], cols["TH_RENDER"], role="ground")
    cube("acceptance_reference_wall", (0, 4.0, 2.5), (32, 1.0, 5.0), mats["stone"], cols["TH_RENDER"], role="stone")
    add_lights(mats, cols)
    scene = bpy.context.scene
    cam = thestra_camera.create_or_update_camera(camera_record(0.0), scene=scene, make_active=True)
    move_to_collection(cam, cols["TH_CAMERA_PREVIEW"])
    add_actors(cols, cam, names=("Walker_Reference", "Walker_StandIn_1", "Walker_StandIn_2"))
    render_views(scene, cols, Path(args.out) / "presentation", "presentation", actors=True)


def clay(args):
    for variant in ("A", "B", "C"):
        scene, cols = build_variant(variant, args, textured=False, winner=False)
        out_dir = Path(args.out) / variant / "clay"
        render_views(scene, cols, out_dir, variant + "1", actors=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.out) / variant / (variant + "1.blend")))


def winner(args):
    scene, cols = build_variant("C", args, textured=True, winner=True)
    out_dir = Path(args.out) / "C" / "winner"
    hide_collection(cols["TH_SOURCE"], True)
    render_views(scene, cols, out_dir, "C3_render_preview", actors=True)
    hide_collection(cols["TH_SOURCE"], False)
    hide_collection(cols["TH_RENDER"], True)
    hide_collection(cols["TH_PREVIEW_ACTORS"], True)
    render_views(scene, cols, out_dir, "C3_source", actors=False)
    hide_collection(cols["TH_RENDER"], False)
    hide_collection(cols["TH_PREVIEW_ACTORS"], False)
    hide_collection(cols["TH_SOURCE"], False)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.out) / "C" / "C3.blend"))


def main():
    args = parse_args()
    Path(args.out).mkdir(parents=True, exist_ok=True)
    if args.phase == "acceptance":
        acceptance(args)
    elif args.phase == "clay":
        clay(args)
    else:
        winner(args)


if __name__ == "__main__":
    main()
