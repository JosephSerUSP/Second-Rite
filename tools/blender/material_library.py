"""Second Rite Town Gauntlet — Authoritative Material Library.

Provides procedural, public CC0, and OpenAI-generated PBR materials
for Blender 5.x with Cycles rendering.
"""
from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXTURES_DIR = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "textures"
PUBLIC_DIR = TEXTURES_DIR / "public_cc0"
AI_DIR = TEXTURES_DIR / "generated_ai"


def _require_blender():
    import bpy
    return bpy


def create_texture_node(nodes, links, image_path: Path, is_color: bool = True, loc=(0, 0)):
    import bpy
    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.location = loc
    if image_path.is_file():
        img = bpy.data.images.load(str(image_path), check_existing=True)
        tex_node.image = img
        if not is_color:
            tex_node.image.colorspace_settings.name = "Non-Color"
    return tex_node


def create_mapping_nodes(nodes, links, loc=(-800, 0), scale=(1.0, 1.0, 1.0)):
    coord = nodes.new("ShaderNodeTexCoord")
    coord.location = loc
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (loc[0] + 200, loc[1])
    mapping.inputs["Scale"].default_value = scale
    links.new(coord.outputs["UV"], mapping.inputs["Vector"])
    return mapping


# ==============================================================================
# STRATEGY A: PROCEDURAL BLENDER MATERIALS
# ==============================================================================

