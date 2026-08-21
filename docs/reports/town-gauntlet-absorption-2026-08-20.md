# Town gauntlet absorption — 2026-08-20

This report records the closure boundary for the August 20 Second Gate town visual experiments.

The following experiment family was intentionally **not** selected for merge as authored town content:

- the first town visual workbench;
- the camera/material workbench built on top of it;
- the bounded-lane playable specimen;
- the material-heavy nine-attempt experiment;
- the clean-room nine-attempt experiment;
- the later material-gauntlet branch.

Their durable findings have been reduced to `docs/design/town-authoring-known-good.md` and `docs/design/town-gauntlet-agent-boundary.md`.

No previous town scene, contact sheet, winner, geometry, material set, authored coordinates, environment package, or town-specific builder is promoted by this absorption pass.

The foundational non-visual camera/projection/calibration work remains a separate architecture concern and is not superseded by this report.

## Durable conclusions absorbed

- 426×240 native review and 24×48 Walker presentation are required for meaningful composition judgment.
- The preferred baseline is a level side view in the ~43 mm / ~28° horizontal-FOV family, with camera distance solved for the actor footprint rather than widening the lens.
- Principal-point/horizon composition around native Y≈110 has been useful; small ±3° pitch experiments remain optional rather than authoritative.
- Fixed-eye projection-window tracking is the correct side-view camera experiment family.
- Shared camera and Walker billboard helpers are infrastructure; art agents must not rederive them.
- Fresh visual scenes need multiple meaningful world-depth layers and real architectural volume, not a façade-only primitive grammar.
- Rich Blender source may collapse aggressively, but runtime remains coarse **real 3D geometry plus one beauty atlas**; a camera-space beauty plane is not the target environment model.
- Procedural, newly sourced public, and newly generated materials are all valid; known registration, color-space, displacement and texture-scale pitfalls are documented in the known-good file.
- The bounded continuous left/right traversal proof is useful behavioral evidence, but its prototype-specific map data and naming are not production ontology.
- Future visual agents should be shielded from historical visual attempts and receive only distilled facts plus exact generic tooling paths.

## Closure policy

The superseded visual/playability experiment PRs may be closed after this report is published. Closing them does not declare their work useless; it prevents their authored content from becoming accidental ancestry for the next art search.

If a future implementation needs a concrete generic fix first discovered in an old experiment, reimplement or transplant that fix through a narrowly scoped architecture/tooling PR rather than reopening the old visual branch as an art base.
