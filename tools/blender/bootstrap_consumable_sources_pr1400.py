"""One-shot bootstrap for PR #1400 consumable Blender sources.

Run *inside pinned Blender*. It creates six authoritative per-item .blend
sources from editable Blender-native construction. Once the first .blend save is
committed, the .blend becomes sole authority and this bootstrap must be removed.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import second_rite_asset_core as asset_core

ROOT = SCRIPT_DIR.parents[1]
SOURCE_DIR = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "items"
TARGETS = ("potion", "hi_potion", "x_potion", "mega_potion", "healing_water", "ether")
_MATERIALS = {}


def material(semantic_id: str):
    mat = _MATERIALS.get(semantic_id)
    if mat is None:
        mat = asset_core.make_material(f"sr_{semantic_id}", semantic_id=semantic_id)
        _MATERIALS[semantic_id] = mat
    return mat


def root_for(stem: str, display_name: str):
    root = bpy.data.objects.new(f"ITEM_{stem}", None)
    bpy.context.scene.collection.objects.link(root)
    root["item_export"] = True
    root["item_export_name"] = stem
    root["item_display_name"] = display_name
    root["item_category"] = "Consumable"
    root["sr_source_authority"] = "blend"
    asset_core.tag_asset_target(
        root,
        asset_id=stem,
        representation="full_model",
        role="item_display",
        authoring_space="item_display",
        placement_frame="item_viewport",
    )
    return root


def profile_revolve(root, name, points, semantic_id, *, steps=12, smooth=True, closed=False):
    """Editable X/Z profile with live Screw and cylindrical UV generation."""
    verts = [(float(radius), 0.0, float(z)) for z, radius in points]
    edges = [(i, i + 1) for i in range(len(verts) - 1)]
    if closed:
        edges.append((len(verts) - 1, 0))
    mesh = bpy.data.meshes.new(f"{name}_profile_mesh")
    mesh.from_pydata(verts, edges, [])
    # Screw only emits UVs when an input UV layer exists. The edge-only profile
    # has no loops yet, but declaring the layer here gives the live modifier an
    # authored UV target; use_stretch_u/v then fills the resolved surface.
    mesh.uv_layers.new(name="UVMap")
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = root
    asset_core.assign_material(obj, material(semantic_id))
    screw = obj.modifiers.new("Revolve", "SCREW")
    screw.axis = "Z"
    screw.angle = math.tau
    screw.steps = steps
    screw.render_steps = steps
    screw.use_merge_vertices = True
    screw.merge_threshold = 0.0001
    screw.use_smooth_shade = smooth
    screw.use_stretch_u = True
    screw.use_stretch_v = True
    return obj


def ring(root, name, z, radius, *, height, thickness, semantic_id, steps=12, smooth=False):
    hh, ht = height * 0.5, thickness * 0.5
    return profile_revolve(
        root,
        name,
        [
            (z - hh, radius - ht),
            (z - hh, radius + ht),
            (z + hh, radius + ht),
            (z + hh, radius - ht),
        ],
        semantic_id,
        steps=steps,
        smooth=smooth,
        closed=True,
    )


def curve_path(root, name, points, semantic_id, *, bevel=0.035, cyclic=False):
    curve = bpy.data.curves.new(f"{name}_curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = bevel
    curve.bevel_resolution = 0
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (float(co[0]), float(co[1]), float(co[2]), 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = root
    asset_core.assign_material(obj, material(semantic_id))
    return obj


def radial_rib(root, name, angle_deg, samples, *, bevel=0.022):
    a = math.radians(angle_deg)
    points = [(r * math.cos(a), r * math.sin(a), z) for z, r in samples]
    return curve_path(root, name, points, "ritual_gold", bevel=bevel)


def build_potion(root):
    profile_revolve(root, "Body_Profile", [
        (-0.78, 0.00), (-0.78, 0.28), (-0.67, 0.37), (-0.45, 0.45),
        (0.12, 0.45), (0.36, 0.35), (0.50, 0.22), (0.64, 0.17), (0.64, 0.00),
    ], "smoked_glass", steps=10)
    ring(root, "Bottle_Lip", 0.57, 0.19, height=0.10, thickness=0.055,
         semantic_id="smoked_glass", steps=10, smooth=True)
    profile_revolve(root, "Wax_Stopper", [
        (0.57, 0.00), (0.57, 0.155), (0.77, 0.145), (0.83, 0.11), (0.83, 0.00),
    ], "wax", steps=8, smooth=False)
    ring(root, "Cloth_Tie", 0.54, 0.205, height=0.055, thickness=0.035,
         semantic_id="aged_cloth", steps=10)


def build_hi_potion(root):
    profile_revolve(root, "Body_Profile", [
        (-0.92, 0.00), (-0.92, 0.25), (-0.79, 0.35), (-0.55, 0.41),
        (0.30, 0.39), (0.54, 0.29), (0.67, 0.17), (0.78, 0.145), (0.78, 0.00),
    ], "smoked_glass", steps=12)
    ring(root, "Lower_Gold_Collar", -0.54, 0.415, height=0.075, thickness=0.040,
         semantic_id="ritual_gold", steps=12)
    ring(root, "Neck_Gold_Collar", 0.67, 0.185, height=0.075, thickness=0.040,
         semantic_id="ritual_gold", steps=12)
    samples = [(-0.54, 0.425), (0.05, 0.405), (0.48, 0.30), (0.66, 0.19)]
    for index, angle in enumerate((45, 135, 225, 315), start=1):
        radial_rib(root, f"Gold_Rib_{index}", angle, samples, bevel=0.018)
    profile_revolve(root, "Gold_Stopper", [
        (0.73, 0.00), (0.73, 0.15), (0.91, 0.14), (0.96, 0.10), (0.96, 0.00),
    ], "ritual_gold", steps=8, smooth=False)


def build_x_potion(root):
    profile_revolve(root, "Crystal_Biconic_Profile", [
        (-0.78, 0.00), (-0.78, 0.20), (-0.60, 0.39), (-0.18, 0.52),
        (0.24, 0.47), (0.52, 0.30), (0.69, 0.15), (0.69, 0.00),
    ], "crystal", steps=6, smooth=False)
    ring(root, "Reliquary_Equator", -0.10, 0.515, height=0.10, thickness=0.050,
         semantic_id="ritual_gold", steps=6)
    ring(root, "Reliquary_Neck", 0.56, 0.22, height=0.085, thickness=0.050,
         semantic_id="ritual_gold", steps=6)
    profile_revolve(root, "Wax_Seal", [
        (0.62, 0.00), (0.62, 0.15), (0.80, 0.13), (0.86, 0.00),
    ], "wax", steps=6, smooth=False)


def build_mega_potion(root):
    profile_revolve(root, "Canteen_Body_Profile", [
        (-0.87, 0.00), (-0.87, 0.33), (-0.73, 0.51), (-0.45, 0.60),
        (0.31, 0.58), (0.50, 0.45), (0.62, 0.27), (0.73, 0.19), (0.73, 0.00),
    ], "smoked_glass", steps=10)
    ring(root, "Lower_Harness", -0.50, 0.61, height=0.085, thickness=0.045,
         semantic_id="ritual_gold", steps=10)
    ring(root, "Upper_Harness", 0.38, 0.55, height=0.085, thickness=0.045,
         semantic_id="ritual_gold", steps=10)
    ring(root, "Neck_Hardware", 0.64, 0.235, height=0.10, thickness=0.055,
         semantic_id="ritual_gold", steps=10)
    curve_path(root, "Left_Handle", [
        (-0.48, 0.0, 0.49), (-0.66, 0.0, 0.63), (-0.70, 0.0, 0.83), (-0.47, 0.0, 0.91),
    ], "ritual_gold", bevel=0.045)
    curve_path(root, "Right_Handle", [
        (0.48, 0.0, 0.49), (0.66, 0.0, 0.63), (0.70, 0.0, 0.83), (0.47, 0.0, 0.91),
    ], "ritual_gold", bevel=0.045)
    profile_revolve(root, "Heavy_Stopper", [
        (0.67, 0.00), (0.67, 0.18), (0.88, 0.17), (0.94, 0.12), (0.94, 0.00),
    ], "dark_wood", steps=8, smooth=False)
    curve_path(root, "Cloth_Seal_Loop", [
        (0.16, -0.18, 0.67), (0.26, -0.25, 0.47), (0.20, -0.29, 0.24), (0.08, -0.30, 0.09),
    ], "aged_cloth", bevel=0.035)


def build_healing_water(root):
    profile_revolve(root, "Pilgrim_Gourd_Profile", [
        (-0.84, 0.00), (-0.84, 0.23), (-0.69, 0.39), (-0.42, 0.50),
        (-0.16, 0.43), (0.02, 0.27), (0.18, 0.33), (0.38, 0.38),
        (0.56, 0.29), (0.67, 0.16), (0.76, 0.13), (0.76, 0.00),
    ], "crystal", steps=14)
    ring(root, "Gourd_Waist_Binding", 0.01, 0.29, height=0.075, thickness=0.035,
         semantic_id="aged_cloth", steps=14)
    ring(root, "Neck_Binding", 0.64, 0.18, height=0.075, thickness=0.035,
         semantic_id="aged_cloth", steps=14)
    profile_revolve(root, "Wood_Stopper", [
        (0.70, 0.00), (0.70, 0.13), (0.87, 0.13), (0.90, 0.09), (0.90, 0.00),
    ], "dark_wood", steps=8, smooth=False)
    curve_path(root, "Carry_Cord", [
        (-0.14, 0.0, 0.68), (-0.39, 0.0, 0.56), (-0.50, 0.0, 0.24),
        (-0.43, 0.0, -0.05), (-0.26, 0.0, -0.20),
    ], "aged_cloth", bevel=0.030)


def build_ether(root):
    profile_revolve(root, "Ampoule_Profile", [
        (-0.96, 0.00), (-0.96, 0.13), (-0.81, 0.23), (-0.56, 0.27),
        (0.31, 0.25), (0.50, 0.18), (0.61, 0.105), (0.86, 0.085), (0.86, 0.00),
    ], "smoked_glass", steps=8)
    for name, z, radius in (("Calibration_1", -0.42, 0.285),
                            ("Calibration_2", -0.05, 0.275),
                            ("Calibration_3", 0.30, 0.255)):
        ring(root, name, z, radius, height=0.045, thickness=0.025,
             semantic_id="ritual_gold", steps=8)
    profile_revolve(root, "Crystal_Needle_Cap", [
        (0.80, 0.00), (0.80, 0.09), (0.97, 0.07), (1.07, 0.00),
    ], "crystal", steps=6, smooth=False)


BUILDERS = {
    "potion": ("Potion", build_potion),
    "hi_potion": ("Hi-Potion", build_hi_potion),
    "x_potion": ("X-Potion", build_x_potion),
    "mega_potion": ("Mega-Potion", build_mega_potion),
    "healing_water": ("Healing Water", build_healing_water),
    "ether": ("Ether", build_ether),
}


def build_one(stem: str):
    destination = SOURCE_DIR / f"{stem}.blend"
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite authoritative source: {destination}")
    asset_core.reset_scene(factory=True)
    bpy.context.preferences.filepaths.save_version = 0
    _MATERIALS.clear()
    display_name, builder = BUILDERS[stem]
    root = root_for(stem, display_name)
    builder(root)
    asset_core.validate_asset_metadata(root)
    bpy.context.view_layer.objects.active = root
    root.select_set(True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    print(f"WROTE CONSUMABLE SOURCE {destination}")


def main():
    for stem in TARGETS:
        build_one(stem)
    print("CONSUMABLE SOURCE BOOTSTRAP OK")


if __name__ == "__main__":
    main()
