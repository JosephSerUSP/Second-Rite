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

import furnishings as furn  # noqa: E402
import interior as kit  # noqa: E402

ASSET_ID = "passage_house_room3"

# Sized to the game's DEFAULT 256px width, not the 426 wide variant. Room 3 is
# meant to read as one self-contained room, and a room wider than the default
# view promises the player a screen edge they can walk to. Derived rather than
# guessed: the side walls land exactly at the frame edge at the floor's front
# plane. Depth stays generous -- depth costs nothing and does not scroll.
DEPTH = 6.4
CEILING_Z = 3.5

WINDOW = (0.6, 2.0, 1.15, 2.5)   # y0, y1, z0, z1
EXIT_Y = -1.4


def build():
    front_depth = kit.floor_edge_x(kit.FLOOR_EDGE_NATIVE_Y)[1]
    half_width = kit.base_half_width_at(front_depth)

    room = kit.Interior(ASSET_ID, half_width=half_width, depth=DEPTH,
                        ceiling_z=CEILING_Z)
    back_x = room.back_x

    room.floor()
    room.back_wall(openings=[WINDOW])
    room.side_walls()
    room.ceiling(beams=5)
    room.window(*WINDOW)
    tab_x, tab_y = room.exit_threshold(EXIT_Y)

    # --- colonial Portuguese surfaces --------------------------------------
    furn.azulejo_dado(room, height=1.0)
    furn.janela(room, "window", *WINDOW)

    # --- the rider's end (screen right) ------------------------------------
    furn.armario(room, "wardrobe", (back_x - 0.4, -3.15))
    furn.cama(room, "bed", (back_x - 1.05, -1.85))
    furn.arca(room, "chest", (back_x - 0.45, -0.3))
    furn.prateleira(room, "shelf", y=3.15, z=2.0, length=1.0)
    furn.lanterna(room, "lantern", y=-1.15, z=2.1)

    # The pale rectangle where a picture used to hang, and the nail left behind.
    room.part("picture_ghost", (0.03, 0.95, 0.72), (back_x - 0.015, -1.9, 1.95),
              room.crock)
    room.part("picture_nail", (0.06, 0.04, 0.04), (back_x - 0.03, -1.9, 2.42),
              room.iron)

    # The coat hook, set low enough to belong to whoever lived here before.
    room.part("coat_hook_plate", (0.05, 0.16, 0.14), (back_x - 0.025, -2.45, 0.95),
              room.iron)
    room.part("coat_hook_arm", (0.13, 0.16, 0.05), (back_x - 0.09, -2.45, 0.90),
              room.iron)

    # --- Saban's end (screen left): straw and the feed bowl ----------------
    furn.mesa(room, "table", (back_x - 2.3, 2.9), length=0.95, width=0.6)
    furn.cadeira(room, "chair", (back_x - 3.05, 2.9))
    furn.pote(room, "jar_big", (back_x - 0.5, 1.35), height=0.5, radius=0.2)
    furn.pote(room, "jar_small", (back_x - 0.45, 1.85), height=0.31, radius=0.12)
    for index, (sx, sy) in enumerate(((1.9, 1.7), (2.6, 1.1), (1.4, 2.2),
                                      (2.9, 1.9), (1.0, 1.3))):
        room.part(f"straw_{index}", (0.85, 0.72, 0.06), (sx, sy, 0.03),
                  room.straw, rotation=(0.0, 0.0, 0.4 * index))
    feed_bowl(room, (1.6, 2.55, 0.0))

    # A near post, giving the room a foreground depth layer.
    room.part("post_left", (0.2, 0.2, CEILING_Z),
              (room.front_x + 0.5, half_width - 0.5, CEILING_Z / 2.0),
              room.wood)

    # --- light: the window, a lamp by the bed, the corridor beyond the door -
    room.window_light((WINDOW[0] + WINDOW[1]) / 2.0,
                      (WINDOW[2] + WINDOW[3]) / 2.0)
    room.light("light_bed_lamp", "POINT", (back_x - 1.35, -1.85, 0.95),
               (0.0, 0.0, -1.0), 18.0, (1.0, 0.78, 0.52), radius=0.14)
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
