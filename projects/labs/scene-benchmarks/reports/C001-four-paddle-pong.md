# Benchmark Report

### Benchmark
ID: C001
Name: Four-Paddle Pong
Benchmark Version: Current Main Semantics
Date: 2026-10-18

### Current Result
complete

### Current Implementation Shape
Authored Scene composition that relies on formula-evaluated `rect` properties in the `windowLayout` system to render 4 paddles and the ball. Uses the fixed Scene clock (`step=0.0166`) and logical input hooks (`on_up`, `on_down`, `on_left`, `on_right`). Update and collision logic are implemented natively with purely authored semantic commands (`SET_SCENE_STATE` multi-assignments and `IF` blocks), replacing raw Lua entirely.

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 0
* approximate SCRIPT lines: 0
* native source files modified: 0
* new generic semantic commands added: 0
* Project-owned files required: c001_four_paddle_pong.json, index.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: None.
* unsupported benchmark requirements: None.
* whether Studio authoring surfaces were sufficient: Yes, JSON structure maps perfectly to standard semantic blocks.
* whether the artifact runs independently of Second Gate: Yes.

### SCRIPT / Native Escape Hatches
None used.

### Missing Reusable Semantics
None

### Awkward But Expressible
Like A001, continuous simulation still heavily taxes authored presentation. While cleanly implemented via `sceneState.time.dt` scaling and multi-assignments, it produces heavily verbose JSON blocks that a typical node-based visual editor or traditional code environment would handle far more compactly. The collision detection logic involves repetitive manual bounds checking.

### Tooling / Discoverability Gaps
None.

### Backend Leakage
None.

### Project Leakage
None.

### Author Legibility
Yes, a competent event-oriented game author could understand the resulting composition. The collision evaluation is broken out into semantic state variables (`hitPaddle1` etc), which greatly improves the legibility of the logic.

### Reusable Successes
The ability for `resolveDim` to evaluate formulas natively for `rect.x` and `rect.y` in window layouts.

### Architecture Recommendation
no architecture change indicated

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: UP/DOWN L-pad, L/R B-pad, Enter to reset, B back.

Owner observations: (pending)
Result: (pending)
