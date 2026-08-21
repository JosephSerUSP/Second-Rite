"""The clean-room material vocabulary.

Art direction this vocabulary serves
------------------------------------
Thestra is not a generic medieval town. Its signature is *one enormous, quiet,
older civic structure* with small, fussy, human-scaled domestic life wedged
into and against it. The material job is therefore contrast of grain, not
variety of colour:

  - a few very large, very quiet surfaces (civic stone, render, lead)
  - a few small, dense, detailed surfaces (boards, iron, cloth, glazing)

Restricted palette, deliberately: cold grey-green stone, warm bone limewash,
oxidised copper-green, dark oiled timber, and ONE saturated accent (madder red)
reserved for doors and cloth so the eye always knows where a door is.

Recurring motif: the tall narrow slot, roughly 1:4, repeated at wildly
different scales -- a drain, a window, a doorway, a gap between buildings.
A repeated *proportion*, never a repeated module.
"""
from __future__ import annotations

import os
from pathlib import Path

from . import mats
from .mats import hexc, register, Material

WORKSPACE = Path(os.environ.get(
    "CLEANROOM_WS",
    r"C:\Users\josep\AppData\Local\Temp\claude"
    r"\D--Antigravity-Hichaukitoden\73de4ba7-91ac-4d34-a1b0-a9aaff1ff989"
    r"\scratchpad\cleanroom"))
PUBLIC = WORKSPACE / "public"
GENERATED = WORKSPACE / "generated"

# ---- palette (sRGB, converted to linear on assignment) --------------------
STONE_COLD = hexc("7C8478")
STONE_DEEP = hexc("545B52")
STONE_PALE = hexc("9AA096")
BONE = hexc("D6CBB6")
BONE_PATCH = hexc("C0B39A")
VERDIGRIS = hexc("6FA08C")
VERDIGRIS_DEEP = hexc("3F5F53")
TIMBER = hexc("4A3B2E")
TIMBER_DEEP = hexc("2B211A")
MADDER = hexc("8C2F26")
MADDER_WORN = hexc("6A3B33")
LEAD = hexc("6E7276")
LEAD_DEEP = hexc("4A4E52")
GLASS = hexc("242C33")
CLOTH = hexc("B4A487")
CLOTH_SHADE = hexc("8A7C63")
GRIME = hexc("46443A")
MORTAR = hexc("A29B8C")
JOINT = hexc("3E3F3A")


def _img(root, stem, key):
    p = root / stem / ("%s_%s.png" % (stem, key)) if (root / stem).is_dir() \
        else root / ("%s_%s.png" % (stem, key))
    return str(p) if Path(p).is_file() else None


def _public(mid, slug, tile_m, *, tint=None, bump=0.4, rough_range=(0.35, 0.95),
            ao_strength=0.7, metallic=0.0, displaceable=False):
    alb = _img(PUBLIC, slug, "albedo")
    if alb is None:
        return None
    height = _img(PUBLIC, slug, "height")

    def build(name, _slug=slug, _tint=tint, _bump=bump, _rr=rough_range,
              _ao=ao_strength, _met=metallic):
        return mats.image_material(
            name,
            albedo=_img(PUBLIC, _slug, "albedo"),
            roughness=_img(PUBLIC, _slug, "roughness"),
            ao=_img(PUBLIC, _slug, "ao"),
            height=_img(PUBLIC, _slug, "height"),
            bump_strength=_bump, rough_range=_rr, tint=_tint,
            ao_strength=_ao, metallic=_met)

    prov = {"strategy": "public", "library": "Poly Haven", "slug": slug,
            "license": "CC0-1.0",
            "provenanceFile": str(PUBLIC / slug / "provenance.json")}
    return register(Material(mid, "public", tile_m, build,
                             height_path=height, provenance=prov,
                             displaceable=displaceable))


def _generated(mid, stem, tile_m, *, tint=None, bump=0.4,
               rough_range=(0.40, 0.95), displaceable=False):
    alb = _img(GENERATED, stem, "albedo")
    if alb is None:
        return None
    height = _img(GENERATED, stem, "height")

    def build(name, _stem=stem, _tint=tint, _bump=bump, _rr=rough_range):
        return mats.image_material(
            name,
            albedo=_img(GENERATED, _stem, "albedo"),
            roughness=_img(GENERATED, _stem, "roughness"),
            ao=_img(GENERATED, _stem, "ao"),
            height=_img(GENERATED, _stem, "height"),
            bump_strength=_bump, rough_range=_rr, tint=_tint)

    prov = {"strategy": "generated", "model": "gpt-image-2",
            "channels": "one flat albedo generated; height/ao/roughness "
                        "derived numerically (exact registration)",
            "metricsFile": str(GENERATED / ("%s_maps.json" % stem))}
    return register(Material(mid, "generated", tile_m, build,
                             height_path=height, provenance=prov,
                             displaceable=displaceable))


