# Surface junctions

**Intent, not status.** This document defines how two adjacent displaced surfaces
should meet. What exists is in `docs/ENGINE-STATE.md`; reviewed engine behavior
belongs in `docs/SPEC.md`.

The design is written against the planned Z-axis work
(`renderer-3d-roadmap.md` §8.3, multi-height rooms) so junction machinery is
built once rather than specialized for flat maps and rebuilt for elevation.

## The problem, measured

A 03.08.2026 diagnostic render of a cobble floor at
`heightMapScale.floor = 0.1` counted pixels no geometry covered:

- 589 pixels of pure `(0,0,0)` against a drawn background of `(58,58,58)`;
- the floor's outer perimeter plus two horizontal bands across it;
- a watertight floor mesh with no interior boundary edges, locating the holes
  between meshes rather than inside one mesh.

That point-in-time measurement is evidence for the design problem, not a claim
about later renderer state.

Three symptoms share one cause:

1. **Cell-to-cell cracks.** Two adjacent floor cells may sample the same field at
   `v = 1` and `v = 0`. On a tileable map those are neighbouring texels rather
   than guaranteed-identical texels, so independently authored edge heights can
   disagree.
2. **The wall-foot void.** A flat wall foot and a signed displaced floor can
   leave the floor below the wall boundary.
3. **Corner pinholes.** Pairwise edge agreement is insufficient where four
   cells meet; the shared corner needs one resolution rule.

The common cause is architectural: **the tile is the unit of authorship, while
the junction between tiles is implicit.** Tiles should not line up merely because
their independently sampled borders happen to agree.

The 03.08.2026 investigation also ruled out decimation as the root cause: mirrored
tiles reduced equivalent seams identically, and reducing both borders of one mesh
in lockstep cannot make two independently authored surfaces agree. Treat this as
diagnostic history, not a statement about which tests or optimizers exist later.

## Why this must be designed against elevation

With one floor plane, a junction is easy to mistake for a rendering detail and
special-case with a clamped rim or fixed apron. Both approaches assume the edge
height is a constant known without considering the surfaces on both sides.

With multi-height rooms it is not constant. A floor's rim height becomes a
property of the boundary — which two cells meet there and what elevation each
carries. The design that survives elevation resolves a junction from declared
data on both sides.

The wall-foot void is the degenerate case of an elevation step. A floor 0.02
below its wall and a floor one whole cell below its neighbour are the same
geometry problem at different scales.

## Design

### Rule 1 — sample the field periodically

A tiling surface must sample `v ∈ [0,1)` and reuse the `v = 0` sample for the
vertex at `v = 1`. Both ends must not be allowed to derive unrelated boundary
heights from neighbouring texels.

This rule is required regardless of later junction work and closes every
junction where both sides share a material and elevation. A regression fixture
for this rule should use a deliberately non-symmetric height map so first/last
columns cannot pass by coincidence.

### Rule 2 — every surface declares a rim height, and mismatches get a riser

Each surface edge carries a declared **rim height**: the height of the surface at
that boundary, in world units, independent of its interior relief.

- Where two rims agree, the surfaces join directly. Interior relief is
  untouched, and relief crosses the boundary exactly as authored.
- Where they disagree — different material, different elevation, or a flat wall
  foot against a displaced floor — the junction emits a **riser**: a band of
  geometry spanning from one rim to the other.

A riser is not a patch. It is the step between two floors at different
elevations, the plinth under a wall, and the closure over a rim mismatch, all as
one construct. It is what a stair, kerb, and ledge are made of.

A fixed wall-only skirt such as a `plane.SKIRT` constant is only a provisional
approximation of this rule: it has no knowledge of the two surfaces it joins and
must not grow into a second junction system. Once rim/riser resolution owns the
boundary, fixed skirts should not coexist with it.

### Rule 3 — corners are resolved once, for all four cells

A corner is shared by up to four cells and two boundaries. It must be resolved as
a corner, not as the incidental endpoint of two independent edges.

The corner's height is a pure function of the four cells' rim heights. Where they
are not all equal, the corner takes the **lowest**, and each cell above it
contributes a riser down to it. Lowest rather than an average because a corner
above any floor is a hole, while a corner below all participating surfaces is
hidden.

Wall runs meeting at a right angle use the same corner ownership rule; two
independently resolved surfaces must not be allowed to invent different geometry
for their shared corner.

### Rule 4 — resolution is local and needs no neighbour mesh query

A cell must compute a shared junction **without reading its neighbour's compiled
mesh**. Resolution is a pure function of both cells' *declared* data — elevation,
material, rim height — evaluated identically on both sides.

This constraint keeps compilation order-independent and caching tractable. If a
cell had to inspect its neighbour's mesh, one edit could invalidate a spreading
region of compiled geometry and two cells compiled at different times could
disagree. A pure function of declared data lets both sides reach the same answer
independently.

## Cost constraints

**Cache pressure.** A junction-aware cache key necessarily carries more context
than a surface-only key. Keep the *interior* context-free and put variable
boundary geometry in risers, which are small and keyed by the rim-height pair
and other boundary identity they bridge.

**Rejected alternative.** A canonical rim could force every surface's
displacement to zero at its edges. That caches perfectly and closes all three
measured symptoms, but it flattens relief at every cell boundary and breaks
relief deliberately crossing a seam. It remains a fallback only if contextual
riser complexity proves unjustified.

**Triangle cost.** Risers exist only where boundary conditions disagree, so a
uniform room should not pay per-cell riser geometry.

## How elevation drops in

Elevation adds a per-cell floor and ceiling elevation, and the same rules absorb
it:

- a cell's rim height becomes `elevation + relief at the rim`;
- a step between rooms is a riser whose rim heights differ by the elevation
  change;
- walls span `floorElevation..ceilingElevation` for their cell;
- corners resolve by Rule 3 unchanged.

Autotiling and x+y seamless walls are the same ownership idea applied to texture
selection: boundary presentation should be keyed by a named junction identity,
not chosen independently by two cells. The geometry design should therefore make
the junction a first-class identity an autotiler can consume.

## Sequencing constraints

Implementation order matters because later rules depend on earlier invariants:

1. Establish periodic boundary sampling with a non-symmetric regression fixture.
2. Establish rim-height data and diagnostics before emitting variable boundary
   geometry.
3. Add risers before corner resolution, so corner behavior is validated against
   closed edges.
4. Add elevation only after flat-map junctions close through the same rules.

This is dependency ordering, not a delivery-status checklist. Reversing it would
make unresolved flat-map junction artifacts load-bearing in the elevation model.

## Open questions

- Where should rim heights live — derived from height-map edge rows, or declared
  in tileset data? Derived means less authoring; declared is validator-checkable
  and cannot drift when art is regenerated.
- Should a riser inherit the albedo of the higher surface, the lower one, or
  carry its own material? A step between two materials has a visible answer and
  the wrong one will read as a bug.
- Does the raycaster path need the same junction abstraction, or only the
  polygonal path? The design should answer from shared boundary semantics rather
  than duplicating special cases by renderer.
