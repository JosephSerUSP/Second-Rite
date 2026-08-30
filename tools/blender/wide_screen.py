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
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/blender"))
import thestra_camera  # noqa: E402

FIXTURE_PATH = ROOT / "tools/blender/fixtures/town_sideview_camera.json"


def widened_record(record, *, target_width, lane_x, centre_y):
    """The canon calibration with a wider projection window, same eye.

    Widened horizontally ONLY.  A town screen's vertical window is fixed: it
    moves only where the player's path has elevation, and on a flat lane the
    player's screen Y never reaches anything above or below the canon frame.
    Rendering extra rows there photographs pixels nobody can ever see.
    """
    wide = json.loads(json.dumps(record))
    # eye.x is a DISTANCE from the action plane; place it against the real one.
    wide["eye"]["x"] = lane_x - abs(float(record["eye"]["x"]))
    wide["eye"]["y"] = centre_y
    wide["targetWidth"] = int(target_width)
    # Keep the principal point centred, so the widening is symmetric about the
    # eye rather than shearing the whole frame to one side.
    wide["viewportCenterX"] = target_width / 2.0
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
    ap.add_argument("--pitch", type=float, default=-17.5,
                    help="camera pitch in degrees; compensated so the anchor's "
                         "feet stay pinned, as study_town_pitch.py does")
    ap.add_argument("--pitch-anchor", type=float, nargs=2, default=(7.8, 11.85),
                    metavar=("X", "Y"), help="world point whose feet the pitch pins")
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
                          centre_y=(lane_min + lane_max) * .5)
    camera = thestra_camera.create_or_update_camera(wide, make_active=True)

    if args.pitch:
        # Pitch alone slides the whole frame vertically.  Principal-point
        # compensation pins a concrete action anchor instead, so the study
        # compares composition rather than framing drift.  This changes framing
        # only: eye, lens, actor position and scale are untouched.
        anchor = Vector((args.pitch_anchor[0], args.pitch_anchor[1], 0.0))
        def feet(cam):
            return thestra_camera.project_world_point(scene, cam, anchor)[1]
        baseline = feet(camera)
        wide["orientation"]["pitchRadians"] = math.radians(args.pitch)
        camera = thestra_camera.create_or_update_camera(wide, make_active=True)
        wide["viewportCenterY"] += baseline - feet(camera)
        camera = thestra_camera.create_or_update_camera(wide, make_active=True)
        drift = abs(feet(camera) - baseline)
        if drift > 1e-3:
            raise RuntimeError(f"pitch compensation failed: feet moved {drift:.4f}px")
        head = thestra_camera.project_world_point(scene, camera, anchor + Vector((0, 0, 1.75)))
        print(f"PITCH {args.pitch:+.1f} deg, feet pinned, 1.75m reads "
              f"{abs(head[1] - feet(camera)):.2f}px")

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
