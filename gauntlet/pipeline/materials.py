# gauntlet/pipeline/materials.py
# Stylized shader and procedural material generator for DRPG sprites in Blender

import os
import bpy

def create_stylized_material(
    name: str,
    base_color: tuple,
    roughness: float = 0.70,
    metallic: float = 0.0,
    specular: float = 0.20,
    emission_color: tuple = (0.0, 0.0, 0.0, 1.0),
    emission_strength: float = 0.0
) -> bpy.types.Material:
    """Creates or updates a stylized Principled BSDF material."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)

    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()

    node_output = nodes.new(type="ShaderNodeOutputMaterial")
    node_output.location = (400, 0)

    node_bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    node_bsdf.location = (0, 0)

    if 'Base Color' in node_bsdf.inputs:
        node_bsdf.inputs['Base Color'].default_value = base_color
    if 'Roughness' in node_bsdf.inputs:
        node_bsdf.inputs['Roughness'].default_value = roughness
    if 'Metallic' in node_bsdf.inputs:
        node_bsdf.inputs['Metallic'].default_value = metallic

    # Specular control (low specular to avoid blown-out white gradients)
    for spec_name in ['Specular IOR Level', 'Specular']:
        if spec_name in node_bsdf.inputs:
            node_bsdf.inputs[spec_name].default_value = specular

    if 'Emission Color' in node_bsdf.inputs:
        node_bsdf.inputs['Emission Color'].default_value = emission_color
        if 'Emission Strength' in node_bsdf.inputs:
            node_bsdf.inputs['Emission Strength'].default_value = emission_strength
    elif 'Emission' in node_bsdf.inputs:
        node_bsdf.inputs['Emission'].default_value = emission_color

    mat.node_tree.links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_textured_material(name: str, img: bpy.types.Image) -> bpy.types.Material:
    """Creates a material using a native Blender image texture with crisp nearest-neighbor interpolation."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)

    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()

    node_output = nodes.new(type="ShaderNodeOutputMaterial")
    node_output.location = (400, 0)

    node_tex = nodes.new(type="ShaderNodeTexImage")
    node_tex.location = (0, 0)
    node_tex.image = img
    node_tex.interpolation = 'Closest' # Crisp retro pixel clarity

    node_emit = nodes.new(type="ShaderNodeEmission")
    node_emit.location = (200, 0)
    node_emit.inputs['Strength'].default_value = 1.0

    mat.node_tree.links.new(node_tex.outputs['Color'], node_emit.inputs['Color'])
    mat.node_tree.links.new(node_emit.outputs['Emission'], node_output.inputs['Surface'])

    return mat

def get_celina_materials() -> dict:
    """
    Celina's palette (Calibrated for high-contrast DRPG sprite readability):
    - Royal Sapphire Frock Coat (#2450B0)
    - Obsidian Velvet Corset (#080810)
    - Pure White Fencing Breeches (#ECEEF6)
    - Saddle Tan Leather Riding Boots (#783C18) with Ivory Soles (#EAE4D4)
    - Crisp Snow White Cravat & Wing Collar (#FFFFFF)
    - Burnished Gold Filigree & Epaulets (#FFC408)
    - Polished Steel Rapier Blade (#F4F8FC)
    - Crisp Anime Face Texture (Closest pixel interpolation)
    """
    from gauntlet.pipeline.texture_builder import create_celina_face_image
    face_img = create_celina_face_image()
    skin_mat = create_textured_material("Celina_Skin", face_img)

    return {
        "skin": skin_mat,
        "hair_raven": create_stylized_material("Celina_HairRaven", (0.04, 0.04, 0.07, 1.0), roughness=0.55),
        "coat_primary": create_stylized_material("Celina_CoatPrimary", (0.12, 0.32, 0.72, 1.0), roughness=0.65),
        "coat_trim": create_stylized_material("Celina_CoatTrim", (1.0, 0.78, 0.05, 1.0), metallic=0.95, roughness=0.15, specular=0.9),
        "shirt_ivory": create_stylized_material("Celina_ShirtIvory", (0.98, 0.98, 0.96, 1.0), roughness=0.65),
        "trousers": create_stylized_material("Celina_Trousers", (0.92, 0.94, 0.98, 1.0), roughness=0.75), # White fencing breeches
        "boots": create_stylized_material("Celina_Boots", (0.42, 0.22, 0.10, 1.0), roughness=0.60), # Saddle leather
        "boot_sole": create_stylized_material("Celina_BootSole", (0.92, 0.88, 0.82, 1.0), roughness=0.70), # Ivory grounding soles
        "vest_corset": create_stylized_material("Celina_Corset", (0.04, 0.04, 0.06, 1.0), roughness=0.85),
        "gem_ruby": create_stylized_material("Celina_Ruby", (0.95, 0.05, 0.18, 1.0), roughness=0.10, specular=1.0, emission_color=(0.95, 0.05, 0.18, 1.0), emission_strength=1.8),
        "rapier_steel": create_stylized_material("Celina_Steel", (0.96, 0.98, 1.0, 1.0), metallic=0.98, roughness=0.04, specular=1.0, emission_color=(0.95, 0.98, 1.0, 1.0), emission_strength=0.8)
    }

