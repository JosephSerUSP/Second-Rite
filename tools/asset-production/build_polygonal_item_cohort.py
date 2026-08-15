"""Second 3D-authoring cohort: planar/asymmetric polygonal fabrication.

Batch A (``build_relic_showcase.py``) asks what the semantic parts + lathe
vocabulary can sculpt.  This cohort asks a deliberately different question:
what happens when an author draws silhouettes and fabricates them into thin
solids instead?

No recipe below calls ``parts.py`` or ``lathe.lathe``.  Geometry comes from
``poly_parts.py``: extruded convex outlines, polygonal frames, bars, bent
polylines and layered plates.  The result should be substantially cheaper in
vertices while opening up blades, masks, glasses, feathers and garments that
were awkward to describe as surfaces of revolution.

Run:
    python tools/asset-production/build_polygonal_item_cohort.py
    lovec . item-sheet tools/asset-production/polygonal-cohort-items.txt polygonal-cohort.png
"""

from __future__ import annotations

from pathlib import Path

import lathe
import poly_parts as poly

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "assets" / "models" / "items"
MTL_NAME = "polygonal_cohort.mtl"

GOLD = "ritual_gold"
BRONZE = "oxidized_bronze"
IRON = "wrought_iron"
CLOTH = "aged_cloth"
GLASS = "smoked_glass"
CRYSTAL = "crystal"
BONE = "bone"
WOOD = "dark_wood"
WET = "wet_residue"
STONE = "old_limestone"

MATERIALS = sorted({GOLD, BRONZE, IRON, CLOTH, GLASS, CRYSTAL, BONE, WOOD, WET, STONE})


def moved(mesh, *, z=0.0, rotate=(0.0, 0.0, 0.0), translate=(0.0, 0.0, 0.0), scale=1.0):
    tx, ty, tz = translate
    return lathe.transform(mesh, translate=(tx, ty, tz + z), rotate=rotate, scale=scale)


def mirror(points):
    return [(-x, y) for x, y in reversed(points)]


def greatsword():
    """One decisive hand-drawn blade silhouette, not a stack of cylinders."""
    blade = poly.extrude_polygon(
        [(-0.22, 0.24), (-0.26, 1.45), (0.0, 1.96), (0.26, 1.45), (0.22, 0.24)],
        0.13, material=IRON, name="blade",
    )
    fuller = moved(poly.bar_between((0.0, 0.42), (0.0, 1.55), 0.055, 0.035,
                                    material=GOLD, name="fuller"), z=0.085)
    guard = poly.bar_between((-0.58, 0.20), (0.58, 0.20), 0.13, 0.18,
                             material=BRONZE, name="guard")
    grip = poly.bar_between((0.0, -0.48), (0.0, 0.18), 0.15, 0.16,
                            material=WOOD, name="grip")
    pommel = poly.regular_plate((0.0, -0.59), 0.19, 6, 0.18, rotation=30,
                                material=GOLD, name="pommel")
    return lathe.merge("greatsword", [blade, fuller, guard, grip, pommel])


def death_sickle():
    """A visibly faceted hooked blade: the bend is authored as a polyline."""
    shaft = poly.bar_between((-0.18, -0.52), (0.14, 1.18), 0.13, 0.14,
                             material=WOOD, name="shaft")
    socket = poly.regular_plate((0.14, 1.18), 0.20, 6, 0.18, rotation=30,
                                material=BRONZE, name="socket")
    blade = poly.arc_bars((0.12, 1.17), 0.76, 8, 143, 5, 0.16, 0.11,
                          material=IRON, name="crescent")
    point = poly.extrude_polygon(
        [(-0.53, 1.54), (-0.86, 1.73), (-0.62, 1.35)],
        0.11, material=IRON, name="blade_tip",
    )
    tooth = poly.extrude_polygon(
        [(0.70, 1.34), (0.98, 1.27), (0.76, 1.12)],
        0.10, material=GOLD, name="back_tooth",
    )
    return lathe.merge("death_sickle", [shaft, socket, blade, point, tooth])


def silver_glasses():
    """Actual empty spectacles: two octagonal frames, lenses, bridge and arms."""
    left_lens = moved(poly.regular_plate((-0.42, 0.78), 0.28, 8, 0.025, rotation=22.5,
                                         material=GLASS, name="left_lens"), z=-0.02)
    right_lens = moved(poly.regular_plate((0.42, 0.78), 0.28, 8, 0.025, rotation=22.5,
                                          material=GLASS, name="right_lens"), z=-0.02)
    left = poly.ring_segments((-0.42, 0.78), 0.32, 8, 0.055, 0.075, rotation=22.5,
                              material=IRON, name="left_frame")
    right = poly.ring_segments((0.42, 0.78), 0.32, 8, 0.055, 0.075, rotation=22.5,
                               material=IRON, name="right_frame")
    bridge = poly.bar_between((-0.11, 0.80), (0.11, 0.80), 0.055, 0.08,
                              material=IRON, name="bridge")
    left_arm = moved(poly.bar_between((-0.70, 0.84), (-1.23, 0.72), 0.055, 0.07,
                                      material=IRON, name="left_arm"), z=-0.05)
    right_arm = moved(poly.bar_between((0.70, 0.84), (1.23, 0.72), 0.055, 0.07,
                                       material=IRON, name="right_arm"), z=-0.05)
    return lathe.merge("silver_glasses", [left_lens, right_lens, left, right, bridge, left_arm, right_arm])


