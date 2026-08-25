### Experiment
B010 — Falling Blocks

### Result
partial but playable

### Authored Surface
`b010_falling_blocks.json`

### SCRIPT / Native Escape Hatches
- SCRIPT used for drawing the grid representation from the flat `SET_VAR` variables into a single text block (`v.boardText`).
- SCRIPT used for collision detection and bounds checking against flat variable spaces.
Reason: While the grid can technically be stored as 140 individual flat variables (`grid_0_0` to `grid_13_9`), manually performing loops or bounds checks across these variables is practically impossible using only `SET_VAR` and `IF` nodes, leading to heavily reliance on Lua scripting.

### Missing Reusable Semantics
- Native 2D grid/array representation and primitives.
- Matrix querying/updating (e.g. sweep clearing rows).

### Awkward But Expressible
- Storing a 10x14 board in the engine as 140 separate variables (`grid_y_x`). This is possible but severely limits dynamic sizing and makes interaction outside of SCRIPT completely unwieldy.

### Tooling / Discoverability Gaps
- None distinct from runtime semantics.

### Backend Leakage
- Index iteration relies on Lua `for` loops in scripts due to lack of native looping structures over variables.

### Project Leakage
- None. Fully isolated.

### Author Legibility
An author without programming experience would find the flat variables confusing once they realized they need loops in raw Lua to interact with them effectively.

### Reusable Successes
- The `on_frame` fixed-step timing using a state variable (`v.tickTimer`) functions perfectly for game ticks.

### Architecture Recommendation
candidate reusable semantic gap (Array and Grid data structures and operations).

### Owner Playtest
**Status:** READY FOR OWNER PLAYTEST

**Launch Instructions:**
1. Run `npm run lab:benchmarks`.
2. Select "B010 Falling Blocks".
3. Arrows to move/drop.

**Owner Observations:**
*(Pending owner playtest)*

**Result:**
*(Pending owner playtest)*
