# Benchmark Report

### Benchmark
ID: A002
Name: Breakout
Benchmark Version: Current Main Semantics
Date: 2026-10-13

### Current Result
complete

### Current Implementation Shape
A fresh reconstruction of A002 using current semantics. Authored Scene composition leverages the fixed clock (`step=0.0166`) and logical hooks (`on_left`, `on_right`). The core loop relies entirely on multiple individual `SET_SCENE_STATE` command nodes (avoiding unsupported array assignments) and declarative `IF` blocks for paddle/ball movement, bounds checking, and paddle collision. An architectural improvement utilizes `require('engine.hooks').call_hook('init_state', {})` inside a `SCRIPT` block to cleanly share setup logic between `on_enter` and `on_select` without duplicating nodes or relying on CI-dropped `SCENE_EVENT` hooks. The presentation uses dynamic `rect` fields in `windows` to evaluate coordinate formulas for the paddle and ball, while relying on a raw Lua `SCRIPT` fallback to render the brick array and handle block intersections.

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 2 (plus 2 inline hook-dispatch escapes)
* approximate SCRIPT lines: ~35
* native source files modified: 0
* new generic semantic commands added: 0
* Project-owned files required: a002_breakout.json, index.json, title.json, terms.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: Raw Lua SCRIPT handles array-based collection mutation (`v.bricks = {}`) and grid-based string rendering exclusively for the bricks.
* unsupported benchmark requirements: None.
* whether Studio authoring surfaces were sufficient: No, SCRIPT was still required for collection management and hook dispatch.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
* Flattened `SET_SCENE_STATE` array assignments into multiple discrete nodes to satisfy engine validation rules.
* Resolved the CI initialization duplication regression by using a raw `SCRIPT` escape hatch `require('engine.hooks').call_hook('init_state', {})` to invoke a shared setup hook from both `on_enter` and `on_select`.

### Improved
* **DRY Initialization:** Using `call_hook` enables sharing initialization commands declaratively without duplicating logic or relying on the flawed `SCENE_EVENT` run_hook approach that fails in CI.

### Regressed
* **Verbose State Nodes:** Because `SET_SCENE_STATE` does not support array assignments, initializing multiple variables (e.g., 14 distinct setup fields) and updating coordinates requires highly verbose, multi-node sequential lists, decreasing legibility.
* **Hook Dispatch Semantics:** While initialization is no longer duplicated, it required a raw Lua `SCRIPT` escape hatch just to call another authored hook, pointing to the absence of a declarative sub-routine dispatch command.

### Still Awkward
The requirement to manage an arbitrary mutable collection of entities (bricks) still forces an escape into raw Lua SCRIPT. The presentation remains split: single entities (ball, paddle) render cleanly via declarative windows, but the multiple brick targets rely on string-building because Thestra lacks semantic commands for rendering lists of dynamic sub-elements or generic array mutation.

### New Architectural Evidence
A002 reinforces that while physics constraints (like `clamp()` formulas) are clean, state initialization is currently unergonomic without an array-assignment capability. The necessity to use a `SCRIPT` escape to dispatch `init_state` demonstrates an architectural gap: Thestra needs a declarative `CALL_HOOK` or `DISPATCH` semantic command to naturally compose and reuse authored logic blocks.

### Verdict
**Playable benchmark; verbose state mutation and missing dispatch.** A002 Breakout effectively models movement via declarative commands and dynamic windows, but suffers from verbose `SET_SCENE_STATE` nodes and the lack of a native hook-call semantic, alongside the persistent evidence that array-mutation and spatial-querying are needed for collection management.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: LEFT/RIGHT to move paddle, Enter to restart, B to back.

Owner observations: (pending)
Result: (pending)
