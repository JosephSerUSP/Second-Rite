# Benchmark Report

### Benchmark
ID: A001
Name: Pong
Benchmark Version: Current Main Semantics
Date: 2026-09-08

### Current Result
complete

### Current Implementation Shape
A complete fresh reconstruction of A001 using authored Scene composition. Relies on formula-evaluated `rect` properties in the `windowLayout` system to render paddles and the ball. Uses the fixed Scene clock (`step=0.0166`) and logical input hooks (`on_up`, `on_down`). The update and collision logic are implemented entirely natively with semantic commands (`SET_VAR` multi-assignments and `IF` blocks), replacing Lua entirely. Uses inline `clamp()` and `abs()` formula helpers for bounds checking and velocity constraints.

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 0
* approximate SCRIPT lines if any: 0
* native source files modified: 0
* new generic semantic commands added, if independently justified: 0
* Project-owned files required: a001_pong.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: None.
* unsupported benchmark requirements: None.
* whether Studio authoring surfaces were sufficient: Yes, JSON structure maps perfectly to standard semantic blocks.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
* Re-implemented freshly.
* Leveraged the `clamp()` helper inside the `SET_VAR` string formulas for paddle movement bounds, replacing `max(0, min(v.gridH - v.paddleH, ...))`.
* Used `abs()` in velocity reversal to ensure the ball always bounces outward from the paddle.
* Consolidated the top and bottom wall bounds check into a single `IF` condition, clamping the `ballY` value directly on collision.

### Improved
* **Formula Elegance:** Using the native `clamp()` helper inside the `SET_VAR` string formulas cleans up boundary constraints compared to manual `max(0, min(...))` calls.
* **Semantic Discoverability:** Breaking out collision evaluations and combining bounds checks into grouped operations improves legibility of authored logic.

### Regressed
None.

### Still Awkward
Continuous simulation still forces somewhat verbose declarative logic, though the introduction of mathematical helpers like `clamp()` and `abs()` noticeably reduces boilerplate.

### New Architectural Evidence
The continuous evolution of generic mathematical helpers (`clamp`, `abs`) within the robust formula evaluation system continues to cleanly absorb requirements that otherwise pressure developers to drop down to `SCRIPT`.

### Verdict
**Complete architectural success.** The addition of standard mathematical formula helpers keeps action-simulation authored semantics legible.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: UP/DOWN to move paddle, Enter to restart, B to back.

Owner observations: (pending)
Result: (pending)
