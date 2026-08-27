"""Alicia's Padaria -- St. Maria.

The town bakery, which is also the town's general store and the only place a
summoner can buy food that travels. Everything here comes out of authored game
text rather than being invented:

    "I sell things that keep you alive! It makes me happy. Watching people
    leave with full bags... it means they might come back."
    "Please drink water before you descend."
    Alicia is scraping wax from a tray. One small lantern, hidden behind the
    counter, bears no human name.

So the room has to hold three trades at once -- bread, staples, and the Vigil's
lanterns -- and it has to look like a business that is coping rather than a
tidy museum of three props. The full brief is
`docs/design/st-maria-shop-briefs.md`.

The shell, thresholds and light vocabulary live in `interior.py`; the
furnishings in `furnishings.py`. This file declares only what makes the Padaria
itself, plus the one axis each contest variant spends.

    blender --background --factory-startup \
        --python tools/blender/recipes/alicias_padaria.py -- --variant alcove
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

import furnishings as furn  # noqa: E402
import interior as kit  # noqa: E402

ASSET_ID = "alicias_padaria"

# Self-contained and unscrollable: sized to the Classic 256 width so the whole
# shop is on screen and no edge invites the player onward. Depth is generous
# because depth costs nothing here -- the bakehouse end is meant to recede.
DEPTH = 6.8
CEILING_Z = 3.7

# The back window sits just off centre, screen-right of the oven, so the room
# has daylight on the customer side and firelight on the working side. Those
# two colours arriving from two places is most of what stops a shoebox reading
# flat, before any axis is spent.
WINDOW = (-0.3, 1.3, 1.45, 2.75)
EXIT_Y = -3.15

COUNTER_AT = (0.5, -0.5)
COUNTER_LENGTH = 3.6
COUNTER_H = 0.88

# Screen-left back: the oven. The alcove variant moves it into the recess.
OVEN_Y = 2.7
ALCOVE = (1.75, 3.75, 1.05)

VARIANTS = ("alcove", "partition", "side_window")

# Which axis this map spends, decided by rendering all three and reviewing them
# head to head rather than by preference. See
# docs/reports/st-maria-shop-interiors-2026-08-26.md.
SHIPPED = "side_window"


def build(variant="side_window"):
    if variant not in VARIANTS:
        raise SystemExit(f"unknown variant {variant!r}; pick one of {VARIANTS}")

    front_depth = kit.floor_edge_x(kit.FLOOR_EDGE_NATIVE_Y)[1]
    half_width = kit.base_half_width_at(front_depth)

    # The SHIPPED variant carries the bare asset id; the others are contest
    # builds and are named so a stray render cannot be mistaken for the map.
    room = kit.Interior(ASSET_ID if variant == SHIPPED
                        else f"{ASSET_ID}_{variant}",
                        half_width=half_width, depth=DEPTH,
                        ceiling_z=CEILING_Z)
    back_x = room.back_x

    # Terracotta underfoot, not board: a bakery floor is swept and washed, and
    # tile is what a colonial Portuguese shop actually stands on.
    room.floor(mat=room.terracotta)

    alcoves = [ALCOVE] if variant == "alcove" else ()
    room.back_wall(openings=[WINDOW], alcoves=alcoves)

    side_openings = None
    if variant == "side_window":
        # Screen-RIGHT wall (side -1), over the customer half. Morning light
        # rakes ACROSS the shop instead of arriving from behind the player.
        side_openings = {-1: [(room.front_x + 1.5, room.front_x + 3.3,
                               1.55, 2.95)]}
    room.side_walls(openings=side_openings)

    room.ceiling(beams=5)
    room.window(*WINDOW)
    tab_x, tab_y = room.exit_threshold(EXIT_Y)

    furn.azulejo_dado(room, height=1.05)
    furn.window_dressing(room, "window", *WINDOW)

    # --- the bakehouse end (screen left) -----------------------------------
    oven_x = back_x - 0.72 + (ALCOVE[2] if variant == "alcove" else 0.0)
    furn.bread_oven(room, "oven", (oven_x, OVEN_Y))
    furn.peel(room, "peel", (oven_x - 1.05, OVEN_Y - 1.25))

    # The wax bench stands beside the oven because it lives off the oven's
    # heat -- the reason one woman does both trades at all. Brought FORWARD of
    # the oven and given its own candle: a review of the first pass reported no
    # visible wax work at all, because the bench was back in the dark where the
    # oven's glow washed straight over it.
    furn.wax_bench(room, "wax_bench", (0.95, 3.15))
    room.light("light_wax_candle", "POINT", (0.35, 3.15, 1.35),
               (-0.6, -0.4, -0.3), 9.0, (1.0, 0.74, 0.44), radius=0.1)

    # Volume, not representative props. "Watching people leave with full bags"
    # is the line the room has to earn, and the first pass read as a tidy
    # museum of three prop zones.
    furn.sack_stack(room, "flour", (2.9, 3.5), count=3)
    furn.sack_stack(room, "flour_front", (0.55, -2.2), count=3)
    furn.barrel(room, "barrel_front", (-0.35, 2.35), radius=0.30, height=0.72)
    furn.demijohn(room, "oil", (2.35, 1.35))
    furn.barrel(room, "barrel", (3.1, 0.55))

    # --- the shop end (screen right) ---------------------------------------
    furn.stock_shelf(room, "stock", (back_x - 0.28, -2.4))
    furn.counter(room, "counter", COUNTER_AT, length=COUNTER_LENGTH,
                 height=COUNTER_H, panels=4, top_mat=room.plaster)
    furn.water_stand(room, "water", (-0.85, -3.15))
    furn.jar(room, "salt_jar", (1.35, -3.45), height=0.52, radius=0.22)
    furn.jar(room, "salt_jar_small", (1.5, -2.95), height=0.34, radius=0.14)

    with room.surface(COUNTER_H + 0.08):
        furn.scales(room, "scales", (COUNTER_AT[0], -1.75))
        furn.bread_basket(room, "basket", (COUNTER_AT[0] - 0.04, 0.55),
                          radius=0.26)
        furn.bread_basket(room, "basket_two", (COUNTER_AT[0] + 0.06, 1.35),
                          radius=0.21)
        furn.cloth_bundle(room, "bundle_ready", (COUNTER_AT[0] + 0.02, -0.35))
        furn.cloth_bundle(room, "bundle_small",
                          (COUNTER_AT[0] - 0.06, -0.85),
                          radius=0.13, height=0.19, rotation=0.7)
        # The honey roll she saved, on a plate by itself, apart from the stock.
        room.part("saved_plate", (0.19, 0.19, 0.015),
                  (COUNTER_AT[0] - 0.02, 1.05, 0.008), room.crock)
        room.part("saved_roll", (0.13, 0.15, 0.08),
                  (COUNTER_AT[0] - 0.02, 1.05, 0.055), room.bread)

    # BEHIND the counter, where a customer cannot reach: the small lantern
    # that bears no human name. Deliberately unlit and half-hidden -- the
    # player is not supposed to be able to read it, only to notice it is there.
    room.part("hidden_lantern_body", (0.15, 0.15, 0.21),
              (COUNTER_AT[0] + 0.46, -1.95, 0.11), room.iron)
    room.part("hidden_lantern_top", (0.19, 0.19, 0.04),
              (COUNTER_AT[0] + 0.46, -1.95, 0.235), room.iron)
    room.part("hidden_lantern_cloth", (0.24, 0.26, 0.03),
              (COUNTER_AT[0] + 0.44, -1.95, 0.27), room.cloth,
              rotation=(0.0, 0.1, 0.0))

    furn.lantern(room, "lantern", y=-0.9, z=2.25)

    # --- the one axis ------------------------------------------------------
    if variant == "partition":
        # The shop line made structural: the counter is where money changes
        # hands, and this is where the customer stops being allowed to walk.
        # Low, with end posts, so it divides the plan without building a
        # second room in one shot.
        room.partition("shop_line", 1.75, 1.35, back_x - 0.1)
    elif variant == "side_window":
        room.side_window(-1, room.front_x + 1.5, room.front_x + 3.3,
                         1.55, 2.95)

    # --- light: every hard shadow has its source in the room ---------------
    # The oven mouth. Warm, low and close to the floor, which is what makes
    # the bakehouse end read hotter than the shop end.
    room.light("light_oven", "POINT", (oven_x - 0.85, OVEN_Y, 0.92),
               (-1.0, 0.0, -0.15), 34.0, (1.0, 0.55, 0.20), radius=0.22)
    room.window_light((WINDOW[0] + WINDOW[1]) / 2.0,
                      (WINDOW[2] + WINDOW[3]) / 2.0)
    room.doorway_light(tab_x, tab_y)

    if variant == "alcove":
        # A dark hole in the back wall is not a feature. The oven's own glow
        # has to reach the recess it now stands in.
        room.light("light_alcove", "POINT",
                   (back_x + 0.45, OVEN_Y, 2.35), (0.0, 0.0, -1.0),
                   16.0, (1.0, 0.66, 0.34), radius=0.3)
    elif variant == "side_window":
        room.side_window_light(-1, room.front_x + 2.4, 2.25)

    room.finish()
    return room


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog=ASSET_ID)
    parser.add_argument("--variant", default=SHIPPED, choices=VARIANTS)
    parser.add_argument("--blend", type=Path, default=None)
    parser.add_argument("--force", action="store_true",
                        help="overwrite the source .blend, DISCARDING any "
                             "hand-authoring in it")
    args = parser.parse_args(argv)

    room = build(args.variant)
    blend = args.blend or (kit.ENVIRONMENT_DIR / f"{ASSET_ID}.blend")
    bpy.context.view_layer.update()
    saved = kit.save_source_blend(blend, force=args.force)
    kit.report(room, saved, extra={"variant": args.variant})


if __name__ == "__main__":
    main()
