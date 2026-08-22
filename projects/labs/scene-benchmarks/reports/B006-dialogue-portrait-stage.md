### Experiment
B006 — Dialogue Portrait Stage

### Result
- complete;
- playable via benchmark launcher.

### Authored Surface
- `projects/labs/scene-benchmarks/data/scenes/b006_dialogue.json`
- `projects/labs/scene-benchmarks/data/terms.json`
- `projects/labs/scene-benchmarks/data/scenes/title.json` (integrated)
- Copied assets into `projects/labs/scene-benchmarks/assets/`

### SCRIPT / Native Escape Hatches
None. Used the existing `SHOW_IMAGE_PICTURE`, `MOVE_IMAGE_PICTURE`, and `ERASE_IMAGE_PICTURE` primitives directly via standard JSON event commands inside `b006_dialogue.json`. Used `SET_VAR` to track step, choice index, and logic state, driving UI via formula transforms in text blocks.

### Missing Reusable Semantics
None identified for this scope. The current semantic vocabulary was able to express dynamic portraits (showing, hiding, moving, changing opacity/scale) based purely on logic conditions evaluated on UI action callbacks (`on_select`, `on_up`, `on_down`).

### Awkward But Expressible
Building a purely "step-based" progression requires creating a `custom` hook (`update_step` in my case) which is recursively called from `on_select` / `on_enter` and consists of sequential `IF` conditions for each step state. A state machine or switch/case equivalent mechanism could potentially make step-oriented linear logic cleaner.

### Tooling / Discoverability Gaps
None for manual JSON authoring.

### Backend Leakage
None. Used standard image manipulation commands.

### Project Leakage
The experiment copies standard NPC portrait art from `hichaukitoden-game` to isolate the benchmark rather than depending on paths into the other project.

### Author Legibility
Yes. A competent event-oriented game author would easily recognize the logic structure: "When the player advances text, change a step variable; when a step variable equals X, change text and move pictures."

### Reusable Successes
The `MOVE_IMAGE_PICTURE` command handling asynchronous/duration-based transitions seamlessly in the background while standard menu logic waits for input is extremely solid. Formula transforms in `{v.speakerName}` and `{v.dialogueText}` naturally bridge the gap between underlying state and UI text fields without needing bespoke callbacks.

### Architecture Recommendation
no architecture change indicated;

## Owner Playtest

- **Playtest Status:** READY FOR OWNER PLAYTEST
- **Instructions:** Launch the lab benchmarks `npm run lab:benchmarks` or run the scene benchmarks project, select `B006 Dialogue Portrait Stage`. Advance dialogue using Enter/Select; you will see portraits move, scale, and crossfade based on who is speaking. At the end, you can make a choice (or conclude) using arrows and Enter/Select.
- **Observations:** (Pending)
- **Result:** (Pending)
