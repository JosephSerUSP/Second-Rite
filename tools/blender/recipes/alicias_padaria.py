"""Alicia's Padaria (Bakery & General Store) -- St. Maria.

A deeply spatial, multi-chamber interior authored to the town camera contract:
1. Front Customer Shop (Loja da Frente):
   - Lower ceiling (2.95m) with dark timber beams and azulejo dado.
   - Screen Right: Hardwood counter with Laura's lunch bundle, ledger desk, bronze scales,
     and bread display basket, bathed in morning daylight from the front window.
   - Screen Far-Right: Mercantile dry-goods shelves, apothecary summoner draughts rack,
     oil demijohns, grain barrel, and grain bin.
   - Overhead: Provision rail hung with garlic braids and cured provisions.
2. Deep Back Bakery Chamber (Casa do Forno):
   - Seen through a wide open masonry archway on Screen Left (stepping back 4.2m deep).
   - Warm glowing wood-fired brick bread oven, dough kneading trough (masseira),
     neatly stacked split firewood, and flour sack pyramids.
   - Rich warm orange furnace light pours through the archway onto the shop floor.

Run:
    blender --background --factory-startup \\
        --python tools/blender/recipes/alicias_padaria.py -- --force
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

# Front shop depth & ceiling
DEPTH = 5.2
CEILING_Z = 2.95

# The grand masonry archway into the deep back bakery chamber:
# Steps back by 4.2m deep on Screen Left (+Y in world space)
BAKERY_ARCH = (-0.15, 3.65, 4.2)         # y0, y1, depth step-back
ARCH_Z = 2.55                            # Arch header height
WINDOW = (-3.35, -1.35, 1.25, 2.35)      # Front shop window (screen right / -Y)
EXIT_Y = -0.65                           # Street exit threshold


def build():
    front_depth = kit.floor_edge_x(kit.FLOOR_EDGE_NATIVE_Y)[1]
    half_width = kit.base_half_width_at(front_depth)

    room = kit.Interior(ASSET_ID, half_width=half_width, depth=DEPTH,
                        ceiling_z=CEILING_Z)
    back_x = room.back_x

    room.floor(mat=room.terracotta)
    # The back wall has the front window on screen right and the grand arch on screen left
    room.back_wall(openings=[WINDOW], alcoves=[BAKERY_ARCH], arch_z=ARCH_Z)
    room.side_walls()
    room.ceiling(beams=5, beam_span=1.6)
    room.window(*WINDOW)
    tab_x, tab_y = room.exit_threshold(EXIT_Y)

    # --- Colonial Portuguese wall surfaces --------------------------------
    furn.azulejo_dado(room, height=0.95)
    furn.window_dressing(room, "window", *WINDOW)

    # ======================================================================
    # 1. DEEP BACK BAKERY CHAMBER (Casa do Forno - Depth +4.2m)
    # ======================================================================
    # Positioned deep inside the back room (back_x + 1.0m to back_x + 4.0m)
    # The wood-fired masonry bread oven sits against the back wall of the bakery
    furn.bread_oven(room, "bread_oven", (back_x + 2.85, 1.85),
                    length=1.55, depth=1.25, height=1.75)
    furn.peel(room, "baker_peel", (back_x + 0.55, 0.05), length=1.85,
              angle_deg=12.0)
    # Large wooden dough kneading trough (masseira) in the mid-bakery
    furn.dough_trough(room, "dough_trough", (back_x + 1.35, 2.25),
                      length=1.45, width=0.62, height=0.82)
    # Neatly stacked split firewood pile for the oven
    furn.woodpile(room, "woodpile", (back_x + 2.65, 0.45),
                  length=1.25, width=0.55, height=0.75)
    # Stack of flour sacks against the bakery side return
    furn.sack_stack(room, "flour_sacks", (back_x + 2.75, 3.25), count=3)
    # Fuel bunker with charcoal / coal
    furn.fuel_bunker(room, "fuel_bunker", (back_x + 1.35, 0.45),
                     length=0.75, width=0.55, height=0.48)

    # ======================================================================
    # 2. FRONT CUSTOMER SHOP (Loja da Frente)
    # ======================================================================
    # Customer service counter positioned in the foreground/midground (screen center-right)
    furn.counter(room, "merchant_counter", (back_x - 1.65, -0.65),
                 length=2.25, width=0.68, height=0.88, panels=3)
    furn.scales(room, "counter_scales", (back_x - 1.65, -1.35),
                height=0.42, width=0.38)
    furn.counter_dressing(room, "counter_dressing", (back_x - 1.65, -0.45))
    furn.bread_basket(room, "counter_bread", (back_x - 1.65, 0.25),
                      radius=0.20, height=0.13)

    # --- Mercantile & Summoner Provisions (Screen Right / -Y) ------------
    furn.mercantile_shelf(room, "dry_goods_shelf", (back_x - 0.45, -2.45),
                          length=1.45, depth=0.38, height=1.75, tiers=3)
    furn.apothecary_rack(room, "summoner_apothecary", y=-2.45, z=1.95,
                         length=1.1, depth=0.22)
    furn.grain_bin(room, "grain_bin", (back_x - 1.85, -3.35),
                   length=0.92, width=0.58, height=0.64)
    furn.demijohn(room, "oil_demijohn_0", (back_x - 0.45, -3.45),
                  height=0.52, radius=0.18)
    furn.demijohn(room, "oil_demijohn_1", (back_x - 0.85, -3.55),
                  height=0.44, radius=0.15)
    furn.barrel(room, "grain_barrel", (back_x - 1.35, -3.55),
                radius=0.30, height=0.74)

    # Overhead ceiling goods rail
    furn.hanging_rack(room, "ceiling_herbs", (back_x - 1.85, -0.65),
                      length=1.35, height=2.55)

    # ======================================================================
    # 3. MOTIVATED LIGHTING RIG (High Contrast & Spatial Depth)
    # ======================================================================
    # 1. Glowing wood-fired bread oven deep in the back bakery chamber
    room.light("light_oven_embers", "POINT",
               (back_x + 2.35, 1.85, 0.95), (-0.85, 0.0, -0.45),
               220.0, (1.0, 0.48, 0.10), radius=0.35)

    # 2. Warm ambient illumination inside the back bakery chamber
    room.light("light_bakery_ambient", "POINT",
               (back_x + 2.05, 1.85, 2.35), (0.0, 0.0, -1.0),
               110.0, (1.0, 0.65, 0.32), radius=0.65)

    # 3. Warm light spill through the grand arch portal into the front shop
    room.light("light_arch_spill", "AREA",
               (back_x + 0.25, 1.85, 1.45), (-0.85, -0.25, -0.45),
               95.0, (1.0, 0.58, 0.20), size=2.4, size_y=2.6)

    # 4. Cool morning daylight raking through the front shop window
    room.window_light((WINDOW[0] + WINDOW[1]) / 2.0,
                      (WINDOW[2] + WINDOW[3]) / 2.0, energy=240.0)

    # 5. Wrought iron wall lantern over the dry-goods shelves
    furn.lantern(room, "lantern_shop", y=-3.65, z=2.05, energy=30.0)

    # 6. Daylight bounce on the street entrance threshold
    room.doorway_light(tab_x, tab_y, energy=24.0)

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
