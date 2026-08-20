"""Strategy A: procedural Blender town materials.

Each builder returns a Principled BSDF material whose relief is driven into a
Bump node, matching the interface of the library and generated builders so the
three strategies are interchangeable in a scene.

Colour note
-----------
Blender colour socket ``default_value`` is LINEAR. Authoring the palette in
sRGB numbers and assigning them straight to sockets renders roughly twice as
bright and noticeably desaturated -- that is what made the first micro-gauntlet
pass read as pale graybox. Every authored colour therefore goes through
``_srgb`` so the numbers below mean what a painter would expect.
"""
from __future__ import annotations

import bpy

from materials import _fresh, _core, _bump


def _c(v: float) -> float:
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _srgb(r, g, b, a=1.0):
    """Author in sRGB, store linear."""
    return (_c(r), _c(g), _c(b), a)


def _ramp(nt, fac_out, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    ramp = r.color_ramp
    while len(ramp.elements) > len(stops):
        ramp.elements.remove(ramp.elements[-1])
    for i, (pos, col) in enumerate(stops):
        el = ramp.elements[i] if i < len(ramp.elements) else ramp.elements.new(pos)
        el.position = pos
        el.color = col
    nt.links.new(fac_out, r.inputs["Fac"])
    return r


def _noise(nt, mp, scale, detail=6.0, roughness=0.5, vector=None):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = roughness
    nt.links.new(vector if vector is not None else mp.outputs["Vector"], n.inputs["Vector"])
    return n


def _tag(mat, ident):
    mat["th_source_strategy"] = "procedural"
    mat["th_source_id"] = "procedural:" + ident
    return mat


def proc_stone_blocks(*, scale=1.0, bump=0.6, name="PROC_stone_blocks"):
    """Coursed ashlar: per-block tone, mortar recess, chipped edges, damp staining."""
    mat = _fresh(name)
    nt, out, bsdf, mp = _core(mat, scale)

    # warp the lookup slightly so courses are not machine-straight
    warp = _noise(nt, mp, 6.0, detail=3.0)
    wadd = nt.nodes.new("ShaderNodeVectorMath")
    wadd.operation = "ADD"
    nt.links.new(mp.outputs["Vector"], wadd.inputs[0])
    wscale = nt.nodes.new("ShaderNodeVectorMath")
    wscale.operation = "SCALE"
    wscale.inputs["Scale"].default_value = 0.012
    nt.links.new(warp.outputs["Color"], wscale.inputs[0])
    nt.links.new(wscale.outputs["Vector"], wadd.inputs[1])
    vec = wadd.outputs["Vector"]

    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.5
    brick.squash = 1.0
    brick.inputs["Scale"].default_value = 3.0
    brick.inputs["Mortar Size"].default_value = 0.020
    brick.inputs["Mortar Smooth"].default_value = 0.20
    brick.inputs["Brick Width"].default_value = 0.62
    brick.inputs["Row Height"].default_value = 0.26
    # a real wall is not two tones; the ramp below adds the rest
    brick.inputs["Color1"].default_value = _srgb(0.62, 0.53, 0.40)
    brick.inputs["Color2"].default_value = _srgb(0.50, 0.43, 0.33)
    brick.inputs["Mortar"].default_value = _srgb(0.40, 0.38, 0.34)
    nt.links.new(vec, brick.inputs["Vector"])

    # per-block tonal drift: large voronoi keyed off the same warped vector
    blockvar = nt.nodes.new("ShaderNodeTexVoronoi")
    blockvar.feature = "F1"
    blockvar.inputs["Scale"].default_value = 26.0
    nt.links.new(vec, blockvar.inputs["Vector"])
    bvar = _ramp(nt, blockvar.outputs["Color"],
                 [(0.15, _srgb(0.78, 0.74, 0.66)),
                  (0.50, _srgb(1.00, 0.97, 0.92)),
                  (0.88, _srgb(0.88, 0.84, 0.72))])

    tint = nt.nodes.new("ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    tint.inputs["Factor"].default_value = 0.55
    nt.links.new(brick.outputs["Color"], tint.inputs[6])
    nt.links.new(bvar.outputs["Color"], tint.inputs[7])

    # damp staining: sparse, soft, only in some regions -- keeps quiet areas quiet
    damp = _noise(nt, mp, 2.6, detail=5.0)
    dramp = _ramp(nt, damp.outputs["Fac"],
                  [(0.46, _srgb(0.55, 0.54, 0.50)), (0.74, (1.0, 1.0, 1.0, 1.0))])
    stain = nt.nodes.new("ShaderNodeMix")
    stain.data_type = "RGBA"
    stain.blend_type = "MULTIPLY"
    stain.inputs["Factor"].default_value = 0.55
    nt.links.new(tint.outputs[2], stain.inputs[6])
    nt.links.new(dramp.outputs["Color"], stain.inputs[7])
    nt.links.new(stain.outputs[2], bsdf.inputs["Base Color"])

    grit = _noise(nt, mp, 260.0, detail=8.0)
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.66
    rr.inputs["To Max"].default_value = 0.95
    nt.links.new(grit.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], bsdf.inputs["Roughness"])

    # height: deep mortar, mild per-block proudness, fine grit
    hm = nt.nodes.new("ShaderNodeMix")
    hm.data_type = "FLOAT"
    hm.inputs["Factor"].default_value = 0.18
    nt.links.new(brick.outputs["Fac"], hm.inputs[2])
    nt.links.new(grit.outputs["Fac"], hm.inputs[3])
    _bump(nt, bsdf, hm.outputs[0], bump)
    return _tag(mat, "stone_blocks")


def proc_plaster(*, scale=1.0, bump=0.25, name="PROC_plaster",
                 base=(0.80, 0.73, 0.59)):
    """Lime stucco: trowel waves, SPARSE cracks, patchy wash, fine tooth.

    The first pass used a dense distance-to-edge voronoi, which reads as a
    regular crazed-ceramic net -- the classic procedural tell. Cracks here are
    thresholded hard and masked by a low-frequency noise so most of the wall has
    none at all.
    """
    mat = _fresh(name)
    nt, out, bsdf, mp = _core(mat, scale)

    wave = _noise(nt, mp, 7.0, detail=4.0, roughness=0.6)
    fine = _noise(nt, mp, 190.0, detail=6.0)

    crack = nt.nodes.new("ShaderNodeTexVoronoi")
    crack.feature = "DISTANCE_TO_EDGE"
    crack.inputs["Scale"].default_value = 16.0
    nt.links.new(mp.outputs["Vector"], crack.inputs["Vector"])
    cramp = _ramp(nt, crack.outputs["Distance"],
                  [(0.0, (0.0, 0.0, 0.0, 1.0)), (0.018, (1.0, 1.0, 1.0, 1.0))])

    # only let cracks exist where a big soft noise says so
    where = _noise(nt, mp, 2.2, detail=3.0)
    gate = _ramp(nt, where.outputs["Fac"],
                 [(0.48, (1.0, 1.0, 1.0, 1.0)), (0.62, (0.0, 0.0, 0.0, 1.0))])
    gated = nt.nodes.new("ShaderNodeMix")
    gated.data_type = "RGBA"
    gated.blend_type = "SCREEN"
    gated.inputs["Factor"].default_value = 1.0
    nt.links.new(cramp.outputs["Color"], gated.inputs[6])
    nt.links.new(gate.outputs["Color"], gated.inputs[7])

    col = _ramp(nt, wave.outputs["Fac"],
                [(0.30, _srgb(base[0] * 0.78, base[1] * 0.77, base[2] * 0.74)),
                 (0.70, _srgb(*base))])
    shade = nt.nodes.new("ShaderNodeMix")
    shade.data_type = "RGBA"
    shade.blend_type = "MULTIPLY"
    shade.inputs["Factor"].default_value = 0.9
    nt.links.new(col.outputs["Color"], shade.inputs[6])
    nt.links.new(gated.outputs[2], shade.inputs[7])
    nt.links.new(shade.outputs[2], bsdf.inputs["Base Color"])

    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.74
    rr.inputs["To Max"].default_value = 0.94
    nt.links.new(fine.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], bsdf.inputs["Roughness"])

    hm = nt.nodes.new("ShaderNodeMix")
    hm.data_type = "FLOAT"
    hm.inputs["Factor"].default_value = 0.35
    nt.links.new(wave.outputs["Fac"], hm.inputs[2])
    nt.links.new(gated.outputs[2], hm.inputs[3])
    _bump(nt, bsdf, hm.outputs[0], bump)
    return _tag(mat, "plaster")


