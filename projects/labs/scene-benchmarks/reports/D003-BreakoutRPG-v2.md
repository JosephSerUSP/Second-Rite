### Experiment
D003 - Breakout as RPG Encounter Metaphor

### Result
complete

### Authored Surface
`projects/labs/scene-benchmarks/data/scenes/d003_breakout_rpg.json` (Authored Scene using menu kind, windows draw mode, IF blocks, and SET_VAR multi-assignments).

### SCRIPT / Native Escape Hatches
None. The previous implementation heavily relied on Lua SCRIPT blocks for the game loop and board rendering. This re-authored version replaces all Lua scripts with purely declarative scene hooks (`on_enter`, `on_select`) using `SET_VAR` and `IF` commands.

### Missing Reusable Semantics
- **Collection Iteration / Arrays:** The engine lacks the ability to iterate over arrays or match spatial properties declaratively in `SET_VAR` or `IF`. As a result, checking collision against 15 skeletons required 15 explicit `IF` blocks.
- **Dynamic Variable Keys:** We cannot access variables by dynamic string keys (e.g., `v["sk_" .. x .. "_" .. y]`). This forces hardcoded variables and checks for every single skeleton (`sk_1_3`, `sk_2_3`, etc).

### Awkward But Expressible
- **Complex String Building:** Generating the 5x5 text-based board with elements (bolt, ward, skeletons) in `SET_VAR` is possible using Lua string concatenation (`..`) within a single formula assignment. However, it requires an extremely long and rigid ternary string, manually accounting for every cell across 6 row variables.

### Tooling / Discoverability Gaps
- Creating the 15 skeleton state variables and the 15 collision check branches is practically impossible to author efficiently in the current visual Studio editor without array iteration features. It currently requires a generative script or manual JSON editing.

### Backend Leakage
- The formula evaluations heavily rely on Lua's specific ternary-like short-circuiting syntax (`cond and a or b`) and its string concatenation operator (`..`). This tightly couples the JSON definitions to the Lua backend, complicating a potential transition to a non-Lua backend.

### Project Leakage
- None. The scene relies purely on its own local state variables and standard scene engine capabilities.

### Author Legibility
An event-oriented game author might easily read the turn physics (updating X/Y positions and `IF` checking bounces), but they would likely find the giant string concatenation formulas for the text board rendering unreadable and overly complex compared to typical RPG Maker string variable features.

### Reusable Successes
- The `SET_VAR` multi-assignment coupled with `IF` sequential processing cleanly handled the physics game loop (movement, bouncing off walls, updating coordinates) in a single frame's `on_select` execution without race conditions.
- Formula strings support full native math (`min`, `max`), which made clamping the ward's movement effortless.
- The declarative window renderer seamlessly handled dynamic multiline text updates whenever the `boardText` string was modified by `SET_VAR`.

### Architecture Recommendation
candidate reusable semantic gap
