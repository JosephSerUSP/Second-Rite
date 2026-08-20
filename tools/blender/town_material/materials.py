"""Town material library: procedural / CC0-library / generated, one interface.

Every builder returns a Blender material whose surface is a Principled BSDF and
whose relief is driven by a height signal through a Bump node (and optionally a
real displacement modifier on TH_SOURCE). Normal maps are never authored by an
image model; library normals are used only where the library shipped a real
tangent-space map.
"""
from __future__ import annotations

from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
MAT_DIR = ROOT / "projects/hichaukitoden-game/assets/authoring/town/materials"
PH_DIR = MAT_DIR / "polyhaven"
GEN_DIR = MAT_DIR / "generated" / "derived"


# ---------------------------------------------------------------- helpers
def _fresh(name):
    mat = bpy.data.materials.get(name)
    if mat:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    return mat


def _core(mat, scale=1.0):
    """Output + Principled + a mapped texture-coordinate chain."""
    nt = mat.node_tree
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["IOR"].default_value = 1.45
    return nt, out, bsdf, mp


def _img(nt, path, non_color=False):
    node = nt.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(str(Path(path).resolve()), check_existing=True)
    if non_color:
        node.image.colorspace_settings.name = "Non-Color"
    node.extension = "REPEAT"
    return node


def _bump(nt, bsdf, height_out, strength):
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    nt.links.new(height_out, b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return b


def _grime(nt, mp, base_color_out, bsdf, amount=0.25, scale=3.0, colour=(0.42, 0.44, 0.36, 1.0)):
    """Procedural weathering overlay: large-scale noise darkens sheltered areas.

    Used to break up library and generated tiling without making every surface
    equally noisy -- amount is deliberately per-material.
    """
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 6.0
    nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[1].position = 0.72
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])

    # Scale the mask by `amount`. Linking the ramp straight into Factor would
    # override the default and apply grime at up to 100%, multiplying the base
    # colour by a near-black tint. Because the noise is driven by the UV vector
    # and facade UVs use v = world z, that darkened every building at the SAME
    # height and read as one black band across the whole street.
    gain = nt.nodes.new("ShaderNodeMath")
    gain.operation = "MULTIPLY"
    gain.inputs[1].default_value = float(amount)
    nt.links.new(ramp.outputs["Color"], gain.inputs[0])

    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    nt.links.new(base_color_out, mix.inputs[6])
    mix.inputs[7].default_value = colour
    nt.links.new(gain.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    return mix


# ---------------------------------------------------------------- strategy B
def library_material(slug, *, scale=1.0, bump=0.35, grime=0.0, use_library_normal=True,
                     name=None):
    """CC0 Poly Haven material: albedo + roughness + AO + height (+ normal)."""
    d = PH_DIR / slug
    mat = _fresh(name or f"LIB_{slug}")
    nt, out, bsdf, mp = _core(mat, scale)

    alb = _img(nt, d / "albedo.jpg")
    nt.links.new(mp.outputs["Vector"], alb.inputs["Vector"])
    colour_out = alb.outputs["Color"]

    ao_p = d / "ao.jpg"
    if ao_p.is_file():
        ao = _img(nt, ao_p, non_color=True)
        nt.links.new(mp.outputs["Vector"], ao.inputs["Vector"])
        m = nt.nodes.new("ShaderNodeMix")
        m.data_type = "RGBA"; m.blend_type = "MULTIPLY"
        m.inputs["Factor"].default_value = 0.6
        nt.links.new(alb.outputs["Color"], m.inputs[6])
        nt.links.new(ao.outputs["Color"], m.inputs[7])
        colour_out = m.outputs[2]

    if grime > 0.0:
        _grime(nt, mp, colour_out, bsdf, amount=grime)
    else:
        nt.links.new(colour_out, bsdf.inputs["Base Color"])

    r_p = d / "roughness.jpg"
    if r_p.is_file():
        r = _img(nt, r_p, non_color=True)
        nt.links.new(mp.outputs["Vector"], r.inputs["Vector"])
        nt.links.new(r.outputs["Color"], bsdf.inputs["Roughness"])

    n_p, h_p = d / "normal.jpg", d / "height.jpg"
    normal_in = None
    if use_library_normal and n_p.is_file():
        n = _img(nt, n_p, non_color=True)
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 1.0
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        normal_in = nm.outputs["Normal"]
    if h_p.is_file():
        h = _img(nt, h_p, non_color=True)
        nt.links.new(mp.outputs["Vector"], h.inputs["Vector"])
        b = _bump(nt, bsdf, h.outputs["Color"], bump)
        if normal_in is not None:
            nt.links.new(normal_in, b.inputs["Normal"])
        mat["height_node"] = h.name
    elif normal_in is not None:
        nt.links.new(normal_in, bsdf.inputs["Normal"])
    mat["th_source_strategy"] = "public-library"
    mat["th_source_id"] = f"polyhaven:{slug}"
    return mat


# ---------------------------------------------------------------- strategy C
def generated_material(name_id, *, scale=1.0, bump=0.45, grime=0.18, name=None):
    """OpenAI-generated flat albedo + numerically derived height/rough/AO."""
    mat = _fresh(name or f"GEN_{name_id}")
    nt, out, bsdf, mp = _core(mat, scale)
    alb = _img(nt, GEN_DIR / f"{name_id}_albedo.png")
    nt.links.new(mp.outputs["Vector"], alb.inputs["Vector"])

    ao = _img(nt, GEN_DIR / f"{name_id}_ao.png", non_color=True)
    nt.links.new(mp.outputs["Vector"], ao.inputs["Vector"])
    m = nt.nodes.new("ShaderNodeMix"); m.data_type = "RGBA"; m.blend_type = "MULTIPLY"
    m.inputs["Factor"].default_value = 0.55
    nt.links.new(alb.outputs["Color"], m.inputs[6])
    nt.links.new(ao.outputs["Color"], m.inputs[7])

    if grime > 0.0:
        _grime(nt, mp, m.outputs[2], bsdf, amount=grime)
    else:
        nt.links.new(m.outputs[2], bsdf.inputs["Base Color"])

    r = _img(nt, GEN_DIR / f"{name_id}_roughness.png", non_color=True)
    nt.links.new(mp.outputs["Vector"], r.inputs["Vector"])
    nt.links.new(r.outputs["Color"], bsdf.inputs["Roughness"])

    h = _img(nt, GEN_DIR / f"{name_id}_height.png", non_color=True)
    nt.links.new(mp.outputs["Vector"], h.inputs["Vector"])
    _bump(nt, bsdf, h.outputs["Color"], bump)
    mat["height_node"] = h.name
    mat["th_source_strategy"] = "openai-generated"
    mat["th_source_id"] = f"openai:{name_id}"
    return mat