def proc_cobblestone(*, scale=1.0, bump=0.85, name="PROC_cobblestone"):
    """Rounded setts with dirt and moss packed into the joints only.

    The first pass drove the moss mix from the inverted joint mask across the
    whole surface, which washed every sett pale green. Moss is now confined to
    a narrow band around the cell edges and modulated by a patch noise, so most
    setts are bare stone.
    """
    mat = _fresh(name)
    nt, out, bsdf, mp = _core(mat, scale)

    cells = nt.nodes.new("ShaderNodeTexVoronoi")
    cells.feature = "F1"
    cells.inputs["Scale"].default_value = 13.0
    cells.inputs["Randomness"].default_value = 0.9
    nt.links.new(mp.outputs["Vector"], cells.inputs["Vector"])

    edge = nt.nodes.new("ShaderNodeTexVoronoi")
    edge.feature = "DISTANCE_TO_EDGE"
    edge.inputs["Scale"].default_value = 13.0
    edge.inputs["Randomness"].default_value = 0.9
    nt.links.new(mp.outputs["Vector"], edge.inputs["Vector"])

    # per-sett stone colour: mid grey granite with warm and dark outliers
    stone = _ramp(nt, cells.outputs["Color"],
                  [(0.06, _srgb(0.17, 0.16, 0.15)),
                   (0.34, _srgb(0.31, 0.29, 0.27)),
                   (0.62, _srgb(0.22, 0.21, 0.20)),
                   (0.90, _srgb(0.38, 0.33, 0.27))])

    # joint band: 1 only very close to a cell edge
    joint = _ramp(nt, edge.outputs["Distance"],
                  [(0.0, (1.0, 1.0, 1.0, 1.0)), (0.085, (0.0, 0.0, 0.0, 1.0))])
    patch = _noise(nt, mp, 3.4, detail=5.0)
    pgate = _ramp(nt, patch.outputs["Fac"],
                  [(0.44, (0.0, 0.0, 0.0, 1.0)), (0.66, (1.0, 1.0, 1.0, 1.0))])
    mossfac = nt.nodes.new("ShaderNodeMath")
    mossfac.operation = "MULTIPLY"
    nt.links.new(joint.outputs["Color"], mossfac.inputs[0])
    nt.links.new(pgate.outputs["Color"], mossfac.inputs[1])

    moss = nt.nodes.new("ShaderNodeMix")
    moss.data_type = "RGBA"
    moss.inputs[7].default_value = _srgb(0.16, 0.19, 0.11)
    nt.links.new(stone.outputs["Color"], moss.inputs[6])
    nt.links.new(mossfac.outputs[0], moss.inputs["Factor"])
    nt.links.new(moss.outputs[2], bsdf.inputs["Base Color"])

    grit = _noise(nt, mp, 340.0)
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.40
    rr.inputs["To Max"].default_value = 0.82
    nt.links.new(grit.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], bsdf.inputs["Roughness"])

    dome = _ramp(nt, edge.outputs["Distance"],
                 [(0.0, (0.0, 0.0, 0.0, 1.0)), (0.20, (1.0, 1.0, 1.0, 1.0))])
    hm = nt.nodes.new("ShaderNodeMix")
    hm.data_type = "FLOAT"
    hm.inputs["Factor"].default_value = 0.10
    nt.links.new(dome.outputs["Color"], hm.inputs[2])
    nt.links.new(grit.outputs["Fac"], hm.inputs[3])
    _bump(nt, bsdf, hm.outputs[0], bump)
    return _tag(mat, "cobblestone")


