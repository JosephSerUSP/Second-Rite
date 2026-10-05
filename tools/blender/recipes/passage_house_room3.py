"""Passage House, Room 3 -- St. Maria.

The room the player is given, and the first interior in the game. Everything
here comes out of the authored opening text rather than being invented:

    "This'll be home for both of you."
    Two beds, a washstand, and a window that does not close properly.
    It is paid for until spring.
    Yours has been cleaned, but not emptied of its previous lives.
    Someone has dragged a feed bowl in from the stable.

So it boards a rider AND a Moa: two beds, a washstand, a window that sits a
little open; it carries traces of whoever had it before (the pale rectangle
where a picture hung, a coat hook set too low for an adult); and Saban's end has
straw and a chipped feed bowl.

THE AXIS SPENT is the ALCOVE. The beds are not against a flat wall: they sit in
an *alcova*, the sleeping recess of a rented colonial room, stepped back from the
room with a header across its mouth, so the room has a corner in its silhouette
and the two beds read as "where you sleep" before anything else does. The rest of
the room is the day side: the window, the washstand, the table, and Saban's end.

This room belongs to the Passage House, one apartment off the gallery (layout doc
section 5.1). Its door is the floor tongue toward the camera; the gallery lies
beyond it.

The shell, thresholds and light vocabulary live in `interior.py`. This file
declares only what makes Room 3 itself.

    python tools/blender/run.py tools/blender/recipes/passage_house_room3.py
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

ALCOVE = (-3.7, -0.9, 2.1)        # y0, y1, how far the wall steps back (screen right)
WINDOW = (1.5, 2.9, 1.15, 2.5)    # y0, y1, z0, z1 -- the day side, screen left
EXIT_Y = -0.1


def build():
    front_depth = kit.floor_edge_x(kit.FLOOR_EDGE_NATIVE_Y)[1]
    half_width = kit.base_half_width_at(front_depth)

    room = kit.Interior(ASSET_ID, half_width=half_width, depth=DEPTH,
                        ceiling_z=CEILING_Z)
    back_x = room.back_x

    room.floor()
    room.back_wall(openings=[WINDOW], alcoves=[ALCOVE])
    room.side_walls()
    room.ceiling(beams=5)
    room.window(*WINDOW)
    tab_x, tab_y = room.exit_threshold(EXIT_Y)

    # --- colonial Portuguese surfaces --------------------------------------
    # The dado stops at the alcove's edge: the helper knows openings, not recesses,
    # and a band across the mouth would hide the beds behind it.
    furn.azulejo_dado(room, height=1.0, y0=ALCOVE[1])
    furn.window_dressing(room, "window", *WINDOW)

    # --- the alcove: two beds, heads to the far wall -------------------------
    alcove_back = back_x + ALCOVE[2]
    for index, y in enumerate((-3.05, -1.55)):
        furn.bed(room, f"bed_{index}", (alcove_back - 1.0, y))
    furn.chest(room, "chest", (alcove_back - 0.4, -2.3), length=0.7, depth=0.5, height=0.5)
    furn.lantern(room, "lantern", y=-2.3, z=2.1)

    # The pale rectangle where a picture used to hang, and the nail left behind.
    room.part("picture_ghost", (0.03, 0.95, 0.72), (back_x - 0.015, 0.1, 1.95), room.crock)
    room.part("picture_nail", (0.06, 0.04, 0.04), (back_x - 0.03, 0.1, 2.42), room.iron)

    # The coat hook, set low enough to belong to whoever lived here before.
    room.part("coat_hook_plate", (0.05, 0.16, 0.14), (back_x - 0.025, 0.95, 0.95), room.iron)
    room.part("coat_hook_arm", (0.13, 0.16, 0.05), (back_x - 0.09, 0.95, 0.90), room.iron)

    # --- the day side: washstand, table, shelf --------------------------------
    washstand(room, (back_x - 0.5, 3.75))
    furn.shelf(room, "shelf", y=0.1, z=2.0, length=1.0)
    furn.table(room, "table", (back_x - 2.4, 0.9), length=0.95, width=0.6)
    furn.chair(room, "chair", (back_x - 3.1, 0.9))
    furn.jar(room, "jar_big", (back_x - 0.5, 1.0), height=0.5, radius=0.2)

    # --- Saban's end (screen left): straw and the feed bowl ----------------
    for index, (sx, sy) in enumerate(((1.5, 3.2), (2.2, 2.6), (1.0, 3.6),
                                      (2.5, 3.5), (0.7, 2.7))):
        room.part(f"straw_{index}", (0.85, 0.72, 0.06), (sx, sy, 0.03),
                  room.straw, rotation=(0.0, 0.0, 0.4 * index))
    feed_bowl(room, (1.5, 3.9, 0.0))

    # --- light: the window, a lamp in the alcove, the gallery beyond the door -
    room.window_light((WINDOW[0] + WINDOW[1]) / 2.0,
                      (WINDOW[2] + WINDOW[3]) / 2.0)
    room.light("light_alcove_lamp", "POINT", (alcove_back - 0.9, -2.3, 1.4),
               (0.0, 0.0, -1.0), 120.0, (1.0, 0.78, 0.52), radius=0.14)
    # The alcove is a recess: without a source of its own it is a black slot.
    room.light("light_alcove_fill", "AREA", (back_x + 0.6, -2.3, 2.5), (0.5, 0.0, -1.0),
               160.0, (1.0, 0.84, 0.62), size=1.8, size_y=2.4)
    room.doorway_light(tab_x, tab_y)

    room.finish()
    return room


def washstand(room, at):
    """A basin on a stand, a jug beside it and a towel rail: the "washstand" of the text."""
    x, y = at
    with room.piece("washstand"):
        for index, (dx, dy) in enumerate(((-0.2, -0.28), (-0.2, 0.28), (0.2, -0.28), (0.2, 0.28))):
            room.part(f"washstand_leg_{index}", (0.06, 0.06, 0.78), (x + dx * 0.5, y + dy, 0.39), room.wood)
        room.part("washstand_top", (0.5, 0.74, 0.05), (x, y, 0.8), room.wood)
        room.part("washstand_basin", (0.34, 0.4, 0.1), (x, y - 0.08, 0.88), room.crock)
        room.part("washstand_jug", (0.14, 0.14, 0.26), (x, y + 0.24, 0.96), room.crock)
        room.part("washstand_rail", (0.04, 0.5, 0.04), (x - 0.22, y, 1.3), room.iron)
        room.part("washstand_towel", (0.02, 0.4, 0.34), (x - 0.24, y, 1.1), room.cloth)


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
