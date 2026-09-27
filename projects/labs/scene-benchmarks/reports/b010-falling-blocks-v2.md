### Experiment
B010 — Falling Blocks

### Result
partial but playable

### Authored Surface
`data/scenes/b010_falling_blocks.json` (inside `projects/labs/scene-benchmarks`)

### SCRIPT / Native Escape Hatches
- `draw_board`: SCRIPT used to read the 140 flat variables (`grid_y_x`) and the piece state to render the text board representation.
- `check_collision_and_lock`: SCRIPT used to perform collision checks on the falling piece against the flat board variables, lock the piece, and perform row clearing by shifting flat variable states down.
- `input_left`, `input_right`, `input_down`, `input_up`: SCRIPT used to perform bounds/collision checks and update piece coordinates based on input.
Reason: 2D grids and piece geometries cannot be easily iterated, queried, or mutated using flat variables without native collection/array primitives. SCRIPT remains the only practical way to write the core logic.

### Missing Reusable Semantics
- Native 2D grid/array representation and primitives.
- Matrix querying/updating (e.g., sweep clearing rows, checking subsets).
- Collection mutation (indexed read/write) in formulas and event commands.

### Awkward But Expressible
- Storing a 10x14 board as 140 separate variables (`grid_0_0` through `grid_13_9`) is expressible but completely unergonomic and scales poorly.

### Tooling / Discoverability Gaps
- None distinct from runtime semantics.

### Backend Leakage
- Index iteration relies on raw Lua `for` loops within SCRIPT due to the lack of declarative array iteration or querying.

### Project Leakage
- None. Fully isolated to the neutral `projects/labs/scene-benchmarks` Project.

### Author Legibility
An author without programming experience would find the flat variable workaround incomprehensible once they realized they need Lua loops to practically interact with them. It reads like a backend script rather than an RPG Maker-style composition of commands.

### Reusable Successes
- Scene-local state variables (`v.pieceX`, `v.lost`, `v.tickTimer`) survive hook calls and are cleanly separated from persistent data.
- Fixed-step `update` mode cleanly powers the game loop tick.
- Formula-driven text interpolation (`"{v.boardText}"`) binds the complex state to the UI without requiring a custom rendering layer.

### Architecture Recommendation
candidate reusable semantic gap (Array, List, and Grid data structures and operations).

### Owner Playtest
**Status:** READY FOR OWNER PLAYTEST

**Launch Instructions:**
1. Run `npm run lab:benchmarks`.
2. Select "B010 Falling Blocks".
3. Use arrows to move/drop, B to back.

**Owner Observations:**
*(Pending owner playtest)*

**Result:**
*(Pending owner playtest)*
