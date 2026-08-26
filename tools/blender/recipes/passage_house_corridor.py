"""Passage House corridor -- St. Maria.

The connective tissue for the boarding house. A corridor with several doors,
one of which is yours; the player only ever enters their own room, so this is
where "which one is mine" has to read.

THE WAY TO TOWN is the other thing this map has to answer. At the screen-right
end the floor opens into a stairwell going down to the street, and daylight
climbs it. So the corridor reads in three registers at once, all of them light:
dim where nothing happens, warm lamplight at YOUR door, cool daylight at the
way out. Stepping onto the stair head transfers; the player never descends
below the character floor limit, so no Y camera scrolling is needed.

It reads through LIGHT rather than signage. The corridor is dim and every door
is dark except Room 3, which has a lamp burning behind it -- warm light in the
reveal and spilling across its threshold. A number plaque would be illegible at
426x240; a lit doorway is legible instantly and is the same answer the interior
lighting doctrine gives everywhere else.

Threshold direction is the other thing this map tests. A room's exit extrudes
the floor OUTWARD, toward the camera, because that is the way you travel. A
corridor's doors lead away from the camera, so their thresholds extrude INWARD
into each recess: the same rule mirrored, and four of them side by side.

The corridor runs off both frame edges, which is what makes it a lane rather
than a box.

    blender --background --factory-startup \
        --python tools/blender/recipes/passage_house_corridor.py --
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

import furnishings as furn  # noqa: E402
import interior as kit  # noqa: E402

ASSET_ID = "passage_house_corridor"

HALF_WIDTH = 11.0     # runs past both frame edges
DEPTH = 4.2           # shallow: an aisle, not a room
CEILING_Z = 3.0

DOOR_TOP = 2.15
DOOR_HALF = 0.55
#            centre,  is this Room 3?
DOORS = ((-7.2, False), (-2.4, True), (2.4, False), (6.2, False))
WINDOW = (8.6, 9.8, 1.4, 2.6)
STAIR_Y = -5.6          # screen right, inside the frame
STAIR_HALF = 0.95
STAIR_TOP = 2.45        # taller and wider than a room door


def build():
    hall = kit.Interior(ASSET_ID, half_width=HALF_WIDTH, depth=DEPTH,
                        ceiling_z=CEILING_Z)

    openings = [(y - DOOR_HALF, y + DOOR_HALF, 0.0, DOOR_TOP) for y, _ in DOORS]
    openings.append((STAIR_Y - STAIR_HALF, STAIR_Y + STAIR_HALF, 0.0, STAIR_TOP))
    openings.append(WINDOW)

    hall.floor()
    hall.back_wall(openings=openings)
    hall.side_walls()
    hall.ceiling(beams=7, beam_span=2.6)
    hall.window(*WINDOW)

    for index, (y, is_room3) in enumerate(DOORS):
        name = "door_room3" if is_room3 else f"door_{index}"
        hall.doorway(name, y - DOOR_HALF, y + DOOR_HALF, DOOR_TOP,
                     lit=True if is_room3 else None)

    # --- the way to town ---------------------------------------------------
    # A wider, taller opening than any room door, with the stair dropping away
    # behind it and daylight coming up. Running the flight AWAY from the camera
    # is what makes it visible at all: a stair toward the viewer falls under the
    # status menu within a tread or two.
    hall.doorway("stair_head", STAIR_Y - STAIR_HALF, STAIR_Y + STAIR_HALF,
                 STAIR_TOP, recess=0.7, open_back=True)
    furn.escada(hall, "stair", y=STAIR_Y, x_start=hall.back_x + 1.25,
                steps=6, width=STAIR_HALF * 2 - 0.2, rise=0.2, run=0.34,
                direction=1.0)
    # Daylight from the street, seen past the treads. Without an emissive
    # plane the opening is just a dark recess -- the same mistake a window
    # makes on a black backdrop.
    hall.part("stair_daylight", (0.06, STAIR_HALF * 2, STAIR_TOP),
              (hall.back_x + 3.4, STAIR_Y, STAIR_TOP / 2.0 - 0.3),
              hall.daylight)

    # --- a little life in the aisle ---------------------------------------
    hall.part("crate_a", (0.7, 0.8, 0.62), (hall.back_x - 0.55, 4.5, 0.31),
              hall.wood)
    hall.part("crate_b", (0.6, 0.66, 0.48), (hall.back_x - 0.6, 5.25, 0.24),
              hall.wood)
    hall.part("bench", (0.5, 2.2, 0.44), (hall.back_x - 0.45, -4.8, 0.22),
              hall.wood)
    furn.arca(hall, "aisle_chest", (hall.back_x - 0.42, 8.4))
    furn.pote(hall, "aisle_jar", (hall.back_x - 0.45, 3.6), height=0.55,
              radius=0.22)
    furn.azulejo_dado(hall, height=0.95)

    # --- light ------------------------------------------------------------
    # Daylight from the window at the far end of the aisle.
    hall.window_light((WINDOW[0] + WINDOW[1]) / 2.0,
                      (WINDOW[2] + WINDOW[3]) / 2.0, energy=180.0)

    # Your door, and only yours, has a lamp burning behind it.
    room3_y = next(y for y, is_room3 in DOORS if is_room3)
    hall.light("light_room3_spill", "AREA",
               (hall.back_x + 0.25, room3_y, 1.5), (-1.0, 0.0, -0.35),
               34.0, (1.0, 0.76, 0.46), size=1.0, size_y=1.9)

    # Two weak wall lanterns, enough to walk by and no more.
    for index, y in enumerate((-2.2, 4.4)):
        furn.lanterna(hall, f"lantern_{index}", y=y, z=2.25, energy=12.0)

    # Daylight climbing the stairwell from the street below. Cool against the
    # lamplight, so "outside" and "mine" never read as the same signal.
    hall.light("light_stairwell", "AREA",
               (hall.back_x + 1.5, STAIR_Y, 1.4), (-1.0, 0.0, -0.25),
               120.0, (0.80, 0.87, 1.0), size=1.7, size_y=2.2)

    hall.finish()
    return hall


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog=ASSET_ID)
    parser.add_argument("--blend", type=Path,
                        default=kit.ENVIRONMENT_DIR / f"{ASSET_ID}.blend")
    parser.add_argument("--force", action="store_true",
                        help="replace existing untouched scaffold output, or "
                             "deliberately discard adopted hand-authoring")
    args = parser.parse_args(argv)

    hall = build()
    bpy.context.view_layer.update()
    blend = kit.save_source_blend(args.blend, force=args.force)
    kit.report(hall, blend)


if __name__ == "__main__":
    main()
