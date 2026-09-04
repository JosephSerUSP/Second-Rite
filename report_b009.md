## B009 — Parasite-Eve-Like Positioning Proof (Fresh Rewrite)

### Experiment
B009 — Parasite-Eve-Like Positioning Proof

### Result
complete

### Authored Surface
- `projects/labs/scene-benchmarks/data/scenes/b009_positioning.json`

### SCRIPT / Native Escape Hatches
None. Completely replaced previously existing `SCRIPT` blocks with authored `SET_VAR` (using `HELPERS` functions natively) and `IF` conditions. The lifecycle is driven fully by `on_frame` updates and formulas handling bounds checks.

### Missing Reusable Semantics
None found for this experiment.

### Awkward But Expressible
State updates relying heavily on nested conditional `IF`s and `SET_VAR` assignments can be quite verbose in raw JSON.

### Tooling / Discoverability Gaps
No specific discovery gap encountered.

### Backend Leakage
None. Handled cleanly within generic semantic scene rules.

### Project Leakage
Isolated inside `scene-benchmarks`. Doesn't require Second Gate assets.

### Author Legibility
Yes, though slightly verbose due to JSON. The concepts map naturally to RPG-Maker-like event systems (if statements, variable assignments with formulas, key wait/actions).

### Reusable Successes
The formula evaluation string handling (`HELPERS` functions like `min`, `max`, `abs`) provided by Thestra enables declarative native logic replacements that previously needed `SCRIPT`. The layout parser correctly handles dynamic string evaluation for positions like `"x": "2 + 1 + v.px"`.

### Architecture Recommendation
no architecture change indicated
