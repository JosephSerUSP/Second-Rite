"""Stress the item export scratch graph with Blender-native object dependencies."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import second_rite_asset_core as core


def tagged(obj, role):
    obj["stress_role"] = role
    return obj


def curve_object(name, points, *, cyclic=False):
    data = bpy.data.curves.new(name + "Data", "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def assert_close(actual, expected, eps=1e-5):
    assert all(abs(a - b) <= eps for a, b in zip(actual, expected)), (actual, expected)


def main():
    core.reset_scene(factory=True)
    root = tagged(bpy.data.objects.new("StressRoot", None), "root")
    bpy.context.scene.collection.objects.link(root)
    root.location = (4.5, -2.25, 1.75)
    root["item_export"] = True
    root["item_export_name"] = "dependency_stress_fixture"
    root["sr_source_authority"] = "blend"
    core.tag_asset_target(
        root,
        asset_id="dependency_stress_fixture",
        representation="full_model",
        role="item_display",
        authoring_space="item_display",
        placement_frame="item_viewport",
    )

    bpy.ops.mesh.primitive_cube_add(size=1.4)
    body = tagged(bpy.context.object, "body")
    core.parent_local(body, root, loc=(0.0, 0.0, 0.0))
    core.assign_material(body, core.make_material("StressIron", semantic_id="wrought_iron"))

    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.24, depth=2.0)
    cutter = tagged(bpy.context.object, "cutter")
    core.parent_local(cutter, root, loc=(0.28, 0.0, 0.0), rot=(0.0, 1.57079632679, 0.0))
    cutter.hide_render = True
    boolean = body.modifiers.new("StressBoolean", "BOOLEAN")
    boolean.operation = "DIFFERENCE"
    boolean.solver = "EXACT"
    boolean.object = cutter

    profile = tagged(curve_object("StressProfile", [(-0.08, -0.04, 0), (0.08, -0.04, 0), (0.08, 0.04, 0), (-0.08, 0.04, 0)], cyclic=True), "profile")
    core.parent_local(profile, root)
    profile.hide_render = True
    path = tagged(curve_object("StressPath", [(-0.65, -0.55, -0.55), (-0.2, -0.7, 0.1), (0.4, -0.5, 0.55)]), "path")
    core.parent_local(path, root)
    path.data.bevel_mode = "OBJECT"
    path.data.bevel_object = profile
    core.assign_material(path, core.make_material("StressCloth", semantic_id="aged_cloth"))

    mirror_origin = tagged(bpy.data.objects.new("StressMirrorOrigin", None), "mirror_origin")
    bpy.context.scene.collection.objects.link(mirror_origin)
    core.parent_local(mirror_origin, root, loc=(0.0, 0.0, 0.0))
    mirror_origin.hide_render = True
    bpy.ops.mesh.primitive_cube_add(size=0.3)
    plate = tagged(bpy.context.object, "plate")
    core.parent_local(plate, root, loc=(0.45, 0.45, 0.0))
    mirror = plate.modifiers.new("StressMirror", "MIRROR")
    mirror.mirror_object = mirror_origin

    deform_path = tagged(curve_object("StressDeform", [(-0.5, 0, -0.2), (0, 0.2, 0), (0.5, 0, 0.2)]), "deform")
    core.parent_local(deform_path, root)
    deform_path.hide_render = True
    bpy.ops.mesh.primitive_cube_add(size=0.18)
    ribbon = tagged(bpy.context.object, "ribbon")
    core.parent_local(ribbon, root, loc=(-0.5, 0.35, 0.0), scale=(3.0, 0.5, 0.5))
    deform = ribbon.modifiers.new("StressCurve", "CURVE")
    deform.object = deform_path
    deform.deform_axis = "POS_X"

    target = tagged(bpy.data.objects.new("StressConstraintTarget", None), "constraint_target")
    bpy.context.scene.collection.objects.link(target)
    core.parent_local(target, root, loc=(-0.35, -0.35, 0.4))
    target.hide_render = True
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.16)
    charm = tagged(bpy.context.object, "charm")
    core.parent_local(charm, root)
    constraint = charm.constraints.new("COPY_LOCATION")
    constraint.name = "StressConstraint"
    constraint.target = target

    # Keep the authoritative relations for post-export immutability checks.
    original_refs = (boolean.object, path.data.bevel_object, mirror.mirror_object, deform.object, constraint.target)

    temp, duplicate_root, duplicates = core.duplicate_hierarchy(bpy.context, root)
    duplicates_by_role = {obj.get("stress_role"): obj for obj in duplicates}
    assert set(duplicates_by_role) >= {"root", "body", "cutter", "profile", "path", "mirror_origin", "plate", "deform", "ribbon", "constraint_target", "charm"}
    assert duplicates_by_role["body"].modifiers["StressBoolean"].object is duplicates_by_role["cutter"]
    assert duplicates_by_role["path"].data.bevel_object is duplicates_by_role["profile"]
    assert duplicates_by_role["plate"].modifiers["StressMirror"].mirror_object is duplicates_by_role["mirror_origin"]
    assert duplicates_by_role["ribbon"].modifiers["StressCurve"].object is duplicates_by_role["deform"]
    assert duplicates_by_role["charm"].constraints["StressConstraint"].target is duplicates_by_role["constraint_target"]
    assert_close(tuple(duplicate_root.matrix_world.translation), (0.0, 0.0, 0.0))
    core.delete_collection(temp.name)

    # The real export path must flatten the richer graph without mutating it.
    with tempfile.TemporaryDirectory(prefix="item-dependency-stress-") as directory:
        outputs = core.export_asset_root(bpy.context, root, Path(directory), center_mode="PIVOT")
        assert len(outputs) == 1 and Path(outputs[0]).is_file()
        assert Path(outputs[0]).with_suffix(".mtl").is_file()

    assert original_refs == (boolean.object, path.data.bevel_object, mirror.mirror_object, deform.object, constraint.target)
    assert all(ref in {cutter, profile, mirror_origin, deform_path, target} for ref in original_refs)
    assert bpy.data.collections.get("__SECOND_RITE_ITEM_EXPORT_TEMP__") is None
    print("ITEM DEPENDENCY GRAPH STRESS OK")


if __name__ == "__main__":
    main()
