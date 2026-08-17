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
- SCRIPT was used once for `resolve_turn` to handle the complex stats math for player and opponent patience, trust, embarrassment, and position logic since nesting `IF` and `SET_VAR` logic for an entire set of 4 different dialogue actions with multiple outcome variables would be overly verbose in JSON AST.

### Missing Reusable Semantics
- Complex expression handling or block assignments within a single `IF` in the JSON DSL would make standard variables more readable compared to dropping into `SCRIPT`.

### Awkward But Expressible
- The engine can build combat-like UI using standard `windows` layouts, but writing a robust stat-manipulation algorithm via AST nodes is awkward compared to scripting. We expressed the state logic via `SCRIPT` which executes synchronously during the `on_select` hook.

### Tooling / Discoverability Gaps
- None. `windows` draw type is quite powerful for bespoke text-adventure or menu-driven combat loops.

### Backend Leakage
- None.

### Project Leakage
- None.

### Author Legibility
- Very legible. The UI windows represent stats and state directly via formula bindings like `{v.player_patience}`, making the connection between the script logic and the presentation extremely clear. An RPG Maker author would understand this as a custom screen with variables handling the display.

### Reusable Successes
- The `windows` layout system, combined with `{v.var}` formula injection and `list` menus powered by `cursor: "v.idx"`, trivially handles turn-based custom menu combat with almost zero extra engine work.

### Architecture Recommendation
- no architecture change indicated

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
