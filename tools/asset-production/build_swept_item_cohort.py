"""Batch C: eight items authored as spatial gestures, sweeps and lofts.

This cohort is deliberately orthogonal to the two earlier experiments:

* Batch A (relic showcase): semantic parts assembled from lathed volumes.
* Batch B (polygonal cohort): 2D silhouettes extruded into thin fabricated solids.
* Batch C (this file): 3D paths carrying cross-sections through space.

The recipes emphasize bend, taper, twist, branching and closed loops. Geometry
comes only from ``sweep_parts``; ``lathe`` is reused as the common mesh/output
contract, not as a shape generator.
"""

from __future__ import annotations

import math
from pathlib import Path

import lathe
import sweep_parts as sweep

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "assets" / "models" / "items"
MTL_NAME = "swept_cohort.mtl"

GOLD = "ritual_gold"
BRONZE = "oxidized_bronze"
IRON = "wrought_iron"
CLOTH = "aged_cloth"
GLASS = "smoked_glass"
CRYSTAL = "crystal"
BONE = "bone"
WOOD = "dark_wood"
WET = "wet_residue"
WAX = "wax"

MATERIALS = sorted({GOLD, BRONZE, IRON, CLOTH, GLASS, CRYSTAL, BONE, WOOD, WET, WAX})


def _ellipse_loop(cx, cy, cz, rx, rz, *, tilt=0.0, points=12):
    """Ellipse in a tilted XZ-ish plane, suitable for swept chain/manacle loops."""
    result = []
    t = math.radians(tilt)
    for i in range(points):
        a = math.tau * i / points
        x = cx + rx * math.cos(a)
        y = cy + rz * math.sin(a) * math.sin(t)
        z = cz + rz * math.sin(a) * math.cos(t)
        result.append((x, y, z))
    return result


def water_scepter():
    """A staff whose upper half becomes a three-dimensional breaking wave."""
    shaft = sweep.sweep(
        [(-0.05, -1.05, 0.00), (-0.10, -0.55, 0.04), (-0.02, -0.12, -0.05),
         (0.08, 0.30, 0.07), (0.03, 0.72, 0.00)],
        scales=[0.075, 0.078, 0.070, 0.062, 0.055], sides=7,
        material=BRONZE, name="scepter_shaft",
    )
    left_wave = sweep.sweep(
        [(0.02, 0.64, 0.00), (-0.23, 0.80, 0.07), (-0.38, 1.03, 0.02),
         (-0.29, 1.27, -0.12), (-0.06, 1.36, -0.18), (0.10, 1.23, -0.10)],
        scales=[0.055, 0.062, 0.070, 0.060, 0.045, 0.022], sides=6,
        material=CRYSTAL, rolls=[0, 8, 18, 30, 45, 65], name="left_wave",
    )
    right_wave = sweep.sweep(
        [(0.01, 0.69, 0.02), (0.24, 0.82, -0.06), (0.39, 1.00, 0.02),
         (0.36, 1.22, 0.16), (0.18, 1.33, 0.23), (0.02, 1.22, 0.15)],
        scales=[0.050, 0.060, 0.068, 0.055, 0.040, 0.020], sides=6,
        material=CRYSTAL, rolls=[0, -10, -20, -32, -46, -60], name="right_wave",
    )
    pearl = sweep.sweep(
        [(0.00, 0.89, 0.02), (0.00, 1.02, 0.04), (0.01, 1.15, 0.08), (0.00, 1.27, 0.04)],
        scales=[0.045, 0.145, 0.125, 0.025], aspect=[(1.0, 0.85)] * 4,
        sides=8, material=GLASS, name="water_pearl",
    )
    gold_curl = sweep.sweep(
        [(-0.06, 0.73, 0.00), (-0.16, 0.94, 0.13), (-0.08, 1.14, 0.23),
         (0.10, 1.18, 0.22), (0.18, 1.05, 0.10)],
        scales=[0.025, 0.028, 0.030, 0.025, 0.015], sides=5,
        material=GOLD, name="gold_curl",
    )
    return lathe.merge("water_scepter", [shaft, left_wave, right_wave, pearl, gold_curl])


