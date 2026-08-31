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

from .recipe import (BalconySpec, BuildingRecipe, CanopySpec, Course, Opening,
                     PierSpec, RoofSection, StepSpec, Wing)


def _two_storey_courses():
    """The shared wall stack for the plan/roof intersection studies."""
    return (
        Course("plinth", 0.36, "rough_limestone"),
        Course("storey", 2.85, "whitewash",
               return_semantic="rough_limestone"),
        Course("band", 0.14, "old_limestone", inset=-0.06),
        Course("storey", 2.55, "whitewash",
               return_semantic="rough_limestone"),
        Course("cornice", 0.22, "rough_limestone", inset=-0.10),
    )


def _corner_pier():
    """The vertical order that turns horizontal courses into a façade frame."""
    return PierSpec(width=0.28, project=0.10, splay=0.10, through="storey")


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
                courses=courses, pier=_corner_pier())
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
        Opening(id="return_ground", kind="window", wing="main",
                lane_offset=2.35, width=0.95, height=1.35, sill_z=1.05,
                elevation="left", grille=True),
        Opening(id="return_upper", kind="window", wing="main",
                lane_offset=4.85, width=0.95, height=1.30, sill_z=4.0,
                elevation="left", shutters=True),
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


def l_plan_house():
    """An L boundary under two intersecting, fused gable sections."""
    courses = _two_storey_courses()
    front = Wing("front", 0.0, 8.0, 3.0, courses=courses,
                 pier=_corner_pier())
    return_wing = Wing("return", 2.5, 3.0, 4.0, setback=3.0,
                       courses=courses)
    return BuildingRecipe(
        id="l_plan_house", version=1,
        wings=(front, return_wing),
        outline=((0, -4), (3, -4), (3, 1), (7, 1), (7, 4), (0, 4)),
        # The front ridge is carried to the return's inside corner.  Without
        # this offset it sits at the front wing midpoint and the two roof runs
        # read as a broken ``I _`` rather than one continuous L.
        roof=(RoofSection("front", ridge_axis="Y", rise=1.45,
                          ridge_offset=1.5),
              RoofSection("return", ridge_axis="X", rise=1.25)),
        openings=(
            Opening("door", "door", "front", -1.8, 1.15, 2.3,
                    panels=4, drip=True),
            Opening("ground_window", "window", "front", 1.2, 1.0, 1.35,
                    sill_z=1.0, shutters=True),
            Opening("upper_left", "window", "front", -1.8, 0.95, 1.3,
                    sill_z=3.85, shutters=True),
            Opening("upper_right", "window", "front", 1.2, 0.95, 1.3,
                    sill_z=3.85, shutters=True,
                    balcony=BalconySpec(width=1.65, depth=0.72)),
            Opening("side_window", "window", "return", 5.0, 0.95, 1.3,
                    sill_z=1.05, elevation="right", shutters=True),
        ),
        metadata={"register": "plan-study", "shape": "L"},
    )


def t_plan_house():
    """A narrow stem meeting a broad rear cross-wing as one body."""
    courses = _two_storey_courses()
    stem = Wing("stem", 0.0, 3.0, 7.0, courses=courses,
                pier=_corner_pier())
    cross = Wing("cross", 0.0, 8.0, 3.0, setback=4.0, courses=courses)
    return BuildingRecipe(
        id="t_plan_house", version=1,
        wings=(stem, cross),
        outline=((0, -1.5), (4, -1.5), (4, -4), (7, -4),
                 (7, 4), (4, 4), (4, 1.5), (0, 1.5)),
        roof=(RoofSection("stem", ridge_axis="X", rise=1.55),
              RoofSection("cross", ridge_axis="Y", rise=1.35)),
        openings=(
            Opening("front_door", "door", "stem", -0.65, 1.0, 2.3,
                    panels=3, pediment=True),
            Opening("front_window", "window", "stem", 0.65, 0.85, 1.25,
                    sill_z=1.05, grille=True),
            Opening("upper_window", "window", "stem", 0.0, 0.9, 1.3,
                    sill_z=3.85, shutters=True,
                    balcony=BalconySpec(width=1.7, depth=0.78)),
            Opening("stem_side", "window", "stem", 2.2, 0.9, 1.25,
                    sill_z=1.05, elevation="left", grille=True),
        ),
        metadata={"register": "plan-study", "shape": "T"},
    )


def canopy_steps_house():
    """A compact house proving the opening-attached exterior vocabulary."""
    courses = _two_storey_courses()
    main = Wing("main", 0.0, 5.6, 5.2, courses=courses,
                pier=_corner_pier())
    return BuildingRecipe(
        id="canopy_steps_house", version=1,
        wings=(main,),
        outline=((0, -2.8), (5.2, -2.8), (5.2, 2.8), (0, 2.8)),
        roof=(RoofSection("main", profile="half_hip", ridge_axis="Y",
                          rise=1.35, hip_fraction=0.48),),
        openings=(
            Opening("canopied_door", "door", "main", -1.25, 1.2, 2.35,
                    lintel=True, drip=False, panels=4,
                    canopy=CanopySpec(depth=0.72, rise=0.20,
                                      thickness=0.09, margin=0.32),
                    steps=StepSpec(count=3, rise=0.14, run=0.30,
                                   margin=0.28)),
            Opening("ground_window", "window", "main", 1.2, 1.0, 1.35,
                    sill_z=1.0, grille=True),
            Opening("upper_left", "window", "main", -1.25, 0.9, 1.25,
                    sill_z=3.85, shutters=True),
            Opening("upper_right", "window", "main", 1.2, 0.9, 1.25,
                    sill_z=3.85, shutters=True,
                    balcony=BalconySpec(width=1.7, depth=0.76)),
            Opening("side_ground", "window", "main", 2.6, 1.0, 1.35,
                    sill_z=1.0, elevation="left", grille=True),
            Opening("side_upper", "window", "main", 3.9, 0.9, 1.25,
                    sill_z=3.85, elevation="right", shutters=True),
        ),
        metadata={"register": "detail-study",
                  "details": ["lean-to canopy", "three-step approach"]},
    )


REGISTRY = {
    "canopy_steps_house": canopy_steps_house,
    "l_plan_house": l_plan_house,
    "narrow_townhouse": narrow_townhouse,
    "t_plan_house": t_plan_house,
}
