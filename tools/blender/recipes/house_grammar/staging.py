"""What the camera makes of a generated building.

A grammar validated only on its own topology passes every test and stages
wrong. These are the predicates that check a building against the camera it
was authored for, so a recipe can be rejected by measurement before anyone
renders it: readable size, the tall-or-continuous occluder rule, and dock
coverage paired with a size metric so coverage cannot be won by building a
blank wall.

**Why the projection is reimplemented here.** The same arithmetic lives in
`interior.native_y_at`, but that module imports ``bpy`` at module level, and
the whole point of the grammar package is that it runs in the ordinary unit
gate. The duplication is deliberate and it is guarded: `test_house_grammar_
staging.py` pins every number here against constants that were measured
independently and written into `exterior.py`'s docstrings -- the 1.75 m walker
reading 48 px with its feet on scanline 128, the ground crossing scanline 240
at X = -12.01, and dock cover heights of 1.09 m at X = -11, 0.64 m at X = -8
and 0.03 m at X = -4. If this file ever drifts from the scene-side maths, one
of those independently derived numbers stops matching.

The camera is not a parameter. A modelled exterior reuses
``fixtures/town_sideview_camera.json`` unchanged, because character pixel scale
is fixed across the whole game; the 2D plate presentation of the same street
uses a larger scale that belongs to the plate, and a modelled screen must not
inherit it.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .records import quantise

FIXTURE = (Path(__file__).resolve().parents[3] / "blender" / "fixtures"
           / "town_sideview_camera.json")

# The frame, in native scanlines. Y = 0 is the top of the screen.
FRAME_BOTTOM_NATIVE_Y = 240.0
# Rows below this are seen THROUGH the translucent status menu.
DOCK_TOP_NATIVE_Y = 144.0
# The walker occupies these rows: head 80, feet 128.
WALKER_HEAD_Y = 80.0
WALKER_FEET_Y = 128.0
WALKER_HEIGHT_M = 1.75

# The tall-or-continuous thresholds, taken from `Exterior.occludes_player` so
# that a building judged here and a prop judged there are judged alike.
IGNORE_COVERS = 0.2
IGNORE_WIDTH = 0.25
BOARD_COVERS = 0.55
BOARD_WIDTH = 0.25
# Only geometry in FRONT of the action plane can be an occluder. The far
# terrace covers the character too, but the player walks in front of it -- it
# is framing. Foreground is what you pass BEHIND, and that is a depth test, so
# a record whose near face is behind X = 0 is never classified at all.
ACTION_PLANE_X = 0.0

_CACHE = {}


def camera_record(path=None):
    """The solved town camera. Cached: it is a fixture, not scene state."""
    source = Path(path) if path else FIXTURE
    key = str(source)
    if key not in _CACHE:
        _CACHE[key] = json.loads(source.read_text(encoding="utf-8"))
    return _CACHE[key]


def _k(record):
    return record["baseViewportHeight"] / (2.0 * record["fovHalfY"])


def native_y_at(x, z, record=None):
    """Native scanline a world point projects to."""
    record = record or camera_record()
    depth = float(x) - record["eye"]["x"]
    if depth <= 1e-6:
        raise ValueError(f"x={x} is at or behind the camera")
    return record["viewportCenterY"] + _k(record) * (record["eye"]["z"] - float(z)) / depth


def half_width_at(depth, record=None):
    record = record or camera_record()
    return record["fovHalfX"] * depth * (record["targetWidth"]
                                         / record["baseViewportWidth"])


def pixels_per_metre_at(x, record=None):
    """Vertical pixels one metre spans at depth ``x``.

    At the action plane this returns the number that fixes character scale for
    the whole game: a 1.75 m walker reads 48 px.
    """
    record = record or camera_record()
    depth = float(x) - record["eye"]["x"]
    if depth <= 1e-6:
        raise ValueError(f"x={x} is at or behind the camera")
    return _k(record) / depth


def dock_cover_height(x, record=None):
    """Height above the ground an object at depth ``x`` needs to reach row 144.

    This falls off fast with depth, which is why a street's near layer is
    barrels and low walls rather than towers: the band only has to reach the
    top of the menu, not the top of the screen.
    """
    record = record or camera_record()
    lo, hi = 0.0, 24.0
    for _ in range(64):
        mid = (lo + hi) / 2.0
        if native_y_at(x, mid, record) > DOCK_TOP_NATIVE_Y:
            lo = mid
        else:
            hi = mid
    return hi


def ground_exit_x(record=None):
    """World X where the ground plane leaves the bottom of the frame."""
    record = record or camera_record()
    k = _k(record)
    depth = k * record["eye"]["z"] / (FRAME_BOTTOM_NATIVE_Y - record["viewportCenterY"])
    return record["eye"]["x"] + depth


# -- placing a grammar record in the scene --------------------------------

def place(record, *, back_x, lane_y, lane_centre):
    """The scene-frame AABB of one grammar record.

    The grammar authors in the building's own frame (+X into the building,
    +Y along the street). This is the only conversion in the package, and it
    matches `Exterior.y`: the runtime lane runs west to east while Blender's
    screen-right is -Y, so a lane position becomes ``lane_centre - lane_y``.
    Getting this backwards is invisible in every topology test and obvious in
    the first render, which is why it lives in one function with a test on it.
    """
    (lx0, ly0, lz0), (lx1, ly1, lz1) = record.bounds()
    ox, oy, oz = record.origin
    x0, x1 = back_x + ox + lx0, back_x + ox + lx1
    # -Y is screen right, so the local +Y extent maps to the LOWER scene Y.
    centre_y = lane_centre - float(lane_y)
    y0 = centre_y - (oy + ly1)
    y1 = centre_y - (oy + ly0)
    return ((quantise(x0), quantise(y0), quantise(oz + lz0)),
            (quantise(x1), quantise(y1), quantise(oz + lz1)))


def readable_size(record, *, back_x, lane_y, lane_centre, camera=None):
    """How large this record actually reads, in native pixels.

    Paired with dock coverage on purpose. Coverage alone rewards building a
    masonry wall across the near band; a wall scores well and reads as
    nothing, because readable size is set by DEPTH, not by extent.
    """
    camera = camera or camera_record()
    (x0, y0, z0), (x1, y1, z1) = place(record, back_x=back_x, lane_y=lane_y,
                                       lane_centre=lane_centre)
    near_x = x0
    top = native_y_at(near_x, z1, camera)
    base = native_y_at(near_x, z0, camera)
    depth = near_x - camera["eye"]["x"]
    frame_width = 2.0 * half_width_at(depth, camera)
    return {
        "heightPx": round(base - top, 2),
        "widthFrames": round((y1 - y0) / frame_width, 3),
        "topRow": round(top, 2),
        "baseRow": round(base, 2),
        "nearX": quantise(near_x),
        # A person standing at this depth for comparison. A frame-fraction
        # metric cannot see that a building dwarfs a person; this can.
        "walkerPx": round(WALKER_HEIGHT_M * pixels_per_metre_at(near_x, camera), 2),
    }


def classify_occluder(record, *, back_x, lane_y, lane_centre, camera=None):
    """Apply the tall-or-continuous rule to one record.

    An occluder may be tall or continuous, never both: a pole is fine, a low
    skirt is fine, a board that swallows the whole character is not, because
    the player loses track of where they are.
    """
    camera = camera or camera_record()
    (x0, y0, z0), (x1, y1, z1) = place(record, back_x=back_x, lane_y=lane_y,
                                       lane_centre=lane_centre)
    near_x = x0
    depth = near_x - camera["eye"]["x"]
    if depth <= 1e-6 or near_x >= ACTION_PLANE_X:
        return None
    top = native_y_at(near_x, z1, camera)
    base = native_y_at(near_x, z0, camera)
    span = WALKER_FEET_Y - WALKER_HEAD_Y
    overlap = max(0.0, min(base, WALKER_FEET_Y) - max(top, WALKER_HEAD_Y))
    covers = overlap / span
    width = (y1 - y0) / (2.0 * half_width_at(depth, camera))
    if covers < IGNORE_COVERS and width < IGNORE_WIDTH:
        return None
    if covers >= BOARD_COVERS and width >= BOARD_WIDTH:
        shape = "BOARD"
    elif width >= BOARD_WIDTH:
        shape = "skirt"
    else:
        shape = "pole"
    return {"role": record.role, "name": record.name,
            "coversCharacter": round(covers, 3),
            "frameWidth": round(width, 3), "shape": shape}


def boards(records, *, back_x, lane_y, lane_centre, camera=None):
    """Every record that violates the tall-or-continuous rule.

    The gate is that this is EMPTY. It is expressed as a list rather than a
    boolean so a failing recipe says which assembly did it.
    """
    found = []
    for record in records:
        verdict = classify_occluder(record, back_x=back_x, lane_y=lane_y,
                                    lane_centre=lane_centre, camera=camera)
        if verdict and verdict["shape"] == "BOARD":
            found.append(verdict)
    return found


def dock_coverage(records, *, back_x, lane_y, lane_centre, camera=None,
                  samples=96):
    """Fraction of the translucent menu band this building actually covers.

    Reported beside the readable size of the tallest record, because the pair
    is the metric: coverage on its own is satisfied by a blank wall.
    """
    camera = camera or camera_record()
    boxes = [place(record, back_x=back_x, lane_y=lane_y, lane_centre=lane_centre)
             for record in records]
    if not boxes:
        return {"coverage": 0.0, "samples": samples}
    near_x = min(box[0][0] for box in boxes)
    depth = near_x - camera["eye"]["x"]
    if depth <= 1e-6:
        return {"coverage": 0.0, "samples": samples}
    half = half_width_at(depth, camera)
    covered = 0
    for index in range(samples):
        y = -half + (index + 0.5) * (2.0 * half / samples)
        for (x0, y0, z0), (x1, y1, z1) in boxes:
            if not y0 <= y <= y1:
                continue
            if native_y_at(x0, z1, camera) <= DOCK_TOP_NATIVE_Y:
                covered += 1
                break
    tallest = max(records, key=lambda record: record.bounds()[1][2])
    size = readable_size(tallest, back_x=back_x, lane_y=lane_y,
                         lane_centre=lane_centre, camera=camera)
    return {"coverage": round(covered / samples, 3), "samples": samples,
            "nearX": quantise(near_x), "readable": size}