def _boot(xoff: float, mirror: float):
    body = sweep.sweep(
        [(xoff, -0.54, 0.45), (xoff, -0.50, 0.17), (xoff, -0.45, -0.10),
         (xoff, -0.25, -0.25), (xoff + 0.02 * mirror, 0.08, -0.27),
         (xoff + 0.04 * mirror, 0.43, -0.24)],
        scales=[0.22, 0.27, 0.25, 0.22, 0.20, 0.22],
        aspect=[(1.15, 0.72), (1.20, 0.68), (1.05, 0.72), (0.90, 0.85), (0.82, 0.92), (0.90, 0.95)],
        sides=8, rolls=[90, 90, 86, 72, 35, 12], material=CLOTH,
        name="boot_body",
    )
    sole = sweep.ribbon(
        [(xoff, -0.68, 0.48), (xoff, -0.65, 0.18), (xoff, -0.61, -0.12), (xoff, -0.52, -0.28)],
        widths=[0.34, 0.39, 0.34, 0.26], thickness=[0.055] * 4,
        rolls=[90, 90, 88, 78], material=IRON, name="boot_sole",
    )
    wing_parts = []
    origins = [(0.38, -0.02, -0.21, 0.42), (0.31, 0.10, -0.22, 0.33), (0.24, 0.20, -0.23, 0.25)]
    for i, (reach, y, z, rise) in enumerate(origins):
        side = mirror
        wing_parts.append(sweep.ribbon(
            [(xoff + 0.17 * side, y, z),
             (xoff + (0.17 + reach * 0.55) * side, y + rise * 0.45, z + 0.04),
             (xoff + (0.17 + reach) * side, y + rise, z + 0.01)],
            widths=[0.10, 0.075, 0.028], thickness=[0.045, 0.035, 0.018],
            rolls=[0, 15 * side, 28 * side], material=CRYSTAL, name=f"wing_{i}",
        ))
    ankle_wrap = sweep.loop(
        _ellipse_loop(xoff, -0.03, -0.26, 0.24, 0.18, tilt=75, points=10),
        radius=0.028, sides=5, material=GOLD, name="ankle_wrap",
    )
    return [body, sole, ankle_wrap, *wing_parts]


def hermes_boots():
    """A paired boot model grown along bent foot/ankle spines with swept wings."""
    return lathe.merge("hermes_boots", _boot(-0.24, -1.0) + _boot(0.24, 1.0))


def mimic_tongue():
    """A wet muscular ribbon that leaves the icon plane and curls toward camera."""
    tongue = sweep.ribbon(
        [(0.00, 0.82, -0.30), (-0.08, 0.58, -0.16), (0.04, 0.30, 0.02),
         (0.18, 0.02, 0.20), (0.05, -0.26, 0.38), (-0.13, -0.48, 0.31),
         (-0.05, -0.70, 0.12)],
        widths=[0.34, 0.38, 0.42, 0.39, 0.31, 0.20, 0.07],
        thickness=[0.12, 0.14, 0.16, 0.15, 0.12, 0.08, 0.035],
        rolls=[10, 18, 32, 46, 70, 95, 118], material=WET, name="tongue",
    )
    vein_l = sweep.sweep(
        [(-0.08, 0.70, -0.22), (-0.10, 0.38, -0.04), (0.05, 0.05, 0.17),
         (0.08, -0.30, 0.33), (-0.04, -0.56, 0.24)],
        scales=[0.018, 0.021, 0.022, 0.016, 0.008], sides=5,
        material=CRYSTAL, name="tongue_vein_l",
    )
    vein_r = sweep.sweep(
        [(0.08, 0.66, -0.24), (0.03, 0.36, -0.02), (0.12, 0.08, 0.16),
         (0.14, -0.18, 0.29)],
        scales=[0.015, 0.019, 0.016, 0.006], sides=5,
        material=CRYSTAL, name="tongue_vein_r",
    )
    drool = sweep.sweep(
        [(0.13, -0.14, 0.36), (0.18, -0.38, 0.43), (0.12, -0.58, 0.44)],
        scales=[0.020, 0.016, 0.005], sides=5, material=GLASS, name="drool",
    )
    return lathe.merge("mimic_tongue", [tongue, vein_l, vein_r, drool])


def cerberus_fang():
    """A hooked canine with three root branches — unmistakably volumetric from the side."""
    fang = sweep.sweep(
        [(0.00, -0.48, 0.02), (0.02, -0.08, 0.00), (0.08, 0.32, 0.08),
         (0.18, 0.67, 0.24), (0.22, 0.92, 0.43), (0.15, 1.10, 0.57)],
        scales=[0.27, 0.30, 0.27, 0.20, 0.11, 0.025],
        aspect=[(1.00, 0.82), (1.00, 0.84), (0.98, 0.86), (0.94, 0.88), (0.90, 0.90), (0.85, 0.85)],
        sides=7, rolls=[0, 3, 8, 16, 24, 31], material=BONE, name="fang",
    )
    roots = []
    for i, path in enumerate([
        [(0.00, -0.36, 0.00), (-0.26, -0.53, -0.08), (-0.38, -0.64, -0.18)],
        [(0.03, -0.38, -0.02), (0.16, -0.58, -0.18), (0.19, -0.70, -0.33)],
        [(-0.01, -0.38, 0.05), (0.18, -0.53, 0.18), (0.31, -0.62, 0.29)],
    ]):
        roots.append(sweep.sweep(path, scales=[0.13, 0.09, 0.035], sides=6,
                                 material=BONE, name=f"root_{i}"))
    scar = sweep.sweep(
        [(-0.18, 0.10, -0.14), (-0.13, 0.20, -0.20), (-0.02, 0.30, -0.22), (0.10, 0.36, -0.17)],
        scales=[0.018, 0.022, 0.020, 0.010], sides=5, material=GOLD, name="scar",
    )
    return lathe.merge("cerberus_fang", [fang, scar, *roots])


