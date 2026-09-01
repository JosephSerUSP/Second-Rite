#!/usr/bin/env python3
"""Derive the Second Gate town side-view camera calibration record.

Nothing here is hand-tuned: the lens is fixed by
`docs/design/town-authoring-known-good.md`, camera distance is solved from the
Walker's fixed native pixel height, and the eye height is solved from where the
Walker's feet should sit in the frame.

`--character-floor-limit` (144) is the LOWEST a character may stand before the
engine would need Y camera scrolling. It is the bottom of the free screen area:
below it sits the permanent translucent menu. It is a constraint on character
placement, NOT a crop: the scene keeps filling the whole 426x240 target and
beyond. Floor continues past the limit, foreground sits in front of it, and
outdoor scenes especially want ground well below it.

Characters usually stand a little above the limit -- `--feet-y` defaults to
144 - 16 = 128.

    python tools/blender/make_town_camera.py
    python tools/blender/make_town_camera.py --feet-y 132 --horizon-y 60
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "tools" / "blender" / "fixtures" / "town_sideview_camera.json"

# Fixed presentation contract.
#
# The game ships three width presets -- 256x240 ("Classic", the canon one),
# 320x240 and 426x240 -- all 240 tall. The lower part of the screen is a
# permanent translucent menu, so the FREE SCREEN AREA is 256x144: that is the
# space a composition actually gets, and it is where the 144 character floor
# limit comes from.
#
# The record is authored at Classic. A wider preset is the same camera with a
# wider window (`stage_room_model.py --target-width`), which reveals more world
# at the same texel scale rather than zooming.
TARGET_W, TARGET_H = 256, 240
BASE_W, BASE_H = 256, 144
WIDTH_PRESETS = (256, 320, 426)
FOV_HALF_X = 0.25                      # tangent; 2*atan(0.25) = 28.0725 deg
WALKER_WORLD_HEIGHT = 1.75
WALKER_NATIVE_PIXELS = 48.0


def build(floor_limit: float, feet_y: float, horizon_y: float,
          pitch_degrees: float = 0.0) -> dict:
    """Solve the record. `pitch_degrees` tips the camera DOWN.

    Pitch is what makes vertical edges stop being parallel; no lens width and no
    principal-point shift on a level camera can do it. It does not change what
    the record has to guarantee: a 1.75 m actor at 48 native pixels, feet at
    `feet_y`. Only how those are solved changes.

    The actor is a VIEW-ALIGNED billboard - an axis-aligned rectangle that only
    scales - so its pixel height depends solely on the SLANT distance to its
    ground point, never on the pitch. That is why `distance` below is the slant,
    and stays the same at every angle; the eye height and the principal point
    absorb the rotation instead.
    """
    fov_half_y = FOV_HALF_X * (BASE_H / BASE_W)
    pitch = math.radians(pitch_degrees)

    # Preserve the lens, solve distance for the actor's fixed pixel height.
    distance = BASE_H * WALKER_WORLD_HEIGHT / (2.0 * fov_half_y * WALKER_NATIVE_PIXELS)

    # Pixels a world unit of height drops below the horizon at the action plane.
    px_per_unit = BASE_H / (2.0 * fov_half_y * distance)

    head_y = feet_y - WALKER_NATIVE_PIXELS

    if pitch == 0.0:
        # Feet sit (eye_height * px_per_unit) below the horizon.
        eye_z = (feet_y - horizon_y) / px_per_unit
        horiz_distance = distance
    else:
        # Pitched: the principal point carries the horizon, and the eye and the
        # horizontal distance follow from where the feet must land at a fixed
        # slant. K is the lens in pixels: px per unit of the camera-space ratio.
        k = px_per_unit * distance
        principal_y = horizon_y + k * math.tan(pitch)
        y_c = distance * (principal_y - feet_y) / k
        horiz_distance = distance * math.cos(pitch) + y_c * math.sin(pitch)
        eye_z = distance * math.sin(pitch) - y_c * math.cos(pitch)
        horizon_y = principal_y

    if head_y < 0.0:
        raise SystemExit(f"Walker head lands at y={head_y:.1f}, above the frame")
    if feet_y > floor_limit:
        raise SystemExit(
            f"Walker feet land at y={feet_y:.1f}, below the character floor "
            f"limit of {floor_limit:g}px; the engine would need Y camera "
            "scrolling to show the character there"
        )

    return {
        "contract": "thestra.world-camera-calibration",
        "version": 1,
        "projection": "perspective",
        "eye": {"x": -horiz_distance, "y": 0.0, "z": eye_z},
        "pitchDegrees": pitch_degrees,
        "horizontalDistance": horiz_distance,
        "orientation": {
            # right = forward x up. With forward +X and up +Z that is -Y.
            # A +Y right vector makes a determinant -1 (mirrored) basis, which
            # create_actor_preview's to_quaternion() cannot represent. See #935.
            "forwardX": 1.0, "forwardY": 0.0,
            "rightX": 0.0, "rightY": -1.0,
            "pitchRadians": pitch,
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
            "characterFloorLimit": floor_limit,
            "note": ("characterFloorLimit is the lowest a character may stand "
                     "before the engine needs Y camera scrolling. It bounds "
                     "CHARACTER PLACEMENT only -- it is not a crop. The scene "
                     "fills the whole target and beyond: floor continues past "
                     "the limit, foreground sits in front of it."),
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
    parser.add_argument("--character-floor-limit", type=float, default=float(BASE_H),
                        help="lowest native y a character may stand at")
    parser.add_argument("--feet-y", type=float, default=float(BASE_H) - 16.0,
                        help="native y of the Walker's feet (default limit - 16)")
    parser.add_argument("--horizon-y", type=float, default=66.0,
                        help="native y of the principal point / horizon")
    parser.add_argument("--pitch-degrees", type=float, default=0.0,
                        help="tip the camera down; this is what bends verticals")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    record = build(args.character_floor_limit, args.feet_y, args.horizon_y,
                   args.pitch_degrees)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    c = record["thestraComposition"]
    print(f"character floor limit: y={c['characterFloorLimit']:g} of {TARGET_H} "
          "(placement bound, NOT a crop -- scene fills the full target)")
    print(f"lens          : fovHalfX {FOV_HALF_X} "
          f"({2 * math.degrees(math.atan(FOV_HALF_X)):.4f} deg horizontal)")
    print(f"solved distance: {c['solvedDistance']:.4f} world units")
    print(f"solved eye     : {c['solvedEyeHeight']:.4f} world units")
    print(f"horizon y      : {c['horizonY']:.1f}")
    print(f"walker head y  : {c['walkerHeadY']:.1f}")
    print(f"walker feet y  : {c['walkerFeetY']:.1f}  "
          f"({c['characterFloorLimit'] - c['walkerFeetY']:.1f}px of headroom above the limit)")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
