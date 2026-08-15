"""One-shot bootstrap for the second production C item-source cohort.

This materializes four editable Blender documents from the preserved Batch C
path/profile data. The resulting .blend files become source authority after
visual review; this bootstrap is deleted before the PR is considered complete.

The experiment deliberately uses Blender's native Curve bevel-object model:
editable 3D path + editable static profile + per-point radius + per-point tilt.
It does NOT hide the one capability boundary: Batch C could vary X:Y aspect at
each path point, while a native bevel object supplies one profile per path.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import second_rite_asset_core as asset_core

ROOT = SCRIPT_DIR.parents[1]
SOURCE_DIR = ROOT / "assets" / "authoring" / "items"
SOURCE_DIR.mkdir(parents=True, exist_ok=True)

GOLD = "ritual_gold"
BRONZE = "oxidized_bronze"
IRON = "wrought_iron"
CLOTH = "aged_cloth"
GLASS = "smoked_glass"
CRYSTAL = "crystal"
WET = "wet_residue"
WAX = "wax"

MATERIAL_IDS = {GOLD, BRONZE, IRON, CLOTH, GLASS, CRYSTAL, WET, WAX}


def c2b(point):
    """Preserved Batch-C direct-OBJ/Y-up coordinates -> Blender Z-up."""
    x, y, z = point
    return (x, -z, y)


def reset():
    asset_core.reset_scene(factory=True)


def materials():
    result = {mid: asset_core.make_material(mid, semantic_id=mid) for mid in MATERIAL_IDS}
    result[GOLD]["sr_runtime_passes_json"] = json.dumps([
        {"uvSource": "sphere", "blend": "add", "strength": 1.0,
         "texture": "assets/models/matcaps/gold.png"}
    ])
    result[CRYSTAL]["sr_runtime_passes_json"] = json.dumps([
        {"uvSource": "sphere", "blend": "add", "strength": 1.0,
         "texture": "assets/models/matcaps/ruby.png"}
    ])
    return result


def root_for(item_id, description):
    root = bpy.data.objects.new(f"ITEM_{item_id}", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.20
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
            "sr_authoring_grammar": "curve_static_profile",
            "sr_authoring_description": description,
        },
    )
    return root


def profile_polygon(name, *, parent, sides=8, aspect=(1.0, 1.0), phase=0.5):
    """Editable cyclic profile used by a path Curve as bevel_object."""
    curve = bpy.data.curves.new(name + "Data", type="CURVE")
    curve.dimensions = "2D"
    curve.resolution_u = 1
    spline = curve.splines.new("POLY")
    spline.points.add(sides - 1)
    spline.use_cyclic_u = True
    ax, ay = aspect
    for i, point in enumerate(spline.points):
        angle = math.tau * (i + phase) / sides
        point.co = (math.cos(angle) * ax, math.sin(angle) * ay, 0.0, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    asset_core.parent_local(obj, parent)
    obj.hide_render = True
    obj.display_type = "WIRE"
    obj["sr_authoring_role"] = "sweep_profile"
    obj["sr_profile_aspect"] = f"{ax:.4f}:{ay:.4f}"
    return obj


def profile_rectangle(name, *, parent, thickness_ratio):
    """Unit-width rectangle; path-point radius carries authored width."""
    half_t = 0.5 * thickness_ratio
    curve = bpy.data.curves.new(name + "Data", type="CURVE")
    curve.dimensions = "2D"
    spline = curve.splines.new("POLY")
    spline.points.add(3)
    spline.use_cyclic_u = True
    for point, (x, y) in zip(spline.points, [(-0.5,-half_t),(0.5,-half_t),(0.5,half_t),(-0.5,half_t)]):
        point.co = (x, y, 0.0, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    asset_core.parent_local(obj, parent)
    obj.hide_render = True
    obj.display_type = "WIRE"
    obj["sr_authoring_role"] = "ribbon_profile"
    obj["sr_profile_thickness_ratio"] = float(thickness_ratio)
    return obj


def path_curve(name, points, radii, rolls, *, parent, material, profile, cyclic=False, original_aspects=None):
    if len(points) != len(radii) or len(points) != len(rolls):
        raise ValueError(f"{name}: path/radius/roll mismatch")
    curve = bpy.data.curves.new(name + "Data", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.resolution_v = 0
    curve.twist_mode = "MINIMUM"
    curve.bevel_mode = "OBJECT"
    curve.bevel_object = profile
    curve.fill_mode = "FULL"
    curve.use_fill_caps = not cyclic
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    spline.use_cyclic_u = cyclic
    for co, radius, roll, point in zip(points, radii, rolls, spline.points):
        point.co = (*c2b(co), 1.0)
        point.radius = float(radius)
        point.tilt = math.radians(float(roll))
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    asset_core.parent_local(obj, parent)
    asset_core.assign_material(obj, material)
    obj["sr_authoring_role"] = "sweep_path"
    if original_aspects is not None:
        obj["sr_original_per_point_aspect"] = json.dumps(original_aspects)
    return obj


def round_path(name, points, radii, *, parent, material, sides=6, rolls=None, cyclic=False):
    profile = profile_polygon(name + "_PROFILE", parent=parent, sides=sides)
    return path_curve(name, points, radii, rolls or [0.0] * len(points),
                      parent=parent, material=material, profile=profile, cyclic=cyclic)


def ellipse_path(name, points, radii, *, parent, material, aspect, sides=8, rolls=None, cyclic=False, original_aspects=None):
    profile = profile_polygon(name + "_PROFILE", parent=parent, sides=sides, aspect=aspect)
    return path_curve(name, points, radii, rolls or [0.0] * len(points),
                      parent=parent, material=material, profile=profile, cyclic=cyclic,
                      original_aspects=original_aspects)


def ribbon_path(name, points, widths, thickness, *, parent, material, rolls=None):
    ratios = [t / w for t, w in zip(thickness, widths)]
    ratio = sum(ratios) / len(ratios)
    profile = profile_rectangle(name + "_PROFILE", parent=parent, thickness_ratio=ratio)
    obj = path_curve(name, points, widths, rolls or [0.0] * len(points),
                     parent=parent, material=material, profile=profile)
    obj["sr_original_per_point_thickness"] = json.dumps(thickness)
    obj["sr_static_profile_ratio"] = ratio
    return obj


def ellipse_loop(cx, cy, cz, rx, rz, *, tilt=0.0, points=12):
    result = []
    t = math.radians(tilt)
    for i in range(points):
        a = math.tau * i / points
        x = cx + rx * math.cos(a)
        y = cy + rz * math.sin(a) * math.sin(t)
        z = cz + rz * math.sin(a) * math.cos(t)
        result.append((x, y, z))
    return result


def authoring_readme(item_id, text):
    block = bpy.data.texts.new("AUTHORING_README")
    block.write(
        f"Production item source: {item_id}\n\n{text}\n\n"
        "Visible geometry is driven by editable 3D Curve paths. Objects ending _PROFILE are hidden from runtime export and define the path cross-section. Path point radius controls taper; tilt controls roll.\n"
        "This cohort intentionally uses one static profile per path. Preserved Batch-C per-point aspect/thickness data remains as custom properties where it varied.\n"
        "Runtime OBJ/MTL are compiled read-only through tools/blender/compile_item_blends.py.\n"
    )


def save(item_id):
    path = SOURCE_DIR / f"{item_id}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
    print(f"WROTE PROFILE SOURCE {path.relative_to(ROOT)}")


def build_hermes_boots():
    reset(); mat = materials(); root = root_for("hermes_boots", "Paired boots built from rolled ellipse paths, ribbon soles/wings and closed ankle loops")
    for xoff, mirror, label in [(-0.24, -1.0, "L"), (0.24, 1.0, "R")]:
        body_points = [(xoff,-0.54,0.45),(xoff,-0.50,0.17),(xoff,-0.45,-0.10),(xoff,-0.25,-0.25),(xoff+0.02*mirror,0.08,-0.27),(xoff+0.04*mirror,0.43,-0.24)]
        body_aspects = [(1.15,0.72),(1.20,0.68),(1.05,0.72),(0.90,0.85),(0.82,0.92),(0.90,0.95)]
        ellipse_path(f"C_Boot_{label}", body_points, [0.22,0.27,0.25,0.22,0.20,0.22], parent=root, material=mat[CLOTH], aspect=(1.00,0.81), sides=8, rolls=[90,90,86,72,35,12], original_aspects=body_aspects)
        ribbon_path(f"C_Sole_{label}", [(xoff,-0.68,0.48),(xoff,-0.65,0.18),(xoff,-0.61,-0.12),(xoff,-0.52,-0.28)], [0.34,0.39,0.34,0.26], [0.055]*4, parent=root, material=mat[IRON], rolls=[90,90,88,78])
        origins = [(0.38,-0.02,-0.21,0.42),(0.31,0.10,-0.22,0.33),(0.24,0.20,-0.23,0.25)]
        for i,(reach,y,z,rise) in enumerate(origins):
            points=[(xoff+0.17*mirror,y,z),(xoff+(0.17+reach*0.55)*mirror,y+rise*0.45,z+0.04),(xoff+(0.17+reach)*mirror,y+rise,z+0.01)]
            ribbon_path(f"C_Wing_{label}_{i}", points, [0.10,0.075,0.028], [0.045,0.035,0.018], parent=root, material=mat[CRYSTAL], rolls=[0,15*mirror,28*mirror])
        round_path(f"C_Ankle_{label}", ellipse_loop(xoff,-0.03,-0.26,0.24,0.18,tilt=75,points=10), [0.028]*10, parent=root, material=mat[GOLD], sides=5, cyclic=True)
    authoring_readme("hermes_boots", "Boot bodies intentionally preserve the original changing aspect table as object metadata. The visible native source uses a representative ellipse; this is the cohort's main fidelity test.")
    save("hermes_boots")


def build_mimic_tongue():
    reset(); mat = materials(); root = root_for("mimic_tongue", "Muscular broad tongue loft with editable profile, groove, veins and drool gestures")
    points=[(0.00,0.82,-0.30),(-0.08,0.58,-0.16),(0.04,0.30,0.02),(0.18,0.02,0.20),(0.05,-0.26,0.38),(-0.13,-0.48,0.31),(-0.05,-0.70,0.12)]
    aspects=[(1.65,0.58),(1.72,0.60),(1.78,0.62),(1.70,0.64),(1.55,0.62),(1.35,0.58),(1.05,0.48)]
    ellipse_path("C_Tongue", points, [0.19,0.215,0.235,0.225,0.18,0.115,0.035], parent=root, material=mat[WET], aspect=(1.57,0.59), sides=8, rolls=[10,18,32,46,70,95,118], original_aspects=aspects)
    round_path("C_Groove", [(0.00,0.73,-0.15),(-0.04,0.45,0.02),(0.07,0.16,0.20),(0.12,-0.12,0.36),(0.01,-0.38,0.34)], [0.016,0.020,0.021,0.016,0.006], parent=root, material=mat[GLASS], sides=5)
    round_path("C_Vein_L", [(-0.10,0.67,-0.20),(-0.12,0.37,-0.02),(0.02,0.05,0.18),(0.05,-0.30,0.34),(-0.05,-0.54,0.24)], [0.014,0.018,0.019,0.014,0.006], parent=root, material=mat[CRYSTAL], sides=5)
    round_path("C_Vein_R", [(0.10,0.65,-0.20),(0.06,0.35,0.00),(0.15,0.08,0.18),(0.16,-0.18,0.30)], [0.013,0.017,0.014,0.005], parent=root, material=mat[CRYSTAL], sides=5)
    round_path("C_Drool", [(0.13,-0.14,0.42),(0.18,-0.38,0.49),(0.12,-0.58,0.47)], [0.021,0.016,0.005], parent=root, material=mat[GLASS], sides=5)
    authoring_readme("mimic_tongue", "Edit C_Tongue and C_Tongue_PROFILE together for the gross silhouette; groove/veins/drool remain independent paths. The original per-point aspect table is preserved on C_Tongue.")
    save("mimic_tongue")


def build_molten_manacle():
    reset(); mat = materials(); root = root_for("molten_manacle", "Irregular closed cuff, chain loops and drips authored as editable cyclic and open Curve paths")
    cuff=[]
    for i in range(14):
        a=math.tau*i/14; r=0.55+0.045*math.sin(a*3+0.6)
        cuff.append((r*math.cos(a),0.10*math.sin(a*2),0.42*math.sin(a)))
    round_path("C_Cuff", cuff, [0.105+0.018*math.sin(i*1.7) for i in range(14)], parent=root, material=mat[BRONZE], sides=7, rolls=[i*11 for i in range(14)], cyclic=True)
    round_path("C_Link_1", ellipse_loop(0.56,-0.10,0.04,0.23,0.33,tilt=22,points=10), [0.070]*10, parent=root, material=mat[IRON], sides=6, cyclic=True)
    round_path("C_Link_2", ellipse_loop(0.84,-0.36,0.10,0.22,0.31,tilt=64,points=10), [0.064]*10, parent=root, material=mat[IRON], sides=6, cyclic=True)
    round_path("C_Drip_1", [(0.18,-0.35,0.31),(0.22,-0.62,0.35),(0.18,-0.82,0.30)], [0.040,0.028,0.006], parent=root, material=mat[WAX], sides=5)
    round_path("C_Drip_2", [(-0.30,-0.29,-0.26),(-0.34,-0.50,-0.30),(-0.30,-0.65,-0.29)], [0.032,0.022,0.006], parent=root, material=mat[WAX], sides=5)
    authoring_readme("molten_manacle", "C_Cuff and both C_Link objects are genuinely cyclic source splines; there is no seam object or baked loop mesh.")
    save("molten_manacle")


def build_phoenix_pinion():
    reset(); mat = materials(); root = root_for("phoenix_pinion", "Continuous flattened feather body with gold rachis, sparse ribbon vanes and ember tip")
    body_points=[(0.00,-0.68,0.00),(0.02,-0.46,0.02),(-0.01,-0.18,0.06),(0.04,0.12,0.12),(0.01,0.40,0.17),(-0.04,0.66,0.16),(-0.03,0.86,0.11),(0.00,1.02,0.05)]
    aspects=[(1.35,0.24),(1.55,0.20),(1.70,0.18),(1.78,0.17),(1.72,0.17),(1.58,0.18),(1.38,0.20),(1.0,0.25)]
    ellipse_path("C_Pinion_Body", body_points, [0.07,0.22,0.34,0.42,0.45,0.37,0.23,0.045], parent=root, material=mat[CRYSTAL], aspect=(1.51,0.20), sides=8, rolls=[-6,-2,3,8,14,21,30,40], original_aspects=aspects)
    round_path("C_Pinion_Spine", [(0.00,-0.82,0.00),(0.02,-0.50,0.02),(-0.02,-0.18,0.07),(0.04,0.16,0.13),(0.00,0.50,0.18),(-0.05,0.78,0.16),(0.00,1.02,0.08)], [0.045,0.055,0.060,0.055,0.048,0.036,0.015], parent=root, material=mat[GOLD], sides=6, rolls=[0,8,18,30,45,60,78])
    specs=[((0.00,-0.36,0.04),0.31,0.06,0.08),((0.02,0.02,0.10),0.38,0.08,0.12),((0.01,0.38,0.17),0.34,0.08,0.13),((-0.03,0.66,0.15),0.25,0.06,0.10)]
    for i,(origin,reach,lift,depth) in enumerate(specs):
        ox,oy,oz=origin
        for side in (-1,1):
            points=[(ox+side*reach*0.48,oy+lift*0.30,oz+depth*0.35),(ox+side*reach*0.78,oy+lift*0.62,oz+depth*0.70),(ox+side*reach,oy+lift,oz+depth*(1.0 if side>0 else 0.78))]
            ribbon_path(f"C_Vane_{i}_{'R' if side>0 else 'L'}", points, [0.075,0.050,0.014], [0.025,0.018,0.008], parent=root, material=mat[CRYSTAL], rolls=[side*8,side*(20+i*2),side*(31+i*3)])
    round_path("C_Ember", [(0.00,-0.78,0.01),(0.02,-0.92,0.03),(0.00,-1.04,0.00)], [0.040,0.055,0.012], parent=root, material=mat[WAX], sides=6)
    authoring_readme("phoenix_pinion", "The feather mass is one editable flattened profile sweep, not a ladder of strips. Eight sparse vane ribbons remain separate source gestures. The original changing body aspect table is preserved on C_Pinion_Body.")
    save("phoenix_pinion")


for builder in (build_hermes_boots, build_mimic_tongue, build_molten_manacle, build_phoenix_pinion):
    builder()