def create_procedural_stone(name: str = "Proc_StoneWall_Ashlar", base_tint=(0.62, 0.58, 0.50)):
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Texture Coordinate & Mapping
    mapping = create_mapping_nodes(nodes, links, loc=(-1000, 0), scale=(2.0, 2.0, 2.0))

    # Voronoi for stone masonry pattern
    voronoi_cells = nodes.new("ShaderNodeTexVoronoi")
    voronoi_cells.location = (-600, 200)
    voronoi_cells.feature = "F1"
    voronoi_cells.distance = "CHEBYCHEV"
    voronoi_cells.inputs["Scale"].default_value = 4.0
    links.new(mapping.outputs["Vector"], voronoi_cells.inputs["Vector"])

    voronoi_edges = nodes.new("ShaderNodeTexVoronoi")
    voronoi_edges.location = (-600, -100)
    voronoi_edges.feature = "DISTANCE_TO_EDGE"
    voronoi_edges.distance = "CHEBYCHEV"
    voronoi_edges.inputs["Scale"].default_value = 4.0
    links.new(mapping.outputs["Vector"], voronoi_edges.inputs["Vector"])

    # Noise for surface grain & weathering
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-600, 500)
    noise.inputs["Scale"].default_value = 18.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.65
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])

    # Color Ramp for Stone variation
    cr_color = nodes.new("ShaderNodeValToRGB")
    cr_color.location = (-300, 200)
    cr_color.color_ramp.elements[0].color = (base_tint[0] * 0.75, base_tint[1] * 0.75, base_tint[2] * 0.75, 1.0)
    cr_color.color_ramp.elements[1].color = (base_tint[0] * 1.15, base_tint[1] * 1.15, base_tint[2] * 1.15, 1.0)
    links.new(voronoi_cells.outputs["Color"], cr_color.inputs["Fac"])

    # Mix stone color with noise grain
    mix_color = nodes.new("ShaderNodeMix")
    mix_color.data_type = "RGBA"
    mix_color.location = (-50, 200)
    mix_color.blend_type = "MULTIPLY"
    mix_color.inputs["Factor"].default_value = 0.4
    links.new(cr_color.outputs["Color"], mix_color.inputs[6])
    links.new(noise.outputs["Color"], mix_color.inputs[7])

    # Mortar mask
    cr_mortar = nodes.new("ShaderNodeValToRGB")
    cr_mortar.location = (-300, -100)
    cr_mortar.color_ramp.elements[0].position = 0.04
    cr_mortar.color_ramp.elements[1].position = 0.12
    links.new(voronoi_edges.outputs["Distance"], cr_mortar.inputs["Fac"])

    mix_mortar = nodes.new("ShaderNodeMix")
    mix_mortar.data_type = "RGBA"
    mix_mortar.location = (0, 100)
    mix_mortar.blend_type = "MIX"
    links.new(cr_mortar.outputs["Color"], mix_mortar.inputs["Factor"])
    mix_mortar.inputs[6].default_value = (0.22, 0.20, 0.18, 1.0) # Mortar color
    links.new(mix_color.outputs[2], mix_mortar.inputs[7])
    links.new(mix_mortar.outputs[2], bsdf.inputs["Base Color"])

    # Bump / Normal
    bump = nodes.new("ShaderNodeBump")
    bump.location = (-100, -200)
    bump.inputs["Strength"].default_value = 0.65
    bump.inputs["Distance"].default_value = 0.1
    links.new(cr_mortar.outputs["Color"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    bsdf.inputs["Roughness"].default_value = 0.85
    return mat


def create_procedural_plaster(name: str = "Proc_PlasterStucco", base_color=(0.74, 0.68, 0.56)):
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    mapping = create_mapping_nodes(nodes, links, loc=(-800, 0), scale=(3.0, 3.0, 3.0))

    # Noise for fine plaster grit
    noise_fine = nodes.new("ShaderNodeTexNoise")
    noise_fine.location = (-500, 200)
    noise_fine.inputs["Scale"].default_value = 35.0
    noise_fine.inputs["Detail"].default_value = 6.0
    links.new(mapping.outputs["Vector"], noise_fine.inputs["Vector"])

    # Noise for large grime / staining
    noise_grime = nodes.new("ShaderNodeTexNoise")
    noise_grime.location = (-500, -100)
    noise_grime.inputs["Scale"].default_value = 2.5
    noise_grime.inputs["Detail"].default_value = 4.0
    links.new(mapping.outputs["Vector"], noise_grime.inputs["Vector"])

    cr_grime = nodes.new("ShaderNodeValToRGB")
    cr_grime.location = (-250, -100)
    cr_grime.color_ramp.elements[0].color = (base_color[0] * 0.75, base_color[1] * 0.75, base_color[2] * 0.70, 1.0)
    cr_grime.color_ramp.elements[1].color = (*base_color, 1.0)
    links.new(noise_grime.outputs["Fac"], cr_grime.inputs["Fac"])

    mix_color = nodes.new("ShaderNodeMix")
    mix_color.data_type = "RGBA"
    mix_color.location = (-50, 100)
    mix_color.blend_type = "OVERLAY"
    mix_color.inputs["Factor"].default_value = 0.25
    links.new(cr_grime.outputs["Color"], mix_color.inputs[6])
    links.new(noise_fine.outputs["Color"], mix_color.inputs[7])
    links.new(mix_color.outputs[2], bsdf.inputs["Base Color"])

    # Bump for gritty stucco surface
    bump = nodes.new("ShaderNodeBump")
    bump.location = (-100, -250)
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.05
    links.new(noise_fine.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    bsdf.inputs["Roughness"].default_value = 0.92
    return mat


def create_procedural_cobblestone(name: str = "Proc_CobblestoneRoad"):
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    mapping = create_mapping_nodes(nodes, links, loc=(-900, 0), scale=(3.5, 3.5, 3.5))

    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.location = (-600, 100)
    voronoi.feature = "DISTANCE_TO_EDGE"
    voronoi.inputs["Scale"].default_value = 5.0
    links.new(mapping.outputs["Vector"], voronoi.inputs["Vector"])

    voronoi_color = nodes.new("ShaderNodeTexVoronoi")
    voronoi_color.location = (-600, 400)
    voronoi_color.feature = "F1"
    voronoi_color.inputs["Scale"].default_value = 5.0
    links.new(mapping.outputs["Vector"], voronoi_color.inputs["Vector"])

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-600, -200)
    noise.inputs["Scale"].default_value = 20.0
    noise.inputs["Detail"].default_value = 8.0
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])

    # Edge ramp for joints
    cr_joints = nodes.new("ShaderNodeValToRGB")
    cr_joints.location = (-350, 100)
    cr_joints.color_ramp.elements[0].position = 0.08
    cr_joints.color_ramp.elements[1].position = 0.25
    links.new(voronoi.outputs["Distance"], cr_joints.inputs["Fac"])

    cr_stones = nodes.new("ShaderNodeValToRGB")
    cr_stones.location = (-350, 400)
    cr_stones.color_ramp.elements[0].color = (0.25, 0.24, 0.22, 1.0)
    cr_stones.color_ramp.elements[1].color = (0.46, 0.44, 0.40, 1.0)
    links.new(voronoi_color.outputs["Color"], cr_stones.inputs["Fac"])

    mix_dirt = nodes.new("ShaderNodeMix")
    mix_dirt.data_type = "RGBA"
    mix_dirt.location = (-100, 200)
    mix_dirt.blend_type = "MIX"
    links.new(cr_joints.outputs["Color"], mix_dirt.inputs["Factor"])
    mix_dirt.inputs[6].default_value = (0.16, 0.14, 0.12, 1.0) # Damp joint dirt
    links.new(cr_stones.outputs["Color"], mix_dirt.inputs[7])
    links.new(mix_dirt.outputs[2], bsdf.inputs["Base Color"])

    bump = nodes.new("ShaderNodeBump")
    bump.location = (-100, -100)
    bump.inputs["Strength"].default_value = 0.8
    bump.inputs["Distance"].default_value = 0.15
    links.new(cr_joints.outputs["Color"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    bsdf.inputs["Roughness"].default_value = 0.88
    return mat


def create_procedural_wood(name: str = "Proc_AgedTimber", dark: bool = True):
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    mapping = create_mapping_nodes(nodes, links, loc=(-800, 0), scale=(1.0, 8.0, 1.0))

    wave = nodes.new("ShaderNodeTexWave")
    wave.location = (-500, 200)
    wave.wave_type = "BANDS"
    wave.bands_direction = "Y"
    wave.inputs["Scale"].default_value = 6.0
    wave.inputs["Distortion"].default_value = 4.5
    wave.inputs["Detail"].default_value = 6.0
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])

    cr = nodes.new("ShaderNodeValToRGB")
    cr.location = (-250, 200)
    if dark:
        cr.color_ramp.elements[0].color = (0.12, 0.08, 0.05, 1.0)
        cr.color_ramp.elements[1].color = (0.28, 0.18, 0.11, 1.0)
    else:
        cr.color_ramp.elements[0].color = (0.26, 0.16, 0.09, 1.0)
        cr.color_ramp.elements[1].color = (0.45, 0.30, 0.18, 1.0)
    links.new(wave.outputs["Color"], cr.inputs["Fac"])
    links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])

    bump = nodes.new("ShaderNodeBump")
    bump.location = (-100, -100)
    bump.inputs["Strength"].default_value = 0.45
    bump.inputs["Distance"].default_value = 0.04
    links.new(wave.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    bsdf.inputs["Roughness"].default_value = 0.72
    return mat


def create_procedural_roof_tile(name: str = "Proc_RoofTile_Terracotta", terracotta: bool = True):
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    mapping = create_mapping_nodes(nodes, links, loc=(-800, 0), scale=(6.0, 3.0, 1.0))

    brick = nodes.new("ShaderNodeTexBrick")
    brick.location = (-500, 150)
    brick.inputs["Scale"].default_value = 2.0
    brick.inputs["Mortar Size"].default_value = 0.03
    links.new(mapping.outputs["Vector"], brick.inputs["Vector"])

    cr = nodes.new("ShaderNodeValToRGB")
    cr.location = (-250, 150)
    if terracotta:
        cr.color_ramp.elements[0].color = (0.48, 0.18, 0.10, 1.0)
        cr.color_ramp.elements[1].color = (0.68, 0.30, 0.16, 1.0)
    else:
        cr.color_ramp.elements[0].color = (0.14, 0.16, 0.22, 1.0)
        cr.color_ramp.elements[1].color = (0.24, 0.28, 0.36, 1.0)
    links.new(brick.outputs["Color"], cr.inputs["Fac"])
    links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])

    bump = nodes.new("ShaderNodeBump")
    bump.location = (-100, -100)
    bump.inputs["Strength"].default_value = 0.7
    bump.inputs["Distance"].default_value = 0.08
    links.new(brick.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    bsdf.inputs["Roughness"].default_value = 0.78
    return mat


def create_procedural_metal(name: str = "Proc_WroughtIron", brass: bool = False):
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    mapping = create_mapping_nodes(nodes, links, loc=(-700, 0), scale=(4.0, 4.0, 4.0))

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-450, 100)
    noise.inputs["Scale"].default_value = 16.0
    noise.inputs["Detail"].default_value = 6.0
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])

    cr = nodes.new("ShaderNodeValToRGB")
    cr.location = (-200, 100)
    if brass:
        cr.color_ramp.elements[0].color = (0.65, 0.48, 0.16, 1.0)
        cr.color_ramp.elements[1].color = (0.85, 0.70, 0.28, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.88
        bsdf.inputs["Roughness"].default_value = 0.38
    else:
        cr.color_ramp.elements[0].color = (0.08, 0.08, 0.10, 1.0)
        cr.color_ramp.elements[1].color = (0.18, 0.18, 0.20, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.92
        bsdf.inputs["Roughness"].default_value = 0.45
    links.new(noise.outputs["Color"], cr.inputs["Fac"])
    links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])

    bump = nodes.new("ShaderNodeBump")
    bump.location = (-100, -150)
    bump.inputs["Strength"].default_value = 0.3
    bump.inputs["Distance"].default_value = 0.02
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


