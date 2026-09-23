### Experiment
C002 — Splitting Ball Pong

### Result
complete

### Authored Surface
Authored Scene JSON (`c002_splitting_pong.json`). Cleanly implemented purely using JSON formulas, modifying `on_select` to fully restore the initialization state previously quarantined.

### SCRIPT / Native Escape Hatches
None used. No `SCRIPT` commands were utilized in this final implementation. The `on_select` initialization hook was restored entirely using declarative `SET_SCENE_STATE` variable assignments rather than legacy script workarounds.

### Missing Reusable Semantics
The JSON formula language still lacks true dynamic collections and map/filter iteration primitives. Spawning multiple objects required manual definition of `ball1`, `ball2`, and `ball3` blocks, alongside manually typed tracking variables (`ball2Active`, `ball2X`, `ball2Y`). This lacks scalability if hundreds of entities are needed.

### Awkward But Expressible
Replicating logic across three identically functioning balls requires repeating collision detection and coordinate updates manually within `SET_SCENE_STATE` and `IF` blocks. Furthermore, aggregating properties for conditions (e.g., checking if *any* ball crossed a threshold) demands heavily chained ternary operators and explicit `or` clauses (`sceneState.ball1X < 0 or (sceneState.ball2Active > 0 and sceneState.ball2X < 0) ...`).

### Tooling / Discoverability Gaps
No major gaps for defining manual object limits, but managing duplicated state hooks without visual tool support for array iteration loops makes editing dense source JSON error-prone.

### Backend Leakage
None. Handled entirely natively within Thestra's JSON constraints, relying strictly on standard math hooks (`min`, `max`) and delta time (`time.dt`).

### Project Leakage
None. Fully isolated.

### Author Legibility
Yes. A competent RPG Maker-style author will easily understand standard manual duplication variables representing identical logical copies of an entity (e.g. duplicating "Bullet 1", "Bullet 2"). The structural repetition is familiar eventing friction.

### Reusable Successes
Selective visibility based entirely on geometric evaluation constraints ("w": "sceneState.ball2Active > 0 and 1 or 0") elegantly avoids native visibility hooks and solves conditional spawning display effectively.

### Architecture Recommendation
gather more evidence
