"""One-shot bootstrap for the first production C/curve item sources.

This file exists only to materialize the initial editable .blend documents from
Batch C's preserved authored path data. The .blend documents become source
authority after review; this bootstrap is then deleted.
"""
from __future__ import annotations

import math
from pathlib import Path

import bpy

import second_rite_asset_core as asset_core

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "assets" / "authoring" / "items"
SOURCE_DIR.mkdir(parents=True, exist_ok=True)

MATERIAL_IDS = {
    "bone", "crystal", "dark_wood", "oxidized_bronze", "ritual_gold",
    "smoked_glass", "wet_residue", "wrought_iron",
}


def reset():
    asset_core.reset_scene(factory=True)


def mats():
    return {mid: asset_core.make_material(mid, semantic_id=mid) for mid in MATERIAL_IDS}


def root_for(item_id: str, description: str):
    root = bpy.data.objects.new(f"ITEM_{item_id}", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.22
    bpy.context.scene.collection.objects.link(root)
    root["item_export"] = True
    root["item_export_name"] = item_id
    asset_core.tag_asset_target(
        root,
        asset_id=item_id,
        representation="full_model",
        role="item_display",
        authoring_space="item_display",
        placement_frame="item_viewport",
        states=["default"],
        default_state="default",
        variants=[],
        extra={
            "sr_source_authority": "blend",
            "sr_authoring_grammar": "curve_spatial_gesture",
            "sr_authoring_description": description,
        },
    )
    return root


def path_curve(name, points, scales, *, parent, material, sides=6, rolls=None, cyclic=False):
    """Editable POLY spatial path with point radius/tilt preserved as source intent."""
    if len(points) != len(scales):
        raise ValueError(f"{name}: points/scales length mismatch")
    base = max(scales)
    curve = bpy.data.curves.new(name + "Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.resolution_v = 0
    curve.bevel_resolution = 0
    curve.bevel_depth = base
    curve.fill_mode = "FULL"
    # Blender's bevel_depth is circular today. Preserve the original requested
    # section side-count as metadata so a future profile/Geometry-Nodes editor
    # can expose it without reverse engineering the compiled mesh.
    curve["sr_cross_section_sides"] = int(sides)
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    spline.use_cyclic_u = cyclic
    rolls = rolls or [0.0] * len(points)
    for co, scale, roll, point in zip(points, scales, rolls, spline.points):
        point.co = (*co, 1.0)
        point.radius = scale / base
        point.tilt = math.radians(roll)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    asset_core.parent_local(obj, parent)
    asset_core.assign_material(obj, material)
    return obj


def note(item_id: str, text: str):
    block = bpy.data.texts.get("AUTHORING_README") or bpy.data.texts.new("AUTHORING_README")
    block.clear()
    block.write(
        f"Production item source: {item_id}\n\n{text}\n\n"
        "This .blend is the editable source authority. Curves retain centerline, per-point radius, and tilt.\n"
        "Runtime OBJ/MTL are compiled read-only through tools/blender/compile_item_blends.py.\n"
    )


def save(item_id: str):
    path = SOURCE_DIR / f"{item_id}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
    print(f"WROTE C SOURCE {path.relative_to(ROOT)}")


def build_cerberus_fang():
    reset(); mat = mats()
    root = root_for("cerberus_fang", "Hooked canine with three root branches; C centerlines are primary authoring geometry")
    path_curve("C_Fang", [(0.00,-0.48,0.02),(0.02,-0.08,0.00),(0.08,0.32,0.08),(0.18,0.67,0.24),(0.22,0.92,0.43),(0.15,1.10,0.57)], [0.27,0.30,0.27,0.20,0.11,0.025], parent=root, material=mat["bone"], sides=7, rolls=[0,3,8,16,24,31])
    roots = [
        [(0.00,-0.36,0.00),(-0.26,-0.53,-0.08),(-0.38,-0.64,-0.18)],
        [(0.03,-0.38,-0.02),(0.16,-0.58,-0.18),(0.19,-0.70,-0.33)],
        [(-0.01,-0.38,0.05),(0.18,-0.53,0.18),(0.31,-0.62,0.29)],
    ]
    for i, points in enumerate(roots):
        path_curve(f"C_Root_{i}", points, [0.13,0.09,0.035], parent=root, material=mat["bone"], sides=6)
    path_curve("C_GoldScar", [(-0.18,0.10,-0.14),(-0.13,0.20,-0.20),(-0.02,0.30,-0.22),(0.10,0.36,-0.17)], [0.018,0.022,0.020,0.010], parent=root, material=mat["ritual_gold"], sides=5)
    note("cerberus_fang", "Move the fang/root/scar curve points to reshape the item; point radius controls taper.")
    save("cerberus_fang")


def build_water_scepter():
    reset(); mat = mats()
    root = root_for("water_scepter", "Staff whose upper gesture breaks into paired crystal waves, pearl and gold curl")
    path_curve("C_Shaft", [(-0.05,-1.05,0.00),(-0.10,-0.55,0.04),(-0.02,-0.12,-0.05),(0.08,0.30,0.07),(0.03,0.72,0.00)], [0.075,0.078,0.070,0.062,0.055], parent=root, material=mat["oxidized_bronze"], sides=7)
    path_curve("C_LeftWave", [(0.02,0.64,0.00),(-0.23,0.80,0.07),(-0.38,1.03,0.02),(-0.29,1.27,-0.12),(-0.06,1.36,-0.18),(0.10,1.23,-0.10)], [0.055,0.062,0.070,0.060,0.045,0.022], parent=root, material=mat["crystal"], sides=6, rolls=[0,8,18,30,45,65])
    path_curve("C_RightWave", [(0.01,0.69,0.02),(0.24,0.82,-0.06),(0.39,1.00,0.02),(0.36,1.22,0.16),(0.18,1.33,0.23),(0.02,1.22,0.15)], [0.050,0.060,0.068,0.055,0.040,0.020], parent=root, material=mat["crystal"], sides=6, rolls=[0,-10,-20,-32,-46,-60])
    path_curve("C_WaterPearl", [(0.00,0.89,0.02),(0.00,1.02,0.04),(0.01,1.15,0.08),(0.00,1.27,0.04)], [0.045,0.145,0.125,0.025], parent=root, material=mat["smoked_glass"], sides=8)
    path_curve("C_GoldCurl", [(-0.06,0.73,0.00),(-0.16,0.94,0.13),(-0.08,1.14,0.23),(0.10,1.18,0.22),(0.18,1.05,0.10)], [0.025,0.028,0.030,0.025,0.015], parent=root, material=mat["ritual_gold"], sides=5)
    note("water_scepter", "All five visible gestures remain separate editable curves; the pearl is intentionally a swell along a short path rather than a baked sphere.")
    save("water_scepter")


def build_blackroot():
    reset(); mat = mats()
    root = root_for("blackroot", "Branching corkscrew root represented as an editable graph of spatial curves")
    path_curve("C_Trunk", [(0.00,-0.72,0.00),(-0.09,-0.38,0.10),(0.06,-0.04,-0.05),(-0.12,0.30,-0.15),(0.03,0.58,0.04),(0.10,0.84,0.17)], [0.20,0.23,0.21,0.18,0.13,0.055], parent=root, material=mat["dark_wood"], sides=7, rolls=[0,20,42,64,83,105])
    specs = [
        ([(-0.06,-0.46,0.07),(-0.36,-0.53,0.16),(-0.56,-0.45,0.32)], [0.13,0.09,0.025]),
        ([(0.02,-0.38,0.02),(0.32,-0.55,-0.12),(0.55,-0.63,-0.06)], [0.12,0.08,0.025]),
        ([(0.02,-0.10,-0.05),(0.32,0.04,0.05),(0.50,0.28,0.19)], [0.10,0.07,0.020]),
        ([(-0.10,0.24,-0.14),(-0.38,0.32,-0.29),(-0.47,0.54,-0.21)], [0.095,0.065,0.020]),
        ([(0.00,0.52,0.02),(0.29,0.63,-0.10),(0.38,0.78,-0.25)], [0.075,0.050,0.018]),
    ]
    for i, (points, scales) in enumerate(specs):
        path_curve(f"C_Branch_{i}", points, scales, parent=root, material=mat["dark_wood"], sides=6, rolls=[0,35,70])
    path_curve("C_Sap", [(0.31,0.02,0.06),(0.35,-0.16,0.10),(0.31,-0.31,0.12)], [0.030,0.022,0.007], parent=root, material=mat["wet_residue"], sides=5)
    note("blackroot", "The object is intentionally a gesture graph: trunk, five branches, and sap are independently editable curves.")
    save("blackroot")


def build_barbed_spear():
    reset(); mat = mats()
    root = root_for("barbed_spear", "Shaft, head, four recurved barbs and binding authored as separate spatial gestures")
    path_curve("C_Shaft", [(0.00,-1.12,0.00),(0.01,-0.45,0.00),(-0.01,0.18,0.02),(0.00,0.68,0.00)], [0.055,0.058,0.055,0.048], parent=root, material=mat["dark_wood"], sides=6)
    # The old sweep used a flattened elliptical section here. The path/radius
    # remain authoritative in this first migration; the source records the old
    # aspect intent as metadata until the profile editor/Geometry Nodes pass.
    head = path_curve("C_Head", [(0.00,0.60,0.00),(0.00,0.87,0.00),(0.02,1.16,0.02),(0.00,1.42,0.00)], [0.13,0.20,0.13,0.018], parent=root, material=mat["wrought_iron"], sides=6, rolls=[0,5,10,15])
    head.data["sr_original_aspect"] = "1.25:0.32,1.35:0.28,1.18:0.24,1.0:0.20"
    barb_paths = [
        [(0.00,0.95,0.00),(-0.22,0.84,0.04),(-0.34,0.67,0.11)],
        [(0.00,1.02,0.00),(0.22,0.91,-0.05),(0.36,0.74,-0.14)],
        [(0.00,1.10,0.00),(0.03,0.97,0.22),(0.10,0.79,0.34)],
        [(0.00,0.88,0.00),(-0.02,0.76,-0.20),(-0.08,0.61,-0.30)],
    ]
    for i, points in enumerate(barb_paths):
        barb = path_curve(f"C_Barb_{i}", points, [0.060,0.045,0.012], parent=root, material=mat["wrought_iron"], sides=5)
        barb.data["sr_original_aspect"] = "1.15:0.55"
    path_curve("C_Binding", [(-0.09,0.55,0.02),(-0.10,0.63,0.09),(0.00,0.69,0.12),(0.10,0.63,0.07),(0.09,0.55,-0.02)], [0.018]*5, parent=root, material=mat["ritual_gold"], sides=5)
    note("barbed_spear", "Spatial construction is editable now; flattened head/barb section intent is retained as source metadata for the profile/Geometry Nodes follow-up.")
    save("barbed_spear")


for fn in (build_cerberus_fang, build_water_scepter, build_blackroot, build_barbed_spear):
    fn()
