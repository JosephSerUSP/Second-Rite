"""One-shot pinned-Blender probe for Geometry Nodes object references in item sources."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import second_rite_asset_core as core


def parse_x_bounds(path: Path):
    xs = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("v "):
            xs.append(float(raw.split()[1]))
    if not xs:
        raise AssertionError("Geometry Nodes probe exported no vertices")
    return min(xs), max(xs)


def main():
    core.reset_scene(factory=True)

    root = bpy.data.objects.new("GNStressRoot", None)
    bpy.context.scene.collection.objects.link(root)
    root.location = (6.0, -3.0, 2.0)
    root["item_export"] = True
    root["item_export_name"] = "gn_object_ref_stress"
    root["sr_source_authority"] = "blend"
    core.tag_asset_target(
        root,
        asset_id="gn_object_ref_stress",
        representation="full_model",
        role="item_display",
        authoring_space="item_display",
        placement_frame="item_viewport",
    )

    # Hidden construction target: the Geometry Nodes host should emit this cube
    # at the target's item-local +1.5 X position after the export root recenters.
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    target = bpy.context.object
    target.name = "GNStressTarget"
    target["stress_role"] = "target"
    core.parent_local(target, root, loc=(1.5, 0.0, 0.0))
    target.hide_render = True
    core.assign_material(target, core.make_material("GNStressGold", semantic_id="ritual_gold"))

    mesh = bpy.data.meshes.new("GNStressHostMesh")
    host = bpy.data.objects.new("GNStressHost", mesh)
    bpy.context.scene.collection.objects.link(host)
    host["stress_role"] = "host"
    core.parent_local(host, root)

    group = bpy.data.node_groups.new("GNStressTree", "GeometryNodeTree")
    group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    output = group.nodes.new("NodeGroupOutput")
    info = group.nodes.new("GeometryNodeObjectInfo")
    info.name = "StressObjectInfo"
    info.inputs["Object"].default_value = target
    group.links.new(info.outputs["Geometry"], output.inputs["Geometry"])

    modifier = host.modifiers.new("StressGeometryNodes", "NODES")
    modifier.node_group = group

    bpy.context.view_layer.update()
    original_target_ref = info.inputs["Object"].default_value
    original_group = modifier.node_group

    temp, _, duplicates = core.duplicate_hierarchy(bpy.context, root)
    by_role = {obj.get("stress_role"): obj for obj in duplicates if obj.get("stress_role")}
    dup_host = by_role["host"]
    dup_target = by_role["target"]
    dup_group = dup_host.modifiers["StressGeometryNodes"].node_group
    dup_info = dup_group.nodes["StressObjectInfo"]
    copied_ref = dup_info.inputs["Object"].default_value
    print("GN GROUP SHARED WITH SOURCE", dup_group is original_group)
    print("GN OBJECT INFO TARGET IS ORIGINAL", copied_ref is target)
    print("GN OBJECT INFO TARGET IS DUPLICATE", copied_ref is dup_target)
    core.delete_collection(temp.name)

    with tempfile.TemporaryDirectory(prefix="gn-object-ref-stress-") as directory:
        outputs = core.export_asset_root(bpy.context, root, Path(directory), center_mode="PIVOT")
        bounds = parse_x_bounds(Path(outputs[0]))
        print("GN RUNTIME X BOUNDS", bounds)
        # Correct item-local placement for a unit cube at x=+1.5 is [1.0, 2.0].
        correct_runtime_placement = 0.95 <= bounds[0] <= 1.05 and 1.95 <= bounds[1] <= 2.05
        print("GN RUNTIME PLACEMENT CORRECT", correct_runtime_placement)

    assert info.inputs["Object"].default_value is original_target_ref
    assert modifier.node_group is original_group
    assert bpy.data.collections.get("__SECOND_RITE_ITEM_EXPORT_TEMP__") is None

    # This probe is meant to positively identify the currently documented
    # boundary. If the graph has somehow become isolated already, fail so the
    # stress lane is updated rather than preserving a stale expectation.
    assert dup_group is original_group, "GN node group is no longer shared; update the stress probe"
    assert copied_ref is target, "GN Object Info was remapped unexpectedly; update the stress probe"
    print("GN SHARED NODE-TREE OBJECT REFERENCE BOUNDARY CONFIRMED")


if __name__ == "__main__":
    main()
