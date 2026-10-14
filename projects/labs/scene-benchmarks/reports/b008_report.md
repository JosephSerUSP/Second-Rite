### Experiment
B008 — Riviera-Style Exploration Screen

### Result
complete

### Authored Surface
The experiment was implemented as a single, authored Scene (`projects/labs/scene-benchmarks/data/scenes/b008_exploration.json`). It uses a `menu` kind scene with multiple presentation windows (title, description, and interaction choices) and authored states for progression.

### SCRIPT / Native Escape Hatches
Used SCRIPT in `init`, `move_cursor`, and `action` to iterate over available choices, evaluate whether a choice is available based on current state variables (`req_state`, `block_state`), map the cursor position to the selected choice, and update the display text dynamically.

### Missing Reusable Semantics
- **Collections/Iteration:** There is no native way for `sceneState` to iterate over a defined list of interaction targets and filter them based on condition flags.
- **Dynamic List Binding:** Cannot natively bind a UI list to a dynamically filtered subset of data. An author must convert the logical subset into a raw newline-delimited text string.

### Awkward But Expressible
State mutations (setting flags like `has_key` or `door_open`) and text updates are well supported conceptually, but stringing them together across arbitrary length interactive menu lists requires manual cursor clamping and manual list reconstruction on every action.

### Tooling / Discoverability Gaps
No specialized UI components for dynamic contextual action lists exist in the default toolset. The author must construct their own selector UI out of primitive text blocks and cursor math.

### Backend Leakage
The SCRIPT logic heavily relies on Lua table primitives (`ipairs`, `table.insert`, `table.concat`). If the backend changed languages, this list-processing string-building logic would have to be ported directly.

### Project Leakage
None. Everything is self-contained within the scene json and the local index.

### Author Legibility
An event author would understand the state variables (`has_key`, `door_open`) and the general concept of hiding/showing choices, but the specific implementation logic (manual index tracking, `math.max`, array filtering) written in SCRIPT is opaque. A true RPG Maker equivalent would be a "Show Choices" command that conditionally hides rows, which is fundamentally cleaner.

### Reusable Successes
The `windows` rendering primitives cleanly support creating an isolated UI layout. `SET_SCENE_STATE` provides a consistent place to hold exploration logic state across frames.

### Architecture Recommendation
candidate reusable semantic gap
