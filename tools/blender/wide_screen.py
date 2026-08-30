"""Render a whole side-view location at canon scale, as a pushbroom strip.

The engine shows 9.33 m of the action plane at a time and scrolls along the
lane, so a location wider than that is several screens. Rendering the whole
width in ONE frame would need a wider FOV, which skews the edges in ways the
scrolling camera never produces -- and a 256-wide crop of that frame would not
match what the engine draws at that scroll position.

So each output column is rendered from the camera position that puts it at
frame centre: many narrow strips at the canon calibration, concatenated. Any
256-wide crop of the result is then a real screen.

Screen X runs opposite world Y: the calibration's right vector is -Y.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(r"D:\Antigravity\Hichaukitoden")
sys.path.insert(0, str(ROOT / "tools/blender"))
import thestra_camera  # noqa: E402

FIXTURE = json.loads((ROOT / "tools/blender/fixtures/town_sideview_camera.json").read_text())
PPU = FIXTURE["thestraComposition"]["pixelsPerWorldUnit"]
TARGET_W = FIXTURE["targetWidth"]
TARGET_H = FIXTURE["targetHeight"]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--document", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--lane-min", type=float, default=0.0)
    ap.add_argument("--lane-max", type=float, default=23.699)
    ap.add_argument("--lane-x", type=float, default=7.8)
    ap.add_argument("--strip", type=int, default=32)
    # At a lane end the camera still shows half a screen beyond it, so the set
    # must exist there or the edge screens show void.  Default to covering
    # everything the camera can ever reach, not just the walkable span.
    ap.add_argument("--margin", type=float, default=None,
                    help="metres beyond each lane end; default half a screen")
    ap.add_argument("--walker-y", type=float, default=None)
    args = ap.parse_args(argv)

    bpy.ops.wm.open_mainfile(filepath=str(args.document.resolve()))
    scene = bpy.context.scene

    camera = thestra_camera.create_or_update_camera(FIXTURE, make_active=True)
    # The fixture's eye.x is a DISTANCE from the action plane, not a world X.
    camera.location.x = args.lane_x - abs(FIXTURE["eye"]["x"])

    if args.walker_y is not None:
        actor = thestra_camera.create_actor_preview(
            ROOT / "projects/hichaukitoden-game/assets/character/npc_alicia.png",
            camera, anchor=(args.lane_x, args.walker_y, 0.0),
            world_height=1.75, name="WIDE_walker")
        actor.hide_render = False

    for name in ("TH_RENDER", "11_SCALE_GUIDES", "10_LEVEL_DESIGN"):
        collection = bpy.data.collections.get(name)
        if collection:
            collection.hide_render = True

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = TARGET_W
    scene.render.resolution_y = TARGET_H
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"

    half_screen = abs(FIXTURE["eye"]["x"]) * FIXTURE["fovHalfX"]
    margin = half_screen if args.margin is None else args.margin
    args.lane_min -= margin
    args.lane_max += margin
    span = args.lane_max - args.lane_min
    total = int(round(span * PPU))
    strips = []
    x = 0
    while x < total:
        width = min(args.strip, total - x)
        centre_x = x + width / 2.0
        # Screen X grows as world Y shrinks.
        camera.location.y = args.lane_max - centre_x / PPU
        path = args.out.parent / f"_strip_{x:05d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        strips.append((x, width, path))
        x += width

    # Composite in Blender's own image API so the render needs no extra deps.
    wide = bpy.data.images.new("wide", width=total, height=TARGET_H, alpha=False)
    buffer = [0.0] * (total * TARGET_H * 4)
    for offset, width, path in strips:
        image = bpy.data.images.load(str(path))
        pixels = list(image.pixels)
        left = (TARGET_W - width) // 2
        for row in range(TARGET_H):
            src = (row * TARGET_W + left) * 4
            dst = (row * total + offset) * 4
            buffer[dst:dst + width * 4] = pixels[src:src + width * 4]
        bpy.data.images.remove(image)
        path.unlink(missing_ok=True)
    wide.pixels = buffer
    wide.filepath_raw = str(args.out.resolve())
    wide.file_format = "PNG"
    wide.save()
    print(f"WIDE OK {args.out} {total}x{TARGET_H} from {len(strips)} strips "
          f"({span:.3f} m, {span * PPU / TARGET_W:.2f} screens)")


main()
