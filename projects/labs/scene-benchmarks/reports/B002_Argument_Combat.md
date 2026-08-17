### Experiment
B002 — Argument as Combat

### Result
* complete

### Authored Surface
- `b002_argument.json` (Custom Scene, UI-only combat using `windows` draw mode)
- `index.json` (Registered Scene)
- `title.json` (Added to title menu hooks)
- `terms.json` (Added option terms)

### SCRIPT / Native Escape Hatches
- None. The turn resolver is authored entirely with standard `IF` and `SET_VAR` Event commands.

### Missing Reusable Semantics
- No missing runtime semantic blocked the experiment. The main cost is authoring verbosity: four tactic branches plus shared pressure/outcome checks require a fairly deep command tree.

### Awkward But Expressible
- Multi-variable turn resolution is verbose in the JSON command tree, especially when preserving ordered outcome precedence, but it is fully expressible without native scripting.
- Clamping Embarrassment on Deflect uses the same formula-expression surface already used elsewhere in the Scene (`v.embarrassment > 20 and v.embarrassment - 20 or 0`) rather than a new command or backend helper.

### Tooling / Discoverability Gaps
- A visual Event-command editor should make nested `IF` branches and batches of related `SET_VAR` operations easier to scan. That is an authoring-legibility concern, not evidence for a new runtime command.
- The `windows` draw type is otherwise quite powerful for bespoke text-adventure or menu-driven combat loops.

### Backend Leakage
- None.

### Project Leakage
- None.

### Author Legibility
- The UI windows represent stats and state directly via formula bindings like `{v.player_patience}`. The turn logic is longer than a native function would be, but every state mutation and branch remains visible in the same Event-command vocabulary an RPG Maker-style author already uses.

### Reusable Successes
- The `windows` layout system, combined with `{v.var}` formula injection and `list` menus powered by `cursor: "v.idx"`, handles turn-based custom menu combat without bespoke engine semantics.
- Standard `IF` + `SET_VAR` commands are sufficient for the complete argument-turn loop, including conditional costs, shared post-action pressure, and ordered win/lose checks.

### Architecture Recommendation
- no runtime architecture change indicated
- improve command-tree authoring/readability before considering a native escape hatch for this shape

### Owner Playtest

**Status:** READY FOR OWNER PLAYTEST

**Instructions:**
1. `npm run lab:benchmarks`
2. Select "B002  Argument as Combat" from the title screen.
3. Use UP/DOWN arrows to select conversational tactics.
4. Press ENTER to execute a tactic against the King.
5. Manage Patience, Trust, and Embarrassment to win or lose.
6. Press B to return to the launcher menu at any time.

**Observations:**
- (Pending owner observations)

**Result:**
- (Pending owner result)
