# Benchmark Report

### Benchmark
ID: A001
Name: Pong
Benchmark Version: Current Main Semantics
Date: 2026-08-20

### Current Result
complete

### Current Implementation Shape
Authored Scene composition that relies on formula-evaluated `rect` properties in the `windowLayout` system to render paddles and the ball, eliminating the previous text grid rendering entirely. Uses the fixed Scene clock (`step=0.0166`) and logical input hooks (`on_up`, `on_down`). Update and collision logic are implemented natively with purely authored semantic commands (`SET_VAR` multi-assignments and `IF` blocks), replacing raw Lua entirely.

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
* Completely eliminated the ~70 lines of raw Lua `SCRIPT` used for movement integration, collision, and board rebuilding.
* Replaced the text-grid string-rebuilding loop with dynamic `rect` fields in `windows`, evaluating coordinate formulas (like `v.ballX` and `v.paddle1Y`) continuously during frame rendering.
* Swapped `init` and `update` logic into pure Thestra semantic operations via `SET_VAR` and `IF`.

### Improved
* **Backend-neutrality:** The implementation is entirely decoupled from raw Lua, proving that Pong simulation rules can be elegantly written with semantic formulas, multi-assignments, and condition blocks.
* **Presentation Composition:** Continuous coordinates translate perfectly into dynamic window position offsets, dropping the need for an awkward string grid. This feels more intuitive and matches how modern UI elements are positioned.

### Regressed
None.

### Still Awkward
Evaluating collision boundaries in a single `IF` formula remains somewhat dense due to how Lua handles multi-condition short-circuits with strings of `and` operators, but it functions accurately without needing a full engine-level ECS or new native commands.

### New Architectural Evidence
The ability for `resolveDim` to evaluate formulas natively for `rect.x` and `rect.y` in window layouts provides a remarkably clean pattern for dynamic presentation without requiring manual engine state replication. Coupling this with the fixed Scene clock proves that the current authoring toolkit is highly capable of driving discrete-time simulations smoothly without native workarounds.

### Verdict
**Complete architectural success.** The evolution of generic engine facilities (robust formula evaluation and dynamic window dimension support) has absorbed the remaining `SCRIPT` pressure entirely. The specimen demonstrates that a backend-neutral real-time action simulation can be fully authored in Thestra without adding specific genre/engine capabilities.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: UP/DOWN to move paddle, Enter to restart, B to back.

Owner observations: (pending)
Result: (pending)
