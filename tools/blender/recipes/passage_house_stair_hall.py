"""Passage House, stair hall -- St. Maria.

The spine of the one building that holds both the Registry and the Summoners'
apartments (layout doc, section 5.1), and the player's way through it: ONE
screen, ONE continuous walk, TWO storeys.

    screen right (-Y)                                            screen left (+Y)
    court door .. post wall .. STAIR rises ----------> upper gallery
    (ground, Cortico level)    (foot)   (top)          [door] [ROOM 3] [door] .. iron gate
                                                       over closed service rooms     to the
                                                       (porter's lodge, wash-house)  Registry

THE PLAYER WALKS BOTH LANES. This is a fork, not a ramp. The ground floor is a
lane that runs the whole length of the hall, UNDER the gallery, from the court door
to the street door in the left end wall. The gallery is a second lane one storey up.
They overlap in Y, so the same Y is two different places. The stair is a LINK between
them (`traversal.links`): at its foot the player presses UP and climbs; at its top
DOWN brings them back; or they simply keep walking left along the ground floor.
The stair stands behind the lane, so the ground path passes in front of it, and the
actor walks in to the stair's depth, up the flight, and out onto the deck.

The camera follows the actor up (`camera.tracking.vertical`): a map's height is not
limited, so a full 3.2 m storey is fine, bounded only by the room that is built.

    levels  gallery: engine Y 0.9..10.0, floor 3.2 (ground is the base lane)
    link    stair:   ground y 15.2 (foot, UP)  <->  gallery y 9.48 (top, DOWN)
    see LEVELS / LINK below; every number is derived from the geometry here.

The ground floor under the gallery has its own life: the building's service doors
(a porter's lodge and a wash-house, shut) and, at the left end, a street door that is
the house's second way out.

WHY IT SITS TOGETHER AS A BUILDING.
  * The court door is in the same back wall as every other door: the whole back
    wall is the court-side face of the house, so the apartments behind the gallery
    look onto the court.
  * The gallery floor is carried: a front fascia beam on stone piers (an arcade
    on the ground floor), joists, a terracotta deck. The stair is solid masonry on
    stepped blocks with a rail. Nothing floats.
  * The gate at the far end of the gallery leads on to the Registry, which is on
    the upper level because the Registry opens on the Praca, the high street.
  * Light tells the route: the court door is the brightest thing on the ground
    floor, a tall window lights the stair, Room 3's lamp is the only warm door.

THE AXIS SPENT is the floor level, taken to a storey: the stair, the deck and the
balustrade carry the second level, and the player walks both.

Room 3's contents are elsewhere; the doorways here are closed except as noted.
The other tenancies are set dressing: boots and a mat, a coat on a peg, a strapped
trunk, straw carried out on boots. Each door has an iron seal plaque.

THE CAMERA looks along the hall with the apartments near and the exit receding
(owner note 2026-10-05: the bright exit already has the most contrast, so it
must not also loom). `distance * tan(fov / 2)` is held at 4.667 m so the Walker
is 48 px at the lane centre:

    --camera '{"distance":14,"fovDegrees":36.87,"yawDegrees":12,"projectionWindowOffsetY":-70.47,"target":{"y":11}}'
    --track 11 156          (+ tracking.vertical: minOffsetY 0, maxOffsetY 100)

Blender Y is screen LEFT. Exported with `--span 22`, engine lane Y is
`11 - blender_y`: the gate end is engine Y ~1.5, the court door 20.

    python tools/blender/run.py tools/blender/recipes/passage_house_stair_hall.py
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

ASSET_ID = "passage_house_stair_hall"

HALF_LENGTH = 11.0        # Blender Y -11..11 (engine 0..22)
DEPTH = 5.6
CEILING_Z = 6.5

GALLERY_Z = 3.2           # the upper floor, level with the Praca
DECK_FRONT_X = -0.85      # the gallery's front edge; the lane (x = 0) is behind it
DECK_THICK = 0.3

COURT_Y, COURT_HALF, COURT_TOP = -9.0, 1.1, 3.0

STAIR_FOOT_Y = -4.2
RISERS = 19
STAIR_RUN = 0.28
STAIR_TOP_Y = STAIR_FOOT_Y + RISERS * STAIR_RUN       # 1.12
STAIR_LANDING = 0.4        # deck between the top step and where the actor stands
STAIR_X0, STAIR_X1 = 1.0, 2.6    # BEHIND the lane (x = 0): the ground path passes in front
STAIR_X = (STAIR_X0 + STAIR_X1) / 2.0

DOOR_TOP = 2.05
DOOR_HALF = 0.55
#            centre, is this Room 3?
UP_DOORS = ((2.5, False), (5.0, True), (7.5, False))
GATE_Y, GATE_TOP = 9.5, 2.4
WINDOW = (-3.0, -1.0, 4.4, 5.9)
STREET_X0, STREET_X1, STREET_TOP = -0.7, 0.7, 2.7
SERVICE_DOORS = (2.45, 7.45)       # ground-floor doors under the gallery, shut

END_Y = HALF_LENGTH - 0.1


def engine_y(blender_y: float) -> float:
    return HALF_LENGTH - blender_y


# The map's lane data, in ENGINE Y (screen right is larger). Everything is derived
# from the geometry above so the walk can never disagree with what was built.
LEVELS = {"gallery": {"minY": 0.9, "maxY": round(engine_y(STAIR_TOP_Y + STAIR_LANDING) + 0.4, 3),
                      "groundZ": GALLERY_Z}}
LINK = {"id": "stair", "x": round(STAIR_X, 3),
        "from": {"level": "ground", "y": round(engine_y(STAIR_FOOT_Y), 3)},
        "to": {"level": "gallery", "y": round(engine_y(STAIR_TOP_Y + STAIR_LANDING), 3)}}
GROUND_LANE = {"minY": 0.3, "maxY": 21.0, "depthX": 0, "groundZ": 0}
# Extra anchors the exporter must publish (`--anchor NAME=Y:Z`): name -> (engine Y, z).
# The court door is the exporter's own `exit_door` (`--exit-y`), so it is not repeated.
ANCHORS = {
    "street_door": (GROUND_LANE["minY"], 0.0),
    "stair_foot": (LINK["from"]["y"], 0.0),
    "stair_top": (LINK["to"]["y"], GALLERY_Z),
    "room3_door": (round(engine_y(5.0), 3), GALLERY_Z),
    "gate_door": (round(engine_y(GATE_Y), 3), GALLERY_Z),
}


def stair_flight(hall):
    """A solid masonry flight BEHIND the lane, rising toward +Y (screen left)."""
    rise = GALLERY_Z / RISERS
    x_mid = (STAIR_X0 + STAIR_X1) / 2.0
    width = STAIR_X1 - STAIR_X0
    with hall.piece("stair"):
        for index in range(RISERS):
            top = (index + 1) * rise
            y = STAIR_FOOT_Y + STAIR_RUN * (index + 0.5)
            hall.part(f"stair_block_{index}", (width, STAIR_RUN, top),
                      (x_mid, y, top / 2.0), hall.stone)
            hall.part(f"stair_tread_{index}", (width + 0.05, STAIR_RUN + 0.02, 0.04),
                      (x_mid - 0.02, y, top + 0.02), hall.wood)
    with hall.piece("stair_rail"):
        for index in range(0, RISERS, 2):
            top = (index + 1) * rise
            y = STAIR_FOOT_Y + STAIR_RUN * (index + 0.5)
            hall.part(f"baluster_{index}", (0.045, 0.045, 0.85),
                      (STAIR_X0 + 0.04, y, top + 0.04 + 0.425), hall.wood)
        slope = math.atan2(GALLERY_Z, STAIR_TOP_Y - STAIR_FOOT_Y)
        length = math.hypot(STAIR_TOP_Y - STAIR_FOOT_Y, GALLERY_Z)
        hall.part("handrail", (0.08, length + 0.1, 0.07),
                  (STAIR_X0 + 0.04, (STAIR_FOOT_Y + STAIR_TOP_Y) / 2.0,
                   GALLERY_Z / 2.0 + 0.04 + 0.9),
                  hall.wood, rotation=(slope, 0.0, 0.0))
        for name, y, z in (("newel_foot", STAIR_FOOT_Y - 0.06, 0.0),
                           ("newel_top", STAIR_TOP_Y + 0.05, GALLERY_Z)):
            hall.part(name, (0.16, 0.16, 1.1), (STAIR_X0 + 0.04, y, z + 0.55), hall.wood)


def gallery(hall):
    """The upper floor: a deck on an arcade, walked at x = 0 behind its rail."""
    y0, y1 = STAIR_TOP_Y, END_Y
    length = y1 - y0
    centre = (y0 + y1) / 2.0
    depth = hall.back_x - DECK_FRONT_X
    x_mid = (hall.back_x + DECK_FRONT_X) / 2.0
    with hall.piece("gallery_deck"):
        hall.part("deck_slab", (depth, length, DECK_THICK),
                  (x_mid, centre, GALLERY_Z - DECK_THICK / 2.0), hall.terracotta)
        hall.part("deck_fascia", (0.18, length, 0.3),
                  (DECK_FRONT_X + 0.09, centre, GALLERY_Z - DECK_THICK / 2.0 - 0.05), hall.wood)
        count = int((length - 0.4) / 0.9)
        for index in range(count):
            hall.part(f"joist_{index}", (depth - 0.3, 0.16, 0.2),
                      (x_mid + 0.1, y0 + 0.5 + 0.9 * index, GALLERY_Z - DECK_THICK - 0.1),
                      hall.wood)
    # The arcade the deck stands on: stone piers on the ground floor.
    with hall.piece("gallery_piers"):
        for index, y in enumerate((1.2, 3.7, 6.2, 8.7)):
            hall.part(f"pier_{index}", (0.42, 0.42, GALLERY_Z - DECK_THICK - 0.04),
                      (DECK_FRONT_X + 0.3, y, (GALLERY_Z - DECK_THICK - 0.04) / 2.0),
                      hall.stone)
        hall.part("pier_end", (0.42, 0.42, GALLERY_Z - DECK_THICK - 0.04),
                  (DECK_FRONT_X + 0.3, END_Y - 0.2, (GALLERY_Z - DECK_THICK - 0.04) / 2.0),
                  hall.stone)
    # The guard rail the player walks behind: open, so the Walker stays readable.
    with hall.piece("gallery_rail"):
        rail_z = GALLERY_Z + 0.88
        hall.part("rail_top", (0.1, length, 0.07), (DECK_FRONT_X + 0.1, centre, rail_z),
                  hall.wood)
        hall.part("rail_low", (0.06, length, 0.05),
                  (DECK_FRONT_X + 0.1, centre, GALLERY_Z + 0.12), hall.wood)
        for index in range(int(length / 0.32)):
            hall.part(f"gallery_baluster_{index}", (0.045, 0.045, 0.8),
                      (DECK_FRONT_X + 0.1, y0 + 0.14 + 0.32 * index, GALLERY_Z + 0.5),
                      hall.wood)
        hall.part("rail_end", (0.14, 0.14, 1.0),
                  (DECK_FRONT_X + 0.1, END_Y - 0.05, GALLERY_Z + 0.5), hall.wood)


def service_door(hall, name, y):
    """A shut ground-floor door under the gallery: the building keeps these rooms."""
    furn.door_frame(hall, f"{name}_frame", y - 0.5, y + 0.5, 1.95)
    hall.part(f"{name}_leaf", (0.08, 1.0, 1.9), (hall.back_x - 0.05, y, 0.95), hall.wood)
    hall.part(f"{name}_hatch", (0.1, 0.4, 0.3), (hall.back_x - 0.1, y, 1.35), hall.charcoal)


def seal_plaque(hall, name, y, z=1.55):
    """The small iron plate beside a tenancy's door that holds its Summoner's seal."""
    with hall.piece(name):
        hall.part(f"{name}_plate", (0.035, 0.2, 0.26), (hall.back_x - 0.02, y, z), hall.iron)
        hall.part(f"{name}_boss", (0.02, 0.09, 0.09), (hall.back_x - 0.05, y, z), hall.bronze)


def door_mat(hall, name, y):
    hall.part(name, (0.55, 0.95, 0.025), (hall.back_x - 0.4, y, 0.0125), hall.cloth)


def boots(hall, name, y):
    """A pair, left where they were taken off, one fallen over."""
    x = hall.back_x - 0.42
    with hall.piece(name):
        hall.part(f"{name}_a", (0.12, 0.3, 0.17), (x, y - 0.14, 0.085), hall.leather)
        hall.part(f"{name}_a_shaft", (0.1, 0.14, 0.2), (x, y - 0.1, 0.27), hall.leather)
        hall.part(f"{name}_b", (0.3, 0.12, 0.13), (x - 0.1, y + 0.2, 0.065), hall.leather)


def coat_on_peg(hall, name, y):
    with hall.piece(name):
        hall.part(f"{name}_peg", (0.14, 0.05, 0.05), (hall.back_x - 0.07, y, 1.85), hall.iron)
        hall.part(f"{name}_coat", (0.1, 0.44, 0.95), (hall.back_x - 0.07, y, 1.34), hall.cloth)
        hall.part(f"{name}_hem", (0.12, 0.5, 0.08), (hall.back_x - 0.08, y, 0.9), hall.cloth)


def straw_wisps(hall, name, y):
    """Straw from a creature's bed, carried out on boots. Only Room 3 has it."""
    with hall.piece(name):
        for index, (dx, dy) in enumerate(((0.0, 0.0), (0.18, 0.28), (-0.12, -0.3), (0.3, -0.12))):
            hall.part(f"{name}_{index}", (0.26, 0.025, 0.012),
                      (hall.back_x - 0.5 + dx * 0.4, y + dy, 0.006), hall.straw)


