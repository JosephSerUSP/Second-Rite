# Town gauntlet absorption — 2026-08-20

This report records the closure boundary for the August 20 Second Gate town visual experiments.

The experiment family was intentionally **not** selected for merge as authored town content. It included the first town visual workbench, camera/material workbenches, the bounded-lane playable specimen, several material-heavy and clean-room gauntlets, and the later sterile lineage experiments.

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
- A small number of independent architectural lineages followed by serious in-lineage refinement produces substantially stronger geometry than a broad nine-scene batch. This research structure is worth retaining even though the authored scenes are not.
- A town frame must read as a view inside a larger environment: authored floor/ground, foreground, architecture and background need world-space overscan beyond the visible frame and the intended projection-window envelope. Accidental void, clipped set edges and razor-thin floor strips are rejection conditions.
- A real foreground layer is not a token occluder. It should sit at meaningful camera depth, belong to the environment and create natural overlap as actors move.
- Rich Blender source may collapse aggressively, but runtime remains coarse **real 3D geometry plus one beauty atlas**; a camera-space beauty plane is not the target environment model.
- The beauty atlas must be causally derived from TH_SOURCE appearance. Copying the final framebuffer into an atlas file is not a bake, and independently synthesizing a separate runtime atlas is not a source-to-runtime bake either.
- Procedural, newly sourced public, and newly generated materials remain valid, but recent runs confirmed that generic procedural noise/bump across every hero surface is texturally weak. Convincing final materials need material-specific structure such as masonry courses, timber grain, roof/paving rhythm, wear and surface-scale coherence.
- A generated/downloaded material only counts as evidence when it is actually connected to and visible in the selected TH_SOURCE scene; generator code or provenance alone is insufficient.
- The bounded continuous left/right traversal proof is useful behavioral evidence, but its prototype-specific map data and naming are not production ontology.
- Future visual agents should be shielded from historical visual attempts and receive only distilled facts plus exact generic tooling paths.

## Latest sterile-lineage disposition

Two later sterile experiments were useful but remain non-mergeable as authored town work.

One produced noticeably stronger architectural massing and depth through the lineage/refinement method, but remained weak in surface treatment and packaged a 426×240 beauty render by copying it directly into the file named as an atlas. Its geometry lesson is retained; its scene and package are not.

The other kept coarse real-3D runtime geometry but used an independently synthesized procedural atlas rather than transferring the rich source appearance. It also remained texturally weak and compositionally incomplete as a full environment.

Both exposed the same missing composition gate: floors and environments were too often framed like finite stage sets, with insufficient foreground and visible emptiness/termination rather than convincing continuity.

## Closure policy

Superseded visual/playability experiment PRs may be closed after their durable findings are recorded here. Closing them does not declare their work useless; it prevents their authored content from becoming accidental ancestry for the next art search.

If a future implementation needs a concrete generic fix first discovered in an old experiment, reimplement or transplant that fix through a narrowly scoped architecture/tooling PR rather than reopening the old visual branch as an art base.
