# Benchmark Report

### Benchmark
ID: A002
Name: Breakout
Benchmark Version: v3 (String Booleans for Formula Evaluation)
Date: 2026-09-11

### Current Result
complete

### Current Implementation Shape
A completely fresh reconstruction of A002. Authored Scene composition leverages the merged fixed Scene clock (`step=0.0166`) and logical hooks (`on_left`, `on_right`) to author input intent. The core game loop for paddle movement, ball movement, bounds checking, and paddle collision uses purely authored semantic commands (`SET_VAR` multi-assignments and `IF` blocks). The presentation uses dynamic `rect` fields in `windows` to evaluate coordinate formulas for the paddle and ball, while relying on a raw Lua `SCRIPT` fallback block to render the brick array collection and handle brick intersection logic. A `goldenScript` sequence is preserved for CI testing.

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
* Updated `a002_breakout.json` to use stringified booleans (`"false"`/`"true"`) in `SET_VAR` values to adhere to `evalFormula` parser string-eval semantics.
* Leveraged standard `SET_VAR` multi-assignments (`assignments` array) for initialization state setup and physics update frames.
* Preserved `goldenScript` to support automated scene validation in CI (`check-specimen-play`).

### Improved
* **Formula Semantic Compatibility:** Using stringified booleans in `SET_VAR` assignments aligns with `evalFormula`'s parser, ensuring variables resolve correctly during expression evaluation and terminal condition checks.
* **Declarative Multi-Assignment:** Consolidated initializations and velocity/position updates into `SET_VAR` multi-assignment arrays.

### Regressed
* **CI Event Scope Limitations:** `SCENE_EVENT` commands with kind `run_hook` are still dropped in CI scene previews, requiring duplicate state initialization assignments across `on_enter` and `on_select`.

### Still Awkward
The requirement to manage an arbitrary mutable collection of entities (bricks) still forces an escape into raw Lua SCRIPT. The presentation remains split: single entities (ball, paddle) render cleanly via declarative windows, but the multiple brick targets rely on string-building because Thestra currently lacks semantic commands for rendering lists of dynamic sub-elements or generic array mutation.

### New Architectural Evidence
A002 continues to show that while declarative state semantics handle single-entity physics cleanly, Thestra requires explicit backend-neutral semantic commands for managing collections (spawning, tracking, and removing multiple distinct entities) and generic 2D collision querying in order to fully model grid-based action simulations declaratively.

### Verdict
**Playable benchmark; unchanged collection friction.** A002 Breakout proves that declarative formulas and dynamic window `rect` dimensions cleanly model paddle/ball physics. However, raw Lua SCRIPT remains required for dynamic brick collection management until array-mutation engine primitives are introduced.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: LEFT/RIGHT to move paddle, Enter to restart, B to back.

Owner observations: (pending)
Result: (pending)
