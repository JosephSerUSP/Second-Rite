# B008 — Riviera-Style Exploration Screen

### Experiment
B008 — Riviera-Style Exploration Screen

### Result
complete

### Authored Surface
- `projects/labs/scene-benchmarks/data/scenes/b008_exploration.json`
- `projects/labs/scene-benchmarks/data/terms.json` (for options text)

### SCRIPT / Native Escape Hatches
- `update_options`: Used to conditionally filter which options are visible based on scene state (`has_key`, `desk_checked`, `door_unlocked`). Thestra doesn't have an easy declarative way to selectively hide/show items from a single list based on complex combinations of state variables.
- `move_cursor_up` / `move_cursor_down`: Re-implemented cursor logic because we are filtering the visible options array via script, meaning the native `listId` indices don't perfectly map 1:1 if we used standard math for looping without checking array bounds of the filtered list.
- `handle_selection`: Evaluates the selection based on the dynamically filtered options array and sets string states, because the `SCENE_EVENT` or standard commands lack string interpolation building, and branching with many `IF` blocks inside the JSON is much more verbose.

### Missing Reusable Semantics
- Native filtering of list options: There's no easy way to provide a list of options in `terms.json` and selectively disable/hide them natively inside the list view without writing a Lua script to construct an array of valid indices (`optionsVisible`).

### Awkward But Expressible
- String updates and feedback messages require explicit Lua strings or awkward state assignment logic.

### Tooling / Discoverability Gaps
None explicitly, though authoring the cursor loop limits requires knowledge of the engine's list state variables if done natively vs in Lua.

### Backend Leakage
None. The logic only touches `sceneState`.

### Project Leakage
None. Contained entirely within the benchmark project.

### Author Legibility
An author would understand the high-level intent (an options list, changing text), but the reliance on Lua scripts to filter the options list breaks the visual declarative nature. They would need to understand how the `filter` property works with an array of indices.

### Reusable Successes
The `windows` rendering makes laying out the UI extremely easy. Using `{sceneState.status_text}` for data binding works perfectly.

### Architecture Recommendation
candidate reusable semantic gap

Consider adding a native way to conditionally show/hide options in a `listId` menu based on scene state variables without dropping into a `SCRIPT` block to build a filtered array.

### Owner Playtest

- **Current playtest status**: pending
- **Launch/control instructions**:
  - Run the benchmark launcher (`npm run lab:benchmarks` or `lovec <gateRoot>`).
  - Select "B008 Riviera Exploration" from the list.
  - Use Up/Down arrows to move the cursor through visible interaction options.
  - Press Enter (A) to select an interaction.
  - The scene concludes and returns when "Leave Room" is selected (which only appears after unlocking the door with the key).
- **Owner observations**: pending
- **Post-playtest result**: pending
