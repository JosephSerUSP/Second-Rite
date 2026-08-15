"""Blender-native found-object cohort for Second Gate.

Batch B is deliberately unlike build_relic_showcase.py. The relic cohort leaned
into lathed profiles, rings, radial repetition and heraldic symmetry. This
cohort uses Blender as the modeling compiler directly: custom extrusions,
polyline tubes, booleans, off-axis primitives and visibly incomplete /
asymmetric construction.

The six replacements are existing item models, so gameplay data is untouched:
Cerberus Fang, Mimic Tongue, Forbidden Lamp, Pile Bunker, Celestial Fossil,
and Phoenix Pinion.

Run from repository root:
    blender --background --factory-startup --python tools/asset-production/build_found_object_showcase.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import second_rite_asset_core as asset_core

OUT = ROOT / "assets" / "models" / "items"
OUT.mkdir(parents=True, exist_ok=True)

asset_core.reset_scene(factory=False)
COLLECTION = asset_core.ensure_collection("Found Object Showcase")
CUTTER_COLLECTION = asset_core.ensure_collection("Found Object Boolean Cutters")
ROOTS = []

# Geometry carries almost all of the expression in this cohort. Unlike Batch A,
# the generator intentionally authors no matcap/overlay post-processing.
MATERIAL_IDS = (
    "rough_limestone", "ritual_gold", "oxidized_bronze", "wrought_iron",
    "dark_wood", "aged_cloth", "smoked_glass", "wet_residue", "bone",
    "wax", "crystal",
)
MAT = {
    material_id: asset_core.make_material(material_id, semantic_id=material_id)
    for material_id in MATERIAL_IDS
}


def root(display_name: str, export_name: str, description: str):
    obj = bpy.data.objects.new(display_name, None)
    COLLECTION.objects.link(obj)
    obj["item_export"] = True
    obj["item_export_name"] = export_name
    obj["item_display_name"] = display_name
    obj["item_category"] = "found_object_showcase"
    obj["item_description"] = description
    asset_core.tag_asset_target(
        obj,
        asset_id=export_name,
        representation="full_model",
        role="item_display",
        authoring_space="item_display",
        placement_frame="item_viewport",
        states=["default"],
        default_state="default",
        variants=[],
    )
    asset_core.validate_asset_metadata(obj)
    ROOTS.append(obj)
    return obj


def select_only(obj):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def smart_uv(obj):
    if obj.type != "MESH" or not obj.data.polygons:
        return obj
    select_only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project()
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


def finish_mesh(obj, parent, material, *, bevel=0.0,
                loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    asset_core.move_to_collection(obj, COLLECTION)
    asset_core.parent_local(obj, parent, loc, rot, scale)
    asset_core.assign_material(obj, MAT[material])
    if bevel > 0:
        asset_core.add_bevel_modifier(obj, bevel, 1)
    asset_core.flat_shade(obj)
    smart_uv(obj)
    return obj


def add_box(parent, name, loc, dims, material, *, rot=(0, 0, 0), bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(
        obj, parent, material, bevel=bevel, loc=loc, rot=rot,
        scale=(dims[0] / 2, dims[1] / 2, dims[2] / 2),
    )


def add_ico(parent, name, loc, scale, material, *, subdivisions=1, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=subdivisions, radius=1, location=(0, 0, 0)
    )
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(obj, parent, material, loc=loc, rot=rot, scale=scale)


def add_cylinder(parent, name, loc, radius, depth, material, *,
                 vertices=8, rot=(0, 0, 0), bevel=0.02):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth,
        end_fill_type="NGON", location=(0, 0, 0),
    )
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(obj, parent, material, bevel=bevel, loc=loc, rot=rot)


def add_cone_between(parent, name, p1, p2, r1, r2, material, *, vertices=8, bevel=0.0):
    p1, p2 = Vector(p1), Vector(p2)
    direction = p2 - p1
    length = direction.length
    if length <= 1e-6:
        raise ValueError(f"{name}: zero-length cone segment")
    midpoint = (p1 + p2) * 0.5
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices, radius1=r1, radius2=r2,
        depth=length, location=(0, 0, 0),
    )
    obj = bpy.context.object
    obj.name = name
    obj = finish_mesh(obj, parent, material, bevel=bevel, loc=midpoint)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    return obj


def add_cylinder_between(parent, name, p1, p2, radius, material, *, vertices=7, bevel=0.0):
    return add_cone_between(
        parent, name, p1, p2, radius, radius, material,
        vertices=vertices, bevel=bevel,
    )


def add_prism(parent, name, outline_xz, depth, material, *,
              loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.025):
    """Extrude a convex XZ polygon along Y, then Smart-UV it."""
    n = len(outline_xz)
    if n < 3:
        raise ValueError("prism outline needs at least three points")
    verts = []
    for y in (-depth / 2, depth / 2):
        verts.extend((x, y, z) for x, z in outline_xz)
    faces = []
    for i in range(1, n - 1):
        faces.append((0, i + 1, i))
        faces.append((n, n + i, n + i + 1))
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    COLLECTION.objects.link(obj)
    return finish_mesh(obj, parent, material, bevel=bevel, loc=loc, rot=rot)


def add_tube(parent, name, points, radius, material):
    """Bent low-poly tube from an explicit path, frozen to a mesh."""
    curve = bpy.data.curves.new(name + "Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 0
    curve.fill_mode = "FULL"
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, value in zip(spline.points, points):
        point.co = (*value, 1.0)
    obj = bpy.data.objects.new(name, curve)
    COLLECTION.objects.link(obj)
    asset_core.parent_local(obj, parent)
    asset_core.assign_material(obj, MAT[material])

    # Freeze curve evaluation now so OBJ output is a deterministic mesh and can
    # be Smart-UV'd under the same rules as the custom extrusions.
    select_only(obj)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    asset_core.flat_shade(obj)
    smart_uv(obj)
    return obj


def add_boolean_hole(target, name, loc, radius, depth, *, vertices=10):
    """Cut a real void through target; the cutter itself is never exported."""
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth,
        end_fill_type="NGON", location=loc,
        rotation=(math.radians(90), 0, 0),
    )
    cutter = bpy.context.object
    cutter.name = name
    asset_core.move_to_collection(cutter, CUTTER_COLLECTION)
    cutter.hide_render = True
    cutter.hide_set(True)
    asset_core.add_boolean_modifier(target, cutter, "DIFFERENCE")
    return cutter


def add_leaf_prism(parent, name, inner, outer, half_width, depth, material, *,
                   y=0.0, bevel=0.018):
    """One tapered feather/flesh vane as a convex quadrilateral."""
    ix, iz = inner
    ox, oz = outer
    dx, dz = ox - ix, oz - iz
    length = math.hypot(dx, dz)
    if length <= 1e-6:
        raise ValueError(f"{name}: zero-length vane")
    px, pz = -dz / length, dx / length
    outline = [
        (ix + px * half_width * 0.55, iz + pz * half_width * 0.55),
        (ox + px * half_width, oz + pz * half_width),
        (ox - px * half_width * 0.65, oz - pz * half_width * 0.65),
        (ix - px * half_width * 0.55, iz - pz * half_width * 0.55),
    ]
    return add_prism(
        parent, name, outline, depth, material,
        loc=(0, y, 0), bevel=bevel,
    )


# 1. Cerberus Fang — curved, scarred, physically repaired.
def build_cerberus_fang():
    r = root(
        "Cerberus Fang", "cerberus_fang",
        "A hooked triple-scarred fang held together by crude iron staples.",
    )
    points = [
        (-0.92, 0.00, -0.72), (-0.70, 0.03, -0.36),
        (-0.40, -0.02, -0.02), (-0.06, 0.03, 0.28),
        (0.32, -0.03, 0.52), (0.68, 0.02, 0.68),
        (0.98, -0.02, 0.72), (1.18, 0.00, 0.64),
    ]
    radii = [0.34, 0.31, 0.27, 0.22, 0.17, 0.12, 0.075, 0.025]
    for i in range(len(points) - 1):
        add_cone_between(
            r, f"FangSegment{i}", points[i], points[i + 1],
            radii[i], radii[i + 1], "bone", vertices=7,
        )
    add_ico(r, "RootTissue", (-0.93, 0.03, -0.74),
            (0.42, 0.31, 0.34), "wet_residue")
    for i, z in enumerate((-0.57, -0.43, -0.27)):
        x = -0.79 + (z + 0.57) * 0.55
        add_tube(
            r, f"Staple{i}",
            [(x - 0.18, -0.26, z - 0.04), (x - 0.20, -0.33, z + 0.10),
             (x + 0.17, -0.33, z + 0.12), (x + 0.19, -0.25, z - 0.02)],
            0.025, "wrought_iron",
        )
    barbs = [
        ((-0.18, 0.01, 0.18), (-0.36, 0.00, 0.52), 0.11),
        ((0.30, -0.02, 0.50), (0.18, -0.03, 0.78), 0.085),
        ((0.68, 0.01, 0.66), (0.62, 0.02, 0.89), 0.06),
    ]
    for i, (a, b, rr) in enumerate(barbs):
        add_cone_between(r, f"Barb{i}", a, b, rr, 0.0, "bone", vertices=6)
    return r


# 2. Mimic Tongue — broad flesh, forked tip, uneven papillae, curl.
def build_mimic_tongue():
    r = root(
        "Mimic Tongue", "mimic_tongue",
        "A severed mimic tongue: broad at the root, asymmetrically forked and still curled.",
    )
    trunk = [
        (-0.52, -0.96), (0.43, -0.91), (0.39, -0.25),
        (0.31, 0.28), (0.14, 0.58), (-0.20, 0.54), (-0.40, 0.14),
    ]
    add_prism(r, "TongueBody", trunk, 0.22, "wet_residue", bevel=0.08)
    add_leaf_prism(r, "LeftFork", (-0.10, 0.43), (-0.88, 1.25),
                   0.18, 0.18, "wet_residue", y=-0.02, bevel=0.06)
    right = add_leaf_prism(r, "RightFork", (0.12, 0.45), (0.66, 1.02),
                           0.15, 0.16, "wet_residue", y=0.07, bevel=0.05)
    right.rotation_euler.x = math.radians(-13)
    add_leaf_prism(r, "TornUnderside", (-0.27, -0.73), (0.12, 0.34),
                   0.14, 0.235, "aged_cloth", y=0.01, bevel=0.025)
    papillae = [
        (-0.33, -0.16, -0.55, 0.08), (0.31, -0.16, -0.34, 0.06),
        (-0.26, -0.16, -0.05, 0.07), (0.24, -0.16, 0.18, 0.055),
        (-0.42, -0.10, 0.53, 0.05),
    ]
    for i, (x, y, z, s) in enumerate(papillae):
        add_ico(r, f"Papilla{i}", (x, y, z),
                (s, s * 0.7, s * 1.25), "bone")
    add_tube(
        r, "SalivaThread",
        [(0.24, -0.17, 0.12), (0.36, -0.25, -0.05), (0.43, -0.28, -0.28)],
        0.018, "crystal",
    )
    return r


# 3. Forbidden Lamp — crooked cage; empty space is the main form.
def build_forbidden_lamp():
    r = root(
        "Forbidden Lamp", "forbidden_lamp",
        "A crooked open cage around a cold shard; one side has snapped and hangs loose.",
    )
    add_box(r, "Foot", (0.0, 0.0, -0.88),
            (0.78, 0.52, 0.18), "wrought_iron", bevel=0.06)
    add_box(r, "LowerTray", (-0.04, 0.0, -0.70),
            (0.62, 0.44, 0.12), "oxidized_bronze", bevel=0.04)
    paths = {
        "LeftFront": [(-0.31, -0.22, -0.64), (-0.43, -0.24, -0.10), (-0.30, -0.23, 0.58)],
        "LeftBack": [(-0.29, 0.21, -0.62), (-0.36, 0.23, 0.08), (-0.22, 0.20, 0.63)],
        "RightBack": [(0.28, 0.20, -0.63), (0.37, 0.22, -0.02), (0.18, 0.18, 0.66)],
        "BrokenRight": [(0.31, -0.21, -0.63), (0.40, -0.22, -0.20), (0.34, -0.24, 0.18)],
    }
    for name, pts in paths.items():
        add_tube(r, name, pts, 0.045, "wrought_iron")
    add_tube(
        r, "Roof",
        [(-0.30, -0.23, 0.58), (-0.05, -0.25, 0.78),
         (0.22, 0.18, 0.66), (-0.22, 0.20, 0.63)],
        0.05, "wrought_iron",
    )
    add_tube(
        r, "DanglingBrokenBar",
        [(0.32, -0.24, 0.22), (0.52, -0.30, 0.38), (0.45, -0.35, 0.03)],
        0.038, "wrought_iron",
    )
    add_tube(
        r, "Hook",
        [(-0.03, 0.00, 0.76), (0.04, 0.00, 1.04),
         (0.25, 0.00, 1.14), (0.37, 0.00, 1.02), (0.29, 0.00, 0.91)],
        0.055, "oxidized_bronze",
    )
    add_ico(r, "ColdShard", (-0.05, -0.02, -0.02),
            (0.25, 0.17, 0.62), "crystal")
    add_cylinder(r, "Wick", (-0.06, -0.02, -0.47),
                 0.06, 0.36, "wax", vertices=6)
    return r


# 4. Pile Bunker — mass, rails and an offset pressure mechanism.
def build_pile_bunker():
    r = root(
        "Pile Bunker", "pile_bunker",
        "A brutal compact impact tool with an exposed rail spike and offset side chamber.",
    )
    add_box(r, "MainHousing", (0.0, 0.0, -0.05),
            (0.86, 0.62, 1.02), "wrought_iron", bevel=0.08)
    add_box(r, "BackPlate", (-0.06, 0.02, -0.62),
            (0.98, 0.72, 0.18), "oxidized_bronze", bevel=0.04)
    blade = [(-0.14, 0.18), (0.14, 0.18), (0.11, 1.28),
             (0.0, 1.66), (-0.11, 1.28)]
    add_prism(r, "DriverSpike", blade, 0.20, "wrought_iron", bevel=0.018)
    add_box(r, "RailL", (-0.28, 0.0, 0.72),
            (0.10, 0.18, 1.22), "oxidized_bronze", bevel=0.025)
    add_box(r, "RailR", (0.28, 0.0, 0.72),
            (0.10, 0.18, 1.22), "oxidized_bronze", bevel=0.025)
    add_box(r, "DriverCollar", (0.0, -0.02, 0.34),
            (0.58, 0.54, 0.18), "ritual_gold", bevel=0.035)
    add_cylinder(r, "SideChamber", (0.51, 0.02, -0.13),
                 0.24, 0.70, "oxidized_bronze", vertices=8,
                 rot=(math.radians(90), 0, 0))
    add_cylinder_between(r, "GripStem",
                         (-0.30, 0.0, -0.40), (-0.74, 0.05, -1.05),
                         0.10, "dark_wood", vertices=7)
    add_box(r, "GripHeel", (-0.79, 0.05, -1.12),
            (0.28, 0.30, 0.20), "dark_wood",
            rot=(0, math.radians(-8), math.radians(-18)), bevel=0.05)
    add_cylinder_between(r, "CrankAxle",
                         (0.42, -0.38, -0.22), (0.42, -0.66, -0.22),
                         0.055, "wrought_iron", vertices=6)
    add_cylinder_between(r, "CrankArm",
                         (0.42, -0.66, -0.22), (0.67, -0.69, -0.36),
                         0.055, "wrought_iron", vertices=6)
    for i, (x, z) in enumerate(((-0.30, -0.42), (0.29, -0.40),
                                (-0.31, 0.18), (0.30, 0.16))):
        add_ico(r, f"Bolt{i}", (x, -0.34, z),
                (0.075, 0.045, 0.075), "ritual_gold")
    return r


# 5. Celestial Fossil — irregular slab, real boolean void, raised fossil.
def build_celestial_fossil():
    r = root(
        "Celestial Fossil", "celestial_fossil",
        "An irregular stone fragment with a bored-through void and a bone spiral fossil.",
    )
    outline = [
        (-0.92, -0.86), (-0.20, -1.05), (0.67, -0.82), (0.93, -0.25),
        (0.78, 0.53), (0.26, 0.96), (-0.46, 0.88), (-0.95, 0.34),
    ]
    slab = add_prism(r, "StoneSlab", outline, 0.34,
                     "rough_limestone", bevel=0.07)
    add_boolean_hole(slab, "AncientBore", (0.47, 0.0, 0.40),
                     0.22, 1.1, vertices=9)
    spiral = []
    cx, cz = (-0.16, -0.02)
    for i in range(24):
        t = i / 23
        angle = t * math.pi * 3.75
        rr = 0.06 + t * 0.48
        spiral.append((cx + rr * math.cos(angle), -0.205,
                       cz + rr * math.sin(angle)))
    add_tube(r, "BoneSpiral", spiral, 0.045, "bone")
    add_tube(r, "VeinA",
             [(-0.77, -0.215, 0.38), (-0.51, -0.225, 0.22),
              (-0.34, -0.218, -0.02)],
             0.025, "crystal")
    add_tube(r, "VeinB",
             [(0.12, -0.216, -0.63), (0.28, -0.222, -0.42),
              (0.58, -0.218, -0.31)],
             0.022, "crystal")
    add_ico(r, "EmbeddedNodule", (-0.62, -0.24, -0.46),
            (0.13, 0.07, 0.17), "oxidized_bronze")
    return r


# 6. Phoenix Pinion — linear repetition, missing chunks and charred edge.
def build_phoenix_pinion():
    r = root(
        "Phoenix Pinion", "phoenix_pinion",
        "A broad pinion with an arcing quill, uneven vanes, missing bites and a charred edge.",
    )
    shaft = [
        (-0.42, 0.02, -1.05), (-0.30, 0.00, -0.62),
        (-0.16, -0.01, -0.18), (-0.02, 0.00, 0.27),
        (0.08, 0.01, 0.70), (0.12, 0.00, 1.12),
    ]
    add_tube(r, "Quill", shaft, 0.065, "bone")
    left = [
        ((-0.30, -0.64), (-0.92, -0.76), 0.11),
        ((-0.24, -0.43), (-1.08, -0.48), 0.12),
        ((-0.17, -0.20), (-1.18, -0.10), 0.13),
        ((-0.09, 0.05), (-1.16, 0.27), 0.13),
        ((-0.02, 0.30), (-1.02, 0.58), 0.12),
        ((0.04, 0.55), (-0.76, 0.84), 0.105),
        ((0.09, 0.79), (-0.47, 1.03), 0.09),
    ]
    right = [
        ((-0.28, -0.58), (0.55, -0.75), 0.10),
        ((-0.21, -0.34), (0.79, -0.40), 0.12),
        # deliberate missing vane around z ~= -0.05
        ((-0.06, 0.17), (0.92, 0.32), 0.12),
        ((0.01, 0.42), (0.88, 0.62), 0.11),
        ((0.07, 0.66), (0.69, 0.88), 0.095),
        ((0.11, 0.86), (0.46, 1.08), 0.075),
    ]
    for i, (inner, outer, width) in enumerate(left):
        add_leaf_prism(r, f"LeftVane{i}", inner, outer, width,
                       0.085, "wax", y=-0.015 - i * 0.004, bevel=0.02)
    for i, (inner, outer, width) in enumerate(right):
        material = "wrought_iron" if i in (3, 4) else "wax"
        add_leaf_prism(r, f"RightVane{i}", inner, outer, width,
                       0.082, material, y=0.02 + i * 0.005, bevel=0.02)
    for i, (inner, outer) in enumerate((
        ((-0.07, 0.08), (-0.72, 0.23)),
        ((0.02, 0.43), (0.60, 0.58)),
        ((0.07, 0.68), (-0.36, 0.86)),
    )):
        add_cylinder_between(
            r, f"GoldScar{i}",
            (inner[0], -0.08, inner[1]),
            (outer[0], -0.08, outer[1]),
            0.018, "ritual_gold", vertices=5,
        )
    return r


BUILDERS = (
    build_cerberus_fang,
    build_mimic_tongue,
    build_forbidden_lamp,
    build_pile_bunker,
    build_celestial_fossil,
    build_phoenix_pinion,
)


def build():
    roots = [builder() for builder in BUILDERS]
    outputs = []
    for item_root in roots:
        outputs.extend(
            asset_core.export_asset_root(
                bpy.context, item_root, OUT,
                export_shape_keys=False,
                center_mode="BOUNDS",
            )
        )
    result = {
        "batch": "found_object_showcase",
        "items": [item_root["item_display_name"] for item_root in roots],
        "outputs": [str(Path(path).relative_to(ROOT)) for path in outputs],
    }
    print("FOUND_OBJECT_SHOWCASE_RESULT=" + json.dumps(result, sort_keys=True))
    return result


if __name__ == "__main__":
    build()
