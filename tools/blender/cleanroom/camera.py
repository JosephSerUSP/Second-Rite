"""Clean-room camera front-end over the generic Thestra calibration tooling.

Authority direction is unchanged and one-way:

    town-camera-authority.json -> LOVE/Thestra -> calibration JSON
        -> thestra_camera.py -> Blender TH_CAMERA_PREVIEW

Nothing here authors a lens, a pitch or an eye. The only thing this module
adds is a *measured* answer to a question the calibration does not itself
answer: at what depth does a 1.75-world-unit actor project to exactly 48
native pixels? That is solved numerically against Blender's own projection,
never eyeballed.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import thestra_camera as tc  # noqa: E402

CALIBRATION = (
    ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring"
    / "town-cleanroom" / "town-camera-calibration.json"
)

WALKER = (
    ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
)

ACTOR_WORLD_HEIGHT = 1.75
ACTOR_FRAME_W = 24
ACTOR_FRAME_H = 48


def load(offset_x: float = 0.0):
    record = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    tc.validate_calibration(record)
    if offset_x:
        record["projectionWindowOffsetX"] = float(offset_x)
    return record


def make_camera(record, *, scene=None, make_active=True):
    import bpy
    scene = scene or bpy.context.scene
    return tc.create_or_update_camera(record, scene=scene, make_active=make_active)


def solve_action_plane(record, cam_obj, *, scene=None,
                       target_px: float = float(ACTOR_FRAME_H),
                       world_height: float = ACTOR_WORLD_HEIGHT):
    """Bisect the camera-forward depth at which `world_height` spans `target_px`.

    Measured through Blender's own world_to_camera_view, so lens shift,
    pixel aspect and sensor fit are all included rather than re-derived.
    """
    import bpy
    scene = scene or bpy.context.scene
    eye = cam_obj.location.copy()
    o = record["orientation"]
    fx, fy = float(o["forwardX"]), float(o["forwardY"])

    def span_px(depth):
        base = (eye.x + fx * depth, eye.y + fy * depth, 0.0)
        top = (base[0], base[1], world_height)
        _, y0 = tc.project_world_point(scene, cam_obj, base)
        _, y1 = tc.project_world_point(scene, cam_obj, top)
        return abs(y0 - y1)

    lo, hi = 0.5, 400.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if span_px(mid) > target_px:
            lo = mid
        else:
            hi = mid
    depth = 0.5 * (lo + hi)
    return {
        "depth": depth,
        "planeX": eye.x + fx * depth,
        "planeY": eye.y + fy * depth,
        "measuredPx": span_px(depth),
        "lensMm": float(cam_obj.data.lens),
        "eye": [eye.x, eye.y, eye.z],
        "pitchDegrees": math.degrees(float(o["pitchRadians"])),
        "hFovDegrees": math.degrees(2.0 * math.atan(float(record["fovHalfX"]))),
    }


def horizon_z(record, cam_obj, plane_x, *, scene=None):
    """World Z on the action plane that lands on the calibration's principal row."""
    import bpy
    scene = scene or bpy.context.scene
    y = cam_obj.location.y
    lo, hi = -50.0, 50.0
    want = float(record["viewportCenterY"])
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        _, py = tc.project_world_point(scene, cam_obj, (plane_x, y, mid))
        if py > want:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
