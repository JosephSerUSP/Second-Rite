"""Laura's Smith -- St. Maria.

The weaponsmith and armory forge operated by Laura. Sells basic swords,
shields, armaments, and provides relic reforging (e.g. the Shattered Blade).

Spatial & Narrative Composition:
- Room size derived from camera contract to fit the 256x240 view perfectly.
- Screen-left (y > 0): Heavy stone charcoal forge (*forja*), glowing coke
  firebox, large leather bellows (*fole*), and chimney flue.
- Center / Midground: Large wrought iron anvil (*bigorna*) on a banded hardwood
  stump (*cepo*), slack tub / quench barrel (*tina de têmpera*), and stacked
  metal ingots.
- Screen-right (y < 0): Heavy smith's workbench (*bancada*) with bench vice,
  wall tool rail (*suporte de ferramentas*), and freestanding armory weapon rack
  (*suporte de armas*) displaying broadswords and shield blanks.
- Back wall: Soot-stained limewashed masonry with waist-high azulejo dado band,
  high barred window for smoke ventilation and cool daylight rim.
- Lighting: Blazing orange/amber incandescence from the forge firebox casting
  long shadows across the floor and highlighting the anvil, cool daylight from
  the high window, and doorway bounce at the entrance threshold.
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

ASSET_ID = "lauras_smith"

DEPTH = 6.4
CEILING_Z = 3.6

# High smoke ventilation window on back wall (y0, y1, z0, z1)
WINDOW = (-0.8, 1.0, 1.8, 2.9)
EXIT_Y = -1.3


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

    # --- Screen-Left: Heavy Masonry Forge & Bellows Station ----------------
    # Heavy stone charcoal forge hearth against the back-left wall
    furn.forja(room, "forge", (back_x - 0.95, 2.55), length=1.8, depth=1.2, height=0.88, chimney_h=2.4)
    # Leather and wood forge bellows attached to tuyere on left flank
    furn.fole(room, "bellows", (back_x - 1.05, 3.7), length=1.05, width=0.52, height=0.40)
    # Staved coal barrel beside bellows
    furn.barril(room, "coal_barrel", (back_x - 1.85, 3.65), height=0.76, radius=0.30)

    # --- Center / Midground: Anvil, Quench Tub, and Metal Ingots -----------
    # Central workstation: large iron anvil on banded hardwood stump
    anvil_x = back_x - 2.5
    furn.bigorna(room, "anvil", (anvil_x, 0.45), horn_len=0.78, width=0.26, height=0.44, stump_h=0.46)
    # Staved wooden quench tub / slack tub beside anvil for heat-treatment
    furn.tina(room, "quench_tub", (anvil_x + 0.35, 1.45), radius=0.32, height=0.56)
    # Heavy stack of cast iron and bronze ingots near anvil base
    furn.pilha_lingotes(room, "ingots", (anvil_x - 0.25, -0.4), rows=3, cols=2)
    # Sledgehammer resting on anvil block
    room.part("sledgehammer", (0.12, 0.45, 0.08), (anvil_x + 0.08, 0.45, 0.95), room.iron)

    # --- Screen-Right: Workbench, Tool Rack, Weapon Armory -----------------
    # Smith's heavy workbench along right side wall
    furn.bancada(room, "workbench", (back_x - 1.25, -2.65), length=1.75, width=0.70, height=0.86)
    # Tool rack on back wall holding tongs and cross-peen hammers
    furn.suporte_ferramentas(room, "tool_rack", y=-2.65, z=1.85, length=1.5)
    # Freestanding armory rack displaying forged weapons and shields
    furn.suporte_armas(room, "weapon_rack", (back_x - 2.85, -2.95), length=1.65, depth=0.45, height=1.75)

    # Oil quench pot / flux jar on workbench shelf
    furn.pote(room, "flux_pot", (back_x - 1.2, -3.2), height=0.32, radius=0.13)
    # Laura's whetstone sharpening block
    room.part("whetstone", (0.28, 0.14, 0.06), (back_x - 1.15, -2.25, 0.90), room.stone)

    # --- Foreground depth elements -----------------------------------------
    # Heavy timber framing post on screen-left
    room.part("post_left", (0.22, 0.22, CEILING_Z),
              (room.front_x + 0.4, half_width - 0.4, CEILING_Z / 2.0), room.wood)
    # Front-left iron scrap bucket / crate near entrance
    room.part("scrap_crate", (0.55, 0.55, 0.38),
              (room.front_x + 0.9, half_width - 0.9, 0.19), room.wood)
    room.part("scrap_iron_0", (0.35, 0.06, 0.06),
              (room.front_x + 0.9, half_width - 0.9, 0.42), room.iron, rotation=(0.2, 0.3, 0.1))

    # --- Lighting Rig (In-Room Motivated Sources Only) ----------------------
    # 1. Blazing, intense orange/amber incandescence from the forge firebox
    room.light("light_forge_fire", "POINT",
               (back_x - 0.9, 2.55, 1.05), (0.0, 0.0, -1.0),
               52.0, (1.0, 0.52, 0.16), radius=0.32)
    # 2. Forge radiant fill warming the anvil and slack tub
    room.light("light_forge_radiance", "AREA",
               (back_x - 1.2, 2.2, 1.4), (-0.85, -0.4, -0.3),
               30.0, (1.0, 0.48, 0.12), size=1.4, size_y=1.2)
    # 3. Workbench task lantern
    room.light("light_bench_lamp", "POINT",
               (back_x - 1.25, -2.65, 1.95), (0.0, 0.0, -1.0),
               18.0, (1.0, 0.82, 0.52), radius=0.16)
    # 4. High ventilation window cool daylight beam
    room.window_light((WINDOW[0] + WINDOW[1]) / 2.0,
                      (WINDOW[2] + WINDOW[3]) / 2.0, energy=200.0)
    # 5. Doorway bounce light at the exit threshold
    room.doorway_light(tab_x, tab_y, energy=26.0)

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
