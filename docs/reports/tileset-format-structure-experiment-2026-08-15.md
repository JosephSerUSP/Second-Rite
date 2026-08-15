# Tileset format experiment — structural geometry / junctions

Status: **experimental branch evidence for #558; not canonical design.**

Baseline: `main@fcdc4ea8fadd9fd38dc1f6e35c9b024d1a862a40`.

## Question

How should Thestra express visually richer wall/floor/ceiling shape without turning presentation geometry into a second collision or Map-topology authority?

The motivating case is a wall family whose corners are visibly chamfered or rounded rather than every logical wall cell producing an axis-aligned rectangular face.

## Current facts

- Logical Map topology remains the compact grid and owns gameplay collision/traversal.
- Current image-authored `plane` geometry displaces a rectangular wall/floor/ceiling surface along its normal.
- A wall height field can therefore create relief, recesses and sculpted face detail, but it does not change the top-down structural junction formed where two exposed wall faces meet.
- The renderer resolves exposed wall faces individually; a face may remain a quad or be replaced/augmented by a mesh source.
- The plane compiler already treats seams/perimeters as serious geometry constraints and seals displaced atlas surfaces back into the logical solid volume.
- Existing `geometry` and OBJ paths prove that authored non-quad geometry is a supported presentation representation, but they do not yet define a reusable junction grammar for ordinary wall cells.

## Structural shape is distinct from surface relief

Keep these concepts separate during the experiment:

```text
logical Map topology
    -> structural profile / junction geometry
        -> surface/material
            -> relief / height field
                -> fixtures / overlays
```

A rounded outside corner is a structural-profile concern. A carved stone face is a surface-relief concern. A torch bracket is a fixture concern.

Combining all three into one generic `geometry` escape hatch is expressive but may make reuse and authoring unnecessarily expensive.

## Candidate A — procedural structural profiles

Test a compact, renderer-owned profile vocabulary for presentation-only wall shaping.

Conceptual data only:

```json
{
  "corner": "round",
  "radius": 0.12,
  "segments": 3
}
```

Candidate profile families to prototype:

- square/default;
- one-cut chamfer;
- low-segment round (2–4 segments);
- wall end/cap;
- inside-corner treatment where needed.

Important invariants:

- geometry remains inside the logical solid footprint for presentation-only profiles;
- collision remains the original grid cell;
- UV/material continuity is deterministic;
- profiles compose with height relief rather than silently disabling it;
- corners do not introduce cracks against floors/ceilings or adjacent straight walls;
- deterministic geometry does not depend on camera direction.

A three-segment round is especially worth testing because it may read as intentional low-poly PS1 architecture rather than a failed smooth curve.

## Candidate B — authored junction meshes

Allow a visual family to provide explicit geometry for adjacency cases such as:

- straight segment;
- exposed end/cap;
- outside corner;
- inside corner;
- T junction;
- cross junction.

Questions:

- How many pieces are actually needed once hidden/non-exposed faces are removed?
- Can orientation/mirroring reduce asset count without creating UV/material surprises?
- Can a junction mesh reference the same Surface material as ordinary walls?
- Does this create a combinatorial kit-authoring burden disproportionate to the visual gain?
- How are height-field relief or material layers applied consistently across a custom junction mesh?

## Candidate C — synthesis

Procedural profiles may cover regular architectural treatments (bevel/round) while authored meshes override exceptional junctions.

If this wins, precedence must be explicit:

```text
custom junction mesh if supplied
else palette/profile-generated junction
else square structural default
```

Do not permit an ambiguous mixture where a profile sometimes modifies an authored mesh and sometimes replaces it.

## Geometry/collision truthfulness

For presentation-only profiles, prefer:

```text
visual geometry ⊆ logical solid cell footprint
```

A bevel/round that removes material from a wall corner is safe: collision may be slightly more conservative than the visible surface but never permits walking through visible solid matter.

A profile that protrudes substantially into the walkable cell is more questionable and should be measured visually. A proposal that changes where the player can actually move is no longer merely a tileset-format experiment and belongs in a separate Map-topology investigation.

## Relationship to height fields

The current plane topology should remain valuable after richer structural profiles land.

Questions to test:

- Can a height field be evaluated over each generated profile face?
- For a rounded/chamfered corner, does relief wrap around the junction or restart per segment?
- Is a surface-space parameterization needed so one semantic wall material remains continuous across generated segments?
- Does the current `middle`/left-edge/right-edge atlas-composite convention become obsolete once structural junctions are geometry rather than painted half-tile overlays?

This is an important format smell: current wall edge data contains atlas packing coordinates and 32px half-cell offsets. A structural profile system should test whether junction identity can become semantic while atlas slicing is pushed into source resolution/compatibility.

## Nasty-room structure fixture

The branch should eventually render one neutral room containing, side by side:

1. square outside corner;
2. one-cut chamfer;
3. 3-segment rounded outside corner;
4. inside corner;
5. exposed wall end/cap;
6. doorway/opening meeting each profile where sensible;
7. height relief on at least square + rounded/chamfered variants;
8. one geometry-backed exceptional wall/junction;
9. one OBJ fixture attached near a shaped corner;
10. floor/ceiling junctions with no visible cracks;
11. unchanged logical collision for all presentation-only profile cases.

## Evaluation

Record:

- triangle counts;
- build/cache cost;
- number of authored assets needed;
- number of orientation cases;
- UV/material seams;
- floor/ceiling/wall cracks;
- how height relief behaves across profile segments;
- how easily a palette can reuse the same profile with another Surface;
- whether the profile is legible in Renderable Bundle provenance;
- whether Blender/export receives ordinary resolved triangles/materials without learning new topology rules.

## First hypothesis

Procedural low-segment profiles are likely a good fit for **regular structural style** while authored geometry remains the escape hatch for exceptional architecture.

The important architecture to prove is that structural profile and material/surface are independent:

```text
soft-round wall profile + wet stone Surface
soft-round wall profile + painted plaster Surface
square wall profile     + wet stone Surface
```

If that composition is awkward, the candidate format is not decomposed cleanly enough.

## Next spike

Implement the smallest renderer-side experiment that generates square, chamfered and three-segment rounded outside corners from the same logical wall layout and same material source, with collision unchanged. Compare that against one authored outside-corner mesh using the same Surface/material. Do not broaden into ramps, freeform collision, or general constructive geometry.
