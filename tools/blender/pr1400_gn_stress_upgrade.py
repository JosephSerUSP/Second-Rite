#!/usr/bin/env python3
"""One-shot PR #1400 upgrade for Geometry Nodes scratch isolation."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "tools/blender/second_rite_asset_core.py"
COMPILE_ONE = ROOT / "tools/blender/compile_item_blend.py"
GN_BLENDER = ROOT / "tools/blender/tests/item_geometry_nodes_object_ref_blender.py"
GN_HOST = ROOT / "tools/blender/tests/test_item_geometry_nodes_object_ref.py"
REPORT = ROOT / "docs/reports/item-source-stress-test-2026-10-05.md"


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one replacement, got {count}")
    return updated


def patch_core() -> None:
    text = CORE.read_text(encoding="utf-8")
    pattern = r'def _remap_duplicate_dependencies\(mapping\):.*?\n\ndef duplicate_hierarchy'
    replacement = '''def _remap_node_socket_object(socket, mapping):
    """Remap an object-valued node socket when its target is in ``mapping``."""
    bpy = _bpy()
    try:
        current = socket.default_value
    except (AttributeError, RuntimeError):
        return 0
    if not isinstance(current, bpy.types.Object):
        return 0
    replacement = mapping.get(current)
    if replacement is None:
        return 0
    try:
        socket.default_value = replacement
    except (AttributeError, RuntimeError, TypeError):
        return 0
    return 1


def _copy_node_tree_for_export(node_tree, mapping, node_tree_mapping):
    """Copy a Geometry Nodes tree and recursively isolate nested node groups.

    Object.copy() keeps a Geometry Nodes modifier's node group shared with the
    authoritative source. Mutating that tree would mutate source authority, but
    leaving it shared means Object Info sockets continue to target source
    objects after the scratch hierarchy is recentered. Copy the node graph for
    the export scratch graph, recursively copy nested groups, and remap only
    object references whose targets are part of the duplicated hierarchy.
    """
    bpy = _bpy()
    existing = node_tree_mapping.get(node_tree)
    if existing is not None:
        return existing

    duplicate = node_tree.copy()
    duplicate["sr_export_temp_node_tree"] = True
    node_tree_mapping[node_tree] = duplicate

    for node in duplicate.nodes:
        _remap_rna_object_pointers(node, mapping)
        for socket in list(node.inputs) + list(node.outputs):
            _remap_node_socket_object(socket, mapping)

        nested = getattr(node, "node_tree", None)
        if isinstance(nested, bpy.types.NodeTree):
            try:
                node.node_tree = _copy_node_tree_for_export(
                    nested, mapping, node_tree_mapping
                )
            except (AttributeError, RuntimeError, TypeError):
                # Some node types expose a read-only node_tree pointer. They
                # remain visible to structural reports instead of being
                # silently mutated in the authoritative graph.
                pass
    return duplicate


def _purge_export_temp_node_trees():
    """Remove zero-user scratch node groups without touching source groups."""
    bpy = _bpy()
    while True:
        removable = [
            tree for tree in bpy.data.node_groups
            if bool(tree.get("sr_export_temp_node_tree", False)) and tree.users == 0
        ]
        if not removable:
            return
        for tree in removable:
            bpy.data.node_groups.remove(tree)


def _remap_duplicate_dependencies(mapping):
    """Make a copied export hierarchy self-contained for object references."""
    node_tree_mapping = {}
    for duplicate in mapping.values():
        _remap_rna_object_pointers(duplicate, mapping)
        _remap_rna_object_pointers(getattr(duplicate, "data", None), mapping)
        for modifier in getattr(duplicate, "modifiers", ()):
            _remap_rna_object_pointers(modifier, mapping)
            if modifier.type == "NODES" and modifier.node_group is not None:
                modifier.node_group = _copy_node_tree_for_export(
                    modifier.node_group, mapping, node_tree_mapping
                )
        for constraint in getattr(duplicate, "constraints", ()):
            _remap_rna_object_pointers(constraint, mapping)


def duplicate_hierarchy'''
    text = replace_once(text, pattern, replacement, "Geometry Nodes scratch isolation")

    # Temp node groups can survive after their object users are removed unless
    # explicitly purged. Attach cleanup to the existing collection cleanup path.
    needle = '''    if collection is not None:
        bpy.data.collections.remove(collection)
'''
    repl = '''    if collection is not None:
        bpy.data.collections.remove(collection)
    purge = globals().get("_purge_export_temp_node_trees")
    if callable(purge):
        purge()
'''
    if text.count(needle) != 1:
        raise SystemExit("delete_collection cleanup insertion point drifted")
    text = text.replace(needle, repl, 1)

    # BOUNDS centering and shape-key variants must operate on *all* scratch
    # objects, including geometry realized from collection instances.
    old = '''        geometry = _select_export_geometry(context, duplicates)
        if not geometry:
            raise RuntimeError(f"{root.name} has no exportable geometry")
        if center_mode == "BOUNDS":
            center = evaluated_bounds(geometry, context.evaluated_depsgraph_get())
            shift = Matrix.Translation(-center)
            for obj in duplicates:
                obj.matrix_world = shift @ obj.matrix_world
        export_name = safe_export_name(root.get(export_name_property, root.name))
        shape_names = _shape_key_names(duplicates) if export_shape_keys else []
'''
    new = '''        geometry = _select_export_geometry(context, duplicates)
        if not geometry:
            raise RuntimeError(f"{root.name} has no exportable geometry")
        scratch_objects = list(_temp.objects)
        if center_mode == "BOUNDS":
            center = evaluated_bounds(geometry, context.evaluated_depsgraph_get())
            shift = Matrix.Translation(-center)
            for obj in scratch_objects:
                obj.matrix_world = shift @ obj.matrix_world
        export_name = safe_export_name(root.get(export_name_property, root.name))
        shape_names = _shape_key_names(scratch_objects) if export_shape_keys else []
'''
    if text.count(old) != 1:
        raise SystemExit("export scratch-object block drifted")
    text = text.replace(old, new, 1)
    old = '''            _set_shape_variant(duplicates, shape_name)
            context.view_layer.update()
'''
    new = '''            _set_shape_variant(scratch_objects, shape_name)
            context.view_layer.update()
'''
    if text.count(old) != 1:
        raise SystemExit("shape variant block drifted")
    text = text.replace(old, new, 1)

    CORE.write_text(text, encoding="utf-8")


def patch_reporter() -> None:
    text = COMPILE_ONE.read_text(encoding="utf-8")
    pattern = r'def _object_pointer_edges\(root\):.*?\n\ndef structural_summary'
    replacement = '''def _object_pointer_edges(root):
    """Describe object-valued source-graph relationships for audit reports."""
    objects = [root, *list(root.children_recursive)]
    object_set = set(objects)
    edges = []

    def inspect(source_obj, owner, owner_kind):
        if owner is None:
            return
        rna = getattr(owner, "bl_rna", None)
        for prop in getattr(rna, "properties", ()):
            if prop.identifier == "rna_type" or getattr(prop, "type", None) != "POINTER":
                continue
            try:
                target = getattr(owner, prop.identifier)
            except (AttributeError, RuntimeError):
                continue
            if not isinstance(target, bpy.types.Object):
                continue
            edges.append({
                "from": source_obj.name,
                "owner": owner_kind,
                "property": prop.identifier,
                "to": target.name,
                "scope": "internal" if target in object_set else "external",
            })

        keys = getattr(owner, "keys", None)
        if callable(keys):
            try:
                owner_keys = list(keys())
            except TypeError:
                owner_keys = []
            for key in owner_keys:
                try:
                    target = owner[key]
                except (KeyError, RuntimeError):
                    continue
                if not isinstance(target, bpy.types.Object):
                    continue
                edges.append({
                    "from": source_obj.name,
                    "owner": owner_kind,
                    "property": f"idprop:{key}",
                    "to": target.name,
                    "scope": "internal" if target in object_set else "external",
                })

    def inspect_node_tree(source_obj, node_tree, path, visited):
        if node_tree is None or node_tree in visited:
            return
        visited.add(node_tree)
        for node in node_tree.nodes:
            owner = f"geometry_node:{path}:{node.name}"
            inspect(source_obj, node, owner)
            for socket in list(node.inputs) + list(node.outputs):
                try:
                    value = socket.default_value
                except (AttributeError, RuntimeError):
                    continue
                if isinstance(value, bpy.types.Object):
                    edges.append({
                        "from": source_obj.name,
                        "owner": f"geometry_socket:{path}:{node.name}",
                        "property": socket.name,
                        "to": value.name,
                        "scope": "internal" if value in object_set else "external",
                    })
            nested = getattr(node, "node_tree", None)
            if isinstance(nested, bpy.types.NodeTree):
                inspect_node_tree(source_obj, nested, f"{path}/{nested.name}", visited)

    for obj in objects:
        inspect(obj, obj, "object")
        inspect(obj, getattr(obj, "data", None), "data")
        for modifier in getattr(obj, "modifiers", ()):
            inspect(obj, modifier, f"modifier:{modifier.name}:{modifier.type}")
        for constraint in getattr(obj, "constraints", ()):
            inspect(obj, constraint, f"constraint:{constraint.name}:{constraint.type}")
        for modifier in getattr(obj, "modifiers", ()):
            if modifier.type == "NODES" and modifier.node_group is not None:
                inspect_node_tree(obj, modifier.node_group, modifier.node_group.name, set())
    return edges


def structural_summary'''
    text = replace_once(text, pattern, replacement, "recursive Geometry Nodes report")
    COMPILE_ONE.write_text(text, encoding="utf-8")


def write_tests() -> None:
    GN_BLENDER.write_text(r'''"""Pinned-Blender regression for nested Geometry Nodes object references."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import second_rite_asset_core as core


