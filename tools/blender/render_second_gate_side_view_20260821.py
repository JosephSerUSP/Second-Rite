#!/usr/bin/env python3
"""Re-render evidence from an already-baked Second Gate winner blend."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--envelope", required=True, type=Path)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def layers(source_col, render_col, collision_col, anchors_col, preview_col, guide_col, camera_col, *, source, runtime):
    source_col.hide_render = False
    render_col.hide_render = not runtime
    for obj in source_col.objects:
        obj.hide_render = obj.type == "MESH" and not source
    for obj in render_col.objects:
        obj.hide_render = not runtime
    for col in (collision_col, anchors_col, guide_col, camera_col):
        if col:
            col.hide_render = True
            for obj in col.objects:
                obj.hide_render = True
    if preview_col:
        preview_col.hide_render = False
        for obj in preview_col.objects:
            obj.hide_render = False


def render(scene, camera, sample, path, *, source_col, render_col, collision_col, anchors_col, preview_col, guide_col, camera_col, source, runtime):
    import second_gate_render
    import view_weighted_atlas

    layers(source_col, render_col, collision_col, anchors_col, preview_col, guide_col, camera_col, source=source, runtime=runtime)
    second_gate_render.apply(scene, "cycles-draft")
    base = view_weighted_atlas._camera_state(camera)
    view_weighted_atlas._apply_view(scene, camera, sample, base)
    scene.render.filepath = str(path)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)
    view_weighted_atlas._restore_camera(scene, camera, base)


def main():
    args = parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import second_gate_render  # noqa: F401
    import view_weighted_atlas

    bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
    scene = bpy.context.scene
    camera = scene.camera
    source_col = bpy.data.collections["TH_SOURCE"]
    render_col = bpy.data.collections["TH_RENDER"]
    collision_col = bpy.data.collections.get("TH_COLLISION")
    anchors_col = bpy.data.collections["TH_ANCHORS"]
    preview_col = bpy.data.collections.get("TH_PREVIEW_ACTORS")
    guide_col = bpy.data.collections.get("TH_PREVIEW_ONLY")
    camera_col = bpy.data.collections.get("TH_CAMERA_PREVIEW")
    samples = [view_weighted_atlas.ViewSample.from_record(row) for row in json.loads(args.envelope.read_text(encoding="utf-8"))["samples"]]
    comparisons = args.output / "comparisons"
    views = args.output / "final_views"
    comparisons.mkdir(parents=True, exist_ok=True)
    views.mkdir(parents=True, exist_ok=True)
    render(scene, camera, samples[0], comparisons / "source_matched_426x240.png", source_col=source_col, render_col=render_col, collision_col=collision_col, anchors_col=anchors_col, preview_col=preview_col, guide_col=guide_col, camera_col=camera_col, source=True, runtime=False)
    render(scene, camera, samples[0], comparisons / "runtime_baked_matched_426x240.png", source_col=source_col, render_col=render_col, collision_col=collision_col, anchors_col=anchors_col, preview_col=preview_col, guide_col=guide_col, camera_col=camera_col, source=False, runtime=True)
    for sample in samples:
        render(scene, camera, sample, views / f"{sample.name}.png", source_col=source_col, render_col=render_col, collision_col=collision_col, anchors_col=anchors_col, preview_col=preview_col, guide_col=guide_col, camera_col=camera_col, source=True, runtime=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))
    print("SECOND_GATE_SIDE_VIEW_RENDER OK")


if __name__ == "__main__":
    main()
