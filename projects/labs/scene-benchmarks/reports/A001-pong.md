# Benchmark Report

### Benchmark
ID: A001
Name: Pong
Benchmark Version: Current Main Semantics
Date: 2026-08-28

### Current Result
complete

### Current Implementation Shape
Authored Scene composition that relies on formula-evaluated `rect` properties in the `windowLayout` system to render paddles and the ball. Uses the fixed Scene clock (`step=0.0166`) and logical input hooks (`on_up`, `on_down`). Update and collision logic are implemented natively with purely authored semantic commands (`SET_VAR` multi-assignments and `IF` blocks), replacing raw Lua entirely. Scene state is now safely encapsulated via inlined `on_enter` assignments, bypassing CI `run_hook` fall-throughs.

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
* Updated `time.dt` to `v.time.dt` in all formulas, properly adopting the exposed delta-time parameter during `on_frame` rather than relying on implicitly broken semantics.
* Inlined the initialization previously held in an external `init_state` hook directly into `on_enter` and `on_select`, as automated validation scenes silence custom hooks via `run_hook`, risking `nil` crashes in CI.
* Improved presentation legibility: factored heavy boolean collision conditions from the main `IF` statements up into descriptive variables (`hitPaddle1`, `hitPaddle2`) inside the `SET_VAR` block preceding them.
* Added `goldenScript` metadata for proper automated testing validation.

### Improved
* **Backend-neutrality:** The implementation is entirely decoupled from raw Lua, proving that Pong simulation rules can be elegantly written with semantic formulas, multi-assignments, and condition blocks.
* **Semantic Discoverability:** Breaking out collision evaluations into semantic state variables drastically improves the legibility of authored game logic over massive one-line strings of `and`/`or`.
* **Reliability:** By inlining initialization state to `on_enter`, the artifact avoids `nil` frame evaluation problems previously encountered under CI preview constraints.

### Regressed
None.

### Still Awkward
Continuous simulation still heavily taxes authored presentation. While cleanly implemented via `v.time.dt` scaling and multi-assignments, it produces heavily verbose JSON blocks that a typical node-based visual editor or traditional code environment would handle far more compactly.

### New Architectural Evidence
The ability for `resolveDim` to evaluate formulas natively for `rect.x` and `rect.y` in window layouts, coupled with intermediate state evaluations (`v.hitPaddle1`), provides a highly compositional pattern for real-time physics bounds checking without requiring new engine abstractions. The addition of `goldenScript` arrays to scenes also greatly facilitates CI assurance against authored behaviors.

### Verdict
**Complete architectural success.** The evolution of generic engine facilities (robust formula evaluation, `v.time.dt`, and dynamic window dimension support) has absorbed the remaining `SCRIPT` pressure entirely. The specimen demonstrates that a backend-neutral real-time action simulation can be fully authored in Thestra natively and legibly.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: UP/DOWN to move paddle, Enter to restart, B to back.

Owner observations: (pending)
Result: (pending)
