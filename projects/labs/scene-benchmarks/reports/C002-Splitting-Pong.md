# Benchmark Report

### Benchmark
ID: C002
Name: Splitting Ball Pong
Benchmark Version: Current Main Semantics
Date: 2026-09-23

### Current Result
complete

### Current Implementation Shape
Authored Scene JSON (`c002_splitting_pong.json`). Cleanly implemented purely using JSON formulas, modifying `on_select` to fully restore the initialization state previously quarantined. No `SCRIPT` commands were utilized in this final implementation. The `on_select` initialization hook was restored entirely using declarative `SET_SCENE_STATE` variable assignments rather than legacy script workarounds.

### Metrics
- SCRIPT instances: 0
- Duplicated physics blocks: 3
- Formula complexity: High for multiplexed checks.
- native source files modified: 0
- new generic semantic commands added: 0
- Project-owned files required: c002_splitting_pong.json, index.json, title.json, terms.json
- RTP dependencies: 1.0
- validation warnings/errors encountered: 0
- bespoke workarounds: None.
- unsupported benchmark requirements: None.
- whether Studio authoring surfaces were sufficient: Yes, JSON structure maps perfectly to standard semantic blocks.
- whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
Removed all `SCRIPT` usage and replaced it entirely with declarative JSON `SET_SCENE_STATE` and `IF` assignments.

### Improved
Initialization is now cleanly managed by declarative hooks rather than quarantined arbitrary Lua execution. Conditional rendering natively manages "spawning" via zero-bounds calculation correctly.

### Regressed
None.

### Still Awkward
Replicating logic across three identically functioning balls requires repeating collision detection and coordinate updates manually within `SET_SCENE_STATE` and `IF` blocks. Furthermore, aggregating properties for conditions (e.g., checking if *any* ball crossed a threshold) demands heavily chained ternary operators and explicit `or` clauses (`sceneState.ball1X < 0 or (sceneState.ball2Active > 0 and sceneState.ball2X < 0) ...`).

### New Architectural Evidence
The JSON formula language still lacks true dynamic collections and map/filter iteration primitives. Spawning multiple objects required manual definition of `ball1`, `ball2`, and `ball3` blocks, alongside manually typed tracking variables (`ball2Active`, `ball2X`, `ball2Y`). This lacks scalability if hundreds of entities are needed. No major gaps for defining manual object limits, but managing duplicated state hooks without visual tool support for array iteration loops makes editing dense source JSON error-prone. Handled entirely natively within Thestra's JSON constraints, relying strictly on standard math hooks (`min`, `max`) and delta time (`time.dt`). A competent RPG Maker-style author will easily understand standard manual duplication variables representing identical logical copies of an entity (e.g. duplicating "Bullet 1", "Bullet 2"). The structural repetition is familiar eventing friction.

### Verdict
candidate reusable semantic gap; gather more evidence.
