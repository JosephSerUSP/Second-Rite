"""One-shot bootstrap for the last two salvaged item Blender sources.

This script exists only to create the initial authoritative .blend documents for
Pile Bunker and Celestial Fossil. It must be deleted after visual acceptance.
Once saved, the .blend files themselves are source authority.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import second_rite_asset_core as core

SOURCE_DIR = ROOT / "assets" / "authoring" / "items"
SOURCE_DIR.mkdir(parents=True, exist_ok=True)


def reset():
    core.reset_scene(factory=True)
    bpy.context.preferences.filepaths.save_version = 0


def materials():
    ids = (
        "rough_limestone",
        "ritual_gold",
        "oxidized_bronze",
        "wrought_iron",
        "dark_wood",
        "bone",
        "crystal",
    )
    return {mid: core.make_material(mid, semantic_id=mid) for mid in ids}


def make_root(item_id: str, description: str):
    root = bpy.data.objects.new(f"ITEM_{item_id}", None)
    bpy.context.scene.collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.22
    root["item_export"] = True
    root["item_export_name"] = item_id
    root["sr_source_authority"] = "blend"
    root["sr_authoring_description"] = description
    core.tag_asset_target(
        root,
        asset_id=item_id,
        representation="full_model",
        role="item_display",
        authoring_space="item_display",
        placement_frame="item_viewport",
        states=["default"],
        default_state="default",
        variants=[],
        extra={"sr_source_authority": "blend"},
    )
    return root


def select_only(obj):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def smart_uv(obj):
    if obj.type != "MESH" or not obj.data.polygons:
        return
    select_only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")


def apply_bevel(obj, width=0.0):
    if width <= 0.0:
        return
    select_only(obj)
    mod = obj.modifiers.new("SourceBevel", "BEVEL")
    mod.width = width
    mod.segments = 1
    mod.limit_method = "ANGLE"
    bpy.ops.object.modifier_apply(modifier=mod.name)


def finish_mesh(obj, parent, material, *, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1), bevel=0.0):
    obj.parent = parent
    obj.location = location
    obj.rotation_euler = rotation
    obj.scale = scale
    select_only(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    core.assign_material(obj, material)
    apply_bevel(obj, bevel)
    smart_uv(obj)
    return obj


def add_box(parent, name, location, dimensions, material, *, rotation=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=2)
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(
        obj,
        parent,
        material,
        location=location,
        rotation=rotation,
        scale=(dimensions[0] / 2, dimensions[1] / 2, dimensions[2] / 2),
        bevel=bevel,
    )


def add_cylinder(parent, name, location, radius, depth, material, *, vertices=8, rotation=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, end_fill_type="NGON")
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(obj, parent, material, location=location, rotation=rotation, bevel=bevel)


def add_ico(parent, name, location, scale, material):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1)
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(obj, parent, material, location=location, scale=scale)


def add_prism(parent, name, outline_xz, depth, material, *, bevel=0.0):
    n = len(outline_xz)
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
    bpy.context.scene.collection.objects.link(obj)
    return finish_mesh(obj, parent, material, bevel=bevel)


def add_cylinder_between(parent, name, p1, p2, radius, material, *, vertices=7):
    p1 = Vector(p1)
    p2 = Vector(p2)
    direction = p2 - p1
    length = direction.length
    if length <= 1e-6:
        raise ValueError(f"{name}: zero-length segment")
    midpoint = (p1 + p2) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=length, end_fill_type="NGON")
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = midpoint
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    core.assign_material(obj, material)
    smart_uv(obj)
    return obj


def add_curve(parent, name, points, material, bevel_depth, *, radii=None, cyclic=False):
    curve = bpy.data.curves.new(name + "Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.resolution_v = 0
    curve.bevel_resolution = 0
    curve.bevel_depth = bevel_depth
    curve.fill_mode = "FULL"
    if hasattr(curve, "use_fill_caps"):
        curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    radii = radii or [1.0] * len(points)
    for co, radius, point in zip(points, radii, spline.points):
        point.co = (*co, 1.0)
        point.radius = radius
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    core.assign_material(obj, material)
    return obj


def authoring_note(item_id: str, text: str):
    block = bpy.data.texts.new("AUTHORING_README")
    block.write(
        f"Second Gate authoritative item source: {item_id}\n\n{text}\n\n"
        "This .blend is source authority. Edit the named semantic objects directly; "
        "compile read-only with tools/blender/compile_item_blends.py.\n"
    )


def save(item_id: str):
    path = SOURCE_DIR / f"{item_id}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print("SAVED FINAL SALVAGED SOURCE", path)


def build_pile_bunker():
    reset()
    mat = materials()
    root = make_root(
        "pile_bunker",
        "Compact impact tool assembled from a housing, exposed driver, rails, pressure chamber, grip, crank and bolts.",
    )

    add_box(root, "B_MainHousing", (0.0, 0.0, -0.05), (0.86, 0.62, 1.02), mat["wrought_iron"], bevel=0.08)
    add_box(root, "B_BackPlate", (-0.06, 0.02, -0.62), (0.98, 0.72, 0.18), mat["oxidized_bronze"], bevel=0.04)

    driver = [(-0.14, 0.18), (0.14, 0.18), (0.11, 1.28), (0.0, 1.66), (-0.11, 1.28)]
    add_prism(root, "B_DriverSpike", driver, 0.20, mat["wrought_iron"], bevel=0.018)
    add_box(root, "B_Rail_L", (-0.28, 0.0, 0.72), (0.10, 0.18, 1.22), mat["oxidized_bronze"], bevel=0.025)
    add_box(root, "B_Rail_R", (0.28, 0.0, 0.72), (0.10, 0.18, 1.22), mat["oxidized_bronze"], bevel=0.025)
    add_box(root, "B_DriverCollar", (0.0, -0.02, 0.34), (0.58, 0.54, 0.18), mat["ritual_gold"], bevel=0.035)
    add_cylinder(
        root,
        "A_SidePressureChamber",
        (0.51, 0.02, -0.13),
        0.24,
        0.70,
        mat["oxidized_bronze"],
        vertices=8,
        rotation=(math.radians(90), 0, 0),
        bevel=0.018,
    )
    add_cylinder_between(root, "A_GripStem", (-0.30, 0.0, -0.40), (-0.74, 0.05, -1.05), 0.10, mat["dark_wood"], vertices=7)
    add_box(
        root,
        "B_GripHeel",
        (-0.79, 0.05, -1.12),
        (0.28, 0.30, 0.20),
        mat["dark_wood"],
        rotation=(0, math.radians(-8), math.radians(-18)),
        bevel=0.05,
    )
    add_cylinder_between(root, "A_CrankAxle", (0.42, -0.38, -0.22), (0.42, -0.66, -0.22), 0.055, mat["wrought_iron"], vertices=6)
    add_cylinder_between(root, "A_CrankArm", (0.42, -0.66, -0.22), (0.67, -0.69, -0.36), 0.055, mat["wrought_iron"], vertices=6)

    for i, (x, z) in enumerate(((-0.30, -0.42), (0.29, -0.40), (-0.31, 0.18), (0.30, 0.16))):
        add_ico(root, f"A_GoldBolt_{i}", (x, -0.34, z), (0.075, 0.045, 0.075), mat["ritual_gold"])

    authoring_note(
        "pile_bunker",
        "The visual identity is the independently selectable industrial assembly. Decorative bevels are materialized for deterministic OBJ output; housing, driver, rails, chamber, grip, crank and bolts remain ordinary editable source objects.",
    )
    save("pile_bunker")


def build_celestial_fossil():
    reset()
    mat = materials()
    root = make_root(
        "celestial_fossil",
        "Irregular stone slab with a genuine bored-through void, raised fossil spiral, mineral veins and embedded nodule.",
    )

    outline = [
        (-0.92, -0.86), (-0.20, -1.05), (0.67, -0.82), (0.93, -0.25),
        (0.78, 0.53), (0.26, 0.96), (-0.46, 0.88), (-0.95, 0.34),
    ]
    slab = add_prism(root, "B_StoneSlab", outline, 0.34, mat["rough_limestone"], bevel=0.07)

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=9,
        radius=0.22,
        depth=1.1,
        end_fill_type="NGON",
        location=(0.47, 0.0, 0.40),
        rotation=(math.radians(90), 0, 0),
    )
    cutter = bpy.context.object
    cutter.name = "B_AncientBore_GUIDE"
    cutter.parent = root
    cutter.hide_render = True
    cutter.display_type = "WIRE"
    cutter["sr_construction_role"] = "bore_guide_after_boolean_materialization"

    select_only(slab)
    mod = slab.modifiers.new("AncientBore", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    smart_uv(slab)
    cutter.hide_set(True)

    spiral = []
    cx, cz = (-0.16, -0.02)
    for i in range(24):
        t = i / 23
        angle = t * math.pi * 3.75
        rr = 0.06 + t * 0.48
        spiral.append((cx + rr * math.cos(angle), -0.205, cz + rr * math.sin(angle)))
    add_curve(root, "C_BoneSpiral", spiral, mat["bone"], 0.045)
    add_curve(
        root,
        "C_MineralVein_A",
        [(-0.77, -0.215, 0.38), (-0.51, -0.225, 0.22), (-0.34, -0.218, -0.02)],
        mat["crystal"],
        0.025,
    )
    add_curve(
        root,
        "C_MineralVein_B",
        [(0.12, -0.216, -0.63), (0.28, -0.222, -0.42), (0.58, -0.218, -0.31)],
        mat["crystal"],
        0.022,
    )
    add_ico(root, "A_EmbeddedNodule", (-0.62, -0.24, -0.46), (0.13, 0.07, 0.17), mat["oxidized_bronze"])

    authoring_note(
        "celestial_fossil",
        "The slab, fossil spiral, both mineral veins and nodule remain separately editable. The through-hole is real topology; its hidden wire cutter is retained as an authoring guide after the deterministic boolean result is materialized.",
    )
    save("celestial_fossil")


if __name__ == "__main__":
    build_pile_bunker()
    build_celestial_fossil()
