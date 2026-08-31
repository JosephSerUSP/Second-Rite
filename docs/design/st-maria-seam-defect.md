# The St. Maria middle-seam defect

This is the one topology defect in the owner-authored `st_maria_praca.blend`
that the house grammar is allowed to repair rather than reproduce. It is
written down here **before** the normalizer exists, because a repair authored
against the three source houses and tuned until their diff goes green is not a
repair — it is a fudge factor with a test suite. Everything below was measured
from the file; nothing was inferred from what would be convenient to fix.

## What it looks like

A mirrored building has a seam: the edge loop lying on the Mirror modifier's
plane, which Blender welds to its reflection when a vertex is within
`merge_threshold` (0.001 here). A vertex a few centimetres off that plane is
**not** welded. It is duplicated across it, and the two copies open a notch on
the seam — small, symmetric, and easy to miss, because the vertex looks
perfectly reasonable on its own. It is only wrong relative to its neighbours.

Two instances exist in the file. Both are a single vertex, both are displaced
by the same 0.07 m, and both carry the same vertex index — the two houses share
a topology lineage, so this is one editing accident propagated by duplication,
not two independent slips.

| Object | Axis | Seam sits at | Defective vertex | Offset |
|---|---|---|---|---|
| `ARCH_west_house` | X | 16.0 | v36 at 15.93 | −0.07 |
| `ARCH_west_house.006` | Y | 115.00169 | v36 at 114.93169 | −0.07 |

## Why the seam is not the mirror plane

`ARCH_west_house.006` has **no vertex at all** on its nominal mirror plane
(Y = 115.0). Its entire seam loop sits at 115.00169 — a uniform 1.7 mm drift of
the whole object relative to its own modifier. The same object is 20.7 mm off
in X.

That drift is *not* the defect. Every vertex in the loop shares it, so the seam
is still a flat, coherent edge loop and the mirror still welds it to itself;
what it costs is a hairline of asymmetry against the world grid, which is a
placement question and the owner's to make. If the predicate keyed on the
nominal plane it would flag all nine of those vertices as broken and "repair"
the building by dragging its seam 1.7 mm sideways.

So the seam is defined as **the coordinate the cohort actually agrees on**, not
the coordinate the modifier nominates. Under that definition both instances
reduce to the same statement, and the drift disappears from view.

## The predicate

For each mesh, for each axis `a` enabled on a Mirror modifier:

1. **Cohort.** `C` = every vertex whose `a` coordinate lies within
   `COHORT_BAND = 0.25` of the modifier's plane. A vertex further out belongs to
   the body of the building, not to its seam.
2. **Seam coordinate.** `s` = the modal `a` coordinate within `C`, compared at
   the weld tolerance `1e-3`. The seam must be a real edge loop, so require at
   least `MIN_COHORT = 3` vertices sitting at `s`; a cohort that cannot agree on
   one coordinate has no seam and is skipped.
3. **Defective vertex.** `v ∈ C` is defective when all of:
   - `|a(v) − s| > 1e-3` — it is off the seam at all;
   - `|a(v) − s| ≤ MAX_PULL = 0.10` — it is off by a *slip*, not by a design
     decision. A bay window, a set-back or a buttress is metres from the seam,
     and no repair may ever move one;
   - it has at least one edge-neighbour sitting exactly at `s` — the vertex is
     part of the seam loop and has been dragged out of it, rather than being
     a legitimate interior vertex that merely happens to be nearby;
   - the defective vertices are a strict minority: `|defective| ≤ 25%` of `C`.
     Note this is not the same as "most of the loop is off `s`" -- because `s`
     is the mode, the majority always *is* the seam. What this clause actually
     catches is a cohort that fragments: half agreeing and the rest scattered
     across two or three other coordinates. There is no coordinate the scatter
     can honestly be pulled towards, so nothing is.
4. **Repair.** Set `a(v) = s`. That axis, that vertex, nothing else. No
   neighbour moves, no face is retriangulated, no other axis is touched.

## What must NOT be repaired

The normalizer is required to refuse each of these, and the tests assert the
refusal rather than the repair. These are the negative controls; without them
a normalizer that repairs everything passes every positive test.

- **A uniformly drifted seam.** Every vertex of the loop off the nominal plane
  by the same amount. This is `ARCH_west_house.006`'s real state and it must
  come back untouched.
- **A far vertex.** A vertex 0.5 m off the seam with a neighbour on it. That is
  a step in the building, not a slip.
- **A vertex with no seam neighbour.** An interior vertex that happens to sit
  within the cohort band. It is not part of the loop.
- **A fragmented cohort.** A loop that splits three ways rather than agreeing
  on one coordinate with a single outlier. There is no "correct" coordinate to
  pull the scatter to, and guessing one is how a repair silently reshapes a
  building.
- **Any axis without a Mirror modifier.** No modifier, no seam.

## Standing

Production recipes emit corrected topology only — the grammar never reproduces
this notch. The normalizer exists solely so that conformance against the
authored `.blend` can be run at all: it lets the comparison say "identical
except for the documented defect" instead of failing on a difference both
sides already agree is wrong.

Any topology difference that this predicate does not name remains a hard
conformance failure.