def blackroot():
    """A branching, corkscrewing root knot whose topology is literally a graph of gestures."""
    trunk = sweep.sweep(
        [(0.00, -0.72, 0.00), (-0.09, -0.38, 0.10), (0.06, -0.04, -0.05),
         (-0.12, 0.30, -0.15), (0.03, 0.58, 0.04), (0.10, 0.84, 0.17)],
        scales=[0.20, 0.23, 0.21, 0.18, 0.13, 0.055], sides=7,
        rolls=[0, 20, 42, 64, 83, 105], material=WOOD, name="root_trunk",
    )
    branches_spec = [
        ([(-0.06,-0.46,0.07),(-0.36,-0.53,0.16),(-0.56,-0.45,0.32)], [0.13,0.09,0.025]),
        ([(0.02,-0.38,0.02),(0.32,-0.55,-0.12),(0.55,-0.63,-0.06)], [0.12,0.08,0.025]),
        ([(0.02,-0.10,-0.05),(0.32,0.04,0.05),(0.50,0.28,0.19)], [0.10,0.07,0.020]),
        ([(-0.10,0.24,-0.14),(-0.38,0.32,-0.29),(-0.47,0.54,-0.21)], [0.095,0.065,0.020]),
        ([(0.00,0.52,0.02),(0.29,0.63,-0.10),(0.38,0.78,-0.25)], [0.075,0.050,0.018]),
    ]
    branches = [sweep.sweep(p, scales=r, sides=6, rolls=[0,35,70], material=WOOD, name=f"branch_{i}")
                for i,(p,r) in enumerate(branches_spec)]
    sap = sweep.sweep(
        [(0.31, 0.02, 0.06), (0.35, -0.16, 0.10), (0.31, -0.31, 0.12)],
        scales=[0.030, 0.022, 0.007], sides=5, material=WET, name="sap",
    )
    return lathe.merge("blackroot", [trunk, sap, *branches])


def molten_manacle():
    """An irregular cuff, two broken links, and molten drips all described as spatial loops/paths."""
    cuff_points = []
    for i in range(14):
        a = math.tau * i / 14
        r = 0.55 + 0.045 * math.sin(a * 3 + 0.6)
        cuff_points.append((r * math.cos(a), 0.10 * math.sin(a * 2), 0.42 * math.sin(a)))
    cuff = sweep.sweep(
        cuff_points, scales=[0.105 + 0.018 * math.sin(i * 1.7) for i in range(14)],
        sides=7, material=BRONZE, closed_path=True, cap_start=False, cap_end=False,
        rolls=[i * 11 for i in range(14)], name="manacle_cuff",
    )
    link1 = sweep.loop(_ellipse_loop(0.56, -0.10, 0.04, 0.23, 0.33, tilt=22, points=10),
                       radius=0.070, sides=6, material=IRON, name="link_1")
    link2 = sweep.loop(_ellipse_loop(0.84, -0.36, 0.10, 0.22, 0.31, tilt=64, points=10),
                       radius=0.064, sides=6, material=IRON, name="link_2")
    drip1 = sweep.sweep([(0.18,-0.35,0.31),(0.22,-0.62,0.35),(0.18,-0.82,0.30)],
                         scales=[0.040,0.028,0.006], sides=5, material=WAX, name="molten_drip_1")
    drip2 = sweep.sweep([(-0.30,-0.29,-0.26),(-0.34,-0.50,-0.30),(-0.30,-0.65,-0.29)],
                         scales=[0.032,0.022,0.006], sides=5, material=WAX, name="molten_drip_2")
    return lathe.merge("molten_manacle", [cuff, link1, link2, drip1, drip2])