def _proc(mid, tile_m, builder, **kw):
    def build(name, _b=builder, _kw=kw):
        return _b(name, **_kw)
    return register(Material(mid, "procedural", tile_m, build,
                             provenance={"strategy": "procedural",
                                         "authored": "cleanroom/mats.py"}))


def build_vocabulary():
    """Register every material. Idempotent; safe to call per attempt."""
    mats.reset_registry()

    # ---- public CC0 scans (large quiet surfaces + one dense small one) ----
    _public("civic_ashlar", "castle_wall_slates", 2.50,
            tint=(0.86, 0.92, 0.86, 1.0), bump=0.55, rough_range=(0.42, 0.95),
            displaceable=True)
    _public("stone_mossy", "mossy_stone_wall", 2.00,
            tint=(0.86, 0.94, 0.86, 1.0), bump=0.75, rough_range=(0.55, 0.98),
            displaceable=True)
    _public("roof_lead", "grey_roof_tiles_02", 1.50,
            tint=(0.80, 0.84, 0.88, 1.0), bump=0.45, rough_range=(0.40, 0.88))
    _public("street_setts", "cobblestone_05", 2.40,
            tint=(0.80, 0.83, 0.80, 1.0), bump=0.60, rough_range=(0.45, 0.95),
            displaceable=True)
    _public("boards_dark", "dark_planks", 2.00,
            tint=(0.92, 0.90, 0.84, 1.0), bump=0.60, rough_range=(0.42, 0.92),
            displaceable=True)

    # ---- generated (flat albedo + numerically derived maps) --------------
    _generated("plaster_bone", "plaster_bone", 1.80, bump=0.52,
               rough_range=(0.60, 0.96), displaceable=True)
    _generated("stone_fine", "stone_ashlar_fine", 2.20, bump=0.75,
               rough_range=(0.42, 0.92), displaceable=True)
    _generated("plaster_verdigris", "plaster_verdigris", 1.60, bump=0.34,
               rough_range=(0.58, 0.96), displaceable=True)

    # ---- procedural (authored here, linear colour) ------------------------
    _proc("timber_dark", 1.10, mats.procedural_timber,
          base=TIMBER, dark=TIMBER_DEEP, bump=0.50, grain=110.0, aspect=0.05)
    _proc("paint_madder", 0.90, mats.procedural_paint,
          base=MADDER, worn=TIMBER_DEEP, wear=0.62, bump=0.30, scale=3.4)
    _proc("metal_verdigris", 0.70, mats.procedural_metal,
          base=VERDIGRIS, metallic=0.78, rough=(0.26, 0.86), bump=0.48, pit=18.0)
    _proc("glass_leaded", 0.55, mats.procedural_glass,
          tint=GLASS, rough=0.14)
    _proc("cloth_awning", 1.30, mats.procedural_cloth,
          base=CLOTH, shade=CLOTH_SHADE, weave=170.0, bump=0.28)
    _proc("grime_moss", 1.40, mats.procedural_grime,
          base_material_color=STONE_DEEP, grime_color=GRIME, coverage=0.50)
    _proc("limewash_pale", 1.70, mats.procedural_plaster,
          base=STONE_PALE, patch=BONE_PATCH, crack=None,
          bump=0.34, scale=2.4, rough=(0.68, 0.97))
    _proc("paving_granite", 1.60, mats.procedural_paving,
          stone=STONE_COLD, joint=JOINT, wet=None, scale=4.2, rough=(0.50, 0.94))
    _proc("roof_slate_proc", 1.20, mats.procedural_roof,
          base=LEAD, dark=LEAD_DEEP, moss=hexc("55604A"), course=0.20)

    return mats.all_materials()


def glazing_lit(name="glass_lit", warmth=hexc("FFB25E"), strength=2.2):
    """A one-off emissive glazing variant for a specific window."""
    def build(n):
        return mats.procedural_glass(n, tint=GLASS, rough=0.14,
                                     emission=warmth, emit_strength=strength)
    return register(Material(name, "procedural", 0.55, build,
                             provenance={"strategy": "procedural"}))
