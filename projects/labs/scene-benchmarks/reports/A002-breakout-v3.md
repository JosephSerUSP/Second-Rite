# Benchmark Report

### Benchmark
ID: A002
Name: Breakout
Benchmark Version: Current Main Semantics
Date: 2026-11-05

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
* Re-implemented freshly from scratch to verify if any new semantic commands could replace the SCRIPT blocks.
* Verified that collection mutation and generic 2D spatial collision querying are still missing from the engine's authored semantics.
* The structure remains identical to the previous attempt as no new engine capabilities were introduced to handle arrays or collections natively in Scenes.

### Improved
* None. The engine capabilities for this specific benchmark remain identical.

### Regressed
* None.

### Still Awkward
The requirement to manage an arbitrary mutable collection of entities (bricks) still forces an escape into raw Lua SCRIPT. The presentation remains split: single entities (ball, paddle) render cleanly via declarative windows, but the multiple brick targets rely on string-building because Thestra currently lacks semantic commands for rendering lists of dynamic sub-elements or generic array mutation.

### New Architectural Evidence
A002 continues to show that while declarative state semantics handle single-entity physics beautifully, Thestra requires explicit backend-neutral semantic commands for managing collections (spawning, tracking, and removing multiple distinct entities) and generic 2D collision querying in order to fully model grid-based action simulations declaratively.

### Verdict
**Playable benchmark; unchanged collection friction.** A002 Breakout proves that declarative formulas and dynamic window `rect` dimensions can cleanly subsume the physics and movement logic of the simulation. However, the reliance on SCRIPT for brick collections adds to the persistent evidence that array-mutation and spatial-querying semantics are the next major authorability frontier.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: LEFT/RIGHT to move paddle, Enter to restart, B to back.

Owner observations: (pending)
Result: (pending)
