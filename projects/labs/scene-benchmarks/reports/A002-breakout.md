# Benchmark Report

### Benchmark
ID: A002
Name: Breakout
Benchmark Version: Initial Implementation
Date: 2026-08-17

### Current Result
playable with backend-specific authoring escape hatch

### Current Implementation Shape
Authored Scene composition renders a text-built `boardText` inside a window frame and uses the merged fixed Scene clock (`step=0.0166`). Logical `on_left` / `on_right` hooks author input intent. The core game loop, including brick array generation, physics, collision detection (ball vs paddle/bricks/bounds), and win/loss state, is entirely implemented in raw Lua `SCRIPT` blocks.

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 2
* approximate SCRIPT lines: ~95
* native source files modified: 0
* new generic semantic commands added: 0
* Project-owned files required: a002_breakout.json, index.json, title.json, terms.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: String-based tile rendering plus raw Lua SCRIPT for mutable simulation state, brick array tracking, and physics logic.
* unsupported benchmark requirements: None at the behavioral level; backend-neutral expression of the implementation is not achieved.
* whether Studio/normal authored surfaces were sufficient without raw backend code: No. The Scene JSON relies heavily on SCRIPT for collection management and state updates, which are backend-specific.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
First attempt.

### Improved
N/A (First Attempt)

### Regressed
N/A (First Attempt)

### Still Awkward
The presentation uses string-rendering, which is indirect for object simulation. The simulation itself relies heavily on raw Lua `SCRIPT`, notably for array-based collection mutation (`v.bricks = {}`, `table.insert`), physics, and intersection querying. These operations are not cleanly expressible via current declarative Event/Scene hooks, putting significant pressure on the author to retreat into backend code.

### New Architectural Evidence
A002 strongly corroborates the evidence from A001, A003, and D002 that Thestra currently lacks expressive backend-neutral semantic commands for managing collections (spawning, tracking, and removing multiple distinct entities) and generic 2D collision querying. The fixed clock and logical hooks work well, but state mutation for multiples of similar objects (bricks) is currently a notable gap.

### Verdict
**Playable benchmark; architectural partial success.** Like Pong, the scene host and lifecycle mechanics carry the project well, but the core implementation escapes into ~95 lines of raw backend Lua to manage the collections and physics. Land as longitudinal evidence indicating the need for collection/array-mutation commands and spatial-querying semantics without prematurely creating Breakout-specific engine behavior.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: LEFT/RIGHT to move paddle, Enter to restart.

Owner observations: (pending)
Result: (pending)
