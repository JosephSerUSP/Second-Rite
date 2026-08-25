### Experiment
B010 — Falling Blocks

### Result
partial but playable

### Authored Surface
`b010_falling_blocks.json`

### SCRIPT / Native Escape Hatches
- Grid representation (`v.board` as a 2D Lua table) and mutation.
- Collision detection and piece bounds checking.
- Board clearing logic and block falling.
- Custom input hooks utilizing SCRIPT to evaluate collision logic on move/drop.
Reason: The engine lacks 2D array native primitives and complex state manipulation commands to easily perform grid sweeps, collision queries, and multi-cell updates.

### Missing Reusable Semantics
- 2D grid/array operations (initialization, iteration, querying, mutation).
- Spatial collision checking against grid states.
- Timed events or loops that aren't tied to the fixed `on_frame` hook logic.

### Awkward But Expressible
- Drawing a grid using string accumulation is expressible but awkward.

### Tooling / Discoverability Gaps
- None distinct from runtime semantics.

### Backend Leakage
- Depends on Lua table semantics and index iteration order, although mitigated by explicitly iterating 0 to N-1.

### Project Leakage
- None. Isolated correctly in `projects/labs/scene-benchmarks`.

### Author Legibility
A competent event-oriented game author would struggle to understand the raw SCRIPT blocks unless they knew Lua. The overarching scene lifecycle (hooks) would make sense, but the core logic is entirely hidden behind the escape hatch.

### Reusable Successes
The `on_frame` update with a timer worked perfectly for a fixed-step tick engine. The window UI layout successfully rendered the output.

### Architecture Recommendation
candidate reusable semantic gap (Grid/Array state and manipulation primitives).

### Owner Playtest

**Status:** READY FOR OWNER PLAYTEST

**Launch Instructions:**
1. Launch the benchmark project using `npm run lab:benchmarks`.
2. Select "B010  Falling Blocks" from the main menu.
3. Use Arrow keys to move the block left/right, and up/down to drop the block.

**Owner Observations:**
*(Pending owner playtest)*

**Result:**
*(Pending owner playtest)*
