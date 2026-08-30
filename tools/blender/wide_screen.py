"""Render a whole side-view location in one frame, at canon scale.

Second Gate's town maps scroll by moving the camera's projection WINDOW, not
its eye. So the whole location is one off-axis perspective frame from the
single canon eye position, widened horizontally -- and any 256-wide crop of it
is exactly the frame the engine draws at that scroll offset, because that crop
IS a projection window offset.

The calibration record already expresses this. Its horizontal coefficient is

    ax = projectionScale.x / fovHalfX * (baseViewportWidth / targetWidth)

so raising ``targetWidth`` alone widens the window at constant pixels-per-
world-unit, from the same eye, with the vertical framing untouched.
``_solve_lens_shift`` then produces the shear that puts the principal point
where the record asks.

An earlier version of this tool assembled the width from many narrow strips
with the eye translated between them. That is a pushbroom projection: it gives
every column a head-on view and so erases the horizontal perspective
divergence the real camera shows. It is the wrong image, and crops of it would
not match the engine.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/blender"))
import thestra_camera  # noqa: E402

FIXTURE_PATH = ROOT / "tools/blender/fixtures/town_sideview_camera.json"


def widened_record(record, *, target_width, lane_x, centre_y, extra_rows=0):
    """The canon calibration with a wider projection window, same eye.

    ``extra_rows`` opens the window vertically by that many canon pixels above
    AND below.  The engine offsets its window in Y as well as X -- that is the
    Y camera scrolling ``characterFloorLimit`` refers to -- so a capture that
    is only wide still shows one vertical scroll position out of several.
    ``viewportCenterY`` moves with the growth so the principal point stays on
    the same world point and the canon frame remains a sub-rect.
    """
    wide = json.loads(json.dumps(record))
    # eye.x is a DISTANCE from the action plane; place it against the real one.
    wide["eye"]["x"] = lane_x - abs(float(record["eye"]["x"]))
    wide["eye"]["y"] = centre_y
    wide["targetWidth"] = int(target_width)
    # Keep the principal point centred, so the widening is symmetric about the
    # eye rather than shearing the whole frame to one side.
    wide["viewportCenterX"] = target_width / 2.0
    if extra_rows:
        wide["targetHeight"] = int(record["targetHeight"]) + 2 * int(extra_rows)
        wide["viewportCenterY"] = float(record["viewportCenterY"]) + int(extra_rows)
    return wide


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--document", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--lane-min", type=float, default=0.0)
    ap.add_argument("--lane-max", type=float, default=23.699)
    ap.add_argument("--lane-x", type=float, default=7.8)
    # At a lane end the camera still shows half a screen beyond it, so the set
    # must exist there or the edge screens show void.
    ap.add_argument("--margin", type=float, default=None,
                    help="metres beyond each lane end; default half a screen")
    ap.add_argument("--walker-y", type=float, default=None)
    ap.add_argument("--extra-rows", type=int, default=0,
                    help="canon pixels of vertical window opened above AND below; "
                         "the engine offsets its window in Y too")
    ap.add_argument("--hide", nargs="*", default=("TH_RENDER", "11_SCALE_GUIDES",
                                                  "10_LEVEL_DESIGN"))
    args = ap.parse_args(argv)

    record = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    ppu = float(record["thestraComposition"]["pixelsPerWorldUnit"])
    half_screen = abs(float(record["eye"]["x"])) * float(record["fovHalfX"])
    margin = half_screen if args.margin is None else args.margin
    lane_min = args.lane_min - margin
    lane_max = args.lane_max + margin
    span = lane_max - lane_min
    width = int(round(span * ppu))

    bpy.ops.wm.open_mainfile(filepath=str(args.document.resolve()))
    scene = bpy.context.scene

    wide = widened_record(record, target_width=width, lane_x=args.lane_x,
                          centre_y=(lane_min + lane_max) * .5,
                          extra_rows=args.extra_rows)
    camera = thestra_camera.create_or_update_camera(wide, make_active=True)

    if args.walker_y is not None:
        actor = thestra_camera.create_actor_preview(
            ROOT / "projects/hichaukitoden-game/assets/character/npc_alicia.png",
            camera, anchor=(args.lane_x, args.walker_y, 0.0),
            world_height=1.75, name="WIDE_walker")
        actor.hide_render = False

    for name in args.hide:
        collection = bpy.data.collections.get(name)
        if collection:
            collection.hide_render = True

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(args.out.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print(f"WIDE OK {args.out} {scene.render.resolution_x}x{scene.render.resolution_y} "
          f"({span:.3f} m, {span * ppu / float(record['targetWidth']):.2f} screens, "
          f"lens {camera.data.lens:.4f}mm shift=({camera.data.shift_x:.4f}, "
          f"{camera.data.shift_y:.4f}))")


if __name__ == "__main__":
    main()
