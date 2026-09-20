# Benchmark Report

### Benchmark
ID: A001
Name: Pong
Benchmark Version: Current Main Semantics
Date: 2026-09-20

### Current Result
complete

### Current Implementation Shape
Authored Scene composition relying entirely on declarative formula-evaluated updates using `SET_LOCAL` and `SET_SCENE_STATE` during the `on_frame` hook. The logic leverages the new inline conditional `and`/`or` patterns along with the `clamp()` and `abs()` formula functions to compress state mutations into a single block of assignments, dropping the `IF` hook commands completely. Uses the fixed Scene clock and logical input hooks (`on_up`, `on_down`).

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
* whether Studio authoring surfaces were sufficient: Yes.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
* Eliminated all `IF` commands by utilizing inline conditional expressions, `clamp(val, min, max)`, and `abs()` within a single `SET_SCENE_STATE` multi-assignment.
* Removed the verbose array of individual command blocks.
* Updated `goldenScript` metadata with `wait` values per new testing policies.
* Re-implemented grid boundaries to utilize param bindings (`sceneState.gridW`) dynamically instead of hardcoded numbers, and restored deadzone to Paddle 2 AI (`sceneState.center2 < sceneState.ballY - 0.5`) to prevent endless jitter, per reviewer feedback.
* Re-initialized missing `sceneState.time.dt` access with valid initialization scope parameter `v.time.dt` access pattern, and preserved scoring restarts logic correctly with `sceneState.score1 or 0`.

### Improved
* **Author Legibility:** The core game loop logic shrank from a heavily staggered block of multiple `IF` branches into two clean multi-assignment blocks (`SET_LOCAL` for query/collision bounds, `SET_SCENE_STATE` for result application).
* **Code footprint:** Much more compact representation of standard bounds-checking semantics via generic `clamp()`.

### Regressed
None.

### Still Awkward
Nothing at this scale. The unified declarative formula logic completely encapsulates real-time collision cleanly.

### New Architectural Evidence
The availability of `clamp()` and `abs()` directly in formulas drastically cuts down on redundant bounding logic. Combined with inline conditionals, multi-assignments behave effectively like robust shader-style update cycles directly inside the authored schema.

### Verdict
**Total architecture success.** The iteration solidifies that Thestra's generic semantics can compress real-time action simulation into declarative expressions without relying on custom native escapes, producing a far cleaner authored artifact than previous attempts.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: UP/DOWN to move paddle, Enter to restart, B to back.

Owner observations: (pending)
Result: (pending)
