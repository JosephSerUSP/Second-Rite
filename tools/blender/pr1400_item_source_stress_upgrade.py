#!/usr/bin/env python3
"""One-shot PR #1400 tooling stress upgrade.

This script exists only to make the repository-side edits that need the pinned
Blender CI lane. The workflow removes it after the upgrade is verified.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "tools/blender/second_rite_asset_core.py"
COMPILE_ONE = ROOT / "tools/blender/compile_item_blend.py"
COMPILE_BATCH = ROOT / "tools/blender/compile_item_blends.py"
TEST_BLENDER = ROOT / "tools/blender/tests/item_dependency_graph_blender.py"
TEST_HOST = ROOT / "tools/blender/tests/test_item_dependency_graph.py"
REPORT = ROOT / "docs/reports/item-source-stress-test-2026-10-05.md"


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one replacement, got {count}")
    return updated


def patch_core() -> None:
    text = CORE.read_text(encoding="utf-8")
    pattern = r'def duplicate_hierarchy\(context, root, collection_name="__SECOND_RITE_ITEM_EXPORT_TEMP__"\):.*?\n\ndef _select_export_geometry'
    replacement = '''def _remap_rna_object_pointers(owner, mapping):
    """Redirect object-valued RNA/custom properties to hierarchy duplicates.

    ``Object.copy()`` deliberately keeps modifier, constraint and Curve-data
    pointer targets. That is useful in Blender generally, but an export scratch
    hierarchy must not keep reaching back into the authoritative source graph:
    once the duplicate root is recentered, original cutters/profile objects are
    in a different coordinate frame. Remap only pointers whose target is inside
    the duplicated hierarchy; external dependencies remain untouched and are
    surfaced by the compiler's structural report.
    """
    if owner is None:
        return 0
    changed = 0
    rna = getattr(owner, "bl_rna", None)
    for prop in getattr(rna, "properties", ()):
        if prop.identifier == "rna_type" or getattr(prop, "is_readonly", False):
            continue
        if getattr(prop, "type", None) != "POINTER":
            continue
        try:
            current = getattr(owner, prop.identifier)
            replacement = mapping.get(current)
        except (AttributeError, RuntimeError, TypeError):
            continue
        if replacement is None:
            continue
        try:
            setattr(owner, prop.identifier, replacement)
        except (AttributeError, RuntimeError, TypeError):
            continue
        changed += 1

    # Geometry Nodes interface object inputs are commonly stored as modifier
    # ID-properties rather than ordinary RNA pointer properties.
    keys = getattr(owner, "keys", None)
    if callable(keys):
        for key in list(keys()):
            try:
                current = owner[key]
                replacement = mapping.get(current)
            except (KeyError, RuntimeError, TypeError):
                continue
            if replacement is None:
                continue
            try:
                owner[key] = replacement
            except (KeyError, RuntimeError, TypeError):
                continue
            changed += 1
    return changed


def _remap_duplicate_dependencies(mapping):
    """Make a copied export hierarchy self-contained for object references."""
    for duplicate in mapping.values():
        _remap_rna_object_pointers(duplicate, mapping)
        _remap_rna_object_pointers(getattr(duplicate, "data", None), mapping)
        for modifier in getattr(duplicate, "modifiers", ()):
            _remap_rna_object_pointers(modifier, mapping)
        for constraint in getattr(duplicate, "constraints", ()):
            _remap_rna_object_pointers(constraint, mapping)


def duplicate_hierarchy(context, root, collection_name="__SECOND_RITE_ITEM_EXPORT_TEMP__"):
    bpy = _bpy()
    from mathutils import Matrix
    delete_collection(collection_name)
    temp = bpy.data.collections.new(collection_name)
    context.scene.collection.children.link(temp)
    sources = list(iter_hierarchy(root))
    mapping = {}
    world_matrices = {source: source.matrix_world.copy() for source in sources}
    for source in sources:
        duplicate = source.copy()
        if source.data is not None:
            duplicate.data = source.data.copy()
        duplicate.animation_data_clear()
        temp.objects.link(duplicate)
        mapping[source] = duplicate
    for source, duplicate in mapping.items():
        duplicate.parent = mapping.get(source.parent)
        duplicate.matrix_parent_inverse = source.matrix_parent_inverse.copy()
        duplicate.matrix_world = world_matrices[source]

    # Blender copies pointer-valued construction relationships verbatim. Make
    # them refer to the copied cutter/profile/target objects *before* shifting
    # the scratch hierarchy away from the authoritative source objects.
    _remap_duplicate_dependencies(mapping)

    shift = Matrix.Translation(-root.matrix_world.translation)
    for source, duplicate in mapping.items():
        duplicate.matrix_world = shift @ world_matrices[source]
    return temp, mapping[root], list(mapping.values())


def _select_export_geometry'''
    text = replace_once(text, pattern, replacement, "duplicate_hierarchy")
    CORE.write_text(text, encoding="utf-8")


def patch_compile_one() -> None:
    text = COMPILE_ONE.read_text(encoding="utf-8")
    pattern = r'def structural_summary\(root, source_path: Path, output_path: Path, material_passes: dict\[str, list\[dict\]\]\):.*?\n\ndef main\(\):'
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
            for key in list(keys()):
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

    for obj in objects:
        inspect(obj, obj, "object")
        inspect(obj, getattr(obj, "data", None), "data")
        for modifier in getattr(obj, "modifiers", ()):
            inspect(obj, modifier, f"modifier:{modifier.name}:{modifier.type}")
        for constraint in getattr(obj, "constraints", ()):
            inspect(obj, constraint, f"constraint:{constraint.name}:{constraint.type}")
        # Object Info / Collection Info references stored inside a shared
        # Geometry Nodes tree are intentionally reported but not rewritten by
        # the scratch-duplicate layer yet. This makes that boundary visible.
        for modifier in getattr(obj, "modifiers", ()):
            if modifier.type != "NODES" or modifier.node_group is None:
                continue
            for node in modifier.node_group.nodes:
                inspect(obj, node, f"geometry_node:{modifier.node_group.name}:{node.name}")
                for socket in list(node.inputs) + list(node.outputs):
                    try:
                        value = socket.default_value
                    except (AttributeError, RuntimeError):
                        continue
                    if isinstance(value, bpy.types.Object):
                        edges.append({
                            "from": obj.name,
                            "owner": f"geometry_socket:{modifier.node_group.name}:{node.name}",
                            "property": socket.name,
                            "to": value.name,
                            "scope": "internal" if value in object_set else "external",
                        })
    return edges


def structural_summary(root, source_path: Path, output_path: Path, material_passes: dict[str, list[dict]]):
    children = list(root.children_recursive)
    edges = _object_pointer_edges(root)
    return {
        "id": root.get("item_export_name"),
        "root": root.name,
        "sourceBlend": relative(source_path),
        "runtimeObj": relative(output_path),
        "objects": [
            {
                "name": obj.name,
                "type": obj.type,
                "hiddenFromRender": bool(obj.hide_render),
                "modifiers": [modifier.type for modifier in getattr(obj, "modifiers", [])],
                "constraintTypes": [constraint.type for constraint in getattr(obj, "constraints", [])],
            }
            for obj in children
        ],
        "modifierTypes": sorted({
            modifier.type
            for obj in children
            for modifier in getattr(obj, "modifiers", [])
        }),
        "constraintTypes": sorted({
            constraint.type
            for obj in children
            for constraint in getattr(obj, "constraints", [])
        }),
        "curveCount": sum(1 for obj in children if obj.type == "CURVE"),
        "meshCount": sum(1 for obj in children if obj.type == "MESH"),
        "hiddenConstructionCount": sum(1 for obj in children if obj.hide_render),
        "sourceObjectDependencies": edges,
        "sourceObjectDependencyCounts": {
            "internal": sum(1 for edge in edges if edge["scope"] == "internal"),
            "external": sum(1 for edge in edges if edge["scope"] == "external"),
        },
        "runtimeMaterialPasses": material_passes,
    }


def main():'''
    text = replace_once(text, pattern, replacement, "structural_summary")
    COMPILE_ONE.write_text(text, encoding="utf-8")


def patch_compile_batch() -> None:
    text = COMPILE_BATCH.read_text(encoding="utf-8")
    old = 'def compile_one(blender: str, source: Path, output_dir: Path, *, check: bool, model_dir: Path | None = None, source_dir: Path | None = None, project: Path | None = None):'
    new = 'def compile_one(blender: str, source: Path, output_dir: Path, *, check: bool, model_dir: Path | None = None, source_dir: Path | None = None, project: Path | None = None, report_dir: Path | None = None):'
    if text.count(old) != 1:
        raise SystemExit("compile_one signature drifted")
    text = text.replace(old, new, 1)

    old = '    env["SECOND_RITE_ITEM_OUTPUT_DIR"] = str(output_dir)\n    if source_dir:'
    new = '''    env["SECOND_RITE_ITEM_OUTPUT_DIR"] = str(output_dir)
    if report_dir is not None:
        report_dir.mkdir(parents=True, exist_ok=True)
        env["SECOND_RITE_ITEM_COMPILE_REPORT"] = str(report_dir / f"{source.stem}.json")
    if source_dir:'''
    if text.count(old) != 1:
        raise SystemExit("compile env block drifted")
    text = text.replace(old, new, 1)

    old = '''    parser.add_argument(
        "--check",
        action="store_true",
        help="compile to a temporary directory and require products to match checked-in OBJ/MTL",
    )'''
    new = old + '''
    parser.add_argument(
        "--report-dir",
        type=Path,
        help="write one machine-readable structural/source-graph JSON report per compiled .blend",
    )'''
    if text.count(old) != 1:
        raise SystemExit("parser check block drifted")
    text = text.replace(old, new, 1)

    old = '    sources = sources_from_args(args.source, source_dir)\n'
    new = '    sources = sources_from_args(args.source, source_dir)\n    report_dir = args.report_dir.resolve() if args.report_dir else None\n'
    if text.count(old) != 1:
        raise SystemExit("sources block drifted")
    text = text.replace(old, new, 1)

    text = text.replace(
        'compile_one(blender, source, output_dir, check=True, model_dir=model_dir, source_dir=source_dir, project=project_root)',
        'compile_one(blender, source, output_dir, check=True, model_dir=model_dir, source_dir=source_dir, project=project_root, report_dir=report_dir)'
    )
    text = text.replace(
        'compile_one(blender, source, output_dir, check=False, model_dir=model_dir, source_dir=source_dir, project=project_root)',
        'compile_one(blender, source, output_dir, check=False, model_dir=model_dir, source_dir=source_dir, project=project_root, report_dir=report_dir)'
    )
    COMPILE_BATCH.write_text(text, encoding="utf-8")


def write_tests() -> None:
    TEST_BLENDER.write_text(r'''"""Stress the item export scratch graph with Blender-native object dependencies."""
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
    core.assign_material(path, core.make_material("StressCloth", semantic_id="cloth"))

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
''', encoding="utf-8")

    TEST_HOST.write_text(r'''"""Pinned-Blender regression for the item export scratch dependency graph."""
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_test_support import blender_executable


class ItemDependencyGraphTests(unittest.TestCase):
    def test_internal_object_dependencies_follow_scratch_duplicates(self):
        result = subprocess.run(
            [
                blender_executable(), "--background", "--factory-startup",
                "--disable-autoexec", "--python-exit-code", "1", "--python",
                str(TOOLS / "tests/item_dependency_graph_blender.py"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout[-5000:] + result.stderr[-2000:])
        self.assertIn("ITEM DEPENDENCY GRAPH STRESS OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")


def write_report() -> None:
    REPORT.write_text('''# Item-source tooling stress test — 2026-10-05

PR #1400 is being used as a **tooling probe**, not as an assertion that its six consumable designs are final art. The weak visual result is useful evidence: the first pass mostly exercised profile/revolve plus simple Curve attachments, so it proved source authority while barely touching the richer Blender-native construction vocabulary that the source contract advertises.

## Stress matrix

| Capability | Before this pass | Stress action | Result / boundary |
|---|---|---|---|
| Editable profile + Screw | exercised by the six consumables | keep as baseline | supported; generated Screw UV behaviour was already fixed during #1400 |
| Hidden Curve bevel/profile object | used by prior migrations, but scratch-copy self-containment was not asserted | translated-root regression | internal profile targets are now remapped to scratch duplicates |
| Boolean cutter | documented and used in prior content | translated-root regression | internal cutter targets are now remapped to scratch duplicates |
| Mirror origin | documented fabrication vocabulary | translated-root regression | internal mirror-object targets are now remapped |
| Curve modifier target | documented ARRAY/Curve-style composition | translated-root regression | internal target is now remapped |
| Constraint target | ordinary Blender construction relation | translated-root regression | internal target is now remapped |
| Geometry Nodes interface object input | advertised open-ended source vocabulary | generic modifier ID-property remap + report visibility | remapped when Blender exposes the object on the modifier; node-tree-internal references remain a visible boundary |
| Geometry Nodes node-tree object reference | advertised open-ended source vocabulary | source-graph report scans node/socket object references | **reported, not rewritten yet**; shared node groups must not be mutated silently |
| Collection/object instances | advertised source vocabulary | not yet adversarially exercised | **next stress target**; selection/export semantics need explicit proof |
| External object references | previously invisible | source-graph report | retained rather than silently rewritten and marked `external` for audit |
| Read-only source authority | established before #1400 | regression export after richer graph duplication | preserved; the source graph remains untouched |

## Failure exposed

`second_rite_asset_core.duplicate_hierarchy()` copied objects and their datablocks, then recentered those duplicates, but Blender pointer relationships inside copied modifiers, constraints and Curve data continued to target the **original** source objects. A Boolean cutter or Curve bevel profile could therefore live in a different coordinate frame from the temporary object being exported. A source could appear correct at an origin-aligned root while becoming wrong when the root moved.

The fix makes the scratch hierarchy self-contained for object-valued RNA pointers and modifier ID-properties when the referenced object is itself under the export root. The regression deliberately uses a non-zero root transform and simultaneously exercises a Boolean cutter, Curve bevel object, Mirror origin, Curve modifier target and constraint target.

## Auditability upgrade

`compile_item_blends.py --report-dir <dir>` now exposes the Blender-side structural report for ordinary batch/check runs. Reports include modifier/constraint vocabularies, hidden-construction counts and object-valued dependency edges classified as `internal` or `external`. This is intentionally diagnostic rather than a new source grammar: a `.blend` remains free-form Blender authority.

The report also scans Geometry Nodes node/socket object references. Those references are **not yet remapped**, because modifying a shared node group would violate the read-only-source principle and safely duplicating nested node graphs is a separate capability. The tooling should show that limit instead of pretending Geometry Nodes are universally safe.

## What #1400 should do next

The six consumables should now be treated as six adversarial authoring experiments, with each redesign chosen to force a different Blender-native construction relation rather than six variations of profile/revolve. The next useful probes are Geometry Nodes object/collection inputs, real instancing, Boolean stacks with hidden guides, anisotropic Curve/GN profiles, and mixed direct-mesh + procedural assemblies. Visual quality remains a review signal: if a supposedly broad toolset keeps producing lathed bottles, the authoring affordances are still too narrow or too opaque.
''', encoding="utf-8")


def main() -> int:
    patch_core()
    patch_compile_one()
    patch_compile_batch()
    write_tests()
    write_report()
    print("PR1400 ITEM SOURCE STRESS UPGRADE PATCHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
