### Experiment
B003 — Rearranging a Bedroom

### Result
complete

### Authored Surface
- `b003_bedroom.json` for the Scene logic, state, presentation, and hooks.
- `terms.json` for the text menu options.

### SCRIPT / Native Escape Hatches
One `update_view` script is used to concatenate strings for the item lists on the desk and bed, and to derive the three lines of narrative text based on the combinatorial state of the `book_loc` and `clock_loc` variables. This is needed because the engine lacks native declarative string concatenation arrays and advanced multi-conditional text-block selection in the presentation layer without an explosion of nested IFs.

### Missing Reusable Semantics
- Declarative array manipulation / string concatenation for UI binding (e.g. joining a dynamic list of items at a location into a single comma-separated string).
- Multi-conditional declarative text substitution (e.g. picking a block of narrative text based on a combination of multiple discrete state values, acting as a switch statement or state machine lookup).

### Awkward But Expressible
Nothing particularly awkward, except having to fall back to SCRIPT for string manipulation. The input handling and basic layout are very clean.

### Tooling / Discoverability Gaps
None.

### Backend Leakage
None. The logic only relies on generic Scene hooks, window presentation, and abstract state variables.

### Project Leakage
None. The scene is fully self-contained within the `labs/scene-benchmarks` project.

### Author Legibility
Yes, an event-oriented game author would easily understand this. It's essentially a set of state variables representing object locations, and a choice menu that updates those variables, followed by a script that updates the screen text based on the new state.

### Reusable Successes
- The declarative window/layout system worked perfectly for setting up a static frame with dynamic text bindings `{sceneState.var}`.
- Menu list binding to `terms.json` using `term:b003.options` is very clean and separates content from layout.

### Architecture Recommendation
candidate reusable semantic gap (declarative string array manipulation/joining and multi-conditional text lookups)

### Owner Playtest
- Status: READY FOR OWNER PLAYTEST
- Launch/control instructions: Play via the benchmark launcher, select "B003 Rearranging a Bedroom", use arrows to select an action and Enter to execute, press Escape/B to return.
- Observations: [pending]
- Result: [pending]
