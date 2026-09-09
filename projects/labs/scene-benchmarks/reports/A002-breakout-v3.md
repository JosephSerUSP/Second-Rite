# Benchmark Report

### Benchmark
ID: A002
Name: Breakout
Benchmark Version: Current Main Semantics
Date: 2026-09-09

### Current Result
complete

### Current Implementation Shape
A fresh reconstruction of A002 following current Thestra semantics. Authored Scene composition leverages the merged fixed Scene clock (`step=0.0166`) and logical hooks (`on_left`, `on_right`) to author input intent. The core game loop for paddle movement, ball movement, bounds checking, and paddle collision uses purely authored semantic commands (`SET_VAR` multi-assignments and `IF` blocks). The presentation uses dynamic `rect` fields in `windows` to evaluate coordinate formulas for the paddle and ball. A raw Lua `SCRIPT` fallback block is used to render the brick array collection and handle brick intersection logic. It uses JSON boolean primitives (`true`, `false`) for `SET_VAR` rather than strings to ensure clean formula evaluation. A `goldenScript` is present to support automated validation.

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 2
* approximate SCRIPT lines: ~35
* native source files modified: 0
* new generic semantic commands added: 0
* Project-owned files required: a002_breakout.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: Raw Lua SCRIPT handles array-based collection mutation (`v.bricks = {}`) and grid-based string rendering exclusively for the bricks.
* unsupported benchmark requirements: None.
* whether Studio authoring surfaces were sufficient: No, SCRIPT was still required for collection management.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
* Re-implemented freshly to confirm stability of declarative `IF` and `SET_VAR` commands.
* Uses native JSON booleans (`false`, `true`) directly for `SET_VAR` in the scene rather than string values (`"false"`), improving evaluation robustness natively inside `evalFormula`.
* Maintained inline `clamp()` formula helpers in `SET_VAR`.
* Maintained duplicated initialization commands in `on_enter` and `on_select` to avoid `SCENE_EVENT` drops during CI previews.

### Improved
* **Boolean Semantics:** Using native JSON boolean primitives natively interfaces with evaluation without string coercions, making the declarative definitions slightly more robust and clean.
* **Consistency:** The formula capabilities, such as `clamp()`, remain perfectly adequate for declarative 2D bound handling.

### Regressed
* **CI Validation Gap:** Similar to V2, `SCENE_EVENT` commands with kind `run_hook` (such as `init_state`) are silently dropped during automated scene previews in CI, leading to nil-variable errors. `SET_VAR` blocks were duplicated across both `on_enter` and `on_select` to circumvent this limitation.

### Still Awkward
The requirement to manage an arbitrary mutable collection of entities (bricks) still forces an escape into raw Lua SCRIPT. The presentation remains split: single entities (ball, paddle) render cleanly via declarative windows, but the multiple brick targets rely on string-building because Thestra currently lacks semantic commands for rendering lists of dynamic sub-elements or generic array mutation.

### New Architectural Evidence
A002 reinforces that declarative state semantics handle single-entity physics cleanly. It highlights the continued need for explicit backend-neutral semantic commands for managing collections (spawning, tracking, and removing multiple distinct entities) and generic 2D collision querying in order to fully model grid-based action simulations declaratively without Lua `SCRIPT` escapes.

### Verdict
**Playable benchmark; unchanged collection friction.** A002 Breakout proves that declarative formulas and dynamic window `rect` dimensions can cleanly subsume the physics and movement logic of the simulation. The reliance on SCRIPT for brick collections adds to the persistent evidence that array-mutation and spatial-querying semantics are still the missing core feature for full semantic authorability.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: LEFT/RIGHT to move paddle, Enter to restart, B to back.

Owner observations: (pending)
Result: (pending)
