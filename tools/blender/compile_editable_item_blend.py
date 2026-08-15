"""Compile one already-open editable item .blend into the runtime OBJ product.

The .blend is the source. This script must never save or rewrite it. Blender is
used only to evaluate the existing authoring graph on a temporary duplicate,
then the shared exporter emits the flattened runtime product.

Run through Blender with the source file already loaded::

    blender --background path/to/item.blend \
      --python tools/blender/compile_editable_item_blend.py

Set SECOND_RITE_ITEM_STUDY_REPORT_DIR to emit one structural JSON report for
later aggregation by the hosted study workflow.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import second_rite_asset_core as asset_core

ROOT = SCRIPT_DIR.parents[1]
MODEL_DIR = ROOT / "assets" / "models" / "items" / "studies" / "blender_editable"
REPORT_DIR = Path(os.environ.get("SECOND_RITE_ITEM_STUDY_REPORT_DIR", ROOT / "docs" / "reports" / "blender-item-authoring-study" / "compile-reports"))


def fail(message: str):
    raise RuntimeError(f"editable item compile failed: {message}")


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def structural_summary(root, source_path: Path, output_path: Path):
    children = list(root.children_recursive)
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
            }
            for obj in children
        ],
        "modifierTypes": sorted({
            modifier.type
            for obj in children
            for modifier in getattr(obj, "modifiers", [])
        }),
        "curveCount": sum(1 for obj in children if obj.type == "CURVE"),
        "meshCount": sum(1 for obj in children if obj.type == "MESH"),
    }


def main():
    source_path = Path(bpy.data.filepath)
    if not source_path.is_file():
        fail("Blender has no saved source file loaded")

    roots = [obj for obj in bpy.context.scene.objects if bool(obj.get("item_export", False))]
    if len(roots) != 1:
        fail(f"expected exactly one item_export root, got {[obj.name for obj in roots]}")
    root = roots[0]
    asset_core.validate_asset_metadata(root)
    if root.get("sr_source_authority") != "blend":
        fail(f"{root.name}: sr_source_authority must be 'blend'")
    if not bool(root.get("sr_study_only", False)):
        fail(f"{root.name}: expected study-only source marker")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    outputs = asset_core.export_asset_root(
        bpy.context,
        root,
        MODEL_DIR,
        export_shape_keys=False,
        center_mode="PIVOT",
    )
    if len(outputs) != 1:
        fail(f"{root.name}: expected one runtime OBJ, got {outputs}")
    output_path = Path(outputs[0])

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"{root.get('item_export_name')}.json"
    report_path.write_text(
        json.dumps(structural_summary(root, source_path, output_path), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"COMPILED SOURCE {relative(source_path)} -> {relative(output_path)}")
    print(f"WROTE REPORT {report_path}")


if __name__ == "__main__":
    main()
