### Experiment

B008 — Riviera-Style Exploration Screen

### Result

complete

### Authored Surface

- `b008_riviera.json`
- added to `title.json` and `terms.json`

### SCRIPT / Native Escape Hatches

None. The experiment was entirely authored using `SET_VAR` and `IF` logic.

### Missing Reusable Semantics

None encountered. The scene system allows for UI-based event manipulation effectively.

### Awkward But Expressible

Constructing a stateful menu by dynamically altering text based on variables (e.g. `{v.desk_unlocked == 1 and 'Unlocked' or 'Locked'}`) works, but maintaining cursor state bounds manually (e.g., `v.cursor == 1 and 4 or v.cursor - 1`) and writing long inline expressions in UI descriptions scales poorly. Using `SET_LIST` might be cleaner for very large dynamic menus, but writing inline conditionals for individual `content` block labels suffices for prototypes.

### Tooling / Discoverability Gaps

None.

### Backend Leakage

None. All logic is expressed through semantic declarative commands and standard UI elements.

### Project Leakage

None. The prototype depends only on standard presentation widgets and variables local to its own scene.

### Author Legibility

Yes. The structure is familiar to event-driven designers. Managing state flags (`has_key`, `desk_unlocked`) and wrapping the cursor index in explicit commands is very readable. Changing text color and options conditionally based on these flags maps well to classic exploration puzzle flows.

### Reusable Successes

Using inline conditionals for dynamic labels inside `{}` blocks is very powerful, as is the declarative UI model which allows immediate redrawing of conditions without needing to destroy and recreate UI elements or explicitly call refresh.

### Architecture Recommendation

no architecture change indicated
