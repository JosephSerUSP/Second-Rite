"""Alicia's Padaria -- St. Maria.

The bakery and provision shop run by Alicia. Sells fresh baked breads (broas,
sweet bread loaves), general staples to the townsfolk (flour sacks, olive oil,
salt, dried herbs), and expedition rations for summoners.

Spatial & Narrative Composition:
- Room size derived from camera contract to fit the 256x240 view perfectly.
- Screen-left (y > 0): Traditional wood-fired arched bread oven (*forno a lenha*),
  flour sacks, firewood, and bread peels.
- Midground centre: Heavy Portuguese merchant counter (*balcão*) with fresh
  loaves in woven baskets, brass balance scales, and provisions.
- Screen-right (y < 0): Wall shelves with ceramic crocks, glass demijohns of oil,
  and Alicia's quiet tea corner with her ceramic cup and small stool.
- Back wall: Limewashed masonry with waist-high azulejo dado band, high barred
  window casting soft cool daylight, and hanging dried herb bundles.
- Lighting: Warm glowing hearth fire from the oven mouth, soft lantern on counter,
  cool daylight beam from high window, and doorway bounce at the exit.
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

ASSET_ID = "alicias_padaria"

DEPTH = 6.2
CEILING_Z = 3.6

# High barred window on back wall (y0, y1, z0, z1)
WINDOW = (-0.6, 1.2, 1.6, 2.8)
EXIT_Y = -1.2


def build():
    front_depth = kit.floor_edge_x(kit.FLOOR_EDGE_NATIVE_Y)[1]
    half_width = kit.base_half_width_at(front_depth)

    room = kit.Interior(ASSET_ID, half_width=half_width, depth=DEPTH,
                        ceiling_z=CEILING_Z)
    back_x = room.back_x

    room.floor()
    room.back_wall(openings=[WINDOW])
    room.side_walls()
    room.ceiling(beams=5, beam_span=1.8)
    room.window(*WINDOW)
    tab_x, tab_y = room.exit_threshold(EXIT_Y)

    # --- Colonial Portuguese finishes --------------------------------------
    furn.azulejo_dado(room, height=1.05)
    furn.janela(room, "window", *WINDOW)

    # --- Screen-Left: Wood-Fired Bread Oven & Baking Hearth -----------------
    # Arched brick oven in the back-left corner
    furn.forno_lenha(room, "oven", (back_x - 0.85, 2.65), length=1.5, depth=1.3, height=1.6)
    # Baker's peel leaning beside oven
    furn.pa_forno(room, "peel", (back_x - 1.1, 1.7), length=1.8, angle_deg=12.0)
    # Burlap sacks of grain and flour stacked by the flour station
    furn.sacos_pilha(room, "flour_sacks", (back_x - 0.65, 3.75), count=3)
    furn.saco(room, "sugar_sack", (back_x - 1.35, 3.85), rotation=0.4)

    # --- Midground: Shop Counter (*Balcão*) & Bread Displays ----------------
    # Merchant counter dividing shopkeeper area from customer floor
    counter_x = back_x - 2.2
    furn.balcao(room, "counter", (counter_x, 0.45), length=2.2, width=0.72, height=0.88, panels=3)
    # Woven bread baskets on the counter top with fresh broas
    furn.cesto_paes(room, "basket_main", (counter_x - 0.05, 0.95), radius=0.20, height=0.12)
    furn.cesto_paes(room, "basket_sweet", (counter_x - 0.05, 0.35), radius=0.18, height=0.11)
    # Brass balance scale for weighing dry rations and coin
    furn.balanca(room, "scales", (counter_x + 0.08, -0.25), height=0.40, width=0.34)
    # Small wooden coin box on counter
    room.part("coin_box", (0.18, 0.24, 0.12), (counter_x + 0.12, -0.55, 0.94), room.wood)

    # --- Screen-Right: Provisions Shelves, Demijohns, Alicia's Nook ---------
    # Deep multi-tier shelf on back wall stocked with crocks and jars
    furn.prateleira(room, "shelf_high", y=-2.6, z=2.2, length=1.8, depth=0.32)
    furn.prateleira(room, "shelf_low", y=-2.6, z=1.5, length=1.8, depth=0.32)
    # Jars, crocks, and herb canisters on shelves
    furn.pote(room, "jar_oil_1", (back_x - 0.22, -2.1), height=0.36, radius=0.14)
    furn.pote(room, "jar_oil_2", (back_x - 0.22, -2.6), height=0.42, radius=0.16)
    furn.pote(room, "jar_salt", (back_x - 0.20, -3.1), height=0.30, radius=0.12)
    # Ceramic crocks on high shelf
    room.part("crock_herb_0", (0.16, 0.16, 0.22), (back_x - 0.18, -2.3, 2.35), room.crock)
    room.part("crock_herb_1", (0.16, 0.16, 0.22), (back_x - 0.18, -2.8, 2.35), room.crock)

    # Wicker-cased demijohns (*garrafões*) of olive oil on the floor
    furn.garrafao(room, "demijohn_0", (back_x - 0.45, -3.5), height=0.55, radius=0.20)
    furn.garrafao(room, "demijohn_1", (back_x - 0.40, -4.0), height=0.48, radius=0.17)

    # Alicia's personal quiet corner: small side table with tea cup & stool
    furn.mesa(room, "side_table", (back_x - 0.8, -1.5), length=0.65, width=0.55, height=0.72)
    furn.cadeira(room, "alicia_stool", (back_x - 1.35, -1.5), seat=0.44, width=0.38)
    # Alicia's tea cup (*chávena*) and teapot
    room.part("teacup", (0.10, 0.10, 0.08), (back_x - 0.8, -1.45, 0.76), room.crock)
    room.part("teapot", (0.16, 0.16, 0.16), (back_x - 0.8, -1.65, 0.80), room.crock)

    # --- Foreground depth elements -----------------------------------------
    # Corner timber beam post on screen-right creating a foreground frame
    room.part("post_right", (0.22, 0.22, CEILING_Z),
              (room.front_x + 0.4, -half_width + 0.4, CEILING_Z / 2.0), room.wood)
    # Front-right storage barrel near entrance
    furn.barril(room, "front_barrel", (room.front_x + 0.8, -half_width + 0.9), height=0.72, radius=0.28)

    # --- Lighting Rig (In-Room Motivated Sources Only) ----------------------
    # 1. Warm blazing fire glow from the bread oven mouth
    room.light("light_oven_fire", "POINT",
               (back_x - 1.1, 2.65, 0.75), (0.0, 0.0, -1.0),
               38.0, (1.0, 0.62, 0.24), radius=0.28)
    # 2. Counter wall lantern illuminating the transaction surface
    room.light("light_counter_lamp", "POINT",
               (counter_x + 0.2, 0.45, 1.95), (0.0, 0.0, -1.0),
               22.0, (1.0, 0.84, 0.58), radius=0.18)
    # 3. High window daylight beam
    room.window_light((WINDOW[0] + WINDOW[1]) / 2.0,
                      (WINDOW[2] + WINDOW[3]) / 2.0, energy=240.0)
    # 4. Doorway bounce light from outside street threshold
    room.doorway_light(tab_x, tab_y, energy=28.0)

    room.finish()
    return room


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog=ASSET_ID)
    parser.add_argument("--blend", type=Path,
                        default=kit.ENVIRONMENT_DIR / f"{ASSET_ID}.blend")
    parser.add_argument("--force", action="store_true",
                        help="overwrite the source .blend, DISCARDING any hand-authoring in it")
    args = parser.parse_args(argv)

    room = build()
    bpy.context.view_layer.update()
    blend = kit.save_source_blend(args.blend, force=args.force)
    kit.report(room, blend)


if __name__ == "__main__":
    main()
