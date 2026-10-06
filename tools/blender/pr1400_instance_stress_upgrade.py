#!/usr/bin/env python3
"""One-shot PR #1400 collection-instance stress upgrade."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "tools/blender/second_rite_asset_core.py"
COMPILE_ONE = ROOT / "tools/blender/compile_item_blend.py"
TEST_BLENDER = ROOT / "tools/blender/tests/item_instance_export_blender.py"
TEST_HOST = ROOT / "tools/blender/tests/test_item_instance_export.py"
REPORT = ROOT / "docs/reports/item-source-stress-test-2026-10-05.md"


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: expected one replacement, got {count}")
    return updated


def patch_core() -> None:
    text = CORE.read_text(encoding="utf-8")
    pattern = r'def _select_export_geometry\(context, objects\):.*?\n\ndef _shape_key_names'
    replacement = '''def _realize_export_instances(context, objects):
    """Realize ordinary Blender object/collection instances in the scratch graph.

    Item sources are allowed to use collection-instance Empties as editable
    construction. OBJ has no instance concept, and the exporter intentionally
    receives only selected geometry, so instance carriers must be made real in
    the temporary export collection first. The authoritative source objects are
    never selected or modified here.
    """
    bpy = _bpy()
    instancers = [
        obj for obj in objects
        if not obj.hide_render and getattr(obj, "instance_type", "NONE") != "NONE"
    ]
    if not instancers:
        return []

    bpy.ops.object.select_all(action="DESELECT")
    before = set(bpy.data.objects)
    for obj in instancers:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.select_set(True)
    context.view_layer.objects.active = instancers[0]
    result = bpy.ops.object.duplicates_make_real(use_base_parent=True, use_hierarchy=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"failed to realize export instances: {result}")
    context.view_layer.update()
    return [obj for obj in bpy.data.objects if obj not in before]


def _select_export_geometry(context, objects):
    bpy = _bpy()
    realized = _realize_export_instances(context, objects)
    candidates = list(objects) + realized
    bpy.ops.object.select_all(action="DESELECT")
    geometry = [obj for obj in candidates
                if obj.type in {"MESH", "CURVE", "SURFACE", "FONT", "META"}
                and not obj.hide_render]
    for obj in geometry:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.select_set(True)
    context.view_layer.objects.active = geometry[0] if geometry else None
    return geometry


def _shape_key_names'''
    text = replace_once(text, pattern, replacement, "instance realization")
    CORE.write_text(text, encoding="utf-8")


def patch_reporter() -> None:
    text = COMPILE_ONE.read_text(encoding="utf-8")
    needle = '''        "hiddenConstructionCount": sum(1 for obj in children if obj.hide_render),
        "sourceObjectDependencies": edges,'''
    replacement = '''        "hiddenConstructionCount": sum(1 for obj in children if obj.hide_render),
        "instanceSources": [
            {
                "name": obj.name,
                "instanceType": obj.instance_type,
                "collection": obj.instance_collection.name if obj.instance_collection else None,
            }
            for obj in children
            if getattr(obj, "instance_type", "NONE") != "NONE"
        ],
        "sourceObjectDependencies": edges,'''
    if text.count(needle) != 1:
        raise SystemExit("structural report insertion point drifted")
    COMPILE_ONE.write_text(text.replace(needle, replacement, 1), encoding="utf-8")


def write_tests() -> None:
    TEST_BLENDER.write_text(r'''"""Adversarial collection-instance export test for authoritative item sources."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import second_rite_asset_core as core


def parse_obj(path: Path):
    vertices = []
    faces = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("v "):
            vertices.append(tuple(float(v) for v in raw.split()[1:4]))
        elif raw.startswith("f "):
            faces.append(raw)
    return vertices, faces