def gas_mask():
    """A faceted face shell with real paired lenses and protruding filters."""
    shell = poly.extrude_polygon(
        [(-0.34, 0.16), (-0.58, 0.52), (-0.52, 1.05), (-0.25, 1.36),
         (0.25, 1.36), (0.52, 1.05), (0.58, 0.52), (0.34, 0.16)],
        0.20, material=CLOTH, name="mask_shell",
    )
    lens_l = moved(poly.regular_plate((-0.24, 0.98), 0.17, 6, 0.035, rotation=30,
                                      material=GLASS, name="lens_l"), z=0.12)
    lens_r = moved(poly.regular_plate((0.24, 0.98), 0.17, 6, 0.035, rotation=30,
                                      material=GLASS, name="lens_r"), z=0.12)
    frame_l = moved(poly.ring_segments((-0.24, 0.98), 0.20, 6, 0.055, 0.075, rotation=30,
                                       material=IRON, name="frame_l"), z=0.14)
    frame_r = moved(poly.ring_segments((0.24, 0.98), 0.20, 6, 0.055, 0.075, rotation=30,
                                       material=IRON, name="frame_r"), z=0.14)
    muzzle = moved(poly.regular_plate((0.0, 0.48), 0.24, 6, 0.24, rotation=30,
                                      material=IRON, name="muzzle"), z=0.10)
    filter_l = moved(poly.regular_plate((-0.43, 0.39), 0.22, 8, 0.30, rotation=22.5,
                                        material=WET, name="filter_l"), z=0.12)
    filter_r = moved(poly.regular_plate((0.43, 0.39), 0.22, 8, 0.30, rotation=22.5,
                                        material=WET, name="filter_r"), z=0.12)
    strap_l = moved(poly.bar_between((-0.48, 0.82), (-0.78, 1.26), 0.075, 0.055,
                                     material=IRON, name="strap_l"), z=-0.13)
    strap_r = moved(poly.bar_between((0.48, 0.82), (0.78, 1.26), 0.075, 0.055,
                                     material=IRON, name="strap_r"), z=-0.13)
    return lathe.merge("gas_mask", [shell, lens_l, lens_r, frame_l, frame_r, muzzle,
                                     filter_l, filter_r, strap_l, strap_r])


def moth_cloak():
    """A garment designed as layered moth wings rather than a torso-shaped box."""
    left_upper_pts = [(-0.05, 1.30), (-0.28, 1.62), (-1.00, 1.42), (-0.76, 0.88)]
    left_lower_pts = [(-0.08, 1.12), (-0.76, 0.88), (-0.88, 0.24), (-0.22, 0.56)]
    left_upper = poly.extrude_polygon(left_upper_pts, 0.075, material=CLOTH, name="left_upper")
    left_lower = poly.extrude_polygon(left_lower_pts, 0.070, material=CLOTH, name="left_lower")
    right_upper = poly.extrude_polygon(mirror(left_upper_pts), 0.075, material=CLOTH, name="right_upper")
    right_lower = poly.extrude_polygon(mirror(left_lower_pts), 0.070, material=CLOTH, name="right_lower")
    collar = poly.extrude_polygon([(-0.24, 1.48), (0.24, 1.48), (0.16, 1.14), (-0.16, 1.14)],
                                  0.12, material=IRON, name="collar")
    ribs = [
        poly.bar_between((-0.06, 1.25), (-0.76, 1.36), 0.045, 0.045, material=BONE, name="rib_l1"),
        poly.bar_between((-0.08, 1.08), (-0.68, 0.65), 0.040, 0.045, material=BONE, name="rib_l2"),
        poly.bar_between((0.06, 1.25), (0.76, 1.36), 0.045, 0.045, material=BONE, name="rib_r1"),
        poly.bar_between((0.08, 1.08), (0.68, 0.65), 0.040, 0.045, material=BONE, name="rib_r2"),
    ]
    eyes = [
        moved(poly.regular_plate((-0.62, 1.16), 0.15, 8, 0.025, material=WET, name="eye_l"), z=0.055),
        moved(poly.regular_plate((0.62, 1.16), 0.15, 8, 0.025, material=WET, name="eye_r"), z=0.055),
    ]
    return lathe.merge("moth_cloak", [left_upper, left_lower, right_upper, right_lower, collar, *ribs, *eyes])


