"""Passage House, Room 3 -- St. Maria.

The room the player is given, and the first interior in the game. Everything
here comes out of the authored opening text rather than being invented:

    "This'll be home for both of you."
    Yours has been cleaned, but not emptied of its previous lives.
    Someone has dragged a feed bowl in from the stable.

So it boards a rider AND a Moa; it carries traces of whoever had it before
(the pale rectangle where a picture hung, a coat hook set too low for an
adult); and Saban's end has straw and a chipped feed bowl.

The shell, thresholds and light vocabulary live in `interior.py`. This file
declares only what makes Room 3 itself.

    blender --background --factory-startup \
        --python tools/blender/recipes/passage_house_room3.py --
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

import interior as kit  # noqa: E402

ASSET_ID = "passage_house_room3"

HALF_WIDTH = 5.4
DEPTH = 7.4          # deliberately deeper than the walkable band
CEILING_Z = 4.3

WINDOW = (0.7, 2.4, 1.15, 2.55)   # y0, y1, z0, z1
EXIT_Y = -1.7


def build():
    room = kit.Interior(ASSET_ID, half_width=HALF_WIDTH, depth=DEPTH,
                        ceiling_z=CEILING_Z)
    back_x = room.back_x

    room.floor()
    room.back_wall(openings=[WINDOW])
    room.side_walls()
    room.ceiling(beams=5)
    room.window(*WINDOW)
    tab_x, tab_y = room.exit_threshold(EXIT_Y)

    # --- the rider's end ---------------------------------------------------
    room.part("bed_frame", (1.75, 1.95, 0.42), (back_x - 0.95, -2.3, 0.21),
              room.wood)
    room.part("bed_mattress", (1.62, 1.82, 0.22), (back_x - 0.95, -2.3, 0.53),
              room.cloth)
    room.part("footlocker", (0.66, 1.15, 0.5), (back_x - 0.62, -0.75, 0.25),
              room.wood)

    # The pale rectangle where a picture used to hang, and the nail left behind.
    room.part("picture_ghost", (0.03, 1.15, 0.85), (back_x - 0.015, -2.25, 2.05),
              room.crock)
    room.part("picture_nail", (0.06, 0.04, 0.04), (back_x - 0.03, -2.25, 2.62),
              room.iron)

    # The coat hook, set low enough to belong to whoever lived here before.
    room.part("coat_hook_plate", (0.05, 0.16, 0.14), (back_x - 0.025, -3.2, 0.95),
              room.iron)
    room.part("coat_hook_arm", (0.13, 0.16, 0.05), (back_x - 0.09, -3.2, 0.90),
              room.iron)

    # --- Saban's end: straw, and the feed bowl dragged in from the stable ---
    for index, (sx, sy) in enumerate(((2.0, 2.2), (2.9, 1.6), (1.6, 2.9),
                                      (3.3, 2.5), (1.1, 1.9))):
        room.part(f"straw_{index}", (0.95, 0.8, 0.06), (sx, sy, 0.03),
                  room.straw, rotation=(0.0, 0.0, 0.4 * index))
    feed_bowl(room, (1.7, 3.55, 0.0))

    # A near post, giving the room a foreground depth layer.
    room.part("post_left", (0.22, 0.22, CEILING_Z),
              (room.front_x + 0.5, -HALF_WIDTH + 0.55, CEILING_Z / 2.0),
              room.wood)

    # --- light: the window, a lamp by the bed, the corridor beyond the door -
    room.window_light((WINDOW[0] + WINDOW[1]) / 2.0,
                      (WINDOW[2] + WINDOW[3]) / 2.0)
    room.light("light_bed_lamp", "POINT", (back_x - 1.1, -2.3, 0.95),
               (0.0, 0.0, -1.0), 22.0, (1.0, 0.78, 0.52), radius=0.14)
    room.doorway_light(tab_x, tab_y)

    room.finish()
    return room


def feed_bowl(room, location):
    """An eight-sided crock with one rim vertex knocked down: the chip."""
    import bmesh
    import second_rite_asset_core as asset_core

    bm = bmesh.new()
    rim, base = [], []
    for index in range(8):
        angle = math.tau * index / 8.0
        cos, sin = math.cos(angle), math.sin(angle)
        rim.append(bm.verts.new((cos * 0.30, sin * 0.30, 0.17)))
        base.append(bm.verts.new((cos * 0.19, sin * 0.19, 0.0)))
    bm.faces.new(reversed(base))
    for index in range(8):
        nxt = (index + 1) % 8
        bm.faces.new((base[index], base[nxt], rim[nxt], rim[index]))
    bm.faces.new(rim)
    rim[3].co.z -= 0.06          # the chip, deterministic
    obj = asset_core.mesh_object_from_bmesh("feed_bowl", bm)
    asset_core.parent_local(obj, room.root, loc=location)
    asset_core.assign_material(obj, room.crock)
    asset_core.flat_shade(obj)
    room.parts.append(obj)
    return obj


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog=ASSET_ID)
    parser.add_argument("--blend", type=Path,
                        default=kit.ENVIRONMENT_DIR / f"{ASSET_ID}.blend")
    parser.add_argument("--force", action="store_true",
                        help="overwrite the source .blend, DISCARDING any "
                             "hand-authoring in it")
    args = parser.parse_args(argv)

    room = build()
    bpy.context.view_layer.update()
    blend = kit.save_source_blend(args.blend, force=args.force)
    kit.report(room, blend)


if __name__ == "__main__":
    main()
