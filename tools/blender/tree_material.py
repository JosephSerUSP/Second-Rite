"""The one Blender material for foliage atlas cards.

Kept apart from the tree lab recipe so anything that needs the material -- the
lab, an exterior recipe, the live bridge -- can build it without importing a
scene builder and its dependency chain.
"""
from __future__ import annotations

from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
ATLAS = ROOT / "projects/hichaukitoden-game/assets/materials/foliage_card/kenney_branch_atlas.png"
MATERIAL_NAME = "sr_foliage_kenney_atlas"


def foliage_material(name: str = MATERIAL_NAME):
    """Create or update the alpha-clipped branch-atlas material."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.get("Kenney Branch Atlas") or nodes.new("ShaderNodeTexImage")
    tex.name = "Kenney Branch Atlas"
    tex.image = bpy.data.images.load(str(ATLAS), check_existing=True)
    tint = nodes.get("Kenney foliage tint") or nodes.new("ShaderNodeMixRGB")
    tint.name = "Kenney foliage tint"
    tint.blend_type = "MULTIPLY"
    # The atlas is a pure white silhouette carrying alpha only, so every bit of
    # colour comes from this node.  A partial mix does not "tint" it -- it
    # blends the result back toward white, which is what left crowns mint.
    tint.inputs[0].default_value = 1.0
    tint.inputs[2].default_value = (.21, .40, .13, 1.0)
    links.new(tex.outputs["Color"], tint.inputs[1])
    links.new(tint.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = .9
    # A trace of emission keeps cards legible when a spray turns away from the
    # key light; the sky still supplies the dominant shading.
    if "Emission Color" in bsdf.inputs:
        # Emission on a white mask lifts the whole card, so keep it to a floor
        # that rescues a back-facing spray without bleaching a lit one.
        bsdf.inputs["Emission Color"].default_value = (.02, .05, .015, 1.0)
        bsdf.inputs["Emission Strength"].default_value = .10
    return mat
