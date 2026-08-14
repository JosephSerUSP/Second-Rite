# Fog Presets, Panorama Layers, and Tileset Authoring — Design

> **Intent, not status.** This document records durable fog/environment and
> authoring requirements. `docs/ENGINE-STATE.md` owns what exists;
> `docs/SPEC.md` owns reviewed renderer behavior.

## Why panorama changes the fog model

A fog system that only mixes every surface toward one solid color cannot express
mist or atmosphere with visible texture and motion. Panorama-backed fog therefore
needs to be treated as a composited environment layer rather than as a special
color constant copied into every surface shader.

The durable renderer rule is:

> Walls, floors, ceilings, sprites, and other fogged surfaces should reveal the
> same resolved fog/environment composition instead of each maintaining a
> parallel hand-written fog formula.

The exact shader/blend implementation may change. The visual ownership must not.

## Panorama layers

Fog panorama is conceptually a list so a Project can compose more than one
layer without changing the data model. Each layer may provide:

- an image/resource reference;
- horizontal and vertical scroll rates;
- opacity;
- a declared supported blend mode.

Layers compose in authored order. An empty panorama means the fog/environment
may fall back to its flat-color treatment.

Scrolling is presentation time, not gameplay state. It must not consume or
perturb gameplay RNG, and deterministic/headless simulation must not depend on
which fog frame happens to be visible.

## Shared fog presets

Maps should be able to reference a named fog preset rather than copying the same
color/density/panorama fields repeatedly. Editing a shared preset is an explicit
shared-content decision; a Map that needs a one-off atmosphere may instead own
an inline/custom configuration.

A missing required preset is an authoring error, not an invitation to borrow an
unrelated Project's atmosphere silently. Validation/resource resolution should
make the problem visible according to the living engine contract.

## Studio authoring

Studio should expose fog/environment presets and tileset material definitions as
first-class authored resources rather than forcing routine edits through raw
JSON. Map properties should make the choice between a shared preset and a local
custom configuration legible.

The editor must preserve the ownership boundary:

- Project/resource data remains authoritative;
- Studio chrome is not game content;
- visual previews consume the engine/runtime presentation seam where
  authoritative output matters rather than growing an independent renderer that
  can drift.

## Explicit non-goals

This design does not require:

- an in-editor painting system for panorama artwork;
- arbitrary custom shader/blend programs per fog layer;
- treating every missing material/resource as a valid fallback;
- making atmospheric scrolling or fog density part of authoritative gameplay
  unless a separate mechanic explicitly consumes it.
