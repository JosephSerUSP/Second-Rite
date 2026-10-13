### Experiment

B006 — Dialogue Portrait Stage

### Result

complete

### Authored Surface

- `projects/labs/scene-benchmarks/data/scenes/b006_dialogue.json`
- `projects/labs/scene-benchmarks/assets/b006_celina.png`
- `projects/labs/scene-benchmarks/assets/b006_merchant.png`

### SCRIPT / Native Escape Hatches

None.

### Missing Reusable Semantics

The `SHOW_IMAGE_PICTURE`, `MOVE_IMAGE_PICTURE`, and `ERASE_IMAGE_PICTURE` commands provided a sufficient vocabulary for positioning and fading character portraits dynamically during the scene. No engine gaps were encountered for the core requirements.

### Awkward But Expressible

Advancing dialog states cleanly without legacy `update_step` behavior required setting `locals._guard` flags to prevent multiple interactions from advancing the step simultaneously. Moving multiple portraits seamlessly across frames required explicit coordination of durations and easings in separate sequential commands within the same event block.

### Tooling / Discoverability Gaps

Discovering the exact structure of picture commands and valid easing types required reading engine internals. A schema or autocomplete definition in the Studio would make authoring these visual sequences significantly less error-prone.

### Backend Leakage

None. The picture coordinates, opacities, and scales are declarative and should translate to any backend capable of rendering sprites on a screen layer.

### Project Leakage

None. All picture assets used are contained entirely within `projects/labs/scene-benchmarks/assets/`.

### Author Legibility

A competent event-oriented game author would readily understand the scene structure. It composes standard RPG Maker-style visual manipulation commands (Show/Move/Erase Picture) combined with simple state variables to track the dialogue progression step.

### Reusable Successes

The declarative `SHOW_IMAGE_PICTURE` and `MOVE_IMAGE_PICTURE` commands handled the design beautifully. The fact that the entire demonstration required zero Lua `SCRIPT` blocks is a strong vindication of the current presentation command semantics.

### Architecture Recommendation

no architecture change indicated

### Owner Playtest

**Status:** pending

**Instructions:** Launch the benchmark project and select "B006 Dialogue Portrait Stage" from the title menu. Press the interaction button to advance the dialogue and observe the portrait transitions. Choose an option when prompted.

**Observations:** pending

**Outcome:** pending
