### Experiment

B008 — Riviera-Style Exploration Screen

### Result

complete

### Authored Surface

A single composed Scene (`projects/labs/b008-riviera-exploration/data/scenes/map.json`) handling exploration through a list menu UI (fountain, chest). State is managed via Scene hooks (`on_enter`, `on_up`, `on_down`, `on_select`) and conditional execution. The project terms file (`data/terms.json`) provides the localizations for the interaction options.

### SCRIPT / Native Escape Hatches

None. The prototype was built purely using `SET_SCENE_STATE`, `IF`, standard message commands, and formula-driven text presentation.

### Missing Reusable Semantics

None identified. The formula evaluation and scene state interpolation handles navigation indices and conditional text updates without issue.

### Awkward But Expressible

Manually routing directional inputs (e.g., `on_up`, `on_down`) to increment/decrement a list cursor index (`sceneState.idx`) using formulas (`sceneState.idx > 1 and sceneState.idx - 1 or 2`) requires some boilerplate boundary checks. Also, using string conditionals within the `{expr:...}` token for UI text updates can become unwieldy for larger sets of options.

### Tooling / Discoverability Gaps

The engine handles the execution cleanly, but Studio lacks a semantic "Context Menu" or "Exploration Points" widget out of the box, requiring manual list or index construction and manual state-to-cursor binding.

### Backend Leakage

None. The state mutations and input bindings are perfectly isolated in the JSON scene schema.

### Project Leakage

None. The project was constructed entirely using the minimal-project-template.js isolated from Second Gate.

### Author Legibility

A competent event-oriented author would recognize this as a finite-state machine mapping input events to state mutations, rendered via a generic window list. While slightly more abstract than literal walking, the composition using a menu and conditional messages is straightforward and common in classic RPGs.

### Reusable Successes

The `SET_SCENE_STATE` command, combined with inline formulas (`sceneState.idx > 1 and sceneState.idx - 1 or 2`), made bounded directional cycling trivial. The `{expr:...}` token in text fields successfully updated descriptions dynamically based on the current selection.

### Architecture Recommendation

no architecture change indicated
