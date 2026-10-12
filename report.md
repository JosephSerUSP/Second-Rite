### Experiment
B005 — Lockpicking

### Result
complete;

### Authored Surface
`projects/labs/scene-benchmarks/data/scenes/b005_lockpicking.json` was rewritten. The initialization (`on_enter`), update timing/bouncing (`on_frame`), and input handling/hit detection (`on_select`) were migrated from raw Lua SCRIPTs to native Thestra command graphs using multiple `SET_SCENE_STATE` commands and `IF` nodes.

### SCRIPT / Native Escape Hatches
A single SCRIPT block named `render` remains in `on_frame`. Reason: Thestra lacks native primitive commands or string-building logic for arrays/string loops. The ASCII art rendering of the lockpicking bar (`[----+====+----]`) still relies on Lua to dynamically construct the string based on needle and sweet-spot states.

### Missing Reusable Semantics
No declarative string building or array-manipulating commands are available in the engine, forcing string formatting loops into SCRIPT. Furthermore, `SET_SCENE_STATE` lacks a way to update multiple state variables simultaneously, forcing large sequences of singular set commands during initialization.

### Awkward But Expressible
Updating `cursor_pos` via delta-time (`sceneState.time and sceneState.time.dt or (1/60)`) works in `SET_SCENE_STATE` formulas, but the formula gets very long as it cannot easily reference intermediate computation step variables inside the command tree.

### Tooling / Discoverability Gaps
Without an `assignments` array, setting up initial scene state is very verbose.

### Backend Leakage
The `render` script relies on standard Lua string concatenation (`..`), which is standard Lua, but any backend not based on Lua would need a way to parse/execute this escape hatch.

### Project Leakage
None. It runs fully isolated in `projects/labs/scene-benchmarks`.

### Author Legibility
A competent event-oriented game author would easily understand the `on_enter` state assignments and the `on_select` IF branching for hit detection. The movement logic in `on_frame` is mostly legible, though relying on a formula for delta-time makes it slightly messier. The string-rendering script would be opaque to a purely event-based author without code experience.

### Reusable Successes
The nested `IF` structure effectively handles the win/loss state branches naturally.

### Architecture Recommendation
candidate reusable semantic gap; (String formatting / primitive UI-bar widget representation to replace the ASCII string loop, and multi-assignment functionality for `SET_SCENE_STATE`).
