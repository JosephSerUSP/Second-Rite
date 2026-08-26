"""Alicia's Padaria -- St. Maria.

The bakery is the town's soft counterpoint to the Labyrinth: a warm oven,
water for people who forget to drink, and practical provisions arranged around
the one thing Alicia cannot stop doing when she is nervous -- feeding people.
The counter is a real barrier, the oven is a real heat source, and the hidden
lantern beneath it gives the room its quiet second meaning during the Vigil.

    blender --background --factory-startup \
        --python tools/blender/recipes/alicias_padaria.py --
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
DEPTH = 6.5
CEILING_Z = 3.45
WINDOW = (1.55, 2.75, 1.50, 2.62)
EXIT_Y = -0.9


def build():
    front_depth = kit.floor_edge_x(kit.FLOOR_EDGE_NATIVE_Y)[1]
    half_width = kit.base_half_width_at(front_depth)
    room = kit.Interior(ASSET_ID, half_width=half_width, depth=DEPTH,
                        ceiling_z=CEILING_Z)
    back_x = room.back_x

    room.floor(mat=room.terracotta)
    room.foreground_floor(depth=10.5, mat=room.terracotta)
    room.back_wall(openings=[WINDOW])
    room.side_walls()
    room.ceiling(beams=5, beam_span=1.45)
    room.window(*WINDOW)
    tab_x, tab_y = room.exit_threshold(EXIT_Y, width=1.65)

    # The blue dado and folded shutters make this a St. Maria room before any
    # props are read. The fired floor gives Alicia's work a different register
    # from the dark boards of Passage House.
    furn.azulejo_dado(room, height=0.98)
    furn.janela(room, "bakery_window", *WINDOW)

    # --- Alicia's working triangle: oven, counter, water ------------------
    # Pull the working line into the actor's depth so the native 256px
    # composition can read the oven and counter as authored stations rather
    # than tiny silhouettes at the back wall.
    furn.forno(room, "bread_oven", (back_x - 3.40, 2.85),
               width=1.72, depth=1.02, height=1.68)
    room.part("counter_body", (0.82, 2.65, 0.86),
              (back_x - 3.70, -0.75, 0.43), room.wood)
    room.part("counter_face_rail", (0.10, 2.48, 0.16),
              (back_x - 4.10, -0.75, 0.56), room.iron)
    room.part("counter_top", (0.94, 2.82, 0.10),
              (back_x - 3.70, -0.75, 0.91), room.wood)
    furn.bread_display(room, "counter_display",
                       (back_x - 4.05, -0.75), length=2.05, depth=0.50)
    furn.lanterna(room, "counter_lantern", y=-0.75, z=2.15, energy=22.0)
    # A small customer-side table makes the foreground extension a real part
    # of the shop: cooled loaves are waiting here, not floating in a test set.
    furn.mesa(room, "pastry_table", (back_x - 4.80, -2.70),
              length=1.18, width=0.88, height=0.70)
    furn.bread_display(room, "pastry_table_display",
                       (back_x - 4.80, -2.70), length=0.94, depth=0.38,
                       loaves=3)
    furn.barrel(room, "water_barrel", (back_x - 4.40, -3.10),
                radius=0.40, height=0.90)
    room.part("water_dipper", (0.12, 0.25, 0.08),
              (back_x - 4.80, -3.10, 0.98), room.wood)
    # A flour sack close to the entrance gives the foreground extension a
    # reason to exist and makes the stock read as a working shop, not a set.
    furn.sack(room, "front_flour_sack", (room.front_x - 0.80, 3.82),
              height=0.74, radius=0.29)

    # --- the stock that makes the shop useful to a summoner ---------------
    furn.sack(room, "flour_sack_a", (back_x - 1.95, 3.72), height=0.84,
              radius=0.30)
    furn.sack(room, "flour_sack_b", (back_x - 1.98, 4.28), height=0.70,
              radius=0.27)
    furn.prateleira(room, "dry_goods", y=1.20, z=1.92, length=2.15, depth=0.30)
    furn.pote(room, "salt_jar", (back_x - 0.55, 1.28), height=0.48,
              radius=0.18)
    furn.pote(room, "honey_jar", (back_x - 0.52, 1.72), height=0.34,
              radius=0.14)
    furn.pote(room, "herb_jar", (back_x - 0.50, 2.18), height=0.30,
              radius=0.12)
    # A cloth-wrapped bread/cheese/pear bundle waits at the edge of the
    # counter: the lunch that turns a shop visit into a relationship.
    room.part("lunch_bundle", (0.34, 0.62, 0.20),
              (back_x - 1.76, 0.35, 1.08), room.cloth)
    furn.bread_loaf(room, "lunch_bread", (back_x - 1.80, 0.20),
                    length=0.42, width=0.17, height=0.18)
    furn.pote(room, "pear", (back_x - 1.78, 0.53), height=0.22,
              radius=0.10, mat=room.bread_crust)

    # --- character details -------------------------------------------------
    room.part("apron_hook", (0.05, 0.18, 0.16),
              (back_x - 0.03, -2.55, 1.24), room.iron)
    room.part("apron_fold", (0.05, 0.42, 0.86),
              (back_x - 0.02, -2.55, 0.68), room.cloth)
    room.part("wax_scrape_tray", (0.06, 0.62, 0.08),
              (back_x - 1.74, -1.94, 1.04), room.wood)

    # The hidden summon lantern is intentionally low and occluded by the
    # counter; its glow is visible before its source is understood.
    room.part("hidden_summon_lantern", (0.13, 0.18, 0.20),
              (back_x - 1.73, -1.42, 0.40), room.lamplight)
    room.light("light_hidden_summon_lantern", "POINT",
               (back_x - 1.82, -1.42, 0.48), (1.0, 0.0, -0.3), 8.0,
               (1.0, 0.62, 0.24), radius=0.12)

    # Light is motivated by the oven, window and the corridor beyond the exit.
    room.window_light((WINDOW[0] + WINDOW[1]) / 2.0,
                      (WINDOW[2] + WINDOW[3]) / 2.0, energy=190.0)
    room.doorway_light(tab_x, tab_y, energy=22.0,
                       colour=(0.76, 0.82, 1.0))

    room.finish()
    return room


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog=ASSET_ID)
    parser.add_argument("--blend", type=Path,
                        default=kit.ENVIRONMENT_DIR / f"{ASSET_ID}.blend")
    parser.add_argument("--force", action="store_true",
                        help="replace existing untouched scaffold output, or "
                             "deliberately discard adopted hand-authoring")
    args = parser.parse_args(argv)
    room = build()
    bpy.context.view_layer.update()
    blend = kit.save_source_blend(args.blend, force=args.force)
    kit.report(room, blend)


if __name__ == "__main__":
    main()
