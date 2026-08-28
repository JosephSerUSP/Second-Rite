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
instead of stopping at the character floor limit, and the near stack covers the
translucent status menu.

That stack is TWO layers, not one:

- **NEAR** (X = -9.5 .. -11.5) is the foreground's foreground. It occludes the
  foreground layer, parallaxes fastest in any flattened presentation, and by
  default does NOT touch the player.
- **FOREGROUND** (X = -6.5 .. -7.5) is the pass-behind layer, and it DOES
  occlude the player. Three pieces across a 29.48 lane, so each is a real
  occlusion event rather than a hedge.

Human-scale goods stay at the action plane and behind, inside `props()`, where
an object of known size reads at its true size and is excluded from the near
layer's measurements.

`--report` prints dock coverage per anchor, the widest near piece as a fraction
of the frame at its own depth, and which pieces cross the player's body rows --
because occluding the player is a legitimate choice that must be a choice.

**Always render this with a character in frame.** The near layer's scale cannot
be judged from those numbers: a 0.447 frame fraction says nothing about whether
a cart dwarfs a person, and two passes went wrong before a walker was staged.
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

    # The near stack has TWO layers, and they are different things.
    #
    # An object at X = -10 sits at depth 8.67 against the player's 18.67, so it
    # renders 2.15x magnified. That magnification is correct perspective, not a
    # bug -- but it decides what may stand there. A crate has a KNOWN real-world
    # size, so at 2x the eye reads it as wrong rather than as near; the first
    # pass filled the front rank with barrels and crates and the street came
    # back looking like giant furniture. Foliage, masonry, cloth and a roof edge
    # have no canonical size, so the same magnification reads as PROXIMITY.
    #
    #   NEAR (X = -9.5 .. -11.5)  the foreground's foreground. Architectural and
    #       organic only. It occludes the foreground layer and, in a flattened
    #       presentation, parallaxes fastest. It does NOT occlude the player:
    #       nothing here rises above the row-144 threshold for its depth.
    #   FOREGROUND (X = -6.5 .. -7.5)  the pass-behind layer. Sparse, and it
    #       DOES occlude the player -- that is the point of it.
    #
    # Human-scale goods live at the action plane and behind, where their size
    # reads true.

    # NEAR: no goods, nothing with a known size.
    #
    # The stone parapet that used to run here is gone. It overlapped the
    # planting in both depth and lane span, so the two shadowed each other and
    # the whole near rank rendered near black -- and the planting was always
    # what this rank wanted. A short kerb survives only at the west end, where
    # the ground steps down to the quay and something has to hold the edge.
    street.low_wall("NEAR_kerb_west", -2.0, 3.1, x=-10.6, height=0.5,
                    thick=0.42)
    # Planting, which is what this rank wanted all along. It is a SKIRT in the
    # house rule's terms -- wide, continuous, and low enough to hide the
    # characters' feet without swallowing them -- and it only became
    # expressible once `foliage` existed as a material and `blob()` as a
    # primitive that is not a cube. Runs are offset from the parapet's gaps so
    # the two never open a hole at the same lane position.
    # Heights are set so the top of the run rises just PAST the menu line and
    # clips the characters' feet. That is the endorsed skirt: it grounds the
    # character in the scene instead of leaving them standing on a clean line
    # above a decorative band. It stays a skirt and not a board because it
    # covers only the bottom fifth of the character.
    for index, (lo, hi, px, h) in enumerate(
            ((3.2, 10.4, -10.9, 0.98), (12.4, 20.2, -10.3, 1.06),
             (22.6, 30.4, -11.1, 0.92))):
        street.hedge("NEAR_hedge_%d" % index, lo, hi, x=px, height=h,
                     seed=index)
    # A roof edge overhanging the lens -- architecture with no readable size,
    # and the cheapest way to cap the frame without walling the street off.
    street.foreground("NEAR_eaves", 12.0, x=-11.2, size=(1.6, 9.0, 0.34),
                      z=-0.1, material_value=street.terracotta)

    # FOREGROUND: the pass-behind pieces. Three across a 29.48 lane, so each is
    # a real occlusion event rather than a hedge.
    # The nets were a single 1.63 x 1.49 m drape, which at this depth is
    # exactly the rejected shape -- tall AND continuous, a board that
    # swallows the whole character. Hung as separate narrow strips it
    # stays tall but stops being continuous, so the player reads through
    # the gaps between them.
    street.net_rack("FG_nets", 3.4, x=-7.4, height=2.4, width=2.0,
                    strips=3)
    # The palm this always wanted to be -- a real one. Tapered leaning trunk
    # and a crown of radiating serrated fronds, not a green ellipse. Bare
    # trunk through the character's rows (a POLE), crown above head height, so
    # the wide half of the silhouette never covers anyone.
    street.palm("FG_palm", 17.9, x=-7.0, trunk_height=2.9, fronds=10,
                frond_length=2.0, seed=4)
    street.foreground("FG_crane_davit", 25.2, x=-7.3, size=(0.28, 0.28, 3.2))
    street.foreground("FG_crane_arm", 24.6, x=-7.3, size=(0.24, 1.5, 0.24),
                      z=3.0, material_value=street.wood)

    # Goods, at and behind the action plane where a crate looks crate-sized.
    # Inside `props()` they are not registered as near layer, so they cannot
    # inflate the coverage number or hide a real gap in the band.
    with street.props():
        for index, (lane_y, px, tipped) in enumerate(
                ((2.4, -1.2, False), (11.1, 0.6, False), (20.6, -0.8, True),
                 (27.4, 1.1, False))):
            street.handcart("PROP_cart_%d" % index, lane_y, x=px,
                            tipped=tipped)
        for index, (lane_y, px, count) in enumerate(
                ((6.8, 2.4, 3), (13.6, 1.1, 2), (18.9, 3.0, 3),
                 (24.9, 1.8, 2))):
            street.stack("PROP_stack_%d" % index, lane_y, x=px, count=count,
                         unit=(0.62, 0.66, 0.46))
        for index, (lane_y, px) in enumerate(
                ((1.2, 1.9), (9.1, 3.4), (17.4, 2.2), (23.6, 3.1),
                 (29.0, 2.6))):
            street.barrel("PROP_barrel_%d" % index, lane_y, x=px, radius=0.34,
                          height=0.84)
        for index, (lane_y, px) in enumerate(
                ((4.9, 2.8), (15.2, 3.6), (26.2, 2.0))):
            street.sacks("PROP_sacks_%d" % index, lane_y, x=px, height=0.46)

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
        # Which near pieces cross the player's body rows. Occluding the
        # player is legitimate and sometimes the point, but it must be a
        # choice rather than a side effect of a height picked for the menu.
        extra["occludesPlayer"] = street.occludes_player()
        # Must be empty: an occluder may be tall or continuous, never both.
        extra["boards"] = street.boards()
    interior.report(street, blend, extra)


if __name__ == "__main__":
    main()
