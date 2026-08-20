"""Render a camera-only perspective study from the current town .blend."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "blender"))
import thestra_camera  # type: ignore


WALKER_PATH = REPO_ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True)
    parser.add_argument("--records", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def vector_tuple(value):
    return [round(float(value[index]), 8) for index in range(3)]


def actor_snapshot():
    collection = bpy.data.collections.get("TH_PREVIEW_ACTORS")
    if collection is None:
        raise RuntimeError("TH_PREVIEW_ACTORS is missing from the current town scene")
    return {
        obj.name: {
            "location": vector_tuple(obj.matrix_world.translation),
        }
        for obj in sorted(collection.objects, key=lambda item: item.name)
    }


def relink_existing_actor_texture():
    """Relink the existing actor image datablock for this unsaved study only.

    The authored blend retains a stale relative path after it is reopened from
    the town folder. The study must use the real sheet while leaving every
    actor object, material node, and saved scene untouched.
    """
    if not WALKER_PATH.is_file():
        raise FileNotFoundError(WALKER_PATH)
    image = bpy.data.images.get("walker.png")
    if image is None:
        raise RuntimeError("walker.png image datablock is missing from the current town scene")
    image.filepath = str(WALKER_PATH)
    image.reload()
    if tuple(image.size) != (144, 48):
        raise RuntimeError(f"walker.png loaded as {tuple(image.size)}, expected (144, 48)")


def set_actor_pixel_scale(obj, camera, scene, frame_width=24, frame_height=48):
    """Scale an existing billboard so one source pixel maps to one output pixel."""
    local_y = [float(vertex.co.y) for vertex in obj.data.vertices]
    local_height = max(local_y) - min(local_y)
    if local_height <= 0:
        raise RuntimeError(f"{obj.name} has no positive sprite-plane height")
    anchor = obj.matrix_world.translation.copy()
    camera_up = camera.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))
    anchor_px = thestra_camera.project_world_point(scene, camera, anchor)
    unit_up_px = thestra_camera.project_world_point(scene, camera, anchor + camera_up)
    pixels_per_world_unit = abs(unit_up_px[1] - anchor_px[1])
    if pixels_per_world_unit <= 1e-8:
        raise RuntimeError(f"{obj.name} camera projection has no vertical scale")
    desired_world_height = float(frame_height) / pixels_per_world_unit
    uniform_scale = desired_world_height / local_height
    obj.scale = (uniform_scale, uniform_scale, uniform_scale)
    bpy.context.view_layer.update()

    top = anchor + camera_up * desired_world_height
    top_px = thestra_camera.project_world_point(scene, camera, top)
    measured_height = abs(top_px[1] - anchor_px[1])
    if abs(measured_height - frame_height) > 1e-4:
        raise RuntimeError(f"{obj.name} failed 1:1 pixel-height calibration: {measured_height}")
    return {
        "uniformScale": round(uniform_scale, 10),
        "worldHeight": round(desired_world_height, 10),
        "sourceFrame": [frame_width, frame_height],
        "measuredPixels": [frame_width, round(measured_height, 8)],
    }


def main():
    args = parse_args()
    blend_path = Path(args.blend).resolve()
    records_path = Path(args.records).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not blend_path.is_file():
        raise FileNotFoundError(blend_path)
    if not records_path.is_file():
        raise FileNotFoundError(records_path)

    payload = json.loads(records_path.read_text(encoding="utf-8"))
    candidates = payload["candidates"]
    if [candidate["id"] for candidate in candidates] != ["A", "B", "B1", "B2", "C"]:
        raise RuntimeError("camera study candidates are not in the required A/B/B1/B2/C order")

    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    scene = bpy.context.scene
    relink_existing_actor_texture()
    original_actor_state = actor_snapshot()
    rows = {
        "contract": payload["contract"],
        "version": payload["version"],
        "reference": payload["reference"],
        "sourceBlend": str(blend_path),
        "renders": [],
        "actorState": original_actor_state,
    }

    for candidate in candidates:
        record = copy.deepcopy(candidate["record"])
        thestra_camera.validate_calibration(record)
        if record["projectionWindowOffsetX"] != 0 or record["projectionWindowOffsetY"] != 0:
            raise RuntimeError(f"{candidate['id']} has a non-zero projection-window offset")
        camera = thestra_camera.create_or_update_camera(
            record, scene=scene, name="TH_CAMERA_PREVIEW", make_active=True)
        scene.render.resolution_x = 426
        scene.render.resolution_y = 240
        scene.render.resolution_percentage = 100
        pixel_scales = {}
        for obj in bpy.data.collections["TH_PREVIEW_ACTORS"].objects:
            thestra_camera.orient_actor_preview(obj, camera)
            pixel_scales[obj.name] = set_actor_pixel_scale(obj, camera, scene)
        bpy.context.view_layer.update()
        scene.render.filepath = str((output_dir / f"{candidate['id']}.png").resolve())
        bpy.ops.render.render(write_still=True)

        after_actor_state = actor_snapshot()
        if after_actor_state != original_actor_state:
            raise RuntimeError(f"camera candidate {candidate['id']} changed actor placement")

        rows["renders"].append({
            "id": candidate["id"],
            "name": candidate["name"],
            "distanceScale": candidate["scale"],
            "pitchDegrees": candidate["pitchDegrees"],
            "pitchRadians": round(float(record["orientation"]["pitchRadians"]), 12),
            "eye": record["eye"],
            "fovHalfX": record["fovHalfX"],
            "fovHalfY": record["fovHalfY"],
            "derivedBlenderLensMm": round(float(camera.data.lens), 8),
            "sensorWidthMm": round(float(camera.data.sensor_width), 8),
            "principalPoint": {
                "viewportCenterX": record["viewportCenterX"],
                "viewportCenterY": record["viewportCenterY"],
                "shiftX": round(float(camera.data.shift_x), 8),
                "shiftY": round(float(camera.data.shift_y), 8),
            },
            "projectionWindowOffsetX": record["projectionWindowOffsetX"],
            "projectionWindowOffsetY": record["projectionWindowOffsetY"],
            "actorBillboards": "temporary camera-facing rotation; feet/world locations preserved",
            "actorPixelScale": pixel_scales,
            "image": str((output_dir / f"{candidate['id']}.png").resolve()),
        })

    (output_dir / "camera-study-report.json").write_text(
        json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"TOWN CAMERA PERSPECTIVE STUDY OK: {output_dir}")


if __name__ == "__main__":
    main()
