"""Bake and prove the selected fresh town winner through the generic V0 pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import build_town_gauntlet_20260820 as gauntlet  # noqa: E402
from town_environment_pipeline import run_pipeline_in_blender  # noqa: E402


def args():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--blend", required=True)
    p.add_argument("--output", required=True)
    return p.parse_args(raw)


def collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        raise RuntimeError(f"missing collection {name}")
    return col


def set_collection_render(name, hidden):
    col = collection(name)
    col.hide_render = hidden
    for obj in col.objects:
        obj.hide_render = hidden


def count_tris(col):
    total = 0
    for obj in col.objects:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        total += len(obj.data.loop_triangles)
    return total


def render_center(path, source_visible, actors_visible):
    scene = bpy.context.scene
    cols = {name: collection(name) for name in (
        "TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_PREVIEW_ACTORS",
        "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW",
    )}
    set_collection_render("TH_SOURCE", not source_visible)
    set_collection_render("TH_RENDER", source_visible)
    set_collection_render("TH_COLLISION", True)
    set_collection_render("TH_PREVIEW_ACTORS", not actors_visible)
    set_collection_render("TH_PREVIEW_ONLY", False)
    cam = gauntlet.thestra_camera.create_or_update_camera(
        gauntlet.camera_record(0.0), scene=scene, name="TH_CAMERA_PREVIEW", make_active=True)
    gauntlet.move_to_collection(cam, cols["TH_CAMERA_PREVIEW"])
    cam.hide_render = False
    for obj in cols["TH_PREVIEW_ACTORS"].objects:
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = cam.matrix_world.to_quaternion()
    gauntlet.configure_render(scene, path)
    bpy.ops.render.render(write_still=True)


def main():
    a = args()
    blend = Path(a.blend).resolve()
    out = Path(a.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    source_tris = count_tris(collection("TH_SOURCE"))
    render_tris_before = count_tris(collection("TH_RENDER"))

    source_path = out / "source_matched_426x240.png"
    render_center(source_path, source_visible=True, actors_visible=False)

    run_pipeline_in_blender(blend, out, atlas_size=512, bake_samples=4)

    runtime_path = out / "runtime_baked_matched_426x240.png"
    render_center(runtime_path, source_visible=False, actors_visible=False)

    runtime_tris = count_tris(collection("TH_RENDER"))
    # The generic pipeline has already made TH_RENDER a one-material atlas
    # target. Save the post-bake authoring state as evidence, not as runtime
    # authority; the runtime products remain the exported package.
    baked_blend = out / "C3_baked.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(baked_blend))
    atlas = out / "environment.png"
    proof = {
        "sourceBlend": str(blend),
        "bakedBlend": str(baked_blend),
        "sourceRender": source_path.name,
        "runtimeRender": runtime_path.name,
        "atlas": atlas.name,
        "atlasDimensions": [512, 512],
        "atlasColorSpace": "Non-Color",
        "sourceTrianglesBase": source_tris,
        "renderTrianglesBeforeBake": render_tris_before,
        "renderTrianglesAfterBake": runtime_tris,
        "previewActorsBaked": False,
        "camera": {
            "target": [426, 240],
            "projection": "perspective",
            "pitchDegrees": 0.0,
            "fovHalfX": 0.25,
            "projectionWindow": "fixed eye; -96/0/+96 via principal-point shift",
        },
        "causality": "TH_SOURCE material/light appearance -> Cycles Combined bake -> TH_RENDER UV atlas",
    }
    (out / "bake_proof.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
