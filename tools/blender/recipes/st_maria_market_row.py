"""Scaffold the St. Maria Market Row source scene -- the first MODELLED exterior.

Market Row is the street both authored 3D interiors open onto: Alicia's Padaria
(map 28) leaves by `padaria_3d_door` at lane 16.0 and Laura's Smithy (map 29) by
`smith_3d_door` at lane 26.5. Modelling this screen is what closes the loop, so
a player can walk out of a real room into a real street instead of onto a plate.

Every anchor below is read from the shipped map rather than retyped, so the
picture of a door cannot drift away from the doorway the provider tests.

    blender -b -noaudio --python tools/blender/recipes/st_maria_market_row.py

The `.blend` it writes is SOURCE AUTHORITY: it refuses to overwrite one that
already exists. After the first run, edit it in Blender.

## What makes this an exterior and not a wide room

The ground reaches the bottom of the frame (native row 240 at X = -12.01)
instead of stopping at the character floor limit, and a near band of parapet,
barrels, planting and two deliberate tall occluders covers the translucent
status menu. `--report` prints the measured dock coverage at every anchor, so
the near layer is a number rather than an opinion.

Three of the near pieces are TALL on purpose -- the awning post at lane 8.4, the
palm at 17.9 and the crane davit at 25.2. Those are the ones the player walks
BEHIND, which is what earns the screen a near layer at all; the low parapet
between them is only covering the menu.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

import exterior as ext  # noqa: E402
import interior  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
MAP = ROOT / "projects" / "hichaukitoden-game" / "data" / "maps" / "18.json"
DEFAULT_BLEND = (ROOT / "projects" / "hichaukitoden-game" / "assets"
                 / "authoring" / "environments" / "st_maria_market_row.blend")
ENVIRONMENT = (ROOT / "projects" / "hichaukitoden-game" / "assets"
               / "environments" / "st_maria_town" / "market" / "environment.json")


def lane_anchors():
    """Runtime lane positions, straight out of the shipped map package."""
    package = json.loads(ENVIRONMENT.read_text(encoding="utf-8"))
    return {name: float(value["position"][1])
            for name, value in package["anchors"].items()}


def lane_span():
    data = json.loads(MAP.read_text(encoding="utf-8"))
    return float(data["traversal"]["lane"]["maxY"])


def build(blend: Path, *, force: bool):
    span = lane_span()
    anchors = lane_anchors()
    street = ext.Exterior("st_maria_market_row", span, back_x=8.6, near_x=-9.2)

    # The street itself, stepping up at the east end where the back steps climb
    # to the Backstreet. The drawn apron agrees with the lane's own profile.
    street.ground(levels=((26.9, span, 0.45),))

    # -- far side: the commercial terrace ---------------------------------
    # Depth stagger, not height: rooflines are out of frame at this camera, so
    # a building that steps forward is the only silhouette variation available.
    street.facade("ARCH_warehouse", 2.6, width=6.4, height=5.6, depth=4.2,
                  x=8.9)
    street.facade("ARCH_customs", 8.0, width=5.0, height=5.2, x=8.2, dado=True)
    street.facade("ARCH_padaria", 16.6, width=6.8, height=5.0, x=8.0,
                  dado=True)
    street.facade("ARCH_smithy", 20.4, width=5.2, height=5.4, depth=3.8,
                  x=8.8)
    street.facade("ARCH_scholar_house", 24.4, width=5.6, height=5.8, x=8.4)
    street.facade("ARCH_east_block", 28.6, width=5.0, height=6.0, depth=4.0,
                  x=9.2)

    # -- the doors the provider actually tests ----------------------------
    street.doorway("DOOR_padaria_3d", anchors["padaria_3d_door"], x=8.0,
                   width=1.25, lamp=True)
    street.doorway("DOOR_smith_3d", anchors["smith_3d_door"], x=8.4,
                   width=1.25, lamp=True)
    street.doorway("DOOR_padaria_plate", anchors["padaria_door"], x=8.0)
    street.doorway("DOOR_smith_plate", anchors["smith_door"], x=8.8)

    # Windows carry the terrace rhythm between the doors.
    for index, lane_y in enumerate((4.4, 10.6, 14.2, 18.4, 23.2, 27.4)):
        street.window("WIN_terrace_%d" % index, lane_y, x=8.2,
                      grille=(index % 2 == 0), lit=(index == 3))

    # The way out at each end. West is an edge exit to the Quay; east climbs.
    street.doorway("DOOR_west_quay", anchors["west_quay"] + 0.4, x=8.9,
                   width=1.9, height=2.9, lintel=True)
    for step in range(4):
        street.part("ARCH_back_steps_%d" % step, (2.6, 0.62, 0.16 * (step + 1)),
                    (6.4, street.y(anchors["back_steps"] - 0.9 + step * 0.62),
                     0.08 * (step + 1)), street.stone)

    # -- mid ground: what Market Row is named for -------------------------
    for index, lane_y in enumerate((anchors["npc_auctioneer"] + 0.9,
                                    anchors["npc_yukio"] - 0.8,
                                    12.1, anchors["npc_scholar"] + 1.1)):
        street.stall("PROP_stall_%d" % index, lane_y,
                     width=2.4 if index % 2 == 0 else 1.9,
                     canopy=(index != 2))
    for index, lane_y in enumerate((7.2, 15.4, 21.9)):
        street.awning("PROP_awning_%d" % index, lane_y, x=8.2,
                      width=2.8 if index == 1 else 2.2)

    # -- near band: what covers the translucent menu ----------------------
    # This was a continuous parapet plus kerb, which measured 0.906 coverage at
    # every anchor and rendered as one poured masonry wall across the bottom
    # 45% of the frame. Coverage is not the goal -- it is a floor. What the
    # menu band wants is a working street seen close up, so the band is now
    # goods and vehicles at varied depth, and the number is allowed to be lower
    # and UNEVEN. A street that covers the menu identically at every lane
    # position is a street with nothing happening in it.
    #
    # Depths are staggered between X = -8.2 and X = -11.6. Nothing here is
    # tall enough to hide a walker standing on row 128: at X = -9.2 an object
    # reaches the top of the menu band at 0.82 m, which is knee height.

    # The band is DEPTH-GRADED, and that is the whole lesson of the first two
    # attempts. The frame narrows fast toward the lens -- half-width is 4.67 m
    # at the action plane, 2.67 m at X = -8 and 1.92 m at X = -11 -- so an
    # object's readable size is set by where it stands, not by what it is. A
    # 2.1 m handcart at X = -11 fills half the screen; the same cart at X = -7
    # reads as a cart. Meanwhile the height NEEDED to cover the menu band
    # falls the other way (1.09 m at X = -11, 0.64 m at X = -8), so the very
    # front of the band can be low and still do its job.
    #
    #   X = -6.5 .. -7.5   the tall few: nets, awning post, palm, davit
    #   X = -8.0 .. -9.0   carts and stacks -- mid-size, open silhouettes
    #   X = -9.5 .. -11.4  low goods only: barrels, sacks, small crates

    # Tall pieces, each a real pass-behind event. Sparse on purpose -- a street
    # full of these is a hedge, not a foreground.
    street.net_rack("FG_nets", 3.4, x=-7.4, height=2.4, width=1.9)
    street.foreground("FG_awning_post", 8.4, x=-7.2, size=(0.3, 0.3, 3.0))
    street.foreground("FG_awning_post_cloth", 8.9, x=-7.2,
                      size=(1.5, 1.7, 0.12), z=2.78,
                      material_value=street.cloth)
    street.planter("FG_palm", 17.9, x=-7.0, height=0.9, spread=1.5)
    street.foreground("FG_crane_davit", 25.2, x=-7.3, size=(0.28, 0.28, 3.2))
    street.foreground("FG_crane_arm", 24.6, x=-7.3, size=(0.24, 1.5, 0.24),
                      z=3.0, material_value=street.wood)

    # Carts are the band's workhorse: tall enough for the menu, open enough to
    # see the street through. Held at X = -8.0..-8.8 so they read as carts.
    for index, (lane_y, px, tipped) in enumerate(
            ((1.9, -8.4, False), (10.6, -8.0, False), (15.1, -8.8, True),
             (21.4, -8.2, False), (28.2, -8.6, False))):
        street.handcart("FG_cart_%d" % index, lane_y, x=px, tipped=tipped)

    for index, (lane_y, px, count) in enumerate(
            ((5.1, -8.7, 3), (12.8, -8.3, 2), (18.6, -8.9, 3),
             (24.1, -8.1, 3), (26.9, -8.8, 2))):
        street.stack("FG_stack_%d" % index, lane_y, x=px, count=count,
                     unit=(0.6, 0.64, 0.44))

    # The front rank: low goods only. Nothing here is over 1.0 m, which is all
    # the menu band asks for at this depth and all the frame can hold.
    for index, (lane_y, px) in enumerate(
            ((0.6, -9.8), (7.3, -10.6), (13.9, -9.6), (20.2, -10.9),
             (23.2, -9.9), (29.1, -10.4))):
        street.barrel("FG_barrel_%d" % index, lane_y, x=px, radius=0.34,
                      height=0.84)
    for index, (lane_y, px) in enumerate(
            ((4.2, -10.2), (11.8, -11.2), (17.1, -10.1), (27.6, -11.0))):
        street.sacks("FG_sacks_%d" % index, lane_y, x=px, height=0.44)
    for index, (lane_y, px, size) in enumerate(
            ((3.1, -11.1, (0.56, 0.6, 0.46)), (9.4, -10.0, (0.5, 0.72, 0.4)),
             (16.4, -11.3, (0.6, 0.6, 0.5)), (22.6, -11.1, (0.52, 0.56, 0.42)),
             (30.0, -10.7, (0.58, 0.62, 0.48)))):
        street.crate("FG_crate_%d" % index, lane_y, x=px, size=size)
    for index, (lane_y, px) in enumerate(
            ((6.4, -9.7), (14.6, -10.8), (22.0, -9.9))):
        street.planter("FG_planter_%d" % index, lane_y, x=px, height=0.5,
                       spread=0.6, clumps=3)

    street.sky_rig()
    return street, anchors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_BLEND)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--report", action="store_true",
                        help="print measured dock coverage at every anchor")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)

    street, anchors = build(args.output.resolve(), force=args.force)
    blend = interior.save_source_blend(args.output.resolve(), force=args.force)

    extra = {"span": street.span, "frontX": round(street.front_x, 4),
             "anchors": {k: round(v, 4) for k, v in sorted(anchors.items())}}
    if args.report:
        extra["dockCoverage"] = {
            name: round(street.dock_coverage(lane_y), 3)
            for name, lane_y in sorted(anchors.items())
        }
        extra["dockCoverHeightAtNearX"] = round(
            ext.dock_cover_height(street.near_x, street.record), 3)
        # The widest near pieces, as a fraction of the frame at their own
        # depth. Anything over ~0.45 is eating the screen, which the coverage
        # number alone will happily reward.
        extra["widestForeground"] = street.foreground_scale()[:6]
    interior.report(street, blend, extra)


if __name__ == "__main__":
    main()
