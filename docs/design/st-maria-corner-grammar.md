# What the St. Maria houses actually do at a corner

Measured from `ARCH_west_house` and `ARCH_west_house.001` in
`st_maria_praca.blend`. Written before the sweep builder exists, for the same
reason `st-maria-seam-defect.md` was: a builder authored against the houses and
tuned until the diff goes green is a fudge factor with a test suite.

The first body builder was a rectilinear cell complex. It was wrong in a way no
amount of tuning reaches: **nine of the twenty-nine faces in an authored house
body are not axis-aligned**, and an axis-aligned grid cannot emit one of them.
The same decision produced 466 faces where the authored house has 29, because a
grid emits one quad per cell face and never merges coplanar neighbours. Both
complaints are that one representation choice.

## The numbers

| | `ARCH_west_house` | first cell-complex build |
|---|---|---|
| body vertices | 42 | 468 |
| body faces | 29 (all quads) | 466 |
| slanted faces | 9 | 0 |

Both authored houses mirror on **X and Y**, so the modelled quadrant is
`x in [-2.1, 0]`, `y in [0, 5.1]`, and the plan below is one quadrant.

## The plan outline

Wall planes sit at `x = -2.0` and `y = 5.0`. The convex corner between them is
not a corner: it is a **pier**, projecting 0.1 m proud of both wall planes, 0.2 m
wide along each wall, joined to the wall by a 45 degree splay of 0.1 m.

Walking the outline from the street wall around into the return:

    (0.0, 5.0) -> (-1.8, 5.0)   wall plane
    (-1.8, 5.0) -> (-1.9, 5.1)  45 degree splay OUT
    (-1.9, 5.1) -> (-2.1, 5.1)  pier face, along y
    (-2.1, 5.1) -> (-2.1, 4.9)  pier face, along x
    (-2.1, 4.9) -> (-2.0, 4.8)  45 degree splay IN
    (-2.0, 4.8) -> (-2.0, 0.0)  wall plane

The splay is what carries the masonry read. A square return in its place is the
difference between a building and a box, and it costs two faces per corner.

## The course stack

Read off the z bands of `ARCH_west_house`:

| band | z | outline | semantic |
|---|---|---|---|
| plinth | 0.0 .. 1.5 | wall + pier | `rough_limestone` |
| main wall | 1.5 .. 4.6 | wall + pier | `rough_limestone` |
| eave splay | 4.6 .. 4.7 | wall -> wall + 0.1, rising 0.1 | `rough_limestone` |
| cornice | 4.7 .. 5.0 | wall + 0.1, continuous | `rough_limestone` |
| gable | 5.0 .. 7.0 | wall, raking to apex | `whitewash` |

Two things follow that the cell complex got wrong on principle:

* **A course transition is a splay, not a step.** Where a course changes its
  inset by `d`, the transition is a 45 degree band of height `d` -- not a
  horizontal shelf meeting a vertical face. The eave faces carry normals
  `(-0.707, 0, -0.707)` and `(0, 0.707, -0.707)`, and the mitre where two splays
  meet carries `(-0.577, -0.577, 0.577)`.
* **The pier does not run the full height.** It stops at the eave (4.6); above
  it the cornice is a continuous band at the full 0.1 projection. So the pier is
  a property of a *range of courses*, not of the building.

The gable repeats the same vocabulary raking: its own splay runs parallel to the
roof pitch (faces with normals `(0.544, 0.577, -0.61)` and
`(-0.658, -0.329, 0.677)`).

## What the builder must therefore be

A **sweep**, not a grid: a plan outline crossed with a course stack, emitting one
quad per (plan edge x band). That is `edges x bands` faces by construction --
about 30 for this house -- with coplanar merging along the wall for free,
because a wall is one edge rather than a row of cells.

Openings remain the one place a wall panel is subdivided, and they subdivide
only the panel they pierce.
