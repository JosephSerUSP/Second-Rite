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
- Camera/billboard basis handedness is load-bearing: a reflected basis cannot be round-tripped through a quaternion without losing the reflection. Explicit basis/matrix handling plus an upright-screen-space assertion is the safer contract.
- Fresh visual scenes need multiple meaningful world-depth layers and real architectural volume, not a façade-only primitive grammar.
- A small number of independent architectural lineages followed by serious in-lineage refinement produces substantially stronger geometry than a broad nine-scene batch. This research structure is worth retaining even though the authored scenes are not.
- A town frame must read as a view inside a larger environment: authored floor/ground, foreground, architecture and background need world-space overscan beyond the visible frame and the intended projection-window envelope. Accidental void, clipped set edges and razor-thin floor strips are rejection conditions.
- A real foreground layer is not a token occluder. It should sit at meaningful camera depth, belong to the environment and create natural overlap as actors move.
- Rich Blender source may collapse aggressively, but runtime remains coarse **real 3D geometry plus one beauty atlas**; a camera-space beauty plane is not the target environment model.
- The beauty atlas must be causally derived from TH_SOURCE appearance. Copying the final framebuffer into an atlas file is not a bake, and independently synthesizing a separate runtime atlas is not a source-to-runtime bake either.
- Selected-to-active bake receivers need an active non-overlapping atlas UV set. Existing tiling/world-space UVs are not sufficient by themselves.
- Combined beauty bake color space must be explicit. A scene-linear bake written as raw bytes into a PNG that consumers interpret as sRGB can render dramatically too dark; the pipeline must either encode the file for the consumer expectation or preserve and honor a true linear-texture contract end to end.
- Procedural, newly sourced public, and newly generated materials remain valid, but recent runs confirmed that generic procedural noise/bump across every hero surface is texturally weak. Convincing final materials need material-specific structure such as masonry courses, timber grain, roof/paving rhythm, wear and surface-scale coherence.
- A generated/downloaded material only counts as evidence when it is actually connected to and visible in the selected TH_SOURCE scene; generator code or provenance alone is insufficient.
- The bounded continuous left/right traversal proof is useful behavioral evidence, but its prototype-specific map data and naming are not production ontology.
- Future visual agents should be shielded from historical visual attempts and receive only distilled facts plus exact generic tooling paths.

## Latest sterile-lineage disposition

Two later sterile experiments were useful but remain non-mergeable as authored town work.

One produced noticeably stronger architectural massing and depth through the lineage/refinement method, but remained weak in surface treatment and packaged a 426×240 beauty render by copying it directly into the file named as an atlas. Its geometry lesson is retained; its scene and package are not.

The other kept coarse real-3D runtime geometry but used an independently synthesized procedural atlas rather than transferring the rich source appearance. It also remained texturally weak and compositionally incomplete as a full environment.

Both exposed the same missing composition gate: floors and environments were too often framed like finite stage sets, with insufficient foreground and visible emptiness/termination rather than convincing continuity.

## Latest clean-room batch — tooling findings

The next clean-room batch produced two additional categories of useful evidence while still not promoting either authored environment.

### Cheap Cycles is sufficient for authoring decisions

One independently authored run used **4-sample Cycles with denoising**, low bounce counts and native 426×240 review successfully through presentation, clay and bake comparison. This supports the separate render-profile work: expensive sample counts should not be the default for exploratory authoring.

### Bake receiver/color-space failures are generic tooling concerns

The larger parallel run found three generic defects worth separating from the town art:

1. reflected camera/billboard basis information was lost by quaternion conversion, producing inverted actors;
2. the selected-to-active receiver did not automatically own a usable non-overlapping atlas UV layout;
3. a scene-linear Combined bake written into a PNG later sampled as sRGB produced a severe brightness mismatch.

Those are pipeline/tooling facts. Their fixes should live in generic Blender/camera/bake lanes rather than be copied from a town scene branch.

### Camera-aware atlas allocation — measurement accepted, implementation not canonized

The same run measured a major mismatch between ordinary surface-area UV allocation and the actual bounded-camera presentation:

- **45 of 182 triangles** were ever visible across the measured projection-window views;
- **69.5% of allocated atlas texels** went to faces that were never visible in that measured camera envelope;
- visible-face texel density ranged from roughly **0.57 to 56.5 texels per native screen pixel**;
- the measured visible screen demand was only about a **264×264** square at true 1:1 density, versus the 1024×1024 atlas used by the specimen.

This is strong evidence that a bounded-camera environment should support camera-aware texel allocation.

The submitted `atlaspack.py` is **not** absorbed as authoritative tooling. It was explicitly not validated end to end, and its policy is too absolute for the broader engine: it takes the maximum projected area across a small fixed set of offsets, backface-culls each sampled view, and can destructively delete faces below a visibility threshold.

The durable direction is more general:

- atlas importance should vary continuously between world/surface-area density and camera/view-weighted density;
- weighting should integrate an authored **camera envelope**, not one exact screenshot;
- currently invisible surfaces should be graded by accessibility rather than all receiving zero weight;
- a face just outside the current view or reachable by a small pitch/yaw/eye change should retain more texel budget than a strongly back-facing or genuinely unreachable face;
- front-facing-but-occluded and back-facing surfaces should not be treated as the same category;
- culling should remain a separate explicit destructive optimization, not an automatic consequence of low screen weight;
- movable-camera scenes should use a weaker view bias / larger camera envelope than effectively static-camera scenes.

A dedicated generic tooling issue should own that continuation rather than reopening the clean-room art branch.

## Closure policy

Superseded visual/playability experiment PRs may be closed after their durable findings are recorded here. Closing them does not declare their work useless; it prevents their authored content from becoming accidental ancestry for the next art search.

If a future implementation needs a concrete generic fix first discovered in an old experiment, reimplement or transplant that fix through a narrowly scoped architecture/tooling PR rather than reopening the old visual branch as an art base.