def strapped_trunk(hall, name, y):
    """A trunk with its straps still buckled: someone who has not unpacked."""
    furn.chest(hall, name, (hall.back_x - 0.45, y))
    with hall.piece(f"{name}_strap"):
        for index, offset in enumerate((-0.28, 0.28)):
            hall.part(f"{name}_strap_{index}", (0.58, 0.05, 0.03),
                      (hall.back_x - 0.45, y + offset, 0.585), hall.leather)


def registry_gate(hall, name, y):
    """A wrought-iron gate with the Registry visible through it, padlocked.

    Locked until the player holds a Crossing Writ, but the house is not hidden:
    past the bars are a counter's edge and a lit lamp, the civic floor this half of
    the building leads to.
    """
    x = hall.back_x + hall.wall_thick - 0.02
    width = DOOR_HALF * 2 - 0.1
    with hall.piece(name):
        for index in range(9):
            bar_y = y - width / 2.0 + width * index / 8.0
            hall.part(f"{name}_bar_{index}", (0.035, 0.035, GATE_TOP - 0.1),
                      (x, bar_y, (GATE_TOP - 0.1) / 2.0 + 0.05), hall.iron)
        for index, z in enumerate((0.3, 1.1, GATE_TOP - 0.2)):
            hall.part(f"{name}_rail_{index}", (0.05, width + 0.06, 0.06), (x, y, z), hall.iron)
        hall.part(f"{name}_padlock", (0.05, 0.1, 0.13), (x - 0.04, y + 0.18, 1.08), hall.bronze)
    back = hall.back_x + hall.wall_thick + 1.5
    hall.part(f"{name}_beyond_wall", (0.06, width + 0.5, GATE_TOP), (back, y, GATE_TOP / 2.0),
              hall.lamplight)
    hall.part(f"{name}_beyond_counter", (0.7, 0.95, 0.92), (back - 0.6, y - 0.1, 0.46), hall.wood)
    hall.part(f"{name}_beyond_ledger", (0.3, 0.4, 0.04), (back - 0.6, y - 0.1, 0.94), hall.paper)
    hall.light(f"{name}_beyond_lamp", "POINT", (back - 0.9, y, GALLERY_Z + 1.9),
               (0.0, 0.0, -1.0), 60.0, (1.0, 0.76, 0.46), radius=0.12)


