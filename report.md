### Experiment

B006 — Dialogue Portrait Stage

### Result

Complete

### Authored Surface

Scene `projects/labs/scene-benchmarks/data/scenes/b006_dialogue.json`
Terms `projects/labs/scene-benchmarks/data/terms.json`

### SCRIPT / Native Escape Hatches

None.

### Missing Reusable Semantics

None.

### Awkward But Expressible

None.

### Tooling / Discoverability Gaps

None.

### Backend Leakage

None.

### Project Leakage

None.

### Author Legibility

An event-oriented game author would likely find this composition understandable. The use of sequential variables (`v.step`) mixed with conditions and `SHOW_IMAGE_PICTURE`/`MOVE_IMAGE_PICTURE` clearly maps to typical visual novel and RPG dialogue staging workflows.

### Reusable Successes

The `SHOW_IMAGE_PICTURE` and `MOVE_IMAGE_PICTURE` commands successfully handled the portrait changes, shifts in focus, and positional movements elegantly. The condition evaluation within `IF` blocks cleanly controlled progression.

### Architecture Recommendation

No architecture change indicated.
