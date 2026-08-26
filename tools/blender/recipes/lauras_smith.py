"""Laura's smith -- St. Maria.

The town's only metalworker, and the shop that sells a summoner their opening
weapons. Everything here comes out of authored game text:

    "Fire purifies. Metal obeys. People... people lie. Steel never lies to
    you. It just is."
    "Don't buy a heroic weapon. Buy something that still works while you're
    running home."
    "Bring me anything the Labyrinth failed to digest."
    Laura's forge is cold. She is hammering old lantern frames flat for reuse.
    "The gold is pure... untouched."

So it is a salvage business as much as a forge; it does fine work as well as
heavy work; and it is the warmest room in St. Maria, which is why people come
in without buying anything. The full brief is
`docs/design/st-maria-shop-briefs.md`.

Deliberately the inverse of Alicia's Padaria in every register the vocabulary
has: dark against bright, ordered against over-full, ember-orange against
daylight, and almost no azulejo -- the dado is a domestic thing, and the one
stretch of it here is beside the door where a customer waits.

    blender --background --factory-startup \
        --python tools/blender/recipes/lauras_smith.py -- --variant platform
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

# Self-contained and unscrollable, and TALLER than the Padaria: a forge hood
# and its flue need the height, and the extra dark air above the fire is what
# makes the room read hot rather than merely dim.
DEPTH = 6.4
CEILING_Z = 3.9

# High and small. A smith wants light on the work, not on the room, and a
# shuttered slot up near the ceiling is what an actual forge has: it vents as
# much as it lights.
WINDOW = (-3.05, -1.85, 2.25, 3.15)
EXIT_Y = -0.4

FORGE_Y = 2.45
HEARTH = (1.25, 3.7)          # the platform variant's raised hearth span

VARIANTS = ("side_window", "platform", "foreground")

# Which axis this map spends, decided by rendering all three and reviewing them
# head to head rather than by preference. See
# docs/reports/st-maria-shop-interiors-2026-08-26.md.
SHIPPED = "platform"


def build(variant="platform"):
    if variant not in VARIANTS:
        raise SystemExit(f"unknown variant {variant!r}; pick one of {VARIANTS}")

    front_depth = kit.floor_edge_x(kit.FLOOR_EDGE_NATIVE_Y)[1]
    half_width = kit.base_half_width_at(front_depth)

    room = kit.Interior(ASSET_ID if variant == SHIPPED
                        else f"{ASSET_ID}_{variant}",
                        half_width=half_width, depth=DEPTH,
                        ceiling_z=CEILING_Z)
    back_x = room.back_x

    # Stone underfoot. A forge floor takes dropped hot iron; board does not.
    room.floor(mat=room.stone)

    # SOOT, not limewash. An adversarial review of the first pass could not
    # tell this room from the bakery -- same white walls, same beams, same
    # shell -- and the cheapest thing that tells two rooms apart at 256px is
    # not a prop, it is the colour of the largest surface in the frame. Laura's
    # walls have not been re-limed in years and stand over a fire all day.
    room.back_wall(openings=[WINDOW], mat=room.plaster)

    side_openings = None
    if variant == "side_window":
        # Screen-RIGHT wall, high, over the customer half -- so the one cool
        # light in the room lands where a customer stands and the fire keeps
        # the working half to itself.
        side_openings = {-1: [(room.front_x + 1.8, room.front_x + 3.4,
                               2.05, 3.25)]}
    room.side_walls(openings=side_openings, mat=room.plaster)

    # Fewer, heavier beams than the Padaria's five: the same ceiling grammar
    # reading as a different roof.
    room.ceiling(beams=3)
    room.window(*WINDOW)
    # Timber, not the default stone: this floor IS stone, and a stone sill in a
    # stone floor is invisible. The threshold has to contrast with whatever it
    # is set into or it stops saying "this direction is passable".
    tab_x, tab_y = room.exit_threshold(EXIT_Y, mat=room.wood)

    # An undressed opening renders as a flat white lightbox -- at this size it
    # reads as a hole in the wall rather than as a window. The grille breaks it
    # into bars, which is also what a smith puts over a street-facing opening.
    furn.window_dressing(room, "window", *WINDOW)

    # The dado is domestic, and this is not a domestic room. One short stretch
    # only, beside the door, where a customer stands and waits.
    furn.azulejo_dado(room, height=1.0, y0=-half_width, y1=-2.1)

    # --- the fire (screen left) --------------------------------------------
    hearth_rise = 0.30 if variant == "platform" else 0.0
    if variant == "platform":
        room.platform("hearth", back_x - 1.75, back_x, HEARTH[0], HEARTH[1],
                      hearth_rise)
    with room.surface(hearth_rise):
        furn.forge(room, "forge", (back_x - 0.62, FORGE_Y), chimney_h=1.5)
        furn.bellows(room, "bellows", (back_x - 1.15, FORGE_Y + 1.05))

    # Staged forward and into the fire's throw, and built bigger than default.
    # An anvil on its stump is the one silhouette that says SMITH without any
    # other prop helping, and in the first pass it was small, far back and in
    # shadow -- so a reviewer could not tell this room from a bakery.
    furn.anvil(room, "anvil", (0.95, 1.15), horn_len=0.95, width=0.30,
               height=0.50, stump_h=0.56)
    furn.quench_tub(room, "quench", (2.35, 0.65))
    furn.ingot_stack(room, "ingots", (2.15, 3.45), rows=4, cols=3)

    # --- the two kinds of work ---------------------------------------------
    # Heavy work happens standing at the anvil; fine work happens sitting,
    # high, over a catch skin. Keeping them apart is what makes this Laura's
    # shop rather than a generic smithy.
    furn.fine_bench(room, "fine_bench", (3.05, -2.85))
    furn.grindstone(room, "grindstone", (0.95, -2.25))

    # --- the salvage business ----------------------------------------------
    furn.scrap_heap(room, "scrap", (3.55, -3.55))
    furn.weapon_rack(room, "rack", (back_x - 0.3, -0.85))
    furn.tool_rail(room, "tools", y=0.9, z=1.95)

    # The commission in progress: a shattered blade, laid on the anvil stump
    # side where it is somebody's specific property rather than stock.
    room.part("commission_blade", (0.05, 0.09, 0.74), (2.0, 1.05, 0.60),
              room.forge_scale, rotation=(0.0, 1.45, 0.15))
    room.part("commission_tag", (0.02, 0.09, 0.06), (1.98, 0.72, 0.62),
              room.cloth)

    # The lunch cloth, folded into a perfect square, on the bench she does not
    # do dirty work at. It is the one soft thing in the room.
    room.part("lunch_cloth", (0.24, 0.26, 0.05), (2.95, -2.35, 0.97),
              room.cloth)

    furn.lantern(room, "lantern", y=-2.6, z=2.05)
    # A second lamp over the rack: a wall of blades that renders as a black
    # ladder sells nothing. This is the light a customer is shown stock by.
    furn.lantern(room, "rack_lantern", y=-0.85, z=2.35, energy=17.0)

    # --- the one axis ------------------------------------------------------
    if variant == "side_window":
        room.side_window(-1, room.front_x + 1.8, room.front_x + 3.4,
                         2.05, 3.25)
    elif variant == "foreground":
        # A hanging post the player walks BEHIND on the way to the counter --
        # placed over the columns the character actually crosses, not against
        # the frame edge, and standing where the fire can reach it so it is a
        # lit near layer rather than a black bar.
        room.foreground("hanging_post", 1.05, span=(-0.30, -0.17),
                        z0=-0.4, z1=CEILING_Z)

    # --- light: the fire is the key, and it is the only key ----------------
    forge_x = back_x - 0.62
    room.light("light_forge", "POINT",
               (forge_x - 0.15, FORGE_Y, hearth_rise + 1.06),
               (-1.0, 0.0, -0.1), 62.0, (1.0, 0.46, 0.14), radius=0.26)
    # A second, weaker bounce low and forward: a forge lights the FLOOR in
    # front of it, and without that the fire reads as a lamp on a wall.
    room.light("light_forge_spill", "POINT",
               (forge_x - 1.5, FORGE_Y - 0.5, 0.55), (-1.0, -0.3, -0.4),
               18.0, (1.0, 0.42, 0.12), radius=0.4)
    room.window_light((WINDOW[0] + WINDOW[1]) / 2.0,
                      (WINDOW[2] + WINDOW[3]) / 2.0, energy=150.0)
    room.doorway_light(tab_x, tab_y)

    if variant == "side_window":
        room.side_window_light(-1, room.front_x + 2.6, 2.6, energy=200.0)
    elif variant == "foreground":
        # Give the near layer something to catch: a lamp hung on the post
        # itself, which is also the in-vocabulary answer -- the near layer is
        # lit by something the place contains, like everything else.
        room.light("light_post_lamp", "POINT",
                   (room.front_x - 0.95, -1.15, 2.35), (0.4, 0.2, -1.0),
                   11.0, (1.0, 0.72, 0.42), radius=0.14)

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
