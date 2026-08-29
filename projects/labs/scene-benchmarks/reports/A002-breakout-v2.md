# Benchmark Report

### Benchmark
ID: A002
Name: Breakout
Benchmark Version: Current Main Semantics
Date: 2026-08-29

### Current Result
complete

### Current Implementation Shape
A completely fresh reconstruction of A002. Authored Scene composition leverages the merged fixed Scene clock (`step=0.0166`) and logical hooks (`on_left`, `on_right`) to author input intent. The core game loop for paddle movement, ball movement, bounds checking, and paddle collision uses purely authored semantic commands (`SET_VAR` multi-assignments and `IF` blocks). The presentation uses dynamic `rect` fields in `windows` to evaluate coordinate formulas for the paddle and ball, while relying on a raw Lua `SCRIPT` fallback block to render the brick array collection and handle brick intersection logic. A `goldenScript` has been added to support automated validation.

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 2
* approximate SCRIPT lines: ~35
* native source files modified: 0
* new generic semantic commands added: 0
* Project-owned files required: a002_breakout.json, index.json, title.json, terms.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: Raw Lua SCRIPT handles array-based collection mutation (`v.bricks = {}`) and grid-based string rendering exclusively for the bricks.
* unsupported benchmark requirements: None.
* whether Studio authoring surfaces were sufficient: No, SCRIPT was still required for collection management.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
* Re-implemented freshly, proving that the declarative `IF` and `SET_VAR` commands remain stable and capable of replacing Lua-based continuous physics and bounds checking.
* Used inline `clamp()` formula helpers in `SET_VAR` to cleanly manage the paddle constraints and ball boundaries, avoiding deeply nested bounds-checking IFs.
* Avoided `SCENE_EVENT` with `run_hook` during initialization, choosing to place setup formulas directly in `on_enter` and duplicating them in `on_select` (for restart), accommodating current automated test behaviors where events might drop.
* Added a `goldenScript` block to support automated testing in CI.

### Improved
* **Formula Elegance:** Using the native `clamp()` helper inside the `SET_VAR` string formulas significantly cleans up boundary constraints compared to manual if-else branching.
* **Testability:** Added the required `goldenScript` metadata for CI to automatically validate the benchmark's scene logic without requiring human input.

### Regressed
* **CI Validation Gap & Initialization Duplication:** `SCENE_EVENT` commands with kind `run_hook` (such as the initial `init_state` hook called from `on_enter` and `on_select`) are silently dropped during automated scene previews in CI, leading to nil-variable errors. To preserve the reset capability (`on_select`) without breaking CI, the `SET_VAR` setup block had to be explicitly duplicated across both hooks rather than shared.

### Still Awkward
The requirement to manage an arbitrary mutable collection of entities (bricks) still forces an escape into raw Lua SCRIPT. The presentation remains split: single entities (ball, paddle) render cleanly via declarative windows, but the multiple brick targets rely on string-building because Thestra currently lacks semantic commands for rendering lists of dynamic sub-elements or generic array mutation.

### New Architectural Evidence
A002 continues to show that while declarative state semantics handle single-entity physics beautifully, Thestra requires explicit backend-neutral semantic commands for managing collections (spawning, tracking, and removing multiple distinct entities) and generic 2D collision querying in order to fully model grid-based action simulations declaratively. The workaround forced by CI event-dropping also suggests a need for an engine-level `init` lifecycle hook or stable shared hook execution for purely state-initializing commands.

### Verdict
**Playable benchmark; unchanged collection friction.** A002 Breakout proves that declarative formulas and dynamic window `rect` dimensions can cleanly subsume the physics and movement logic of the simulation. However, the reliance on SCRIPT for brick collections adds to the persistent evidence that array-mutation and spatial-querying semantics are the next major authorability frontier.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: LEFT/RIGHT to move paddle, Enter to restart, B to back.

Owner observations: (pending)
Result: (pending)
