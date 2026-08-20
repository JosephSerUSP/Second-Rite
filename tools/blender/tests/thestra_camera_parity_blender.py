"""Run inside Blender: compare Blender projection against the Lua-owned parity fixture."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--fixture", required=True)
    return parser.parse_args(argv)


def transform_tuple(obj):
    matrix = obj.matrix_world
    return tuple(float(matrix[r][c]) for r in range(4) for c in range(4))


def max_transform_delta(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def record_for_offset(base, offset):
    record = copy.deepcopy(base)
    record["viewportCenterX"] = float(base["viewportCenterX"]) + float(offset)
    record["projectionWindowOffsetX"] = float(offset)
    return record


def main():
    args = parse_args()
    root = Path(args.root).resolve()
    sys.path.insert(0, str(root / "tools" / "blender"))
    import thestra_camera
    import bpy

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    scene = bpy.context.scene
    tolerance = float(fixture.get("pixelTolerance", 1e-4))
    base_transform = None
    maximum_error = 0.0

    for offset in fixture["offsets"]:
        record = record_for_offset(fixture["camera"], offset)
        camera = thestra_camera.create_or_update_camera(record, scene=scene)
        current_transform = transform_tuple(camera)
        if base_transform is None:
            base_transform = current_transform
        elif max_transform_delta(base_transform, current_transform) > 1e-10:
            raise AssertionError("projection-window offset moved TH_CAMERA_PREVIEW transform")
        for sample in fixture["samples"]:
            actual = thestra_camera.project_world_point(scene, camera, sample["world"])
            expected = (sample["screenAtZero"][0] + float(offset), sample["screenAtZero"][1])
            error = max(abs(actual[0] - expected[0]), abs(actual[1] - expected[1]))
            maximum_error = max(maximum_error, error)
            if error > tolerance:
                raise AssertionError(
                    f"offset {offset:+g} {sample['name']} error {error:.9g}px: "
                    f"actual={actual}, expected={expected}"
                )

    camera = thestra_camera.create_or_update_camera(fixture["camera"], scene=scene)
    sample = next(sample for sample in fixture["samples"] if sample["name"] == "mixed")
    expected = sample["screenAtZero"]

    original_shift = camera.data.shift_x
    camera.data.shift_x = original_shift + 0.02
    wrong_shift = thestra_camera.project_world_point(scene, camera, sample["world"])
    camera.data.shift_x = original_shift
    shift_error = max(abs(wrong_shift[0] - expected[0]), abs(wrong_shift[1] - expected[1]))
    if shift_error <= tolerance:
        raise AssertionError("negative control: deliberately wrong lens shift did not fail parity")

    original_location = camera.location.copy()
    camera.location.x += 0.25
    bpy.context.view_layer.update()
    wrong_translation = thestra_camera.project_world_point(scene, camera, sample["world"])
    camera.location = original_location
    bpy.context.view_layer.update()
    translation_error = max(abs(wrong_translation[0] - expected[0]),
                            abs(wrong_translation[1] - expected[1]))
    if translation_error <= tolerance:
        raise AssertionError("negative control: deliberately translated camera did not fail parity")

    print(json.dumps({
        "status": "passed",
        "offsetCases": len(fixture["offsets"]),
        "samplesPerCase": len(fixture["samples"]),
        "maxPixelError": maximum_error,
        "wrongShiftError": shift_error,
        "wrongTranslationError": translation_error,
        "transformInvariant": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
