### Experiment
D003 - Breakout as RPG Encounter Metaphor

### Result
complete

### Authored Surface
- Scene definition (`d003_breakout_rpg.json`) driving state and UI

### SCRIPT / Native Escape Hatches
None. The entire scene is authored declaratively via `IF` and `SET_SCENE_STATE` commands attached to `on_enter`, `on_up`, `on_down`, and `on_select` hooks.

### Missing Reusable Semantics
- Native random number generation is not exposed to formula strings without relying on `math.random` implicitly, prompting the use of a simple linear congruential generator stored in `sceneState.rng` for predictable pseudo-randomness across rounds.

### Awkward But Expressible
Nothing particularly awkward in this new iteration; replacing the spatial 2D collision simulation of previous iterations with an abstracted RPG "Stance" vs "Attack Lane" system mapped flawlessly to menu semantics.

### Tooling / Discoverability Gaps
None for this iteration.

### Backend Leakage
The use of Lua's ternary syntax (`cond and a or b`) inside formulas is standard for the engine but leaks the Lua syntax to the user.

### Project Leakage
Self-contained under `projects/labs/scene-benchmarks`.

### Author Legibility
Extremely legible. A standard RPG event author could easily trace the turn logic: update selection with Up/Down, resolve combat math and bounce deflection in Select, and read the dynamic UI bindings natively. The removal of the giant spatial layout strings greatly improved readability.

### Reusable Successes
- The `SET_SCENE_STATE` command cleanly supports complex multi-assignments.
- UI data binding using `{sceneState.var}` expressions worked perfectly for dynamically updating HP, counters, and event log text on each turn.
- Formula expressions handled the custom RNG math effectively.

### Architecture Recommendation
no architecture change indicated

### Owner Playtest
- **Status:** READY FOR OWNER PLAYTEST
- **Launch:** Run `npm run lab:benchmarks` and select `D003  Breakout RPG`
- **Observations:** [pending]
- **Result:** [pending]
