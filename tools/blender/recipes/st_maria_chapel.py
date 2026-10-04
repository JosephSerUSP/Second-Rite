"""The Chapel -- St. Maria, on the Praca.

Sister Agnes's chapel. Everything here comes out of authored game text rather
than being invented:

    "Blue tiles, cold wax, and a door that is never locked."   (map 22 intro)
    "Agnes is repairing the chapel steps with a patience better suited to
     embroidery."  "She brushes stone dust from her sleeves and returns to
     work."                                                    (map 1, Agnes)

The camera looks ACROSS the nave, so the lane is the aisle down its length:
the altar at screen left, the door at screen right, and the pews in rows on
both sides of the aisle -- one bank between the camera and the player, which
the player walks behind, and one bank beyond. A chapel seen from the end is a
stage set; seen from the side it is a long room the player crosses (owner
direction, 2026-10-04). It is a SCROLLING lane, 16 m like map 22's, and it
ends in real walls at both ends. A carpet runs down the aisle to the main
door, which is where a church's main door is: in the end wall opposite the
altar, so the aisle leads from one to the other (owner direction).

The tall azulejo panel belongs to this one building. The votive stand is
mostly burnt out. The exit is simply open. The axis spent is the PLATFORM: a
two-step stone chancel whose edge faces down the nave, under repair -- a
lifted stone, a fresh mortar patch, a tub of lime with a trowel, stone dust.

The retable's recess is left dark and empty. What the chapel keeps there is a
question for the owner (the church is "attuned to a strange source of truth";
that is canon direction, not iconography).

Blender Y is screen LEFT. This room is exported with `--span 16`, so its
engine lane Y is `8 - blender_y`: the altar end is engine Y ~0, the door end
~16.

The shipped source is adopted. This recipe documents its original scaffold;
edit st_maria_chapel.blend directly rather than rebuilding the adopted file.

    python tools/blender/run.py tools/blender/recipes/st_maria_chapel.py -- --blend out/chapel-scaffold.blend
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

import furnishings as furn  # noqa: E402
import interior as kit  # noqa: E402

ASSET_ID = "st_maria_chapel"

HALF_LENGTH = 8.0                # the hall runs Blender Y -8..8 (engine 0..16)
DEPTH = 6.0
CEILING_Z = 4.6

# The chancel at the altar end (screen left), its steps facing down the nave.
LOWER_STEP_Y = 4.9
UPPER_STEP_Y = 5.4
LOWER_RISE = 0.16
UPPER_RISE = 0.32
ALTAR_AT = (0.9, 6.9)

# The aisle is the lane (X=0). Pews stand in rows across it: the foreground
# bank between the camera and the player, the background bank behind.
PEW_ROWS_Y = (3.6, 2.65, 1.7, 0.75, -0.2, -1.15, -2.1, -3.05, -4.0)
# The foreground bank is shorter and hugs the aisle: nearer the camera a pew
# is drawn larger, and a long one became a wall in front of the player.
FRONT_BANK = (-1.0, 1.1)         # centre X, length across the hall
BACK_BANK = (1.4, 1.8)

# Windows along the long wall, between the rows of the congregation.
WINDOWS = tuple((y - 0.5, y + 0.5, 2.2, 3.6) for y in (6.4, 2.5, -1.3, -5.1))

# The door that is never locked is the main door, in the end wall opposite
# the altar (screen right), centred on the aisle: the lane runs from the
# chancel straight out of it. It stands open onto the Praca. Very few
# churches put the main entrance in a side wall (owner direction, 2026-10-04).
DOOR = (-0.6, 0.7, 2.8)          # x0, x1, height, in the -Y end wall
EXIT_Y = -HALF_LENGTH + 0.6      # the exit anchor, just inside the door

# The aisle carpet runs from the chancel step to the door.
CARPET_Y = (-HALF_LENGTH + 0.3, 4.4)

DADO_HEIGHT = 1.6


def build():
    room = kit.Interior(ASSET_ID, half_width=HALF_LENGTH, depth=DEPTH,
                        ceiling_z=CEILING_Z)
    back_x = room.back_x
    front_x = room.front_x

    room.floor(mat=room.stone)
    door_x0, door_x1, door_z = DOOR
    room.back_wall(openings=list(WINDOWS))
    room.side_walls(openings={-1: [(door_x0, door_x1, 0.0, door_z)]})
    room.pitched_ceiling(rise=1.4, bays=9)
    for opening in WINDOWS:
        room.window(*opening)
    door_cx, door_wall = room.side_doorway("door", -1, door_x0, door_x1, door_z,
                                           open_back=True)
    furn.door_frame(room, "door_frame", door_x0, door_x1, door_z, wall="-y")
    # The panelled leaf stands open, folded back against the end wall.
    room.part("door_leaf", (1.0, 0.07, door_z - 0.08),
              (door_x1 + 0.6, door_wall + 0.09, (door_z - 0.08) / 2.0), room.wood)

    # --- the chancel: the axis this room spends -----------------------------
    room.platform("chancel_step", front_x, back_x, LOWER_STEP_Y, HALF_LENGTH,
                  LOWER_RISE, mat=room.stone, edge="-y")
    room.platform("chancel", front_x, back_x, UPPER_STEP_Y, HALF_LENGTH,
                  UPPER_RISE, mat=room.stone, edge="-y")

    # --- surfaces -----------------------------------------------------------
    furn.azulejo_dado(room, height=DADO_HEIGHT)
    for index, opening in enumerate(WINDOWS):
        furn.window_dressing(room, f"window_{index}", *opening)

    # --- the altar, raised on the chancel, facing down the nave -------------
    with room.surface(UPPER_RISE):
        furn.altar(room, "altar", ALTAR_AT, turn=90)

    # --- the congregation: two banks of pews either side of the aisle -------
    for row, y in enumerate(PEW_ROWS_Y):
        for bank, (x, length) in (("front", FRONT_BANK), ("back", BACK_BANK)):
            furn.pew(room, f"pew_{bank}_{row}", (x, y), length=length, turn=90)

    # --- the aisle carpet ----------------------------------------------------
    carpet_y0, carpet_y1 = CARPET_Y
    furn.woven_runner(room, "aisle_carpet", (0.02, (carpet_y0 + carpet_y1) / 2.0),
                      length=carpet_y1 - carpet_y0, width=0.9,
                      cloth_mat=kit.material("red_wool"), border_mat=room.terracotta,
                      motif_mat=room.wax)

    # --- the font by the door; the votives before the chancel ---------------
    furn.font(room, "font", (door_x1 + 1.35, door_wall + 0.5))
    furn.votive_stand(room, "votive_stand", (back_x - 0.45, LOWER_STEP_Y - 0.9),
                      lit=3)

    # --- the repair in progress, at the foot of the chancel step ------------
    step_face = LOWER_STEP_Y - room.floor_thick
    room.part("lifted_step_stone", (0.58, 0.34, 0.15), (0.75, step_face - 0.35, 0.075),
              room.stone, rotation=(0.0, 0.0, 0.3))
    room.part("fresh_mortar", (0.62, 0.012, 0.12),
              (0.75, step_face - 0.006, LOWER_RISE / 2.0), room.whitewash)
    room.part("stone_dust", (1.1, 0.5, 0.006), (0.55, step_face - 0.3, 0.003),
              room.whitewash)
    furn.mortar_tub(room, "mortar_tub", (1.5, step_face - 0.35))

    # --- light: the windows, the altar candles, the votives, the door -------
    for index, (y0, y1, z0, z1) in enumerate(WINDOWS):
        light = room.window_light((y0 + y1) / 2.0, (z0 + z1) / 2.0, energy=150.0)
        light.name = f"light_window_{index}"
    altar_x, altar_y = ALTAR_AT
    room.light("light_altar_candles", "POINT",
               (altar_x - 0.3, altar_y - 0.6, UPPER_RISE + 1.6), (0.0, 0.0, -1.0),
               22.0, (1.0, 0.76, 0.46), radius=0.2)
    room.light("light_votives", "POINT", (back_x - 0.8, LOWER_STEP_Y - 0.9, 1.3),
               (0.0, 0.0, -1.0), 30.0, (1.0, 0.74, 0.44), radius=0.12)
    room.light("light_door_daylight", "AREA", (door_cx, door_wall + 0.4, 1.6),
               (0.0, 1.0, -0.35), 140.0, (0.86, 0.92, 1.0), size=1.2, size_y=2.4)

    room.finish()
    return room


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