def proc_wood(*, scale=1.0, bump=0.45, name="PROC_wood",
              base=(0.36, 0.24, 0.15), plank_rows=7.0):
    """Aged planks: per-board tone, hard stretched grain, dark gaps, grey wear."""
    mat = _fresh(name)
    nt, out, bsdf, mp = _core(mat, scale)

    planks = nt.nodes.new("ShaderNodeTexBrick")
    planks.inputs["Scale"].default_value = 1.0
    planks.inputs["Brick Width"].default_value = 2.4
    planks.inputs["Row Height"].default_value = 1.0 / plank_rows
    planks.inputs["Mortar Size"].default_value = 0.008
    planks.inputs["Color1"].default_value = _srgb(*base)
    planks.inputs["Color2"].default_value = _srgb(min(base[0] * 1.4, 1.0),
                                                 min(base[1] * 1.35, 1.0),
                                                 min(base[2] * 1.3, 1.0))
    planks.inputs["Mortar"].default_value = _srgb(0.06, 0.045, 0.035)
    nt.links.new(mp.outputs["Vector"], planks.inputs["Vector"])

    stretch = nt.nodes.new("ShaderNodeMapping")
    stretch.inputs["Scale"].default_value = (1.0, 55.0, 1.0)
    nt.links.new(mp.outputs["Vector"], stretch.inputs["Vector"])
    grain = _noise(nt, mp, 12.0, detail=9.0, vector=stretch.outputs["Vector"])

    gr = _ramp(nt, grain.outputs["Fac"],
               [(0.26, _srgb(0.42, 0.38, 0.34)),
                (0.52, (1.0, 1.0, 1.0, 1.0)),
                (0.80, _srgb(0.70, 0.66, 0.62))])
    gm = nt.nodes.new("ShaderNodeMix")
    gm.data_type = "RGBA"
    gm.blend_type = "MULTIPLY"
    gm.inputs["Factor"].default_value = 0.85
    nt.links.new(planks.outputs["Color"], gm.inputs[6])
    nt.links.new(gr.outputs["Color"], gm.inputs[7])

    # silvered weathering on exposed boards
    weather = _noise(nt, mp, 3.0, detail=4.0)
    wramp = _ramp(nt, weather.outputs["Fac"],
                  [(0.50, (0.0, 0.0, 0.0, 1.0)), (0.72, (1.0, 1.0, 1.0, 1.0))])
    silver = nt.nodes.new("ShaderNodeMix")
    silver.data_type = "RGBA"
    silver.inputs[7].default_value = _srgb(0.52, 0.50, 0.46)
    nt.links.new(gm.outputs[2], silver.inputs[6])
    nt.links.new(wramp.outputs["Color"], silver.inputs["Factor"])
    nt.links.new(silver.outputs[2], bsdf.inputs["Base Color"])

    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.62
    rr.inputs["To Max"].default_value = 0.93
    nt.links.new(grain.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], bsdf.inputs["Roughness"])

    hm = nt.nodes.new("ShaderNodeMix")
    hm.data_type = "FLOAT"
    hm.inputs["Factor"].default_value = 0.45
    nt.links.new(planks.outputs["Fac"], hm.inputs[2])
    nt.links.new(grain.outputs["Fac"], hm.inputs[3])
    _bump(nt, bsdf, hm.outputs[0], bump)
    return _tag(mat, "wood")


