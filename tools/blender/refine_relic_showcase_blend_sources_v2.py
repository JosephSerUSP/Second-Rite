"""One-shot art-direction pass over already-authoritative relic .blend documents.

Unlike the initial migration bootstrap, this script does not reconstruct any item.
It opens an existing committed source document, adjusts its named artist-facing
objects, and saves that same document. Delete this script after review acceptance.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy


def require(name: str):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"expected authored object {name!r} in {bpy.data.filepath}")
    return obj


def set_poly_points(curve_obj, coords, radii=None):
    splines = curve_obj.data.splines
    if len(splines) != 1:
        raise RuntimeError(f"{curve_obj.name}: expected one authored spline")
    spline = splines[0]
    if len(spline.points) != len(coords):
        raise RuntimeError(
            f"{curve_obj.name}: expected {len(coords)} points, found {len(spline.points)}"
        )
    radii = radii or [1.0] * len(coords)
    for co, radius, point in zip(coords, radii, spline.points):
        point.co = (*co, 1.0)
        point.radius = radius


def refine_black_hinge():
    # Restore the heavy paired-gate-leaf read. The V1 leaves were broad enough
    # that the gold halo curves became the dominant front-view silhouette.
    left = require("A_Leaf_L")
    right = require("A_Leaf_R")
    for leaf in (left, right):
        leaf.scale = (0.64, 1.18, 0.70)

    # Pull the leaves a little farther apart and toward the viewer while reducing
    # the halo footprint. The pin remains the visual centre of gravity.
    left.location.x = -0.61
    right.location.x = 0.61
    left.location.y = -0.035
    right.location.y = -0.035

    halo_l = require("C_Halo_L")
    halo_r = require("C_Halo_R")
    for halo in (halo_l, halo_r):
        halo.scale = (0.82, 0.82, 0.84)
        halo.data.bevel_depth = 0.031

    heart = require("A_CrystalHeart")
    heart.scale.x *= 1.10
    heart.scale.z *= 1.12

    root = require("ITEM_black_hinge")
    root["sr_art_direction_v2"] = (
        "Heavier iron leaves; subordinate halo arcs; enlarged crystal heart. "
        "Direct edit of authoritative Blend source after viewer review."
    )


def refine_chrysalis_sigil():
    # V1 was convincing front-on but collapsed into a paper-thin sigil from the
    # side. Thicken the cocoon and petals, then stagger the three ribs in depth.
    cocoon = require("A_CrystalCocoon")
    cocoon.scale.y = 0.72

    for idx, y in enumerate((-0.11, -0.035, 0.045)):
        rib = require(f"C_RitualRib_{idx}")
        rib.location.y = y
        rib.data.bevel_depth = 0.030

    petal_specs = {
        "A_WingPetal_L_0": (-0.09, -15.0),
        "A_WingPetal_L_1": (0.07, -23.0),
        "A_WingPetal_R_0": (0.09, 15.0),
        "A_WingPetal_R_1": (-0.07, 23.0),
    }
    for name, (y, x_degrees) in petal_specs.items():
        petal = require(name)
        petal.scale.y = 0.43
        petal.location.y = y
        petal.rotation_euler.x = math.radians(x_degrees)

    gem = require("A_FrontGem")
    gem.location.y = -0.46

    root = require("ITEM_chrysalis_sigil")
    root["sr_art_direction_v2"] = (
        "Deepened cocoon and wing petals; ribs staggered in depth so the sigil "
        "reads as a layered ceremonial object from oblique and side views."
    )


def refine_vial_of_second_breath():
    # Replace the V1 porcupine-like rays with six explicitly authored curved
    # exhalation/feather gestures. They remain simple three-point Curves: the
    # improvement comes from their placement and arc, not a new abstraction.
    curves = {
        "C_BreathFeather_L_0": [(-0.27, 0.05, 0.13), (-0.48, -0.01, 0.42), (-0.78, -0.09, 0.69)],
        "C_BreathFeather_L_1": [(-0.29, 0.00, -0.01), (-0.54, 0.08, 0.10), (-0.82, 0.02, 0.18)],
        "C_BreathFeather_L_2": [(-0.28, -0.03, -0.24), (-0.51, 0.04, -0.36), (-0.72, 0.13, -0.53)],
        "C_BreathFeather_R_0": [(0.28, -0.01, 0.16), (0.53, 0.09, 0.39), (0.81, 0.03, 0.61)],
        "C_BreathFeather_R_1": [(0.29, 0.04, -0.02), (0.56, -0.06, 0.07), (0.86, -0.12, 0.11)],
        "C_BreathFeather_R_2": [(0.27, 0.00, -0.22), (0.50, -0.10, -0.33), (0.75, -0.03, -0.48)],
    }
    for name, points in curves.items():
        obj = require(name)
        set_poly_points(obj, points, radii=[1.0, 0.68, 0.08])
        obj.data.bevel_depth = 0.045

    halo = require("C_BrokenHalo")
    halo.data.bevel_depth = 0.024
    halo.scale = (0.92, 0.92, 0.94)

    stopper = require("A_CrystalStopper")
    stopper.scale.x *= 1.06
    stopper.scale.y *= 1.06

    root = require("ITEM_vial_of_second_breath")
    root["sr_art_direction_v2"] = (
        "Six breath Curves reshaped into layered asymmetric exhalation/feather "
        "gestures after V1 viewer review rejected the straight-spine read."
    )


stem = Path(bpy.data.filepath).stem
REFINERS = {
    "black_hinge": refine_black_hinge,
    "chrysalis_sigil": refine_chrysalis_sigil,
    "vial_of_second_breath": refine_vial_of_second_breath,
}

if stem not in REFINERS:
    raise RuntimeError(f"no V2 relic refiner registered for {stem!r}")

REFINERS[stem]()
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("REFINED AUTHORITATIVE RELIC SOURCE", stem, bpy.data.filepath)
