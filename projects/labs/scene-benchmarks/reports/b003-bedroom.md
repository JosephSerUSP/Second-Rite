### Experiment
B003 — Rearranging a Bedroom

### Result
complete

### Authored Surface
A new standalone scene, `b003_bedroom.json`, integrated into the benchmark menu. The scene utilizes `sceneState` variables to store item placement on specific slots (desk, bed, shelf) and displays text based on the object arrangement.

### SCRIPT / Native Escape Hatches
- `update_narrative`: A small script to execute conditional logic mapping the current arrangement combinations to specific textual narrative lines.
- `swap_item`: A script to cycle objects between slots array-style.
These were used to handle multi-variable conditional narrative switching and collection swapping, which could be cumbersome to express using only raw `IF`/`SET_SCENE_STATE` commands.

### Missing Reusable Semantics
- A native way to shuffle or swap specific list/dictionary entries inside `sceneState`.
- Data-driven text matching (e.g., condition grids) without writing `if/elseif` chains in SCRIPT for narrative updates based on multiple state values.

### Awkward But Expressible
- State variable comparisons mapping to text strings work fine via `IF` commands but quickly scale out of control for spatial combinations, hence the SCRIPT hatch usage.

### Tooling / Discoverability Gaps
- It's somewhat tedious to visualize multi-variable states on a window layout without explicit text-binding blocks in Studio.

### Backend Leakage
- None. The SCRIPT block logic manipulates basic Lua tables and strings securely.

### Project Leakage
- None. Stays completely within the Scene Benchmarks project scope.

### Author Legibility
An RPG Maker author would easily understand this structure as it parallels using generic Event Variables for item IDs and updating text boxes via a Parallel Process or conditional branches. Using an explicit SCRIPT block rather than native event conditionals is the only slight departure, but perfectly readable.

### Reusable Successes
The UI frame system dynamically displaying interpolated strings (`{sceneState.narrative_1}`) worked wonderfully to automatically reflect background state shifts without manual text redraw commands.

### Architecture Recommendation
candidate reusable semantic gap

### Owner Playtest
- Status: READY FOR OWNER PLAYTEST
- Instructions: Launch the benchmark via `npm run lab:benchmarks`. Select "B003 Rearranging a Bedroom". Use arrow keys to select slots, Enter to cycle/swap items, and B to return. Observe the dynamic narrative text changes as the bedroom arrangement changes.
- Observations: [pending]
- Result: [pending]
