"""One-shot direct-source V3 edit for Vial of Second Breath.

V2 fixed the six authored paths but round bevels still read as porcupine spines in
the real item viewer. Keep those paths; replace only their cross-section with one
shared flattened editable profile and explicit roll. Delete after acceptance.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy


if Path(bpy.data.filepath).stem != "vial_of_second_breath":
    raise RuntimeError("this refiner must be run on vial_of_second_breath.blend")

root = bpy.data.objects.get("ITEM_vial_of_second_breath")
if root is None:
    raise RuntimeError("missing Vial export root")


def require(name):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"missing authored object {name}")
    return obj


def remake_path(obj, coords, tilts):
    curve = obj.data
    curve.splines.clear()
    spline = curve.splines.new("POLY")
    spline.points.add(len(coords) - 1)
    radii = (1.00, 0.84, 0.54, 0.08)
    for co, radius, tilt, point in zip(coords, radii, tilts, spline.points):
        point.co = (*co, 1.0)
        point.radius = radius
        point.tilt = math.radians(tilt)
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.resolution_v = 0
    curve.twist_mode = "MINIMUM"
    curve.fill_mode = "FULL"
    curve.use_fill_caps = True


profile = bpy.data.objects.get("C_BreathFeather_PROFILE")
if profile is None:
    data = bpy.data.curves.new("C_BreathFeather_PROFILE_Data", type="CURVE")
    data.dimensions = "2D"
    data.resolution_u = 1
    spline = data.splines.new("POLY")
    spline.points.add(5)
    spline.use_cyclic_u = True
    # Broad but paper-thin hexagonal section. Point radius on each path supplies
    # the longitudinal taper, so the source remains very easy to art-direct.
    section = [
        (-0.075, -0.010),
        (0.000, -0.014),
        (0.075, -0.010),
        (0.075, 0.010),
        (0.000, 0.014),
        (-0.075, 0.010),
    ]
    for point, (x, y) in zip(spline.points, section):
        point.co = (x, y, 0.0, 1.0)
    profile = bpy.data.objects.new("C_BreathFeather_PROFILE", data)
    bpy.context.scene.collection.objects.link(profile)
    profile.parent = root
    profile.matrix_parent_inverse = root.matrix_world.inverted()
    profile.hide_render = True
    profile.display_type = "WIRE"
    profile["sr_authoring_role"] = "ribbon_profile"
    profile["sr_profile_note"] = "Shared dry-breath feather cross-section; path point radius controls taper."

paths = {
    "C_BreathFeather_L_0": (
        [(-0.27,0.05,0.13),(-0.39,-0.01,0.31),(-0.61,-0.08,0.55),(-0.82,-0.03,0.72)],
        [82,86,92,100],
    ),
    "C_BreathFeather_L_1": (
        [(-0.29,0.00,-0.01),(-0.43,0.08,0.04),(-0.66,0.04,0.16),(-0.86,-0.04,0.22)],
        [92,96,102,108],
    ),
    "C_BreathFeather_L_2": (
        [(-0.28,-0.03,-0.24),(-0.42,0.04,-0.29),(-0.59,0.11,-0.43),(-0.76,0.15,-0.58)],
        [100,104,110,116],
    ),
    "C_BreathFeather_R_0": (
        [(0.28,-0.01,0.16),(0.42,0.08,0.30),(0.63,0.10,0.50),(0.82,0.02,0.64)],
        [98,94,88,82],
    ),
    "C_BreathFeather_R_1": (
        [(0.29,0.04,-0.02),(0.45,-0.05,0.02),(0.68,-0.09,0.10),(0.87,-0.11,0.13)],
        [88,84,79,74],
    ),
    "C_BreathFeather_R_2": (
        [(0.27,0.00,-0.22),(0.41,-0.09,-0.28),(0.58,-0.12,-0.40),(0.76,-0.02,-0.52)],
        [80,76,72,68],
    ),
}

for name, (coords, tilts) in paths.items():
    obj = require(name)
    remake_path(obj, coords, tilts)
    obj.data.bevel_depth = 0.0
    obj.data.bevel_mode = "OBJECT"
    obj.data.bevel_object = profile
    obj["sr_authoring_role"] = "breath_feather_path"

root["sr_art_direction_v3"] = (
    "V2 paths retained and expanded to four authored points; round tube bevels replaced "
    "with one shared flattened feather profile after real-viewer review."
)

bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("REFINED VIAL BREATH FEATHER PROFILE", bpy.data.filepath)
