"""Composite the actor onto a rendered plate, the way the engine draws it.

The world keystones because the camera is pitched. The actor must not. A
character is an axis-aligned rectangle that only ever scales with depth - it
never shears, leans or foreshortens - so it cannot be a plane in the scene.
It is a sprite blitted at the projected position of its ground point.

This does exactly that, using the same projection the engine needs, so a preview
frame shows what will actually be on screen rather than a billboard that has
quietly inherited the world's perspective.

    python tools/towngen/compose_actor.py --plate out/.../massing_x.png \\
        --pitch 17.5 --horizon-y 66 --at -8 --at 0 --at 9
"""

import argparse
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import camera_modes as cm  # noqa: E402

SHEET = os.path.join(ROOT, "projects", "hichaukitoden-game",
                     "assets", "character", "walker.png")
CELLS = 6


def cell(index=0):
    """One 24x48 frame of the sheet, with its real alpha.

    No keying. walker.png reports mode "RGB" because Pillow only exposes the
    colour key through `info["transparency"]`, but `convert("RGBA")` honours the
    PNG's tRNS chunk and yields the correct alpha. Trusting `.mode` here costs
    an afternoon.
    """
    sheet = Image.open(SHEET)
    assert sheet.info.get("transparency"), "walker.png lost its tRNS chunk"
    sheet = sheet.convert("RGBA")
    w = sheet.size[0] // CELLS
    return sheet.crop((index * w, 0, (index + 1) * w, sheet.size[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plate", required=True)
    ap.add_argument("--out")
    ap.add_argument("--pitch", type=float, default=17.5)
    ap.add_argument("--horizon-y", type=float, default=66.0)
    ap.add_argument("--at", type=float, action="append", default=None,
                    help="lane position, in world units; repeatable")
    a = ap.parse_args()
    lanes = a.at if a.at else [-8.0, 0.0, 9.0]

    import math
    theta = math.radians(a.pitch)
    dist, height, principal_y = cm.solve_billboard(theta, a.horizon_y)

    plate = Image.open(a.plate).convert("RGBA")
    principal_x = plate.size[0] / 2.0
    sprite = cell(0)

    for lane_y in lanes:
        sx, sy, px_h = cm.project_ground(theta, dist, height, principal_y,
                                         lane_y, principal_x)
        # Nearest-neighbour only: this is pixel art and must not be filtered.
        scale = px_h / sprite.size[1]
        w = max(1, int(round(sprite.size[0] * scale)))
        h = max(1, int(round(px_h)))
        s = sprite.resize((w, h), Image.NEAREST)
        plate.alpha_composite(s, (int(round(sx - w / 2.0)), int(round(sy - h))))

    out = a.out or a.plate.replace(".png", "_actor.png")
    plate.convert("RGB").save(out)
    chk = cm.billboard_check(theta, dist, height, principal_y)
    print("composited %d actor(s) -> %s" % (len(lanes), out))
    print("  pitch %.1f  dist %.4f  eye %.4f  principal %.2f"
          % (a.pitch, dist, height, principal_y))
    print("  feet y %.2f (want 128)  sprite %.2fpx (want %d)  horizon y %.2f"
          % (chk["feetY"], chk["spritePx"], cm.WALKER_PX, chk["horizonY"]))


if __name__ == "__main__":
    main()
