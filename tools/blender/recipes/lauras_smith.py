"""Laura's smith -- St. Maria.

Laura's shop is a working room, not a weapon showroom. The forge, anvil,
bellows and quench trough form a visible chain of use; unfinished blades hang
beside repaired lantern frames; and Alicia's lunch sits somewhere Laura can
pretend not to notice it. The room should smell like iron before the player
sees Laura.

    blender --background --factory-startup \
        --python tools/blender/recipes/lauras_smith.py --
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
DEPTH = 7.0
CEILING_Z = 3.60
WINDOW = (2.55, 3.75, 1.72, 2.88)
EXIT_Y = -0.85


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
    room.ceiling(beams=5, beam_span=1.55)
    room.window(*WINDOW)
    tab_x, tab_y = room.exit_threshold(EXIT_Y, width=1.65)

    furn.azulejo_dado(room, height=0.92)
    furn.janela(room, "smith_window", *WINDOW, shutters=False)

    # --- the working line, left to right in the player's view --------------
    # Keep the forge/anvil/quench chain in one readable depth band. At the
    # town's native resolution, pushing every station against the back wall
    # turns a working smithy into a row of dark blocks.
    furn.forge_hearth(room, "forge", (back_x - 3.50, 3.00),
                      width=1.45, depth=1.08, height=0.84)
    # A large, low ember face is intentionally visible at native size. The
    # light is still caused by the hearth; this is its readable silhouette.
    room.part("forge_ember_face", (0.06, 0.56, 0.30),
              (back_x - 4.04, 3.00, 1.08), room.lamplight)
    room.light("forge_ember_fill", "POINT",
               (back_x - 4.14, 3.00, 1.12), (1.0, 0.0, -0.35), 220.0,
               (1.0, 0.24, 0.04), radius=0.22)
    room.part("forge_hood", (0.72, 1.48, 0.42),
              (back_x - 3.08, 3.00, 2.38), room.charcoal)
    room.part("forge_chimney", (0.42, 0.72, 0.52),
              (back_x - 3.08, 3.00, 2.90), room.forge_scale)
    furn.bellows(room, "bellows", (back_x - 3.70, 1.95),
                 length=1.00, width=0.52, height=0.44)
    furn.anvil(room, "anvil", (back_x - 4.00, -0.72), width=1.24,
               height=0.94, face_mat=room.daylight)
    furn.lanterna(room, "anvil_lantern", y=-0.72, z=2.12, energy=34.0)
    furn.quench_trough(room, "quench", (back_x - 3.50, -2.55),
                       length=1.40, width=0.68, height=0.58)
    room.light("anvil_work_light", "POINT",
               (back_x - 4.45, -0.72, 1.90), (1.0, 0.0, -0.75), 120.0,
               (1.0, 0.58, 0.24), radius=0.28)

    # A wall of practical inventory: three unfinished weapons, plus old
    # lantern frames Laura hammers flat during the Vigil.
    furn.weapon_rack(room, "weapon_rack", y=2.02, z=1.18,
                     length=2.18, blades=4)
    room.part("lantern_frame_rail", (0.10, 1.56, 0.10),
              (back_x - 0.18, -2.98, 1.90), room.iron)
    for index, y in enumerate((-3.45, -3.05, -2.65)):
        room.part(f"lantern_frame_{index}", (0.08, 0.28, 0.38),
                  (back_x - 0.24, y, 1.56), room.forge_scale)

    # Coal and scrap are deliberately low, giving the actor a foreground
    # layer that belongs to the work rather than being a token occluder.
    furn.sack(room, "scrap_sack", (back_x - 0.72, 4.12), height=0.72,
              radius=0.30)
    furn.barrel(room, "coal_barrel", (back_x - 0.75, 4.55),
                radius=0.34, height=0.78, mat=room.charcoal)
    for index, y in enumerate((1.05, 1.36, 1.67)):
        room.part(f"coal_lump_{index}", (0.20, 0.24, 0.16),
                  (back_x - 0.92, y, 0.10), room.charcoal,
                  rotation=(0.0, 0.0, 0.3 * index))
    furn.sack(room, "front_coal_sack", (room.front_x - 0.78, 4.00),
              height=0.70, radius=0.28)

    # Alicia's lunch waits on a small bench away from the hot line. The folded
    # cloth is a legible warm accent in an otherwise iron-and-stone room.
    room.part("lunch_bench", (0.52, 1.16, 0.46),
              (back_x - 0.62, -4.00, 0.23), room.wood)
    room.part("lunch_cloth", (0.56, 0.62, 0.06),
              (back_x - 0.92, -4.00, 0.50), room.cloth)
    furn.bread_loaf(room, "lunch_roll", (back_x - 0.98, -4.00),
                    length=0.40, width=0.17, height=0.17)

    # A hammer and tongs make the anvil read as a station rather than a dark
    # pedestal. The tools are placed in the actor's sightline.
    room.part("hammer_handle", (0.62, 0.09, 0.09),
              (back_x - 4.02, -0.16, 1.10), room.wood,
              rotation=(0.0, 0.0, 0.34))
    room.part("hammer_head", (0.18, 0.22, 0.16),
              (back_x - 3.84, 0.03, 1.20), room.forge_scale)
    room.part("tongs", (0.72, 0.06, 0.06),
              (back_x - 3.93, -1.15, 1.02), room.forge_scale,
              rotation=(0.0, 0.0, -0.26))
    # A low workbench gives the foreground its causal role: finished tools
    # leave the anvil here before Laura carries them to the rack.
    furn.mesa(room, "tool_bench", (back_x - 4.50, -3.25),
              length=1.25, width=0.86, height=0.68)
    room.part("tool_bench_cloth", (0.72, 0.48, 0.05),
              (back_x - 4.50, -3.25, 0.73), room.cloth)

    room.window_light((WINDOW[0] + WINDOW[1]) / 2.0,
                      (WINDOW[2] + WINDOW[3]) / 2.0, energy=155.0)
    room.doorway_light(tab_x, tab_y, energy=18.0,
                       colour=(0.70, 0.78, 0.95))
    # Forge light is authored at the hearth and is removed/reduced naturally
    # by the later Vigil state when the map is revisited by the runtime.

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
