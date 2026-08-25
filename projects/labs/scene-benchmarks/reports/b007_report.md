### Experiment
B007 — Tactics Microboard

### Result
complete

### Authored Surface
The experiment was implemented as a single, authored Scene (`projects/labs/scene-benchmarks/data/scenes/b007_tactics.json`). It uses a menu-kind scene with multi-window presentation (one for instructions, one for text board rendering, and one for a status header).

### SCRIPT / Native Escape Hatches
Extensive use of SCRIPT in `init`, `move_cursor`, `action`, and `cancel_action`.
- Reason: The current Thestra standard formula evaluator and semantic surface (like `SET_VAR`) is unable to represent complex grid arrays, compute manhattan distance dynamically between variables, or iterate over a collection of units with complex object state.
- Thus, raw Lua blocks were employed to handle unit movement constraints, state mutation (HP manipulation), and rendering logic (converting a table of units and a conceptual grid into text presentation).

### Missing Reusable Semantics
1. **Collections / Entities:** There are no native data structures available to normal authored variables for lists or entity components. SCRIPT is the only way to manage a collection of independent units that each have position, stats, and identity.
2. **Grid Mathematics:** Reusable grid functions for range checking, pathing, and collision are completely absent.
3. **Loops / Finding Data:** Finding a unit at (X, Y) required writing a `for` loop in Lua because engine variables do not support associative maps or search patterns on collections.

### Awkward But Expressible
Using simple variables for Cursor X/Y and Delta X/Y (`dx`/`dy`) through `SET_VAR` across multiple directional hooks is verbose but very clean conceptually. However, deferring to Lua for bounds checking immediately highlights the awkwardness of not having max/min clamping within `SET_VAR` math safely available.

### Tooling / Discoverability Gaps
There is currently no convenient way to view the output of `SCRIPT` debugging outside of the text UI. Authoring Lua strings via JSON is extremely unpleasant.

### Backend Leakage
- The SCRIPT assumes the Lua environment structure, particularly using raw mathematical operators like `math.abs` and `ipairs`. If ported to a completely different language structure without a full Lua wrapper, these loops and math calls would fail or require tedious reimplementation.

### Project Leakage
No leakage. Everything stays contained within `b007_tactics.json`, `index.json`, and `terms.json` in the `scene-benchmarks` lab folder.

### Author Legibility
An RPG Maker dev would easily understand the general structure of Event Hooks (`on_up`, `on_down`, `on_select`), but the moment they peek inside `init` or `action` they'd encounter raw Lua instead of intuitive commands like "Set Variable Array", "Check Distance", or "Get Event at Position". The event hooks themselves are highly legible; the implementation underneath is not.

### Reusable Successes
The hook architecture natively handling discrete inputs (`on_left`, `on_right`, etc.) and guarding them with `_guard` works robustly. The multi-window rendering layout allows cleanly isolating UI states into distinct presentation boxes. `SCENE_EVENT` easily allowed popping out or integrating into the lab without any friction.

### Architecture Recommendation
candidate reusable semantic gap
