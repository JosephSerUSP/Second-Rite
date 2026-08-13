# Raycaster Tileset, Doors, and Vertex Lighting — Design

> **Intent, not status.** This document records durable visual and authoring
> constraints that originated in the first-person raycaster work. For what the
> engine exposes, read [`docs/ENGINE-STATE.md`](../ENGINE-STATE.md); for reviewed
> renderer behavior, read `docs/SPEC.md`. Renderer implementation may evolve
> without invalidating the design constraints below.

## Why

First-person maps need to read as authored places rather than as one repeated
wall texture with scripted transitions layered on top. Town and dungeon spaces
should be able to share the same world ontology while differing materially:
wall families, doors/openings, floor and ceiling treatment, sky, props, and
lighting are presentation choices over a logical Map rather than separate kinds
of gameplay world.

The important distinction is between **gameplay-significant structure** and
**ambient visual variation**. A door/opening can change traversal or trigger an
Event and therefore must be authorable. Small material variations within an
otherwise equivalent wall family should not require per-cell authoring merely
to avoid repetition.

## Tileset and material vocabulary

Tilesets are named authored resource families. Their low-resolution visual
language should survive renderer changes:

- sample pixel-art textures with nearest-neighbour intent rather than smoothing
  painted low-resolution detail away;
- let one tileset describe distinct structural roles such as ordinary walls,
  doors/openings, floor, ceiling, and sky where the Project needs them;
- keep reusable material/variant definitions in tileset/resource data rather
  than embedding renderer-specific coordinates throughout Map data;
- allow a Map to select the material family appropriate to that place without
  creating a new Map ontology.

Exact manifest fields and resource-resolution rules belong to `docs/SPEC.md`.
They are deliberately not duplicated here.

## Deterministic ambient variation

Ambient variants may be selected deterministically from stable spatial identity
rather than authored on every cell. This gives visual variety without growing
Map authoring noise or consuming gameplay RNG.

That rule has two limits:

1. A variant that changes gameplay meaning must be authored or otherwise
   semantically resolvable; visual hashing must never decide whether a passage
   is locked, open, hazardous, or interactive.
2. The deterministic key must remain stable enough that reloading the same
   authored Map does not make its architecture visibly reshuffle.

## Doors and openings

Doors belong to the structural surface vocabulary, not to the generic
camera-facing sprite vocabulary. They may be represented by wall-attached
fixtures, opening geometry, models, or another renderer-owned form, but their
semantic anchor is the Map/Event structure they decorate.

A door used for traversal should hand control to ordinary Map/Event semantics.
The renderer must not become the authority that decides whether the player may
cross it. Interior presentation may be reused across several doors where the
game intentionally treats those interiors as a shared composition; bespoke
locations may provide bespoke presentation without changing the transition
model.

## Sky and ceiling intent

Exterior and interior spaces need different upper-world treatment. A Map may
therefore choose an authored sky/environment treatment or an enclosed ceiling
without changing movement or Event semantics.

Sky composition is not a light source by implication. Its anchoring, panorama
behavior, and relationship to expanded render surfaces are presentation
contracts; the reviewed rules live in `docs/SPEC.md`, including the canonical
composition/horizon invariant.

## Vertex-authored lighting

Lighting is spatial art direction. Authors need to be able to paint colored
light over the Map without turning each rendered surface into bespoke content.
A useful model is a light field defined at Map vertices/corners and sampled
continuously between them:

- light carries RGB, not only scalar brightness;
- an absent authored light contribution is neutral/full brightness;
- interpolation should be continuous across adjacent cells so the author does
  not fight visible seams;
- base material hue and lighting hue multiply/compose rather than one silently
  replacing the other;
- editor visualization should show the interpolated result rather than only a
  sparse set of control points.

The data representation and renderer implementation are intentionally left to
the living engine contract. The design invariant is that lighting remains an
authored spatial field with deterministic interpolation, not a collection of
hardcoded renderer exceptions.

## Authoring ergonomics

Lighting controls should behave like painting rather than like editing a table
of RGB triples. A color picker, bounded brush radius, paint/smoothing tools, and
an interpolated overlay are appropriate affordances. Resetting a Map's lighting
should restore the neutral/default state rather than materializing a redundant
full-brightness field.

Procedural Maps may require a different authoring surface because there is no
stable authored vertex grid to paint before generation. That distinction is a
content-authoring constraint, not permission for the runtime to maintain two
unrelated lighting semantics.

## Renderer boundary

The original implementation pressure came from a raycaster, but these design
requirements are deliberately renderer-agnostic:

- the logical Map remains gameplay authority;
- presentation may move from slices to polygonal surfaces or another backend;
- deterministic variants, structural provenance, materials, sky, and lighting
  remain resolved presentation facts over that Map;
- a renderer refactor must not smuggle free movement, new collision, or another
  world representation into gameplay merely because it can draw richer geometry.
