"""Passage House corridor -- St. Maria.

The connective tissue for the boarding house. A corridor with several doors,
one of which is yours; the player only ever enters their own room, so this is
where "which one is mine" has to read.

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


def build():
    hall = kit.Interior(ASSET_ID, half_width=HALF_WIDTH, depth=DEPTH,
                        ceiling_z=CEILING_Z)

    openings = [(y - DOOR_HALF, y + DOOR_HALF, 0.0, DOOR_TOP) for y, _ in DOORS]
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

    # --- a little life in the aisle ---------------------------------------
    hall.part("crate_a", (0.7, 0.8, 0.62), (hall.back_x - 0.55, 4.5, 0.31),
              hall.wood)
    hall.part("crate_b", (0.6, 0.66, 0.48), (hall.back_x - 0.6, 5.25, 0.24),
              hall.wood)
    hall.part("bench", (0.5, 2.2, 0.44), (hall.back_x - 0.45, -4.8, 0.22),
              hall.wood)
    hall.part("sack", (0.55, 0.6, 0.5), (hall.back_x - 0.75, -9.2, 0.25),
              hall.cloth)

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
    for index, y in enumerate((-5.0, 5.0)):
        hall.light(f"light_lantern_{index}", "POINT",
                   (hall.back_x - 0.35, y, 2.25), (0.0, 0.0, -1.0),
                   11.0, (1.0, 0.82, 0.58), radius=0.16)

    hall.finish()
    return hall


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog=ASSET_ID)
    parser.add_argument("--blend", type=Path,
                        default=kit.ENVIRONMENT_DIR / f"{ASSET_ID}.blend")
    parser.add_argument("--force", action="store_true",
                        help="overwrite the source .blend, DISCARDING any "
                             "hand-authoring in it")
    args = parser.parse_args(argv)

    hall = build()
    bpy.context.view_layer.update()
    blend = kit.save_source_blend(args.blend, force=args.force)
    kit.report(hall, blend)


if __name__ == "__main__":
    main()