def proc_roof_tile(*, scale=1.0, bump=0.9, name="PROC_roof_tile"):
    """Overlapping barrel tiles.

    The first pass produced flat rectangles because the row grid carried all the
    relief. The barrel profile now comes from a sine wave across X, and the rows
    only cut the overlap step, which is what actually makes tiles read as tiles.
    """
    mat = _fresh(name)
    nt, out, bsdf, mp = _core(mat, scale)

    barrel = nt.nodes.new("ShaderNodeTexWave")
    barrel.wave_type = "BANDS"
    barrel.bands_direction = "X"
    barrel.wave_profile = "SIN"
    barrel.inputs["Scale"].default_value = 3.5
    barrel.inputs["Distortion"].default_value = 0.6
    barrel.inputs["Detail"].default_value = 2.0
    nt.links.new(mp.outputs["Vector"], barrel.inputs["Vector"])

    rows = nt.nodes.new("ShaderNodeTexBrick")
    rows.inputs["Scale"].default_value = 1.0
    rows.inputs["Brick Width"].default_value = 0.143
    rows.inputs["Row Height"].default_value = 0.115
    rows.inputs["Mortar Size"].default_value = 0.012
    rows.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1.0)
    rows.inputs["Color2"].default_value = (1.0, 1.0, 1.0, 1.0)
    rows.inputs["Mortar"].default_value = (0.0, 0.0, 0.0, 1.0)
    nt.links.new(mp.outputs["Vector"], rows.inputs["Vector"])

    # per-tile clay colour keyed off the row/column cell
    tilevar = nt.nodes.new("ShaderNodeTexVoronoi")
    tilevar.inputs["Scale"].default_value = 22.0
    nt.links.new(mp.outputs["Vector"], tilevar.inputs["Vector"])
    clay = _ramp(nt, tilevar.outputs["Color"],
                 [(0.10, _srgb(0.42, 0.20, 0.12)),
                  (0.40, _srgb(0.54, 0.28, 0.16)),
                  (0.70, _srgb(0.36, 0.19, 0.13)),
                  (0.92, _srgb(0.47, 0.29, 0.19))])

    # barrel shading darkens the trough side, lichen greys the north faces
    shade = _ramp(nt, barrel.outputs["Fac"],
                  [(0.10, _srgb(0.62, 0.60, 0.56)), (0.72, (1.0, 1.0, 1.0, 1.0))])
    cm = nt.nodes.new("ShaderNodeMix")
    cm.data_type = "RGBA"
    cm.blend_type = "MULTIPLY"
    cm.inputs["Factor"].default_value = 0.75
    nt.links.new(clay.outputs["Color"], cm.inputs[6])
    nt.links.new(shade.outputs["Color"], cm.inputs[7])

    lich = _noise(nt, mp, 14.0, detail=7.0)
    lr = _ramp(nt, lich.outputs["Fac"],
               [(0.60, (0.0, 0.0, 0.0, 1.0)), (0.76, (1.0, 1.0, 1.0, 1.0))])
    lm = nt.nodes.new("ShaderNodeMix")
    lm.data_type = "RGBA"
    lm.inputs[7].default_value = _srgb(0.42, 0.44, 0.33)
    nt.links.new(cm.outputs[2], lm.inputs[6])
    nt.links.new(lr.outputs["Color"], lm.inputs["Factor"])
    nt.links.new(lm.outputs[2], bsdf.inputs["Base Color"])

    bsdf.inputs["Roughness"].default_value = 0.80
    hm = nt.nodes.new("ShaderNodeMix")
    hm.data_type = "FLOAT"
    hm.inputs["Factor"].default_value = 0.30
    nt.links.new(barrel.outputs["Fac"], hm.inputs[2])
    nt.links.new(rows.outputs["Fac"], hm.inputs[3])
    _bump(nt, bsdf, hm.outputs[0], bump)
    return _tag(mat, "roof_tile")


