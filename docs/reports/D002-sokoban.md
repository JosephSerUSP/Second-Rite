### Experiment

D002 — Sokoban as Scene

### Result

complete

### Authored Surface

- Created a new scene `data/scenes/sokoban.json`.
- Uses `windows` draw mode with a single text block frame window holding the dynamically updated `{v.boardText}` formula along with win conditions and control hints.
- Hooks (`on_enter`, `on_up`, `on_down`, `on_left`, `on_right`, `on_select` for reset, `on_cancel` to exit) handle logical input natively.

### SCRIPT / Native Escape Hatches

- `on_enter` logic uses a `SCRIPT` block to initialize the board (`v.grid` array, crates, walls, goals, and player positions) and build the string representation of the grid since we cannot iterate natively over a grid/array via declarative commands.
- Movement hooks use `SCRIPT` to handle grid coordinate translations, collision checks, array updates for crate pushing, and win condition checking. SCRIPT was required because native engine capabilities do not naturally support array mutations or multidimensional bounds queries.
- String concatenation loops are done in `SCRIPT` to construct `v.boardText`.

### Missing Reusable Semantics

- **Collections/Array manipulation:** The lack of native variable arrays, grids, or map semantics within purely declarative UI/Scene logic necessitates using `SCRIPT` for data structure initialization, cell checks, and updates.
- **Multidimensional queries:** Without explicit grid semantics, there is no way to perform 2D collision natively outside of a true map scene.

### Awkward But Expressible

- **String rendering of a grid:** Using `v.boardText` inside a text window to draw the ASCII-art-like game board works, but forces manually rebuilding a multiline string rather than updating individual UI tiles, requiring us to wipe and redraw the whole text on every state change.

### Tooling / Discoverability Gaps

- A developer has to figure out that SCRIPT is required to accomplish grid manipulation.
- Building the string loop dynamically is something that might be foreign to someone used to an RPG Maker event editor interface.

### Backend Leakage

- Using Lua's `table.insert` and `table.concat` assumes standard Lua library capabilities.

### Project Leakage

- None. The scene runs isolated entirely through new json variables and standard engine hooks.

### Author Legibility

- **Mixed:** The scene flow hooks (`on_up`, `on_select`, etc.) are very clean and legibly compose logical input. However, the heavy use of Lua SCRIPT logic block to manage grids means an RPG Maker-style author might be unable to author the state transitions cleanly.

### Reusable Successes

- `v.` flow variables seamlessly carry across hooks and SCRIPT boundaries.
- The built-in SNES logical map (hooks) easily translate keyboard inputs (up/down/left/right, select, cancel) without manually writing keyboard listeners.
- The text window natively evaluates the final board state string effectively.

### Architecture Recommendation

- candidate reusable semantic gap (Grid/Array Variables and Multidimensional checks)
