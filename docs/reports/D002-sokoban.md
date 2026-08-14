### Experiment

D002 — Sokoban as Scene

### Result

complete

### Review status

The prototype is preserved as the experiment actually authored it. This autopsy was re-reviewed against current `main@6176a5b16f18e08cbf404425948d8f98448f7e47` after merged #452 established the backend-neutral Thestra Formula contract.

One claim in the prototype's inline SCRIPT comment and the first-pass autopsy was too broad: **Thestra Formula does support read-only record access, 1-based list indexing (`value[index]`), and `#list`.** The experiment therefore does not demonstrate a need for a Grid primitive or for Formula indexing. The demonstrated gap is narrower: Event Programs cannot currently materialize populated collection values, mutate an authored collection by index, or iterate an arbitrary authored collection without escaping into SCRIPT.

### Authored Surface

- Created a new Scene `data/scenes/sokoban.json`.
- Uses `windows` draw mode with a single text block frame window holding the dynamically updated `{v.boardText}` formula along with win conditions and control hints.
- Hooks (`on_enter`, `on_up`, `on_down`, `on_left`, `on_right`, `on_select` for reset, `on_cancel` to exit) handle logical input natively.
- Direction hooks use ordinary ordered `SET_VAR` assignments for `dx` / `dy`; Scene-local `v` state survives cleanly across hooks and SCRIPT boundaries.

### SCRIPT / Native Escape Hatches

- `on_enter` uses SCRIPT to **construct populated collection state** (`v.grid` and `v.goals`) and build the initial display string. Current Formula cannot return a populated list/record and `SET_VAR` can only store a Formula result, so this initialization cannot currently be expressed through ordinary collection-neutral Event commands.
- Movement uses SCRIPT for **indexed mutation** of the flat grid, goal iteration, crate pushing, and completion checks. Formula can read a list element such as `v.grid[index]`; what is missing is an authored mutation surface equivalent to replacing/appending/removing collection elements and a generic way to iterate an authored list.
- Multiline board rendering uses Lua loops plus `table.insert` / `table.concat`. A sufficiently small board could be manually unrolled through formulas, but that would be poor authoring evidence rather than a reusable solution.

### Missing Reusable Semantics

- **Authored collection construction/state:** there is no backend-neutral Event command surface for creating a populated list/record in Scene-local state. Populated table literals and table-valued Formula results are deliberately outside the Formula contract.
- **Authored collection mutation:** there is no generic indexed set/replace/append/remove operation over explicitly authored collection state.
- **Authored collection iteration:** current `FOR_EACH` covers engine-owned battler scopes; it does not iterate an arbitrary authored collection.

D002 alone does **not** justify special multidimensional/Grid semantics. Its board is already representable as a flat list plus computed index, and current Formula can read that representation. A second substantially different fixture should determine the smallest reusable collection vocabulary before implementation is frozen. Follow-up: #472.

### Awkward But Expressible

- **Read-only indexed queries:** after #452, Formula can read 1-based list elements and list length. That part of the original diagnosis is expressible without SCRIPT when the collection already exists.
- **String rendering of a grid:** using `v.boardText` inside a text window works, but the lack of arbitrary collection iteration means the prototype rebuilds the whole multiline string in SCRIPT after every state change.
- **2D addressing:** a flat list with `index = y * width + x + 1` is sufficient for this specimen; no dedicated 2D query primitive was demonstrated as necessary.

### Tooling / Discoverability Gaps

- An author can discover Formula indexing from the Formula contract/editor help, but there is no corresponding collection mutation command to reach for once a read needs to become a write.
- The current escape hatch makes Lua collection idioms (`ipairs`, indexed assignment, `table.insert`, `table.concat`) the path of least resistance for this class of Scene, which weakens backend-neutral authorability.

### Backend Leakage

- The gameplay implementation directly uses Lua tables, `ipairs`, indexed table assignment, `table.insert`, and `table.concat` inside SCRIPT.
- This leakage is evidence for a reusable authored collection surface, not evidence that these Lua operations should be exposed verbatim as the portable contract.

### Project Leakage

- None. The Scene is isolated authored content and uses standard Scene hooks/state plus the existing SCRIPT escape hatch.

### Author Legibility

- **Mixed.** Lifecycle, logical input, direction selection, window composition, reset and exit are compact and legible in authored Scene data. The actual board state transition becomes a sizeable Lua program as soon as repeated mutable elements are involved.

### Reusable Successes

- `v` Scene-local state carries naturally across hooks and SCRIPT boundaries.
- Logical input hooks map directly to Sokoban movement without backend keyboard listeners.
- Ordered multi-assignment `SET_VAR` is a good fit for paired direction values.
- Formula-driven text presentation consumes the derived board string without bespoke rendering code.
- The experiment remained a normal authored Scene; no `sokoban.lua`, Sokoban-specific native command, or production Battle change was needed.

### Architecture Recommendation

Treat D002 as evidence for **backend-neutral authored collection state/mutation semantics**, tracked by #472, not as a request for `GRID_*` commands or a broader Formula language.

Before freezing any new command vocabulary, pressure-test #472 with at least one different collection shape from the Creative Lab (for example Snake body growth, Breakout bricks, tactics units, or splitting-ball Pong). Preserve Formula as read-only and put authoritative mutation behind registered, inspectable Event semantics.
