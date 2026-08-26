"""Laura's Smith (Forge & Armory) -- St. Maria.

A deeply spatial, high-ceiling industrial forge authored to the town camera contract:
1. Cavernous Main Working Hall:
   - High ceiling (3.85m) with heavy timber cross-ties and an overhead storage mezzanine.
   - Deep side window raking cool daylight across the midground hot-working floor.
   - Anvil on banded stump (cepo), quench tub, and rotary grindstone in the light beam.
   - Armory display with weapon racks, armor stand, and smith's workbench with vice.
2. Deep Stone Hearth Bay (Recanto da Forja):
   - Seen through a massive stone archway on Screen Left (3.4m wide, stepping back 3.4m deep).
   - Masonry forge hearth with glowing charcoal bed, leather bellows, and fuel bunkers.
   - Intense warm fire glow spills forward across the anvil and floor.

Run:
    blender --background --factory-startup \\
        --python tools/blender/recipes/lauras_smith.py -- --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

import furnishings as furn  # noqa: E402
import interior as kit  # noqa: E402

ASSET_ID = "lauras_smith"

# Main forge hall depth & high industrial ceiling
DEPTH = 5.6
CEILING_Z = 3.85

# The deep stone masonry archway into the active forge hearth bay:
# Steps back by 3.4m deep on Screen Left (+Y in world coords)!
FORGE_BAY = (0.25, 3.65, 3.4)            # y0, y1, depth step-back
ARCH_Z = 2.85                            # Masonry arch height
EXIT_Y = -0.65                           # Street exit threshold


def build():
    front_depth = kit.floor_edge_x(kit.FLOOR_EDGE_NATIVE_Y)[1]
    half_width = kit.base_half_width_at(front_depth)

    room = kit.Interior(ASSET_ID, half_width=half_width, depth=DEPTH,
                        ceiling_z=CEILING_Z)
    back_x = room.back_x

    side_win_x0 = back_x - 3.8
    side_win_x1 = back_x - 1.8
    side_win_z0 = 1.45
    side_win_z1 = 2.95

    room.floor(mat=room.terracotta)
    # The back wall has the deep stone forge bay on screen left and the workbench wall on screen right
    room.back_wall(alcoves=[FORGE_BAY], arch_z=ARCH_Z)
    room.side_walls(openings={1: [(side_win_x0, side_win_x1, side_win_z0, side_win_z1)]})
    room.ceiling(beams=5, beam_span=1.6)
    room.side_window(1, side_win_x0, side_win_x1, side_win_z0, side_win_z1)
    tab_x, tab_y = room.exit_threshold(EXIT_Y)

    # --- Colonial Portuguese wall surfaces --------------------------------
    furn.azulejo_dado(room, height=0.95)

    # ======================================================================
    # 1. DEEP STONE FORGE HEARTH BAY (Recanto da Forja - Depth +3.4m)
    # ======================================================================
    # The heavy masonry forge hearth sits deep in the stone alcove
    furn.forge(room, "forge_hearth", (back_x + 2.25, 1.85),
               length=1.95, depth=1.25, height=0.88, chimney_h=2.8)
    furn.bellows(room, "forge_bellows", (back_x + 2.25, 3.05),
                 length=1.15, width=0.54, height=0.40)
    furn.fuel_bunker(room, "coal_bunker", (back_x + 1.15, 3.15),
                     length=0.95, width=0.65, height=0.52)
    furn.woodpile(room, "forge_logs", (back_x + 2.45, 0.65),
                  length=1.15, width=0.52, height=0.72)

    # ======================================================================
    # 2. CENTRAL HOT-WORKING FLOOR (Midground / Screen Left)
    # ======================================================================
    # Anvil on banded stump right in the path of light from side window & forge
    furn.anvil(room, "anvil", (back_x - 1.65, 0.85),
               horn_len=0.85, width=0.30, height=0.48, stump_h=0.48)
    # Quench tub filled with water beside anvil
    furn.quench_tub(room, "quench_tub", (back_x - 1.55, 1.95),
                    radius=0.36, height=0.58)
    # Rotary grindstone for sharpening in the window daylight beam
    furn.grindstone(room, "grindstone", (back_x - 2.85, 2.75),
                    wheel_dia=0.58, wheel_thick=0.12, height=0.78, length=0.85)

    # ======================================================================
    # 3. ARMORY, WORKBENCH & MEZZANINE (Screen Right)
    # ======================================================================
    # Smith's workbench with vice along the back wall
    furn.workbench(room, "workbench", (back_x - 0.55, -2.15),
                   length=1.75, width=0.70, height=0.86)
    furn.tool_rail(room, "tool_rail", y=-2.15, z=2.15, length=1.45)
    furn.ingot_stack(room, "ingot_stack", (back_x - 0.48, -3.45),
                     rows=3, cols=2)
    furn.barrel(room, "scrap_barrel", (back_x - 1.15, -3.45),
                radius=0.32, height=0.76)

    # Overhead storage mezzanine loft holding raw bar stock
    furn.storage_loft(room, "storage_loft", (back_x - 0.55, -2.15),
                      length=2.8, depth=0.85, height=3.0)

    # Finished weapon displays and armor in the foreground
    furn.weapon_rack(room, "weapon_rack", (back_x - 2.25, -2.65),
                     length=1.75, depth=0.48, height=1.75)
    furn.armor_stand(room, "armor_stand", (back_x - 2.85, -1.25),
                     height=1.62, width=0.58)

    # ======================================================================
    # 4. MOTIVATED LIGHTING RIG (High Contrast & Chiaroscuro)
    # ======================================================================
    # 1. Incandescent glowing coke/charcoal fire deep inside the forge hearth
    room.light("light_forge_fire", "POINT",
               (back_x + 2.25, 1.85, 1.15), (0.0, 0.0, -1.0),
               220.0, (1.0, 0.36, 0.04), radius=0.35)

    # 2. Warm ambient illumination inside the deep stone forge bay
    room.light("light_forge_ambient", "POINT",
               (back_x + 2.05, 1.85, 2.45), (0.0, 0.0, -1.0),
               110.0, (1.0, 0.55, 0.20), radius=0.65)

    # 3. Warm firelight spilling through the stone arch onto anvil and floor
    room.light("light_hearth_spill", "AREA",
               (back_x + 0.35, 1.85, 1.65), (-0.85, -0.15, -0.50),
               110.0, (1.0, 0.45, 0.12), size=2.4, size_y=2.6)

    # 4. Cool morning daylight raking diagonally through the side window
    room.side_window_light(1, (side_win_x0 + side_win_x1) / 2.0,
                           (side_win_z0 + side_win_z1) / 2.0, energy=280.0)

    # 5. Wall lantern over the smith's workbench
    furn.lantern(room, "lantern_workbench", y=-2.15, z=2.25, energy=28.0)

    # 6. Light bouncing inward from the street entrance threshold
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
