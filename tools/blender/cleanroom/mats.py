"""Clean-room material system.

Three strategies, one contract:

  procedural  -- Blender node networks authored here from zero
  generated   -- ONE flat evenly-lit albedo from an image model, every other
                 channel DERIVED numerically from it (registration is exact by
                 construction; no generated normal map is ever trusted)
  public      -- freshly discovered CC0 scans downloaded during this task

Every material declares `tile_m`, its real physical repeat in metres.
`apply(obj, material)` generates world-space box UVs at exactly that scale, so
a stone course is the same physical size on a wall, a jamb and a plinth.

Colour discipline: authored colours are given as sRGB 0..255 and converted to
LINEAR before they touch a Blender socket. Assigning sRGB numbers straight to
a colour socket renders roughly twice too bright and desaturated.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import bpy

from .scene import world_box_uv


# --------------------------------------------------------------------------
# colour
# --------------------------------------------------------------------------

def srgb_to_linear(c):
    c = c / 255.0 if c > 1.0 else float(c)
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb(r, g, b, a=1.0):
    """sRGB 0..255 -> linear RGBA, the only way this package writes colour."""
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), a)


def hexc(code, a=1.0):
    code = code.lstrip("#")
    return rgb(int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16), a)


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------

class Material:
    def __init__(self, mid, kind, tile_m, builder, *, height_path=None,
                 provenance=None, displaceable=False):
        self.id = mid
        self.kind = kind
        self.tile_m = float(tile_m)
        self.builder = builder
        self.height_path = height_path
        self.provenance = provenance or {}
        self.displaceable = displaceable
        self._blender = None

    def blender(self):
        if self._blender is None or self._blender.name not in bpy.data.materials:
            self._blender = self.builder(self.id)
        return self._blender


_REGISTRY = {}


def register(material):
    _REGISTRY[material.id] = material
    return material


def get(mid):
    if mid not in _REGISTRY:
        raise KeyError("unknown clean-room material '%s'" % mid)
    return _REGISTRY[mid]


def all_materials():
    return dict(_REGISTRY)


def reset_registry():
    _REGISTRY.clear()


def apply(obj, mid, *, uv_offset=(0.0, 0.0)):
    """Assign a registered material and generate its world-scale UVs."""
    mat = get(mid) if isinstance(mid, str) else mid
    obj.data.materials.clear()
    obj.data.materials.append(mat.blender())
    world_box_uv(obj, tile=mat.tile_m, offset=uv_offset)
    return obj


# --------------------------------------------------------------------------
# node helpers
# --------------------------------------------------------------------------

def _fresh(name):
    existing = bpy.data.materials.get(name)
    if existing:
        bpy.data.materials.remove(existing)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, nt, bsdf


def _uv(nt):
    node = nt.nodes.new("ShaderNodeUVMap")
    node.uv_map = "UVMap"
    node.location = (-1100, 0)
    return node


def _load_image(path, *, non_color=False):
    path = str(Path(path))
    name = Path(path).name
    img = bpy.data.images.get(name)
    if img is None or img.filepath_from_user() != path:
        img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return img


def _set(bsdf, key, value):
    if key in bsdf.inputs:
        bsdf.inputs[key].default_value = value


# --------------------------------------------------------------------------
# image-backed material (used by both `generated` and `public`)
# --------------------------------------------------------------------------

def image_material(name, *, albedo, roughness=None, ao=None, height=None,
                   bump_strength=0.35, spec=0.35, metallic=0.0,
                   rough_range=(0.35, 0.95), tint=None, ao_strength=0.7):
    """Albedo image + numerically derived supporting maps.

    Normals come from a Bump node driven by the *height* map, never from a
    generated tangent-space normal image.
    """
    mat, nt, bsdf = _fresh(name)
    uv = _uv(nt)

    alb = nt.nodes.new("ShaderNodeTexImage")
    alb.image = _load_image(albedo)
    alb.interpolation = "Cubic"
    alb.location = (-800, 260)
    nt.links.new(uv.outputs["UV"], alb.inputs["Vector"])
    color_out = alb.outputs["Color"]

    if tint is not None:
        mix = nt.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs["Fac"].default_value = 1.0
        mix.location = (-560, 300)
        nt.links.new(color_out, mix.inputs["Color1"])
        mix.inputs["Color2"].default_value = tint
        color_out = mix.outputs["Color"]

    if ao:
        aon = nt.nodes.new("ShaderNodeTexImage")
        aon.image = _load_image(ao, non_color=True)
        aon.location = (-800, -40)
        nt.links.new(uv.outputs["UV"], aon.inputs["Vector"])
        lift = nt.nodes.new("ShaderNodeMixRGB")
        lift.blend_type = "MIX"
        lift.inputs["Fac"].default_value = ao_strength
        lift.inputs["Color1"].default_value = (1, 1, 1, 1)
        lift.location = (-560, -40)
        nt.links.new(aon.outputs["Color"], lift.inputs["Color2"])
        mul = nt.nodes.new("ShaderNodeMixRGB")
        mul.blend_type = "MULTIPLY"
        mul.inputs["Fac"].default_value = 1.0
        mul.location = (-340, 200)
        nt.links.new(color_out, mul.inputs["Color1"])
        nt.links.new(lift.outputs["Color"], mul.inputs["Color2"])
        color_out = mul.outputs["Color"]

    nt.links.new(color_out, bsdf.inputs["Base Color"])

    if roughness:
        rn = nt.nodes.new("ShaderNodeTexImage")
        rn.image = _load_image(roughness, non_color=True)
        rn.location = (-800, -340)
        nt.links.new(uv.outputs["UV"], rn.inputs["Vector"])
        rmap = nt.nodes.new("ShaderNodeMapRange")
        rmap.location = (-520, -340)
        rmap.inputs["To Min"].default_value = rough_range[0]
        rmap.inputs["To Max"].default_value = rough_range[1]
        nt.links.new(rn.outputs["Color"], rmap.inputs["Value"])
        nt.links.new(rmap.outputs["Result"], bsdf.inputs["Roughness"])
    else:
        _set(bsdf, "Roughness", rough_range[1])

    if height and bump_strength > 0:
        hn = nt.nodes.new("ShaderNodeTexImage")
        hn.image = _load_image(height, non_color=True)
        hn.location = (-800, -640)
        nt.links.new(uv.outputs["UV"], hn.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.location = (-300, -560)
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.06
        nt.links.new(hn.outputs["Color"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    _set(bsdf, "Metallic", metallic)
    _set(bsdf, "Specular IOR Level", spec)
    _set(bsdf, "Specular", spec)
    return mat


# --------------------------------------------------------------------------
# procedural building blocks
# --------------------------------------------------------------------------

def _noise(nt, uv, *, scale=8.0, detail=6.0, roughness=0.55, loc=(-700, 0)):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.location = loc
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    if "Roughness" in n.inputs:
        n.inputs["Roughness"].default_value = roughness
    nt.links.new(uv.outputs["UV"], n.inputs["Vector"])
    return n


def _musgrave_like(nt, uv, *, scale=4.0, detail=10.0, loc=(-700, -200)):
    return _noise(nt, uv, scale=scale, detail=detail, roughness=0.72, loc=loc)


def _ramp(nt, fac, stops, loc=(-460, 0)):
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.location = loc
    els = r.color_ramp.elements
    while len(els) > 1:
        els.remove(els[-1])
    els[0].position = stops[0][0]
    els[0].color = stops[0][1]
    for pos, col in stops[1:]:
        e = els.new(pos)
        e.color = col
    nt.links.new(fac, r.inputs["Fac"])
    return r


def _brick(nt, uv, *, scale=6.0, mortar=0.02, bias=0.0, row_h=0.35,
           squash=1.0, loc=(-700, 200)):
    b = nt.nodes.new("ShaderNodeTexBrick")
    b.location = loc
    b.offset = 0.5
    b.squash = squash
    b.inputs["Scale"].default_value = scale
    b.inputs["Mortar Size"].default_value = mortar
    b.inputs["Mortar Smooth"].default_value = 0.12
    b.inputs["Bias"].default_value = bias
    b.inputs["Row Height"].default_value = row_h
    b.inputs["Brick Width"].default_value = 1.0
    nt.links.new(uv.outputs["UV"], b.inputs["Vector"])
    return b


def procedural_stone(name, *, base, dark, mortar, course_h=0.30,
                     rough=(0.55, 0.92), bump=0.55, grain=26.0):
    """Coursed ashlar: brick mask for the courses, layered noise for wear."""
    mat, nt, bsdf = _fresh(name)
    uv = _uv(nt)
    b = _brick(nt, uv, scale=1.0, mortar=0.028, row_h=course_h, squash=0.86)
    b.inputs["Color1"].default_value = base
    b.inputs["Color2"].default_value = dark
    b.inputs["Mortar"].default_value = mortar

    fine = _noise(nt, uv, scale=grain, detail=8.0, loc=(-700, -120))
    broad = _noise(nt, uv, scale=1.6, detail=4.0, roughness=0.7, loc=(-700, -420))
    weather = _ramp(nt, broad.outputs["Fac"],
                    [(0.30, (0.55, 0.55, 0.55, 1)), (0.78, (1.0, 1.0, 1.0, 1))],
                    loc=(-460, -420))

    tone = nt.nodes.new("ShaderNodeMixRGB")
    tone.blend_type = "MULTIPLY"
    tone.inputs["Fac"].default_value = 0.55
    tone.location = (-200, 120)
    nt.links.new(b.outputs["Color"], tone.inputs["Color1"])
    nt.links.new(weather.outputs["Color"], tone.inputs["Color2"])

    speck = nt.nodes.new("ShaderNodeMixRGB")
    speck.blend_type = "OVERLAY"
    speck.inputs["Fac"].default_value = 0.22
    speck.location = (20, 120)
    nt.links.new(tone.outputs["Color"], speck.inputs["Color1"])
    nt.links.new(fine.outputs["Color"], speck.inputs["Color2"])
    nt.links.new(speck.outputs["Color"], bsdf.inputs["Base Color"])

    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.location = (20, -260)
    rr.inputs["To Min"].default_value = rough[0]
    rr.inputs["To Max"].default_value = rough[1]
    nt.links.new(fine.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], bsdf.inputs["Roughness"])

    bumpn = nt.nodes.new("ShaderNodeBump")
    bumpn.location = (60, -520)
    bumpn.inputs["Strength"].default_value = bump
    bumpn.inputs["Distance"].default_value = 0.05
    mixh = nt.nodes.new("ShaderNodeMixRGB")
    mixh.blend_type = "MIX"
    mixh.inputs["Fac"].default_value = 0.35
    mixh.location = (-200, -560)
    nt.links.new(b.outputs["Fac"], mixh.inputs["Color1"])
    nt.links.new(fine.outputs["Fac"], mixh.inputs["Color2"])
    nt.links.new(mixh.outputs["Color"], bumpn.inputs["Height"])
    nt.links.new(bumpn.outputs["Normal"], bsdf.inputs["Normal"])
    _set(bsdf, "Specular IOR Level", 0.28)
    return mat


def procedural_plaster(name, *, base, patch, crack=None, rough=(0.72, 0.95),
                       bump=0.22, scale=3.2):
    mat, nt, bsdf = _fresh(name)
    uv = _uv(nt)
    broad = _noise(nt, uv, scale=scale, detail=6.0, roughness=0.62, loc=(-700, 120))
    fine = _noise(nt, uv, scale=42.0, detail=3.0, loc=(-700, -180))
    col = _ramp(nt, broad.outputs["Fac"],
                [(0.28, patch), (0.62, base), (0.88, base)], loc=(-420, 120))
    speck = nt.nodes.new("ShaderNodeMixRGB")
    speck.blend_type = "OVERLAY"
    speck.inputs["Fac"].default_value = 0.10
    speck.location = (-140, 120)
    nt.links.new(col.outputs["Color"], speck.inputs["Color1"])
    nt.links.new(fine.outputs["Color"], speck.inputs["Color2"])
    out_color = speck.outputs["Color"]

    if crack is not None:
        veins = nt.nodes.new("ShaderNodeTexVoronoi")
        veins.location = (-700, -460)
        veins.feature = "DISTANCE_TO_EDGE"
        veins.inputs["Scale"].default_value = 5.5
        nt.links.new(uv.outputs["UV"], veins.inputs["Vector"])
        vr = _ramp(nt, veins.outputs["Distance"],
                   [(0.0, crack), (0.05, (1, 1, 1, 1))], loc=(-420, -460))
        cm = nt.nodes.new("ShaderNodeMixRGB")
        cm.blend_type = "MULTIPLY"
        cm.inputs["Fac"].default_value = 0.6
        cm.location = (100, 60)
        nt.links.new(out_color, cm.inputs["Color1"])
        nt.links.new(vr.outputs["Color"], cm.inputs["Color2"])
        out_color = cm.outputs["Color"]

    nt.links.new(out_color, bsdf.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.location = (100, -240)
    rr.inputs["To Min"].default_value = rough[0]
    rr.inputs["To Max"].default_value = rough[1]
    nt.links.new(broad.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], bsdf.inputs["Roughness"])
    bn = nt.nodes.new("ShaderNodeBump")
    bn.location = (100, -500)
    bn.inputs["Strength"].default_value = bump
    nt.links.new(fine.outputs["Fac"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
    _set(bsdf, "Specular IOR Level", 0.20)
    return mat


def procedural_timber(name, *, base, dark, rough=(0.48, 0.86), bump=0.45,
                      grain=90.0, aspect=0.06):
    """Anisotropic grain: noise squashed hard along one UV axis."""
    mat, nt, bsdf = _fresh(name)
    uv = _uv(nt)
    map_node = nt.nodes.new("ShaderNodeMapping")
    map_node.location = (-900, 0)
    map_node.inputs["Scale"].default_value = (1.0, aspect, 1.0)
    nt.links.new(uv.outputs["UV"], map_node.inputs["Vector"])

    n = nt.nodes.new("ShaderNodeTexNoise")
    n.location = (-700, 0)
    n.inputs["Scale"].default_value = grain
    n.inputs["Detail"].default_value = 8.0
    nt.links.new(map_node.outputs["Vector"], n.inputs["Vector"])
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.location = (-700, -260)
    wave.wave_type = "BANDS"
    wave.bands_direction = "Y"
    wave.inputs["Scale"].default_value = 5.0
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 3.0
    nt.links.new(uv.outputs["UV"], wave.inputs["Vector"])

    mixf = nt.nodes.new("ShaderNodeMixRGB")
    mixf.blend_type = "MIX"
    mixf.inputs["Fac"].default_value = 0.45
    mixf.location = (-460, -120)
    nt.links.new(wave.outputs["Fac"], mixf.inputs["Color1"])
    nt.links.new(n.outputs["Fac"], mixf.inputs["Color2"])
    col = _ramp(nt, mixf.outputs["Color"], [(0.18, dark), (0.72, base)],
                loc=(-220, 0))
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.location = (-220, -300)
    rr.inputs["To Min"].default_value = rough[0]
    rr.inputs["To Max"].default_value = rough[1]
    nt.links.new(mixf.outputs["Color"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], bsdf.inputs["Roughness"])
    bn = nt.nodes.new("ShaderNodeBump")
    bn.location = (0, -420)
    bn.inputs["Strength"].default_value = bump
    nt.links.new(mixf.outputs["Color"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
    _set(bsdf, "Specular IOR Level", 0.25)
    return mat


def procedural_metal(name, *, base, rough=(0.24, 0.62), bump=0.30,
                     metallic=0.92, pit=40.0):
    mat, nt, bsdf = _fresh(name)
    uv = _uv(nt)
    n = _noise(nt, uv, scale=pit, detail=7.0, loc=(-700, 0))
    corrode = _noise(nt, uv, scale=3.0, detail=5.0, roughness=0.7, loc=(-700, -300))
    col = _ramp(nt, corrode.outputs["Fac"],
                [(0.30, (base[0] * 0.45, base[1] * 0.40, base[2] * 0.34, 1)),
                 (0.74, base)], loc=(-420, -120))
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.location = (-200, -300)
    rr.inputs["To Min"].default_value = rough[0]
    rr.inputs["To Max"].default_value = rough[1]
    nt.links.new(corrode.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], bsdf.inputs["Roughness"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.location = (-200, -460)
    mr.inputs["To Min"].default_value = metallic * 0.55
    mr.inputs["To Max"].default_value = metallic
    nt.links.new(corrode.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], bsdf.inputs["Metallic"])
    bn = nt.nodes.new("ShaderNodeBump")
    bn.location = (0, -560)
    bn.inputs["Strength"].default_value = bump
    nt.links.new(n.outputs["Fac"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def procedural_paint(name, *, base, worn, rough=(0.30, 0.70), bump=0.14,
                     wear=0.35, scale=7.0):
    """Painted wood: colour on top of an exposed-substrate mask."""
    mat, nt, bsdf = _fresh(name)
    uv = _uv(nt)
    chip = _noise(nt, uv, scale=scale, detail=9.0, roughness=0.72, loc=(-700, 0))
    mask = _ramp(nt, chip.outputs["Fac"],
                 [(0.42 + (1.0 - wear) * 0.12, (0, 0, 0, 1)),
                  (0.56 + (1.0 - wear) * 0.12, (1, 1, 1, 1))], loc=(-460, 0))
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.location = (-200, 0)
    mix.inputs["Color1"].default_value = worn
    mix.inputs["Color2"].default_value = base
    nt.links.new(mask.outputs["Color"], mix.inputs["Fac"])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.location = (-200, -260)
    rr.inputs["To Min"].default_value = rough[0]
    rr.inputs["To Max"].default_value = rough[1]
    nt.links.new(mask.outputs["Color"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], bsdf.inputs["Roughness"])
    bn = nt.nodes.new("ShaderNodeBump")
    bn.location = (0, -460)
    bn.inputs["Strength"].default_value = bump
    nt.links.new(chip.outputs["Fac"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
    _set(bsdf, "Specular IOR Level", 0.42)
    return mat


def procedural_glass(name, *, tint, rough=0.16, emission=None, emit_strength=0.0):
    """Dark leaded glazing. Opaque on purpose: transmissive glass bakes badly."""
    mat, nt, bsdf = _fresh(name)
    uv = _uv(nt)
    n = _noise(nt, uv, scale=14.0, detail=4.0, loc=(-700, 0))
    col = _ramp(nt, n.outputs["Fac"],
                [(0.30, (tint[0] * 0.5, tint[1] * 0.5, tint[2] * 0.6, 1)),
                 (0.80, tint)], loc=(-440, 0))
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    _set(bsdf, "Roughness", rough)
    _set(bsdf, "Specular IOR Level", 0.85)
    if emission is not None and emit_strength > 0:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = emission
        elif "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = emission
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emit_strength
    return mat


def procedural_cloth(name, *, base, shade, rough=0.88, weave=140.0, bump=0.30):
    mat, nt, bsdf = _fresh(name)
    uv = _uv(nt)
    w = nt.nodes.new("ShaderNodeTexWave")
    w.location = (-700, 0)
    w.wave_type = "BANDS"
    w.inputs["Scale"].default_value = weave
    w.inputs["Distortion"].default_value = 0.4
    nt.links.new(uv.outputs["UV"], w.inputs["Vector"])
    fade = _noise(nt, uv, scale=2.4, detail=4.0, loc=(-700, -280))
    col = _ramp(nt, fade.outputs["Fac"], [(0.25, shade), (0.80, base)],
                loc=(-440, -160))
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    _set(bsdf, "Roughness", rough)
    _set(bsdf, "Specular IOR Level", 0.12)
    bn = nt.nodes.new("ShaderNodeBump")
    bn.location = (0, -400)
    bn.inputs["Strength"].default_value = bump
    nt.links.new(w.outputs["Fac"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def procedural_paving(name, *, stone, joint, wet=None, scale=1.0, rough=(0.42, 0.90)):
    mat, nt, bsdf = _fresh(name)
    uv = _uv(nt)
    v = nt.nodes.new("ShaderNodeTexVoronoi")
    v.location = (-760, 0)
    v.feature = "DISTANCE_TO_EDGE"
    v.inputs["Scale"].default_value = scale
    nt.links.new(uv.outputs["UV"], v.inputs["Vector"])
    vc = nt.nodes.new("ShaderNodeTexVoronoi")
    vc.location = (-760, -260)
    vc.feature = "F1"
    vc.inputs["Scale"].default_value = scale
    nt.links.new(uv.outputs["UV"], vc.inputs["Vector"])

    joints = _ramp(nt, v.outputs["Distance"],
                   [(0.0, joint), (0.045, stone)], loc=(-500, 0))
    variance = _ramp(nt, vc.outputs["Color"] if "Color" in vc.outputs else vc.outputs["Distance"],
                     [(0.20, (0.72, 0.70, 0.68, 1)), (0.85, (1.06, 1.04, 1.02, 1))],
                     loc=(-500, -260))
    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs["Fac"].default_value = 0.8
    mul.location = (-240, 0)
    nt.links.new(joints.outputs["Color"], mul.inputs["Color1"])
    nt.links.new(variance.outputs["Color"], mul.inputs["Color2"])
    out_color = mul.outputs["Color"]

    grit = _noise(nt, uv, scale=60.0, detail=6.0, loc=(-760, -520))
    ov = nt.nodes.new("ShaderNodeMixRGB")
    ov.blend_type = "OVERLAY"
    ov.inputs["Fac"].default_value = 0.16
    ov.location = (-20, 40)
    nt.links.new(out_color, ov.inputs["Color1"])
    nt.links.new(grit.outputs["Color"], ov.inputs["Color2"])
    out_color = ov.outputs["Color"]

    if wet is not None:
        pools = _noise(nt, uv, scale=1.1, detail=3.0, roughness=0.8, loc=(-760, -760))
        pm = _ramp(nt, pools.outputs["Fac"],
                   [(0.42, (1, 1, 1, 1)), (0.52, (0, 0, 0, 1))], loc=(-500, -760))
        dark = nt.nodes.new("ShaderNodeMixRGB")
        dark.location = (200, 40)
        dark.inputs["Color2"].default_value = wet
        nt.links.new(pm.outputs["Color"], dark.inputs["Fac"])
        nt.links.new(out_color, dark.inputs["Color1"])
        out_color = dark.outputs["Color"]

    nt.links.new(out_color, bsdf.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.location = (-20, -300)
    rr.inputs["To Min"].default_value = rough[0]
    rr.inputs["To Max"].default_value = rough[1]
    nt.links.new(grit.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], bsdf.inputs["Roughness"])
    bn = nt.nodes.new("ShaderNodeBump")
    bn.location = (-20, -560)
    bn.inputs["Strength"].default_value = 0.55
    bn.inputs["Distance"].default_value = 0.03
    nt.links.new(v.outputs["Distance"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
    _set(bsdf, "Specular IOR Level", 0.30)
    return mat


def procedural_roof(name, *, base, dark, moss=None, course=0.22, rough=(0.55, 0.92)):
    mat, nt, bsdf = _fresh(name)
    uv = _uv(nt)
    b = _brick(nt, uv, scale=1.0, mortar=0.012, row_h=course, squash=0.55)
    b.inputs["Color1"].default_value = base
    b.inputs["Color2"].default_value = dark
    b.inputs["Mortar"].default_value = (dark[0] * 0.6, dark[1] * 0.6, dark[2] * 0.6, 1)
    weather = _noise(nt, uv, scale=2.2, detail=6.0, roughness=0.7, loc=(-700, -280))
    wr = _ramp(nt, weather.outputs["Fac"],
               [(0.32, (0.6, 0.62, 0.58, 1)), (0.80, (1.05, 1.02, 1.0, 1))],
               loc=(-440, -280))
    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs["Fac"].default_value = 0.75
    mul.location = (-180, 0)
    nt.links.new(b.outputs["Color"], mul.inputs["Color1"])
    nt.links.new(wr.outputs["Color"], mul.inputs["Color2"])
    out_color = mul.outputs["Color"]
    if moss is not None:
        m = _noise(nt, uv, scale=6.0, detail=8.0, roughness=0.8, loc=(-700, -560))
        mm = _ramp(nt, m.outputs["Fac"],
                   [(0.55, (0, 0, 0, 1)), (0.72, (1, 1, 1, 1))], loc=(-440, -560))
        mx = nt.nodes.new("ShaderNodeMixRGB")
        mx.location = (60, 0)
        mx.inputs["Color2"].default_value = moss
        nt.links.new(mm.outputs["Color"], mx.inputs["Fac"])
        nt.links.new(out_color, mx.inputs["Color1"])
        out_color = mx.outputs["Color"]
    nt.links.new(out_color, bsdf.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.location = (60, -300)
    rr.inputs["To Min"].default_value = rough[0]
    rr.inputs["To Max"].default_value = rough[1]
    nt.links.new(weather.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], bsdf.inputs["Roughness"])
    bn = nt.nodes.new("ShaderNodeBump")
    bn.location = (60, -540)
    bn.inputs["Strength"].default_value = 0.5
    nt.links.new(b.outputs["Fac"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
    _set(bsdf, "Specular IOR Level", 0.24)
    return mat


def procedural_grime(name, *, base_material_color, grime_color, coverage=0.45,
                     rough=0.94):
    """A standalone grime/moss surface for sills, gutter lines and bases."""
    mat, nt, bsdf = _fresh(name)
    uv = _uv(nt)
    n = _noise(nt, uv, scale=9.0, detail=9.0, roughness=0.78, loc=(-700, 0))
    mask = _ramp(nt, n.outputs["Fac"],
                 [(0.62 - coverage * 0.4, (0, 0, 0, 1)),
                  (0.78 - coverage * 0.3, (1, 1, 1, 1))], loc=(-460, 0))
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.location = (-200, 0)
    mix.inputs["Color1"].default_value = base_material_color
    mix.inputs["Color2"].default_value = grime_color
    nt.links.new(mask.outputs["Color"], mix.inputs["Fac"])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    _set(bsdf, "Roughness", rough)
    _set(bsdf, "Specular IOR Level", 0.10)
    bn = nt.nodes.new("ShaderNodeBump")
    bn.location = (0, -300)
    bn.inputs["Strength"].default_value = 0.35
    nt.links.new(n.outputs["Fac"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# --------------------------------------------------------------------------
# displacement textures
# --------------------------------------------------------------------------

def height_texture(name, image_path):
    """Legacy image texture for the Displace modifier (UV coords, metre tile)."""
    tex = bpy.data.textures.get(name)
    if tex is None:
        tex = bpy.data.textures.new(name, type="IMAGE")
    tex.image = _load_image(image_path, non_color=True)
    tex.extension = "REPEAT"
    tex.use_interpolation = True
    return tex


def procedural_height_texture(name, *, kind="CLOUDS", size=0.35, depth=6):
    tex = bpy.data.textures.get(name)
    if tex is None:
        tex = bpy.data.textures.new(name, type=kind)
    if kind == "CLOUDS":
        tex.noise_scale = size
        tex.noise_depth = depth
    return tex
