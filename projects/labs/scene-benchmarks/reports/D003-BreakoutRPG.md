
### Experiment
D003 - Breakout as RPG Encounter Metaphor

### Result
complete

### Authored Surface
- Scene definition (`d003_breakout_rpg.json`) driving state and UI
- `title.json` updated to link to the new scene
- `terms.json` updated with the option for the main menu list.

### SCRIPT / Native Escape Hatches
1. `init` script to initialize variables for board logic. This requires complex looping and table creation for the 2D grid/skeletons which the declarative logic doesn't support well natively.
2. `execute_turn` script that computes the movement of the 'ward' and the 'bolt'. This handles collisions logic against the bounds, and enemies natively. Again, physics (even simplistic 2D cell-based physics) does not exist in standard event commands so custom logic via SCRIPT was necessary.

### Missing Reusable Semantics
No semantics are missing to get this specific prototype done because Lua gives me full control, however there is no built-in engine way for grid or coordinate based movement/physics.

### Awkward But Expressible
Using strings to map the array structures for rendering. The engine lacks multi-dimensional arrays or grid structures out of the box, requiring a dictionary of `[x]_[y]` formatted strings for entity positional tracking and lookup.

### Tooling / Discoverability Gaps
There is no visual tooling for drawing abstract shapes, characters, or bounding areas.

### Backend Leakage
Using normal string concatenation and Lua table manipulation. I've avoided any LOVE-specific commands so it should be backend portable.

### Project Leakage
Self-contained under `projects/labs/scene-benchmarks`. I explicitly placed the `d003_breakout_rpg.json` inside the benchmark project folder alongside existing samples.

### Author Legibility
A game author would find this mostly confusing as it's almost entirely custom Lua embedded in JSON. It uses hooks (`on_up`, `on_down`, `on_select`) perfectly, but the actual body of the code heavily relies on understanding standard programming logic for updating frames, rather than event triggers.

### Reusable Successes
The hook architecture (`on_select`, `on_up`, `on_down`) is very responsive for building turn-based menus out of thin air. The text injection into window components (`{v.boardText}`) perfectly displays dynamic UI boards.

### Architecture Recommendation
no architecture change indicated

### Owner Playtest

- **Status:** READY FOR OWNER PLAYTEST
- **Launch:** Run `npm run lab:benchmarks` and select `D003  Breakout RPG`
- **Observations:** [pending]
- **Result:** [pending]
