"""Recipes composed from the grammar.

Each entry is a function returning a :class:`BuildingRecipe` and nothing else:
no vertex tables, no topology, no Blender. If a building here needs something
the grammar cannot say, the grammar is missing an operation and the operation
is what gets added -- a raw vertex dump in this file would be the block
prototype coming back in a different costume.

The first entry is deliberately alone. Six typologies judged at once is six
chances to converge on one silhouette before anyone has looked, which is how
PRs #941 and #942 arrived at the same room; the remaining registers are added
after the owner has read this one.
"""

from __future__ import annotations

from .recipe import BuildingRecipe, Course, Opening, RoofSection, Wing


def narrow_townhouse():
    """Three storeys on a four-metre frontage, gable to the street.

    The narrow townhouse is the register the Praça's terrace does not have.
    Everything already authored there is wide, low and ridge-parallel, so the
    axis this building moves is the one the camera can actually see: it is
    narrow enough that its two neighbours read as separate buildings, and its
    ridge runs INTO depth so the street gets a gable end rather than a slope.

    Its height is not a mistake. At the terrace line an 8.95 m front leaves the
    frame well above the roofline, which the exterior doctrine takes as given --
    height differences are invisible at this camera and depth differences are
    not. What the height buys is the storey banding: three string courses
    stacked in the visible band below scanline 144 are what make this read as
    tall rather than as a wide house cropped.
    """
    courses = (
        # Rough limestone to the water table, because the street is washed and
        # whitewash does not survive at ankle height.
        Course("plinth", 0.35, "rough_limestone"),
        Course("storey", 3.00, "whitewash", return_semantic="rough_limestone"),
        # The string courses project rather than recess: a projecting rail
        # catches the sky fill and draws a bright line, and a bright line is
        # the only storey marker that survives at native resolution.
        Course("band", 0.14, "rough_limestone", inset=-0.05),
        Course("storey", 2.70, "whitewash", return_semantic="rough_limestone"),
        Course("band", 0.14, "rough_limestone", inset=-0.05),
        Course("storey", 2.40, "whitewash", return_semantic="rough_limestone"),
        Course("cornice", 0.22, "rough_limestone", inset=-0.09),
        # The cap follows the roof, not this height -- the body builder reads
        # the rise off the roof section. The number here only has to be legal.
        Course("gable_cap", 1.80, "whitewash", return_semantic="whitewash"),
    )
    wing = Wing(id="main", lane_offset=0.0, width=4.20, depth=7.00,
                courses=courses)
    roof = RoofSection(wing="main", profile="gable", ridge_axis="X",
                       rise=1.80, overhang=0.32, thickness=0.18)
    openings = (
        Opening(id="front_door", kind="door", wing="main", lane_offset=-1.05,
                width=1.15, height=2.40, profile="plain", panels=4,
                drip=True, reveal=0.18),
        Opening(id="ground_window", kind="window", wing="main",
                lane_offset=1.10, width=1.00, height=1.45, sill_z=1.05,
                grille=True, shutters=False),
        Opening(id="first_left", kind="window", wing="main",
                lane_offset=-1.05, width=0.95, height=1.40, sill_z=4.00,
                shutters=True),
        Opening(id="first_right", kind="window", wing="main",
                lane_offset=1.05, width=0.95, height=1.40, sill_z=4.00,
                shutters=True),
        Opening(id="second_left", kind="window", wing="main",
                lane_offset=-1.05, width=0.90, height=1.25, sill_z=6.90,
                shutters=True),
        Opening(id="second_right", kind="window", wing="main",
                lane_offset=1.05, width=0.90, height=1.25, sill_z=6.90,
                shutters=True),
    )
    return BuildingRecipe(
        id="narrow_townhouse", version=1,
        wings=(wing,), roof=(roof,), openings=openings,
        # The façade is symmetric about the lane centre and the door is not.
        # Baking Y rather than mirroring it is the declaration that the
        # asymmetry is the design, so the symmetry test reads it as intent.
        baked_axes=("Y",),
        metadata={"register": "townhouse",
                  "note": "first novel typology; owner read pending"},
    )


REGISTRY = {"narrow_townhouse": narrow_townhouse}