def get_agnes_materials() -> dict:
    """
    Agnes's palette:
    - Saturated Rust/Ochre Quilted Gambeson (#B84818)
    - Burnished Bronze Pauldron & Boss (#E8A030)
    - Slate-Silver Steel Greaves & Warhammer (#8A9AA8)
    - Dark Espresso Leather Skirt (#241812)
    - Warm Earthy Skin (#D8A07A) with fierce anime face atlas
    - Fiery Auburn Braided Hair (#882810)
    - Forest Green Eyes (#30A040)
    """
    from gauntlet.pipeline.texture_builder import create_agnes_face_image
    face_img = create_agnes_face_image()
    skin_mat = create_textured_material("Agnes_Skin", face_img)

    return {
        "skin": skin_mat,
        "skin_shadow": create_stylized_material("Agnes_SkinShadow", (0.68, 0.46, 0.34, 1.0), roughness=0.65),
        "hair": create_stylized_material("Agnes_Hair", (0.55, 0.16, 0.06, 1.0), roughness=0.60),
        "gambeson_rust": create_stylized_material("Agnes_GambesonRust", (0.72, 0.28, 0.10, 1.0), roughness=0.75),
        "bronze_armor": create_stylized_material("Agnes_BronzeArmor", (0.92, 0.62, 0.18, 1.0), metallic=0.92, roughness=0.18),
        "iron_metal": create_stylized_material("Agnes_IronMetal", (0.72, 0.76, 0.82, 1.0), metallic=0.95, roughness=0.15, emission_color=(0.75, 0.80, 0.85, 1.0), emission_strength=0.3),
        "leather_dark": create_stylized_material("Agnes_LeatherDark", (0.16, 0.11, 0.08, 1.0), roughness=0.80),
        "copper_trim": create_stylized_material("Agnes_CopperTrim", (0.92, 0.50, 0.22, 1.0), metallic=0.90, roughness=0.20),
        "eye_green": create_stylized_material("Agnes_EyeGreen", (0.20, 0.85, 0.30, 1.0), roughness=0.15, emission_color=(0.20, 0.85, 0.30, 1.0), emission_strength=1.5),
        "shirt_linen": create_stylized_material("Agnes_ShirtLinen", (0.94, 0.90, 0.84, 1.0), roughness=0.75),
    }

def get_gambler_materials() -> dict:
    """
    The Gambler's palette:
    - Pure Emerald Velvet Duster (#0D683A)
    - Damask Velvet Crimson Vest (#8A1424)
    - Stark Ivory Silk Shirt & Spats (#F8F6F2)
    - Charcoal Pinstripe Trousers (#181A22)
    - Deep Violet Fedora Band & Feather (#642888)
    - Gilded Watch Chain & Buttons (#F2B824)
    - Glowing Tarot Playing Cards (White / Scarlet)
    """
    from gauntlet.pipeline.texture_builder import create_gambler_face_image
    face_img = create_gambler_face_image()
    skin_mat = create_textured_material("Gambler_Skin", face_img)

    return {
        "skin": skin_mat,
        "hair": create_stylized_material("Gambler_Hair", (0.04, 0.04, 0.06, 1.0), roughness=0.55),
        "duster_emerald": create_stylized_material("Gambler_DusterEmerald", (0.06, 0.44, 0.20, 1.0), roughness=0.75),
        "vest_crimson": create_stylized_material("Gambler_VestCrimson", (0.58, 0.08, 0.14, 1.0), roughness=0.70),
        "shirt_ivory": create_stylized_material("Gambler_ShirtIvory", (0.98, 0.98, 0.96, 1.0), roughness=0.60),
        "trousers_charcoal": create_stylized_material("Gambler_TrousersCharcoal", (0.10, 0.11, 0.15, 1.0), roughness=0.85),
        "boots_leather": create_stylized_material("Gambler_BootsLeather", (0.06, 0.05, 0.04, 1.0), roughness=0.50),
        "spats_ivory": create_stylized_material("Gambler_SpatsIvory", (0.96, 0.96, 0.94, 1.0), roughness=0.65),
        "brass_trim": create_stylized_material("Gambler_BrassTrim", (0.98, 0.80, 0.15, 1.0), metallic=0.95, roughness=0.15),
        "ribbon_violet": create_stylized_material("Gambler_RibbonViolet", (0.45, 0.15, 0.60, 1.0), roughness=0.60),
        "card_white": create_stylized_material("Gambler_CardWhite", (1.0, 1.0, 1.0, 1.0), roughness=0.10, emission_color=(1.0, 1.0, 1.0, 1.0), emission_strength=1.6),
        "card_red": create_stylized_material("Gambler_CardRed", (0.95, 0.06, 0.14, 1.0), roughness=0.10, emission_color=(0.95, 0.06, 0.14, 1.0), emission_strength=1.8),
    }