def main():
    core.reset_scene(factory=True)

    # Deliberately keep the instanced kit outside the item hierarchy. This is
    # how ordinary Blender collection instances are authored: the Empty under
    # the item root references a reusable collection datablock.
    kit = bpy.data.collections.new("StressInstanceKit")
    mesh = bpy.data.meshes.new("StressInstanceCubeMesh")
    mesh.from_pydata(
        [(-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
         (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)],
        [],
        [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2),
         (2, 6, 7, 3), (4, 0, 3, 7)],
    )
    cube = bpy.data.objects.new("StressInstanceCube", mesh)
    kit.objects.link(cube)
    core.assign_material(cube, core.make_material("StressInstanceGold", semantic_id="ritual_gold"))

    root = bpy.data.objects.new("StressInstanceRoot", None)
    bpy.context.scene.collection.objects.link(root)
    root.location = (8.0, -3.0, 2.0)
    root["item_export"] = True
    root["item_export_name"] = "instance_stress_fixture"
    root["sr_source_authority"] = "blend"
    core.tag_asset_target(
        root,
        asset_id="instance_stress_fixture",
        representation="full_model",
        role="item_display",
        authoring_space="item_display",
        placement_frame="item_viewport",
    )

    instance = bpy.data.objects.new("StressCollectionInstance", None)
    bpy.context.scene.collection.objects.link(instance)
    core.parent_local(instance, root, loc=(1.25, 0.0, 0.0), scale=(0.8, 1.1, 0.6))
    instance.instance_type = "COLLECTION"
    instance.instance_collection = kit

    source_object_count = len(bpy.data.objects)
    source_collection_count = len(bpy.data.collections)
    original_collection = instance.instance_collection
    original_transform = instance.matrix_world.copy()

    with tempfile.TemporaryDirectory(prefix="item-instance-stress-") as directory:
        outputs = core.export_asset_root(bpy.context, root, Path(directory), center_mode="PIVOT")
        assert len(outputs) == 1
        output = Path(outputs[0])
        assert output.is_file()
        vertices, faces = parse_obj(output)
        assert len(vertices) >= 8, f"instance produced too few vertices: {len(vertices)}"
        assert len(faces) >= 6, f"instance produced too few faces: {len(faces)}"
        xs = [v[0] for v in vertices]
        # X is unchanged by the OBJ axis conversion. The root is recentered,
        # while the instance's +1.25 local offset and 0.8 X scale survive.
        assert min(xs) < 1.0 < max(xs), (min(xs), max(xs))
        assert 0.75 < min(xs) < 0.95, min(xs)
        assert 1.55 < max(xs) < 1.75, max(xs)

    # Realization belongs entirely to the temporary export graph.
    assert instance.instance_collection is original_collection
    assert instance.matrix_world == original_transform
    assert len(bpy.data.objects) == source_object_count, (source_object_count, len(bpy.data.objects))
    assert len(bpy.data.collections) == source_collection_count
    assert bpy.data.collections.get("__SECOND_RITE_ITEM_EXPORT_TEMP__") is None
    print("ITEM COLLECTION INSTANCE EXPORT STRESS OK")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

    TEST_HOST.write_text(r'''"""Pinned-Blender host regression for collection-instance item export."""
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_test_support import blender_executable


class ItemInstanceExportTests(unittest.TestCase):
    def test_collection_instance_is_realized_only_in_export_scratch_graph(self):
        result = subprocess.run(
            [
                blender_executable(), "--background", "--factory-startup",
                "--disable-autoexec", "--python-exit-code", "1", "--python",
                str(TOOLS / "tests/item_instance_export_blender.py"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout[-6000:] + result.stderr[-2000:])
        self.assertIn("ITEM COLLECTION INSTANCE EXPORT STRESS OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")


def patch_report() -> None:
    text = REPORT.read_text(encoding="utf-8")
    old = '| Collection/object instances | advertised source vocabulary | not yet adversarially exercised | **next stress target**; selection/export semantics need explicit proof |'
    new = '| Collection-instance Empties | advertised source vocabulary | translated-root realization regression | **supported** by realizing scratch instances before OBJ selection; authoritative collections remain untouched |'
    if old not in text:
        raise SystemExit("stress matrix instance row drifted")
    text = text.replace(old, new, 1)
    text += '''

## Instance stress follow-up

The next adversarial probe confirmed a concrete contract mismatch: ordinary Blender collection instances are represented by `EMPTY` objects, while the runtime exporter selected only geometry object types. The instance carrier was therefore excluded before OBJ export, despite instances being part of the documented authoring vocabulary.

The export scratch phase now makes visible Blender instances real **only on the duplicated graph**, then selects the resulting geometry. A pinned-Blender regression uses a translated item root, a scaled/offset collection-instance Empty, and a reusable collection that is not part of the root hierarchy. It verifies runtime geometry and placement, and it verifies that object/collection counts plus the authoritative instance reference and transform are unchanged after export cleanup.

This deliberately does not claim universal instancing support. Geometry Nodes instances are evaluated through modifier output and remain a separate stress axis; nested collection-instance graphs and linked-library collections should receive their own probes before being described as guaranteed.
'''
    REPORT.write_text(text, encoding="utf-8")


def main() -> int:
    patch_core()
    patch_reporter()
    write_tests()
    patch_report()
    print("PR1400 INSTANCE STRESS UPGRADE PATCHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
