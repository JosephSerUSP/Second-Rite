# Benchmark Report

### Benchmark
ID: A001
Name: Pong
Benchmark Version: Current Main Semantics
Date: 2026-10-28

### Current Result
complete

### Current Implementation Shape
Authored Scene composition that relies on formula-evaluated `rect` properties in the `windowLayout` system to render paddles and the ball. Uses the fixed Scene clock (`step=0.0166`) and logical input hooks (`on_up`, `on_down`). Update and collision logic are implemented natively with purely authored semantic commands (`SET_SCENE_STATE` multi-assignments and `IF` blocks), replacing raw Lua entirely.

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 0
* approximate SCRIPT lines: 0
* native source files modified: 0
* new generic semantic commands added: 0
* Project-owned files required: a001_pong.json, index.json, title.json, terms.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: None.
* unsupported benchmark requirements: None.
* whether Studio authoring surfaces were sufficient: Yes, JSON structure maps perfectly to standard semantic blocks.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
* Re-implemented from scratch.
* Streamlined variables to `sceneState` directly, removing the `v.` prefix for clarity based on current formula state exposing `sceneState`.
* Retained the inlined initialization pattern into `on_enter` and `on_select` for CI hook safety.
* Condensed collision logic into direct `hit1` and `hit2` logical conditions evaluated in a single `SET_SCENE_STATE` command, providing similar clarity without bloating the file.
* Removed `score1` and `score2` initialization defaults inside formula evaluations as `on_enter` securely initializes them.

### Improved
* **Formula Transparency:** Standardizing on `sceneState.time.dt` directly demonstrates clear context paths inside the evaluation sandbox, eliminating `v.` confusion.
* **Semantic Legibility:** Condensed `SET_SCENE_STATE` assignments allow expressing the physics steps (positioning, delta-time adjustments) and intersection predicates concisely in one node block.

### Regressed
None.

### Still Awkward
Continuous simulation still heavily taxes authored presentation. While cleanly implemented via `sceneState.time.dt` scaling and multi-assignments, it produces heavily verbose JSON blocks that a typical node-based visual editor or traditional code environment would handle far more compactly.

### New Architectural Evidence
The current formula evaluation naturally supports inline conditionals (e.g., `sceneState.by > sceneState.p2y + 2 and 15.0 or 0`) which enables rudimentary AI tracking for the opposing paddle without custom scripts or complicated action graphs.

### Verdict
**Consistent architectural success.** The generic engine facilities (`time.dt`, formula conditionals, and dynamic window rects) are completely sufficient to express this real-time logic natively, reaffirming the semantic capability without needing any raw Lua execution.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: UP/DOWN to move paddle, Enter to restart, B to back.

Owner observations: (pending)
Result: (pending)
