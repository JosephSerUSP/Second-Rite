"""Compile one already-open authoritative item ``.blend`` into runtime OBJ/MTL.

This script runs *inside Blender*. The loaded ``.blend`` is source authority and
must never be saved or rewritten by compilation. The shared asset core evaluates
and applies modifiers only on a temporary duplicate, then emits the flattened
runtime product.

Expected source convention::

    assets/authoring/items/<item_id>.blend

Expected root properties::

    item_export = true
    item_export_name = "<item_id>"
    sr_source_authority = "blend"

Run::

    blender --background assets/authoring/items/foo.blend \
      --python tools/blender/compile_item_blend.py
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
SOURCE_DIR = ROOT / "assets" / "authoring" / "items"
DEFAULT_MODEL_DIR = ROOT / "assets" / "models" / "items"


def fail(message: str):
    raise RuntimeError(f"item blend compile failed: {message}")


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def source_root():
    roots = [obj for obj in bpy.context.scene.objects if bool(obj.get("item_export", False))]
    if len(roots) != 1:
        fail(f"expected exactly one item_export root, got {[obj.name for obj in roots]}")
    return roots[0]


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
    source_path = Path(bpy.data.filepath).resolve()
    if not source_path.is_file():
        fail("Blender has no saved source file loaded")
    try:
        source_path.relative_to(SOURCE_DIR.resolve())
    except ValueError:
        fail(f"source must live under {relative(SOURCE_DIR)}; got {relative(source_path)}")

    root = source_root()
    asset_core.validate_asset_metadata(root)
    if root.get("sr_source_authority") != "blend":
        fail(f"{root.name}: sr_source_authority must be 'blend'")

    export_name = asset_core.safe_export_name(root.get("item_export_name"))
    if not export_name or export_name == "item":
        fail(f"{root.name}: item_export_name must identify the item")
    if source_path.stem != export_name:
        fail(
            f"source filename and item_export_name disagree: "
            f"{source_path.stem!r} vs {export_name!r}"
        )

    output_dir = Path(os.environ.get("SECOND_RITE_ITEM_OUTPUT_DIR", DEFAULT_MODEL_DIR)).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = asset_core.export_asset_root(
        bpy.context,
        root,
        output_dir,
        export_shape_keys=False,
        center_mode="PIVOT",
    )
    if len(outputs) != 1:
        fail(f"{root.name}: expected one runtime OBJ, got {outputs}")
    output_path = Path(outputs[0]).resolve()
    if output_path.stem != export_name:
        fail(f"exporter returned unexpected product {output_path.name!r}")

    summary = structural_summary(root, source_path, output_path)
    report_path = os.environ.get("SECOND_RITE_ITEM_COMPILE_REPORT")
    if report_path:
        destination = Path(report_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE REPORT {destination}")

    print(f"COMPILED ITEM SOURCE {relative(source_path)} -> {relative(output_path)}")


if __name__ == "__main__":
    main()
