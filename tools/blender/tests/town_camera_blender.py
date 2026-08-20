"""Blender-side acceptance checks for the next town gauntlet camera."""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))


def matrix_signature(matrix):
    return tuple(float(value) for row in matrix for value in row)


def close_tuple(a, b, eps=1e-9):
    return len(a) == len(b) and all(abs(x - y) <= eps for x, y in zip(a, b))


def main():
    import bpy
    import thestra_camera

    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)

    record = json.loads(args.camera.read_text(encoding="utf-8"))
    thestra_camera.validate_calibration(record)
    if abs(float(record["orientation"]["pitchRadians"])) > 1e-10:
        raise RuntimeError("town camera must be level for the next gauntlet")

    scene = bpy.context.scene
    base = thestra_camera.create_or_update_camera(record, scene=scene, make_active=True)
    lens = float(base.data.lens)
    if not (40.0 <= lens <= 45.0):
        raise RuntimeError(f"owner-selected ~40 mm family drifted: Blender lens={lens:.6f} mm")
    expected = 36.0 * 0.5 * (
        float(record["projectionScale"]["x"])
        / float(record["fovHalfX"])
        * (float(record["baseViewportWidth"]) / float(record["targetWidth"]))
    )
    if abs(lens - expected) > 1e-8:
        raise RuntimeError(f"derived lens mismatch: {lens} vs {expected}")

    baseline_matrix = matrix_signature(base.matrix_world)
    baseline_lens = lens
    baseline_center_x = float(record["viewportCenterX"])

    for offset in (-96.0, 0.0, 96.0):
        shifted = copy.deepcopy(record)
        shifted["projectionWindowOffsetX"] = offset
        shifted["viewportCenterX"] = baseline_center_x + offset
        camera = thestra_camera.create_or_update_camera(shifted, scene=scene, make_active=True)
        if not close_tuple(matrix_signature(camera.matrix_world), baseline_matrix):
            raise RuntimeError(f"projection-window offset {offset:+g} moved the camera transform")
        if abs(float(camera.data.lens) - baseline_lens) > 1e-9:
            raise RuntimeError(f"projection-window offset {offset:+g} changed the lens")

    print(
        "THESTRA_TOWN_CAMERA_BLENDER OK "
        f"lens={baseline_lens:.4f}mm pitch=0 offsets=-96,0,+96 transformInvariant=true"
    )


if __name__ == "__main__":
    main()
