# Generated Map inspection prototype

This report records the read-oriented Studio prototype for the current
single-generated-scope Map path. It deliberately does not introduce Location,
Area, Zone renaming, multiple generation scopes, or save semantics.

Studio submits an unsaved Map snapshot and an explicit seed to the narrow
engine bridge. LÖVE resolves that snapshot through `engine.exploration` in an
isolated `GameSession`, then returns semantic facts for the provisional scope
`map:<id>:generated`: authored anchors/zones/events, generated rooms/corridors/
openings/zones/events/features/lights, protected cells, and the real
resolved tileset identity. The browser only overlays and inspects those facts;
it does not generate layout or compile geometry.

The generated inspection G6 state is intentionally a new, owner-reviewable
visual surface. The actual captured during this branch is committed at:

`docs/reports/artifacts/map-inspection-g6-actual-2026-08-12.png`

It has no committed reference yet. The image is evidence for owner visual
signoff, not visual approval. Existing unrelated G6 mismatches remain
unchanged and were not recaptured.

Current provenance limits are explicit: fixture entries expose the resolver's
actual feature id, role, predicate, probability, deterministic cell roll, and
reachability/protection facts; the prototype does not invent a richer
generator explanation. Future multi-scope identity and reusable-anchor
provenance remain outside this prototype.
