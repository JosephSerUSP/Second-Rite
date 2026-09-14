### Experiment
B003 — Rearranging a Bedroom

### Result
complete

### Authored Surface
Authored as an independent Scene (`b003_bedroom.json`) utilizing standard UI windows (`list`, `frame`) alongside state management commands (`SET_VAR`, `IF`) and dynamic text formulations.

### SCRIPT / Native Escape Hatches
None. The declarative logic native to the current engine was completely sufficient for rendering UI options and resolving object states.

### Missing Reusable Semantics
None encountered during this implementation. The task fundamentally maps well to managing UI and setting variables.

### Awkward But Expressible
Writing extensive string interpolation rules (`{(v.urn == 2 and v.chair == 2) and ... or ...}`) in the narrative window is functional, but it could grow highly tedious to maintain for very large sets of complex overlapping combinations.

### Tooling / Discoverability Gaps
None explicitly encountered for this task, as we are manually building the JSON structures and there are no obscure parameters utilized.

### Backend Leakage
None. The implementation solely rests on abstracted UI rendering systems and variable logic evaluated by the declarative command handler.

### Project Leakage
None. The logic only uses localized terms and logic without referencing external project variables.

### Author Legibility
Yes. A competent RPG Maker-style event author would understand using list menus and conditional variable checks (using standard if-then logic mapping to variables representing object states) to trigger different textual events.

### Reusable Successes
The declarative string formulation for presentation text seamlessly incorporates variable logic (`{v.urn == 1 and 'Desk' or ...}`), eliminating the need for bulky condition-rendering SCRIPT code to represent these object combinations dynamically in the UI.

### Architecture Recommendation
no architecture change indicated
