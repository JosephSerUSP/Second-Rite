"""Render four structural review views from one already-open item .blend.

The source document is never saved. This is intentionally a cheap Workbench
review of the committed authoring graph, separate from runtime compilation and
from any slower material/beauty review.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
OUTPUT_DIR = Path(os.environ.get(
    "SECOND_RITE_ITEM_STUDY_PREVIEW_DIR",
    ROOT / "docs" / "reports" / "blender-item-authoring-study" / "previews",
))


def fail(message: str):
    raise RuntimeError(f"editable item preview failed: {message}")


def main():
    source_path = Path(bpy.data.filepath)
    if not source_path.is_file():
        fail("Blender has no saved source file loaded")

    roots = [obj for obj in bpy.context.scene.objects if bool(obj.get("item_export", False))]
    if len(roots) != 1:
        fail(f"expected exactly one item_export root, got {[obj.name for obj in roots]}")
    root = roots[0]
    item_id = root.get("item_export_name")
    if not item_id:
        fail(f"{root.name}: missing item_export_name")

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 192
    scene.render.resolution_y = 192
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True

    camera = bpy.data.objects.get("PREVIEW_Camera")
    if camera is None or camera.type != "CAMERA":
        fail(f"{item_id}: source does not contain PREVIEW_Camera")
    scene.camera = camera

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    original = root.rotation_euler.copy()
    views = [
        ("front", (0.0, 0.0, 0.0)),
        ("three_quarter", (math.radians(12), 0.0, math.radians(55))),
        ("side", (0.0, 0.0, math.radians(90))),
        ("top", (math.radians(72), 0.0, math.radians(30))),
    ]
    try:
        for label, rotation in views:
            root.rotation_euler = rotation
            bpy.context.view_layer.update()
            scene.render.filepath = str(OUTPUT_DIR / f"{item_id}-{label}.png")
            bpy.ops.render.render(write_still=True)
            print(f"RENDERED {item_id} {label}")
    finally:
        root.rotation_euler = original
        bpy.context.view_layer.update()


if __name__ == "__main__":
    main()
