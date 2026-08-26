#!/usr/bin/env python3
"""Derive the Second Gate town side-view camera calibration record.

Nothing here is hand-tuned: the lens is fixed by
`docs/design/town-authoring-known-good.md`, camera distance is solved from the
Walker's fixed native pixel height, and the eye height is solved from where the
Walker's feet should sit inside the COMPOSITION.

The composition is the top `--compose-height` rows of the native target, not the
whole target. The status menu occupies the remainder, so anything below the
composition (floor extension, plinth, a solid plate) is superfluous by design
and must not carry the frame.

    python tools/blender/make_town_camera.py
    python tools/blender/make_town_camera.py --feet-at 0.90 --horizon-at 0.42
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "tools" / "blender" / "fixtures" / "town_sideview_camera.json"

# Fixed presentation contract.
TARGET_W, TARGET_H = 426, 240
BASE_W, BASE_H = 256, 144
FOV_HALF_X = 0.25                      # tangent; 2*atan(0.25) = 28.0725 deg
WALKER_WORLD_HEIGHT = 1.75
WALKER_NATIVE_PIXELS = 48.0


def build(compose_height: float, feet_at: float, horizon_at: float) -> dict:
    fov_half_y = FOV_HALF_X * (BASE_H / BASE_W)

    # Preserve the lens, solve distance for the actor's fixed pixel height.
    distance = BASE_H * WALKER_WORLD_HEIGHT / (2.0 * fov_half_y * WALKER_NATIVE_PIXELS)

    # Pixels a world unit of height drops below the horizon at the action plane.
    px_per_unit = BASE_H / (2.0 * fov_half_y * distance)

    horizon_y = horizon_at * compose_height
    feet_y = feet_at * compose_height
    head_y = feet_y - WALKER_NATIVE_PIXELS

    # Feet sit (eye_height * px_per_unit) below the horizon; solve eye height.
    eye_z = (feet_y - horizon_y) / px_per_unit

    if head_y < 0.0:
        raise SystemExit(f"Walker head lands at y={head_y:.1f}, above the frame")
    if feet_y > compose_height:
        raise SystemExit(
            f"Walker feet land at y={feet_y:.1f}, below the {compose_height:g}px "
            "composition and therefore under the status menu"
        )

    return {
        "contract": "thestra.world-camera-calibration",
        "version": 1,
        "projection": "perspective",
        "eye": {"x": -distance, "y": 0.0, "z": eye_z},
        "orientation": {
            # right = forward x up. With forward +X and up +Z that is -Y.
            # A +Y right vector makes a determinant -1 (mirrored) basis, which
            # create_actor_preview's to_quaternion() cannot represent. See #935.
            "forwardX": 1.0, "forwardY": 0.0,
            "rightX": 0.0, "rightY": -1.0,
            "pitchRadians": 0.0,
        },
        "projectionScale": {"x": 1.0, "y": 1.0},
        "fovHalfX": FOV_HALF_X,
        "fovHalfY": fov_half_y,
        "nearPlane": 0.05,
        "farPlane": 96.0,
        "targetWidth": TARGET_W, "targetHeight": TARGET_H,
        "baseViewportWidth": BASE_W, "baseViewportHeight": BASE_H,
        "viewportCenterX": TARGET_W // 2,
        "viewportCenterY": horizon_y,
        "projectionWindowOffsetX": 0, "projectionWindowOffsetY": 0,
        "coordinateSystem": {
            "handedness": "right-handed", "worldUp": "+Z", "worldHorizontal": "XY",
            "cameraForward": "+depth", "cameraRight": "+right",
            "screenOrigin": "top-left", "screenY": "+down",
            "blenderCameraForward": "-Z", "blenderCameraUp": "+Y",
        },
        "thestraComposition": {
            "composeHeight": compose_height,
            "note": ("Composition is the top composeHeight rows of targetHeight; "
                     "the status menu owns the rest. Nothing below composeHeight "
                     "may be load-bearing."),
            "walkerFeetY": feet_y,
            "walkerHeadY": head_y,
            "horizonY": horizon_y,
            "solvedDistance": distance,
            "solvedEyeHeight": eye_z,
            "pixelsPerWorldUnit": px_per_unit,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="make_town_camera")
    parser.add_argument("--compose-height", type=float, default=float(BASE_H),
                        help="rows of the native target that carry composition")
    parser.add_argument("--feet-at", type=float, default=0.86,
                        help="Walker feet, as a fraction of the composition")
    parser.add_argument("--horizon-at", type=float, default=0.458,
                        help="principal point, as a fraction of the composition")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    record = build(args.compose_height, args.feet_at, args.horizon_at)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    c = record["thestraComposition"]
    print(f"composition   : top {c['composeHeight']:g} of {TARGET_H} rows "
          f"({TARGET_H - c['composeHeight']:g} under the status menu)")
    print(f"lens          : fovHalfX {FOV_HALF_X} "
          f"({2 * math.degrees(math.atan(FOV_HALF_X)):.4f} deg horizontal)")
    print(f"solved distance: {c['solvedDistance']:.4f} world units")
    print(f"solved eye     : {c['solvedEyeHeight']:.4f} world units")
    print(f"horizon y      : {c['horizonY']:.1f}")
    print(f"walker head y  : {c['walkerHeadY']:.1f}")
    print(f"walker feet y  : {c['walkerFeetY']:.1f}  "
          f"({c['composeHeight'] - c['walkerFeetY']:.1f}px of composition below the feet)")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
