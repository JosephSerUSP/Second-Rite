#!/usr/bin/env python3
"""Bake and inspect the selected Second Gate side-view winner."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--envelope", required=True, type=Path)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def triangle_count(objects):
    total = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        total += len(obj.data.loop_triangles)
    return total


def set_visual_layers(source_col, render_col, collision_col, anchors_col, preview_col, guide_col, camera_col, *, source, runtime, actors):
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
        preview_col.hide_render = not actors
        for obj in preview_col.objects:
            obj.hide_render = not actors


def render_view(scene, camera, sample, output_path, *, source_col, render_col, collision_col, anchors_col, preview_col, guide_col, camera_col, show_source, show_runtime, show_actors):
    import second_gate_render
    import view_weighted_atlas

    set_visual_layers(
        source_col, render_col, collision_col, anchors_col, preview_col, guide_col, camera_col,
        source=show_source, runtime=show_runtime, actors=show_actors,
    )
    second_gate_render.apply(scene, "cycles-draft")
    base_state = view_weighted_atlas._camera_state(camera)
    view_weighted_atlas._apply_view(scene, camera, sample, base_state)
    scene.render.filepath = str(output_path)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)
    view_weighted_atlas._restore_camera(scene, camera, base_state)


def run(args):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import second_gate_render  # noqa: F401
    import town_environment_pipeline
    import view_weighted_atlas

    source_blend = args.source.resolve()
    output = args.output.resolve()
    package = output / "package"
    views = output / "final_views"
    comparisons = output / "comparisons"
    for directory in (package, views, comparisons):
        directory.mkdir(parents=True, exist_ok=True)

    envelope_payload = json.loads(args.envelope.read_text(encoding="utf-8"))
    samples = [view_weighted_atlas.ViewSample.from_record(record) for record in envelope_payload["samples"]]

    bpy.ops.wm.open_mainfile(filepath=str(source_blend))
    scene = bpy.context.scene
    camera = scene.camera
    source_col = bpy.data.collections["TH_SOURCE"]
    render_col = bpy.data.collections["TH_RENDER"]
    collision_col = bpy.data.collections.get("TH_COLLISION")
    anchors_col = bpy.data.collections["TH_ANCHORS"]
    preview_col = bpy.data.collections.get("TH_PREVIEW_ACTORS")
    guide_col = bpy.data.collections.get("TH_PREVIEW_ONLY")
    camera_col = bpy.data.collections.get("TH_CAMERA_PREVIEW")

    started = time.perf_counter()
    town_environment_pipeline.run_pipeline_in_blender(
        source_blend,
        package,
        atlas_size=512,
        bake_samples=4,
        render_profile="cycles-draft",
        atlas_allocation="view-weighted",
        camera_envelope=samples,
        view_policy="bounded-camera",
        margin_px=4,
    )

    # Pipeline joins TH_RENDER into one coarse target.  Keep the source layer
    # and target layer together in the saved inspection blend, but render them
    # separately for the source/runtime comparison.
    runtime_obj = next(obj for obj in render_col.objects if obj.type == "MESH")
    source_triangles = triangle_count(source_col.objects)
    runtime_triangles = triangle_count([runtime_obj])
    manifest = json.loads((package / "environment.json").read_text(encoding="utf-8"))
    counts = {
        "sourceTriangles": source_triangles,
        "sourceMeshObjects": sum(1 for obj in source_col.objects if obj.type == "MESH"),
        "runtimeTriangles": runtime_triangles,
        "runtimeVertices": len(runtime_obj.data.vertices),
        "runtimeMeshObjects": 1,
        "atlasDimensions": manifest["stats"]["textureDimensions"],
        "allocation": manifest["provenance"]["atlasAllocation"],
        "allocationPolicy": manifest["provenance"]["allocationPolicy"],
        "cameraEnvelopeSamples": [sample.to_record() for sample in samples],
        "bakeSeconds": manifest["provenance"]["bakeSeconds"],
    }
    (output / "triangle_counts.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")

    center = samples[0]
    render_view(scene, camera, center, comparisons / "source_matched_426x240.png", source_col=source_col, render_col=render_col, collision_col=collision_col, anchors_col=anchors_col, preview_col=preview_col, guide_col=guide_col, camera_col=camera_col, show_source=True, show_runtime=False, show_actors=True)
    render_view(scene, camera, center, comparisons / "runtime_baked_matched_426x240.png", source_col=source_col, render_col=render_col, collision_col=collision_col, anchors_col=anchors_col, preview_col=preview_col, guide_col=guide_col, camera_col=camera_col, show_source=False, show_runtime=True, show_actors=True)
    for sample in samples:
        render_view(scene, camera, sample, views / f"{sample.name}.png", source_col=source_col, render_col=render_col, collision_col=collision_col, anchors_col=anchors_col, preview_col=preview_col, guide_col=guide_col, camera_col=camera_col, show_source=True, show_runtime=False, show_actors=True)

    source_collection_state = {
        "source": [obj.name for obj in source_col.objects if obj.type == "MESH"],
        "render": [obj.name for obj in render_col.objects if obj.type == "MESH"],
        "collision": [obj.name for obj in collision_col.objects] if collision_col else [],
        "anchors": [obj.name for obj in anchors_col.objects],
        "previewActors": [obj.name for obj in preview_col.objects] if preview_col else [],
        "previewOnly": [obj.name for obj in guide_col.objects] if guide_col else [],
        "cameraPreview": [obj.name for obj in camera_col.objects] if camera_col else [],
    }
    (output / "collection_contract.json").write_text(json.dumps(source_collection_state, indent=2) + "\n", encoding="utf-8")
    scene["second_gate_runtime_bake"] = "view-weighted bounded-camera atlas"
    scene["second_gate_runtime_package"] = str(package.relative_to(ROOT)).replace("\\", "/")
    scene["second_gate_source_triangles"] = source_triangles
    scene["second_gate_runtime_triangles"] = runtime_triangles
    scene["second_gate_atlas_dimensions"] = "512x512"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "winner_source_and_baked.blend"))

    report = {
        "winner": "ember_bell_foundry",
        "sourceBlend": source_blend.name,
        "outputBlend": "winner_source_and_baked.blend",
        "package": "package/",
        "views": [path.name for path in sorted(views.glob("*.png"))],
        "comparisons": [path.name for path in sorted(comparisons.glob("*.png"))],
        "counts": counts,
        "collectionContract": source_collection_state,
        "elapsedSeconds": round(time.perf_counter() - started, 4),
    }
    (output / "winner_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("SECOND_GATE_SIDE_VIEW_BAKE OK")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run(parse_args())