def mirror_armor():
    """Broad layered breastplate whose reflective identity is literally a plate."""
    torso = poly.extrude_polygon(
        [(-0.40, 0.30), (0.40, 0.30), (0.57, 1.40), (-0.57, 1.40)],
        0.22, material=BRONZE, name="torso",
    )
    mirror_panel = moved(poly.extrude_polygon(
        [(-0.27, 0.50), (0.27, 0.50), (0.36, 1.25), (-0.36, 1.25)],
        0.045, material=CRYSTAL, name="mirror_panel"), z=0.135)
    left_shoulder = poly.extrude_polygon(
        [(-0.56, 1.34), (-1.02, 1.20), (-0.96, 0.88), (-0.52, 0.98)],
        0.18, material=IRON, name="left_shoulder",
    )
    right_shoulder = poly.extrude_polygon(mirror([
        (-0.56, 1.34), (-1.02, 1.20), (-0.96, 0.88), (-0.52, 0.98)
    ]), 0.18, material=IRON, name="right_shoulder")
    collar = poly.bar_between((-0.42, 1.38), (0.42, 1.38), 0.13, 0.18,
                              material=GOLD, name="collar")
    waist = poly.bar_between((-0.38, 0.35), (0.38, 0.35), 0.12, 0.18,
                             material=IRON, name="waist")
    facet_l = moved(poly.extrude_polygon([(-0.31, 0.56), (-0.03, 0.86), (-0.03, 1.18), (-0.31, 1.12)],
                                           0.025, material=GLASS, name="facet_l"), z=0.17)
    facet_r = moved(poly.extrude_polygon(mirror([(-0.31, 0.56), (-0.03, 0.86), (-0.03, 1.18), (-0.31, 1.12)]),
                                           0.025, material=GLASS, name="facet_r"), z=0.17)
    return lathe.merge("mirror_armor", [torso, mirror_panel, left_shoulder, right_shoulder,
                                        collar, waist, facet_l, facet_r])


def angel_feather():
    """A long, slightly damaged feather assembled from individually drawn vanes."""
    shaft = poly.bar_between((0.0, -0.42), (0.06, 1.68), 0.075, 0.075,
                             material=GOLD, name="shaft")
    vanes = []
    levels = [(-0.02, 0.10, 0.48), (0.18, 0.13, 0.62), (0.40, 0.14, 0.72),
              (0.64, 0.13, 0.78), (0.88, 0.11, 0.70), (1.12, 0.09, 0.56),
              (1.34, 0.07, 0.40)]
    for index, (y, rise, length) in enumerate(levels):
        left = [(0.00, y - 0.08), (-length * 0.82, y - 0.02),
                (-length, y + rise), (0.02, y + 0.10)]
        right = mirror(left)
        # one missing chunk keeps this from reading as a heraldic perfectly
        # symmetric icon; it is a carried object with wear.
        if index != 2:
            vanes.append(poly.extrude_polygon(left, 0.055, material=BONE, name=f"vane_l_{index}"))
        vanes.append(poly.extrude_polygon(right, 0.055, material=BONE, name=f"vane_r_{index}"))
    tip = poly.extrude_polygon([(-0.06, 1.55), (0.06, 1.55), (0.03, 1.92)],
                               0.06, material=BONE, name="tip")
    return lathe.merge("angel_feather", [shaft, *vanes, tip])


def rear_mirror():
    """A hand mirror with an actual open frame and a deep-backed glass plate."""
    glass = moved(poly.regular_plate((0.0, 0.92), 0.43, 10, 0.035, rotation=18,
                                     material=GLASS, name="glass"), z=0.01)
    frame = poly.ring_segments((0.0, 0.92), 0.52, 10, 0.08, 0.11, rotation=18,
                               material=GOLD, name="frame")
    handle = poly.bar_between((0.0, -0.42), (0.0, 0.43), 0.16, 0.16,
                              material=WOOD, name="handle")
    throat = poly.extrude_polygon([(-0.20, 0.38), (0.20, 0.38), (0.13, 0.58), (-0.13, 0.58)],
                                  0.15, material=BRONZE, name="throat")
    pommel = poly.regular_plate((0.0, -0.53), 0.20, 6, 0.17, rotation=30,
                                material=GOLD, name="pommel")
    finial = poly.extrude_polygon([(-0.08, 1.43), (0.08, 1.43), (0.0, 1.70)],
                                  0.10, material=GOLD, name="finial")
    return lathe.merge("rear_mirror", [glass, frame, handle, throat, pommel, finial])


COHORT = {
    "greatsword": greatsword,
    "death_sickle": death_sickle,
    "silver_glasses": silver_glasses,
    "gas_mask": gas_mask,
    "moth_cloak": moth_cloak,
    "mirror_armor": mirror_armor,
    "angel_feather": angel_feather,
    "rear_mirror": rear_mirror,
}


def build() -> None:
    lathe.write_mtl(
        OUT / MTL_NAME,
        MATERIALS,
        comment="polygonal fabrication comparison cohort",
        sheens={GOLD: "assets/models/matcaps/gold.png"},
    )
    for stem, recipe in COHORT.items():
        mesh = recipe()
        mesh.name = stem
        lathe.write_obj(
            mesh,
            OUT / f"{stem}.obj",
            mtllib=MTL_NAME,
            comment="polygonal cohort: fabricated from poly_parts.py; no lathed geometry",
        )
        print(f"{stem}: {len(mesh.vertices)} verts, {len(mesh.faces)} faces")


if __name__ == "__main__":
    build()