def parse_x_bounds(path: Path):
    xs = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("v "):
            xs.append(float(raw.split()[1]))
    assert xs, "Geometry Nodes stress export produced no vertices"
    return min(xs), max(xs)


def geometry_output_group(name):
    group = bpy.data.node_groups.new(name, "GeometryNodeTree")
    group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    output = group.nodes.new("NodeGroupOutput")
    return group, output


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

    inner, inner_output = geometry_output_group("GNStressInner")
    info = inner.nodes.new("GeometryNodeObjectInfo")
    info.name = "StressObjectInfo"
    info.inputs["Object"].default_value = target
    inner.links.new(info.outputs["Geometry"], inner_output.inputs["Geometry"])

    outer, outer_output = geometry_output_group("GNStressOuter")
    nested = outer.nodes.new("GeometryNodeGroup")
    nested.name = "StressNestedGroup"
    nested.node_tree = inner
    outer.links.new(nested.outputs["Geometry"], outer_output.inputs["Geometry"])

    modifier = host.modifiers.new("StressGeometryNodes", "NODES")
    modifier.node_group = outer

    bpy.context.view_layer.update()
    original_group_count = len(bpy.data.node_groups)
    original_outer = modifier.node_group
    original_inner = inner
    original_target_ref = info.inputs["Object"].default_value

    temp, _, duplicates = core.duplicate_hierarchy(bpy.context, root)
    by_role = {obj.get("stress_role"): obj for obj in duplicates if obj.get("stress_role")}
    dup_host = by_role["host"]
    dup_target = by_role["target"]
    dup_outer = dup_host.modifiers["StressGeometryNodes"].node_group
    dup_nested = dup_outer.nodes["StressNestedGroup"]
    dup_inner = dup_nested.node_tree
    dup_info = dup_inner.nodes["StressObjectInfo"]

    assert dup_outer is not original_outer
    assert dup_inner is not original_inner
    assert dup_info.inputs["Object"].default_value is dup_target
    assert info.inputs["Object"].default_value is target
    core.delete_collection(temp.name)
    assert len(bpy.data.node_groups) == original_group_count

    with tempfile.TemporaryDirectory(prefix="gn-object-ref-stress-") as directory:
        outputs = core.export_asset_root(bpy.context, root, Path(directory), center_mode="PIVOT")
        bounds = parse_x_bounds(Path(outputs[0]))
        assert 0.95 <= bounds[0] <= 1.05, bounds
        assert 1.95 <= bounds[1] <= 2.05, bounds

    assert modifier.node_group is original_outer
    assert nested.node_tree is original_inner
    assert info.inputs["Object"].default_value is original_target_ref
    assert len(bpy.data.node_groups) == original_group_count
    assert bpy.data.collections.get("__SECOND_RITE_ITEM_EXPORT_TEMP__") is None
    print("ITEM NESTED GEOMETRY NODES OBJECT REFERENCE STRESS OK")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

    GN_HOST.write_text(r'''"""Host wrapper for the Geometry Nodes item-source regression."""
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_test_support import blender_executable


class ItemGeometryNodesObjectReferenceTests(unittest.TestCase):
    def test_nested_node_groups_are_scratch_copied_and_object_refs_remapped(self):
        result = subprocess.run(
            [
                blender_executable(), "--background", "--factory-startup",
                "--disable-autoexec", "--python-exit-code", "1", "--python",
                str(TOOLS / "tests/item_geometry_nodes_object_ref_blender.py"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout[-7000:] + result.stderr[-3000:])
        self.assertIn("ITEM NESTED GEOMETRY NODES OBJECT REFERENCE STRESS OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")


def patch_report() -> None:
    text = REPORT.read_text(encoding="utf-8")
    old = '| Geometry Nodes node-tree object reference | advertised open-ended source vocabulary | source-graph report scans node/socket object references | **reported, not rewritten yet**; shared node groups must not be mutated silently |'
    new = '| Geometry Nodes node-tree object reference | advertised open-ended source vocabulary | translated-root nested-node-group regression | **supported for object references** by scratch-copying node trees recursively and remapping item-internal object sockets; source node groups remain untouched |'
    if old not in text:
        raise SystemExit("Geometry Nodes matrix row drifted")
    text = text.replace(old, new, 1)
    text += '''

## Geometry Nodes stress follow-up

A pinned Blender probe made the node-tree boundary concrete. `Object.copy()` left the scratch object's Geometry Nodes modifier sharing the authoritative node group; an Object Info socket still pointed to the original hidden construction object. With a translated item root, the resulting runtime cube exported at X `[-0.5, 0.5]` instead of its intended item-local `[1.0, 2.0]` placement.

The scratch duplication path now copies Geometry Nodes trees rather than editing shared source datablocks, recursively isolates nested Geometry Node groups, and remaps object-valued node properties/socket defaults when the referenced object belongs to the duplicated item hierarchy. Temporary node groups are explicitly marked and purged after scratch objects are removed. A regression checks both a nested node group and the real OBJ result, then requires the authoritative node groups and Object Info target to remain byte-for-byte-in-concept untouched in memory.

This support is deliberately scoped to **object-valued references**. Collection Info references are a separate graph relation because the item hierarchy maps objects, not arbitrary Blender collections; collection-valued GN references remain a stress target rather than being silently claimed safe.

The same review exposed a general-export edge around collection instances: BOUNDS centering and shape-key variant handling previously operated only on the original duplicated hierarchy, excluding instance-realized scratch geometry. Those operations now use the complete temporary export collection. The item compiler uses PIVOT centering, but the general helper no longer has that inconsistent instance boundary.
'''
    REPORT.write_text(text, encoding="utf-8")


def main() -> int:
    patch_core()
    patch_reporter()
    write_tests()
    patch_report()
    print("PR1400 GEOMETRY NODES STRESS UPGRADE PATCHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