# ==============================================================================
# STRATEGY B: PUBLIC-LIBRARY PBR (CC0 POLY HAVEN)
# ==============================================================================

def create_public_pbr_material(name: str, tex_id: str, uv_scale: float = 1.0):
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (500, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    mapping = create_mapping_nodes(nodes, links, loc=(-800, 0), scale=(uv_scale, uv_scale, uv_scale))

    tex_folder = PUBLIC_DIR / tex_id
    diff_file = next(tex_folder.glob("*diffuse*.*"), None) or next(tex_folder.glob("*diff*.*"), None)
    rough_file = next(tex_folder.glob("*rough*.*"), None)
    norm_file = next(tex_folder.glob("*nor_gl*.*"), None) or next(tex_folder.glob("*nor*.*"), None)
    disp_file = next(tex_folder.glob("*displacement*.*"), None) or next(tex_folder.glob("*disp*.*"), None)

    if diff_file and diff_file.is_file():
        t_diff = create_texture_node(nodes, links, diff_file, is_color=True, loc=(-400, 300))
        links.new(mapping.outputs["Vector"], t_diff.inputs["Vector"])
        links.new(t_diff.outputs["Color"], bsdf.inputs["Base Color"])

    if rough_file and rough_file.is_file():
        t_rough = create_texture_node(nodes, links, rough_file, is_color=False, loc=(-400, 50))
        links.new(mapping.outputs["Vector"], t_rough.inputs["Vector"])
        links.new(t_rough.outputs["Color"], bsdf.inputs["Roughness"])

    if norm_file and norm_file.is_file():
        t_norm = create_texture_node(nodes, links, norm_file, is_color=False, loc=(-400, -200))
        links.new(mapping.outputs["Vector"], t_norm.inputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.location = (-100, -200)
        nmap.inputs["Strength"].default_value = 0.85
        links.new(t_norm.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    elif disp_file and disp_file.is_file():
        t_disp = create_texture_node(nodes, links, disp_file, is_color=False, loc=(-400, -200))
        links.new(mapping.outputs["Vector"], t_disp.inputs["Vector"])
        bump = nodes.new("ShaderNodeBump")
        bump.location = (-100, -200)
        bump.inputs["Strength"].default_value = 0.75
        bump.inputs["Distance"].default_value = 0.1
        links.new(t_disp.outputs["Color"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


# ==============================================================================
# STRATEGY C: OPENAI GENERATED PBR SOURCES
# ==============================================================================

def create_ai_pbr_material(name: str, mat_id: str, uv_scale: float = 1.0, bump_strength: float = 0.75):
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    mapping = create_mapping_nodes(nodes, links, loc=(-900, 0), scale=(uv_scale, uv_scale, uv_scale))

    tex_folder = AI_DIR / mat_id
    albedo_file = tex_folder / f"{mat_id}_albedo.png"
    height_file = tex_folder / f"{mat_id}_height.png"
    rough_file = tex_folder / f"{mat_id}_roughness.png"
    ao_file = tex_folder / f"{mat_id}_ao.png"

    if albedo_file.is_file():
        t_albedo = create_texture_node(nodes, links, albedo_file, is_color=True, loc=(-500, 300))
        links.new(mapping.outputs["Vector"], t_albedo.inputs["Vector"])
        
        if ao_file.is_file():
            t_ao = create_texture_node(nodes, links, ao_file, is_color=False, loc=(-500, 600))
            links.new(mapping.outputs["Vector"], t_ao.inputs["Vector"])
            mix_ao = nodes.new("ShaderNodeMix")
            mix_ao.data_type = "RGBA"
            mix_ao.location = (-100, 400)
            mix_ao.blend_type = "MULTIPLY"
            mix_ao.inputs["Factor"].default_value = 0.5
            links.new(t_albedo.outputs["Color"], mix_ao.inputs[6])
            links.new(t_ao.outputs["Color"], mix_ao.inputs[7])
            links.new(mix_ao.outputs[2], bsdf.inputs["Base Color"])
        else:
            links.new(t_albedo.outputs["Color"], bsdf.inputs["Base Color"])

    if rough_file.is_file():
        t_rough = create_texture_node(nodes, links, rough_file, is_color=False, loc=(-500, 50))
        links.new(mapping.outputs["Vector"], t_rough.inputs["Vector"])
        links.new(t_rough.outputs["Color"], bsdf.inputs["Roughness"])

    if height_file.is_file():
        t_height = create_texture_node(nodes, links, height_file, is_color=False, loc=(-500, -200))
        links.new(mapping.outputs["Vector"], t_height.inputs["Vector"])
        bump = nodes.new("ShaderNodeBump")
        bump.location = (-100, -200)
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.12
        links.new(t_height.outputs["Color"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


# ==============================================================================
# STRATEGY HYBRID: CC0 + PROCEDURAL GRIME + AI HEIGHT ORNAMENT
# ==============================================================================

def create_hybrid_stone_facade(name: str = "Hybrid_WeatheredStoneFacade"):
    """Composite material: Public CC0 stone base + procedural moss/grime + AI height relief."""
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (700, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (400, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    mapping = create_mapping_nodes(nodes, links, loc=(-1000, 0), scale=(1.5, 1.5, 1.5))

    # Base: Public CC0 rustic stone wall
    stone_folder = PUBLIC_DIR / "rustic_stone_wall"
    diff_file = next(stone_folder.glob("*diffuse*.*"), None)
    rough_file = next(stone_folder.glob("*rough*.*"), None)
    norm_file = next(stone_folder.glob("*nor_gl*.*"), None)

    t_diff = create_texture_node(nodes, links, diff_file, is_color=True, loc=(-600, 300))
    links.new(mapping.outputs["Vector"], t_diff.inputs["Vector"])

    # Procedural Grime / Moss overlay
    noise_moss = nodes.new("ShaderNodeTexNoise")
    noise_moss.location = (-600, 600)
    noise_moss.inputs["Scale"].default_value = 8.0
    noise_moss.inputs["Detail"].default_value = 6.0
    links.new(mapping.outputs["Vector"], noise_moss.inputs["Vector"])

    cr_moss = nodes.new("ShaderNodeValToRGB")
    cr_moss.location = (-300, 600)
    cr_moss.color_ramp.elements[0].position = 0.55
    cr_moss.color_ramp.elements[1].position = 0.75
    cr_moss.color_ramp.elements[1].color = (0.18, 0.28, 0.12, 1.0) # Moss green
    links.new(noise_moss.outputs["Fac"], cr_moss.inputs["Fac"])

    mix_moss = nodes.new("ShaderNodeMix")
    mix_moss.data_type = "RGBA"
    mix_moss.location = (-50, 400)
    mix_moss.blend_type = "MIX"
    links.new(cr_moss.outputs["Color"], mix_moss.inputs["Factor"])
    links.new(t_diff.outputs["Color"], mix_moss.inputs[6])
    mix_moss.inputs[7].default_value = (0.16, 0.24, 0.10, 1.0) # Dark moss
    links.new(mix_moss.outputs[2], bsdf.inputs["Base Color"])

    # Roughness from CC0 + procedural dampness
    if rough_file:
        t_rough = create_texture_node(nodes, links, rough_file, is_color=False, loc=(-600, 50))
        links.new(mapping.outputs["Vector"], t_rough.inputs["Vector"])
        links.new(t_rough.outputs["Color"], bsdf.inputs["Roughness"])

    # Normal map from CC0
    if norm_file:
        t_norm = create_texture_node(nodes, links, norm_file, is_color=False, loc=(-600, -200))
        links.new(mapping.outputs["Vector"], t_norm.inputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.location = (-200, -200)
        nmap.inputs["Strength"].default_value = 0.9
        links.new(t_norm.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    return mat