def proc_metal(*, scale=1.0, bump=0.4, name="PROC_metal"):
    """Tarnished wrought iron: dark metal with localised rust bloom.

    The first pass ramped the whole surface into pale tan cloud. Rust is now a
    hard-thresholded minority of the surface so the base stays dark iron.
    """
    mat = _fresh(name)
    nt, out, bsdf, mp = _core(mat, scale)

    pit = _noise(nt, mp, 55.0, detail=8.0)
    rust = _noise(nt, mp, 5.5, detail=7.0)

    rmask = _ramp(nt, rust.outputs["Fac"],
                  [(0.58, (0.0, 0.0, 0.0, 1.0)), (0.70, (1.0, 1.0, 1.0, 1.0))])

    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs[6].default_value = _srgb(0.085, 0.082, 0.080)   # dark iron
    col.inputs[7].default_value = _srgb(0.42, 0.20, 0.09)      # rust
    nt.links.new(rmask.outputs["Color"], col.inputs["Factor"])
    nt.links.new(col.outputs[2], bsdf.inputs["Base Color"])

    met = nt.nodes.new("ShaderNodeMix")
    met.data_type = "FLOAT"
    met.inputs[2].default_value = 0.90     # clean iron is metallic
    met.inputs[3].default_value = 0.05     # rust is not
    nt.links.new(rmask.outputs["Color"], met.inputs["Factor"])
    nt.links.new(met.outputs[0], bsdf.inputs["Metallic"])

    rgh = nt.nodes.new("ShaderNodeMix")
    rgh.data_type = "FLOAT"
    rgh.inputs[2].default_value = 0.38
    rgh.inputs[3].default_value = 0.85
    nt.links.new(rmask.outputs["Color"], rgh.inputs["Factor"])
    nt.links.new(rgh.outputs[0], bsdf.inputs["Roughness"])

    hm = nt.nodes.new("ShaderNodeMix")
    hm.data_type = "FLOAT"
    hm.inputs["Factor"].default_value = 0.5
    nt.links.new(pit.outputs["Fac"], hm.inputs[2])
    nt.links.new(rmask.outputs["Color"], hm.inputs[3])
    _bump(nt, bsdf, hm.outputs[0], bump)
    return _tag(mat, "metal")