def barbed_spear():
    """A cheap shaft whose threat comes from spatially branching recurved barbs."""
    shaft = sweep.sweep(
        [(0.00,-1.12,0.00),(0.01,-0.45,0.00),(-0.01,0.18,0.02),(0.00,0.68,0.00)],
        scales=[0.055,0.058,0.055,0.048], sides=6, material=WOOD, name="spear_shaft",
    )
    head = sweep.sweep(
        [(0.00,0.60,0.00),(0.00,0.87,0.00),(0.02,1.16,0.02),(0.00,1.42,0.00)],
        scales=[0.13,0.20,0.13,0.018],
        aspect=[(1.25,0.32),(1.35,0.28),(1.18,0.24),(1.0,0.20)],
        sides=6, rolls=[0,5,10,15], material=IRON, name="spear_head",
    )
    barb_paths = [
        [(0.00,0.95,0.00),(-0.22,0.84,0.04),(-0.34,0.67,0.11)],
        [(0.00,1.02,0.00),(0.22,0.91,-0.05),(0.36,0.74,-0.14)],
        [(0.00,1.10,0.00),(0.03,0.97,0.22),(0.10,0.79,0.34)],
        [(0.00,0.88,0.00),(-0.02,0.76,-0.20),(-0.08,0.61,-0.30)],
    ]
    barbs = [sweep.sweep(p, scales=[0.060,0.045,0.012], aspect=[(1.15,0.55)]*3,
                         sides=5, material=IRON, name=f"barb_{i}") for i,p in enumerate(barb_paths)]
    binding = sweep.sweep(
        [(-0.09,0.55,0.02),(-0.10,0.63,0.09),(0.00,0.69,0.12),(0.10,0.63,0.07),(0.09,0.55,-0.02)],
        scales=[0.018]*5, sides=5, material=GOLD, name="binding",
    )
    return lathe.merge("barbed_spear", [shaft, head, binding, *barbs])


def phoenix_pinion():
    """A feather made as a curved rachis plus depth-aware vane gestures, not a flat silhouette."""
    spine_points = [
        (0.00,-0.80,0.00),(0.02,-0.50,0.02),(-0.02,-0.18,0.07),
        (0.04,0.16,0.13),(0.00,0.50,0.18),(-0.05,0.78,0.16),(0.00,1.02,0.08),
    ]
    spine = sweep.sweep(spine_points, scales=[0.045,0.055,0.060,0.055,0.048,0.036,0.015],
                        sides=6, rolls=[0,8,18,30,45,60,78], material=GOLD, name="pinion_spine")
    vanes = []
    specs = [
        ((0.01,-0.48,0.03),0.48,0.07,0.10),
        ((-0.01,-0.24,0.06),0.58,0.09,0.13),
        ((0.02,0.02,0.10),0.64,0.11,0.16),
        ((0.03,0.27,0.15),0.60,0.12,0.18),
        ((0.00,0.50,0.18),0.50,0.11,0.17),
        ((-0.03,0.70,0.17),0.38,0.09,0.13),
    ]
    for i,(origin,reach,lift,depth) in enumerate(specs):
        ox,oy,oz=origin
        for side in (-1,1):
            path=[
                (ox,oy,oz),
                (ox+side*reach*0.52, oy+lift*0.42, oz+depth*0.62),
                (ox+side*reach, oy+lift, oz+depth*(1.0 if side>0 else 0.72)),
            ]
            vanes.append(sweep.ribbon(
                path, widths=[0.10,0.075,0.018], thickness=[0.034,0.028,0.010],
                rolls=[side*6, side*(18+i*2), side*(30+i*3)], material=CRYSTAL,
                name=f"vane_{i}_{side}",
            ))
    ember = sweep.sweep(
        [(0.00,-0.78,0.01),(0.02,-0.92,0.03),(0.00,-1.04,0.00)],
        scales=[0.040,0.055,0.012], sides=6, material=WAX, name="ember_tip",
    )
    return lathe.merge("phoenix_pinion", [spine, ember, *vanes])


COHORT = {
    "water_scepter": water_scepter,
    "hermes_boots": hermes_boots,
    "mimic_tongue": mimic_tongue,
    "cerberus_fang": cerberus_fang,
    "blackroot": blackroot,
    "molten_manacle": molten_manacle,
    "barbed_spear": barbed_spear,
    "phoenix_pinion": phoenix_pinion,
}


def build() -> None:
    lathe.write_mtl(
        OUT / MTL_NAME,
        MATERIALS,
        comment="Batch C spatial sweep / gesture cohort",
        sheens={GOLD: "assets/models/matcaps/gold.png", CRYSTAL: "assets/models/matcaps/ruby.png"},
    )
    for stem, recipe in COHORT.items():
        mesh = recipe()
        mesh.name = stem
        lathe.write_obj(
            mesh,
            OUT / f"{stem}.obj",
            mtllib=MTL_NAME,
            comment="Batch C: authored as spatial sweep gestures",
        )
        print(f"{stem}: {len(mesh.vertices)} verts, {len(mesh.faces)} faces")


if __name__ == "__main__":
    build()