def post_wall(hall, name, y, z=1.05):
    """The lodgers' pigeonholes: a wall of post, some of it never collected."""
    cols, rows = 5, 3
    cell_y, cell_z = 0.3, 0.3
    with hall.piece(name):
        hall.part(f"{name}_board", (0.1, cols * cell_y + 0.1, rows * cell_z + 0.1),
                  (hall.back_x - 0.06, y, z + rows * cell_z / 2.0), hall.wood)
        for r in range(rows):
            for c in range(cols):
                cy = y + (c - (cols - 1) / 2.0) * cell_y
                cz = z + (r + 0.5) * cell_z
                hall.part(f"{name}_hole_{r}_{c}", (0.03, cell_y - 0.05, cell_z - 0.05),
                          (hall.back_x - 0.105, cy, cz), hall.charcoal)
                if (r * cols + c) % 4 != 1:
                    hall.part(f"{name}_letter_{r}_{c}", (0.04, cell_y - 0.08, 0.15),
                              (hall.back_x - 0.125, cy, cz - 0.05), hall.paper)


def build():
    hall = kit.Interior(ASSET_ID, half_width=HALF_LENGTH, depth=DEPTH, ceiling_z=CEILING_Z)

    openings = [(COURT_Y - COURT_HALF, COURT_Y + COURT_HALF, 0.0, COURT_TOP)]
    openings += [(y - DOOR_HALF, y + DOOR_HALF, GALLERY_Z, GALLERY_Z + DOOR_TOP)
                 for y, _ in UP_DOORS]
    openings.append((GATE_Y - DOOR_HALF, GATE_Y + DOOR_HALF, GALLERY_Z, GALLERY_Z + GATE_TOP))
    openings.append(WINDOW)

    hall.floor(mat=hall.stone)
    hall.back_wall(openings=openings)
    hall.side_walls(openings={1: [(STREET_X0, STREET_X1, 0.0, STREET_TOP)]})
    hall.ceiling(beams=9, beam_span=2.3)
    hall.window(*WINDOW)

    # --- the way in from the court ---------------------------------------------
    hall.doorway("court_door", COURT_Y - COURT_HALF, COURT_Y + COURT_HALF, COURT_TOP,
                 recess=0.7, open_back=True)
    furn.door_frame(hall, "court_door_frame", COURT_Y - COURT_HALF, COURT_Y + COURT_HALF,
                    COURT_TOP, jamb=0.26)
    hall.part("court_daylight", (0.06, COURT_HALF * 2 + 1.2, COURT_TOP),
              (hall.back_x + 2.5, COURT_Y - 0.3, COURT_TOP / 2.0 - 0.1), hall.daylight)

    # --- the street door: the house's second way out, in the end wall ---------------
    _, street_wall = hall.side_doorway("street_door", 1, STREET_X0, STREET_X1, STREET_TOP,
                                       open_back=True)
    furn.door_frame(hall, "street_door_frame", STREET_X0, STREET_X1, STREET_TOP, wall="+y",
                    jamb=0.22)
    hall.part("street_daylight", (STREET_X1 - STREET_X0 + 0.8, 0.06, STREET_TOP),
              (0.0, street_wall + 1.4, STREET_TOP / 2.0 - 0.1), hall.daylight)

    # --- the two storeys ---------------------------------------------------------
    stair_flight(hall)
    gallery(hall)

    with hall.surface(GALLERY_Z):
        for index, (y, is_room3) in enumerate(UP_DOORS):
            name = "door_room3" if is_room3 else f"door_room{index + 2}"
            hall.doorway(name, y - DOOR_HALF, y + DOOR_HALF, DOOR_TOP,
                         lit=True if is_room3 else None)
            furn.door_frame(hall, f"{name}_frame", y - DOOR_HALF, y + DOOR_HALF, DOOR_TOP)
            seal_plaque(hall, f"seal_{name}", y - 1.0)
        hall.doorway("door_gate", GATE_Y - DOOR_HALF, GATE_Y + DOOR_HALF, GATE_TOP,
                     open_back=True)
        furn.door_frame(hall, "door_gate_frame", GATE_Y - DOOR_HALF, GATE_Y + DOOR_HALF,
                        GATE_TOP)
        registry_gate(hall, "registry_gate", GATE_Y)
        # tenancies
        door_mat(hall, "mat_room2", UP_DOORS[0][0])
        boots(hall, "boots_room2", UP_DOORS[0][0] + 0.15)
        door_mat(hall, "mat_room3", UP_DOORS[1][0])
        straw_wisps(hall, "straw_room3", UP_DOORS[1][0])
        strapped_trunk(hall, "trunk_between", 6.25)
        coat_on_peg(hall, "coat_room4", UP_DOORS[2][0] + 1.0)
    # Lantern lights sit at absolute heights, so these stand outside the raised block.
    furn.lantern(hall, "gallery_lantern_a", y=3.75, z=GALLERY_Z + 2.2, energy=26.0)
    furn.lantern(hall, "gallery_lantern_b", y=8.55, z=GALLERY_Z + 2.2, energy=26.0)
    furn.window_dressing(hall, "stair_window", *WINDOW)

    # --- the ground floor --------------------------------------------------------
    for index, y in enumerate(SERVICE_DOORS):
        service_door(hall, f"service_door_{index}", y)
    post_wall(hall, "post_wall", -6.6)
    furn.waiting_bench(hall, "hall_bench", (hall.back_x - 0.55, -6.6), length=2.0)
    furn.water_stand(hall, "water_stand", (hall.back_x - 0.5, -8.0))
    furn.jar(hall, "court_jar", (hall.back_x - 0.5, COURT_Y + 1.9), height=0.55, radius=0.22)
    furn.lantern(hall, "hall_lantern", y=-5.0, z=1.9, energy=70.0)
    furn.lantern(hall, "arcade_lantern_a", y=2.45 + 1.2, z=1.7, energy=70.0)
    furn.lantern(hall, "arcade_lantern_b", y=7.45 - 1.2, z=1.7, energy=70.0)
    furn.azulejo_dado(hall, height=1.05)

    # --- light ---------------------------------------------------------------------
    hall.window_light((WINDOW[0] + WINDOW[1]) / 2.0, (WINDOW[2] + WINDOW[3]) / 2.0,
                      energy=700.0)
    hall.light("light_street", "AREA", (0.0, street_wall - 0.3, 1.5), (0.0, -1.0, -0.3),
               120.0, (1.0, 0.93, 0.8), size=1.2, size_y=1.8)
    hall.light("light_court", "AREA", (hall.back_x + 0.2, COURT_Y, 1.6), (-1.0, 0.0, -0.3),
               170.0, (1.0, 0.93, 0.8), size=1.6, size_y=2.0)
    hall.light("light_under_gallery", "AREA", (DECK_FRONT_X + 1.2, 5.0, GALLERY_Z - 0.35),
               (0.35, 0.0, -1.0), 150.0, (1.0, 0.86, 0.64), size=2.2, size_y=8.0)
    room3_y = next(y for y, is_room3 in UP_DOORS if is_room3)
    hall.light("light_room3_spill", "AREA", (hall.back_x + 0.25, room3_y, GALLERY_Z + 1.5),
               (-1.0, 0.0, -0.35), 60.0, (1.0, 0.76, 0.46), size=1.0, size_y=1.9)

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
