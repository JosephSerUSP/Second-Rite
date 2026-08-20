# Clean-room Second Gate town gauntlet

Date: 2026-08-20
Selected lineage: B
Native review target: 426x240
Baseline: level side view, preferred lens family, projection-window tracking

## Gate result

The minimal sterile scene was rendered before architecture. It contains one
Walker protagonist and two Walker stand-ins using the exact generic
`thestra_camera.create_actor_preview` helper. The gate records upright pose,
feet anchoring, 24x48 slicing, nearest filtering, alpha clipping, native scale,
level pitch, lens family and fixed-eye projection-window invariance.

## Architectural lineages

Three lineages were authored from factory-reset Blender scenes. Each was
reviewed as clay before the in-place refinement pass. The retained direction is
lineage B: two human-scale masses are tied by a real upper connection, with a
thick-wall underpass, supports, staircase, action lane and architecture
continuing beyond the visible frame.

## Runtime collapse

The final scene contains rich TH_SOURCE geometry, a subdivided open source
facade panel, and a separate coarse real-3D TH_RENDER. TH_RENDER uses one fresh
beauty atlas through world-stable UVs; it is not a camera-space background plane.
TH_COLLISION and TH_ANCHORS are prepared for a later reviewed traversal
integration. Preview actors are isolated from both environment collections.

## Composition follow-up

Review feedback on the submitted frames: the architecture is compositionally
interesting, but the buildings read close to the Walker. The next study should
compare a farther-back authored action/depth arrangement with a small camera
framing study. Preserve the proven level baseline and preferred lens family;
do not widen the lens merely to make the scene feel farther away.

## Evidence

- `minimal/minimal-gate-426x240.png`
- `clay/lineages-clay-comparison.png`
- `clay/lineages-refined-comparison.png`
- `final/source-beauty-426x240.png`
- `final/runtime-atlas-426x240.png`
- `final/projection-left--96-426x240.png`
- `final/projection-center-+0-426x240.png`
- `final/projection-right-+96-426x240.png`
- `final/second-gate-town-environment.blend`
- `final/beauty_atlas.png`
- `final/metrics.json`
- `final/material-provenance.json`
- `final/anchors.json`

## Asset input audit

The only pre-existing repository visual file read was exactly:

`projects/hichaukitoden-game/assets/character/walker.png`

All environment geometry and material sources in this run are fresh.
