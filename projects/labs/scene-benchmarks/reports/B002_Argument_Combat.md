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
- None. The combat mechanics, state checks, variable updates, and branching dialogue choices were all successfully implemented using normal `IF` and `SET_VAR` command trees. Initially, `SCRIPT` was evaluated as a convenience, but expressing it natively via JSON proved completely tractable and fully respects the engine's event-driven philosophy.

### Missing Reusable Semantics
- None. The `SET_VAR` command inherently supports multiple `assignments`, which cleanly handles batch state updates (like updating trust, patience, and UI text simultaneously) without needing a single missing generic semantic.

### Awkward But Expressible
- While fully functional and expressible, writing a deeply nested dialogue tree with threshold checks and multi-variable logic using raw JSON `IF`/`SET_VAR` objects is inevitably verbose. It highlights an authoring ergonomics gap where Studio tools are desperately needed to make branching state visually manageable, even though the engine handles it flawlessly.

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
