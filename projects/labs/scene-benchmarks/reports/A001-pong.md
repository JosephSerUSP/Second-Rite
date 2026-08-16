# Benchmark Report

### Benchmark
ID: A001
Name: Pong
Benchmark Version: Initial Implementation
Date: 2026-08-16

### Current Result
complete

### Current Implementation Shape
Authored scene utilizing text string building in `boardText` rendered via window frame, updated with a `fixed` mode loop (`step=0.0166`). Movement and collisions are handled continuously inside Lua `SCRIPT` block within `on_frame`. Controls are updated via logic input `on_up`, `on_down` incrementing `inputY`.

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 2
* approximate SCRIPT lines: ~70
* native source files modified: 0
* new generic semantic commands added: 0
* Project-owned files required: a001_pong.json, index.json, title.json, terms.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: String-based tile rendering due to lack of custom draw capabilities.
* unsupported benchmark requirements: None
* whether Studio authoring surfaces were sufficient: Yes, fully authored in JSON.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
First attempt.

### Improved
N/A (First Attempt)

### Regressed
N/A (First Attempt)

### Still Awkward
Rendering continuous objects via text string grid inside a frame is somewhat awkward but perfectly functional. True continuous sprite positioning within an authored Scene (outside of battles/maps) remains unsupported without breaking out into pure Lua draw layers.

### New Architectural Evidence
Continuous update (`on_frame`) coupled with string interpolation for UI frames works efficiently for retro-style textual representations of physical game state.

### Verdict
The engine handles text-based custom real-time rendering successfully inside its UI frame paradigm via variable interpolation, proving custom interactive mini-games are possible without leaking to the backend.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: UP/DOWN to move paddle, Enter to restart.

Owner observations: (pending)
Result: (pending)
