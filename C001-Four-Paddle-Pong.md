### Experiment
C001 — Four-Paddle Pong

### Result
complete

### Authored Surface
Authored as a standalone discrete Scene (`projects/labs/scene-benchmarks/data/scenes/c001_four_pong.json`) using standard declarative logic, registered in the `title.json` menu and the project's scene registry.

### SCRIPT / Native Escape Hatches
None. The implementation relies completely on the declarative `SET_VAR` multi-assignments and `IF` logic within the `on_frame` hook, mimicking `a001_pong.json`. All paddle boundary locking, AI tracking, physics and input handling use mathematical expressions directly without the need for raw Lua.

### Missing Reusable Semantics
None needed.

### Awkward But Expressible
The core simulation for bounce and AI control relies heavily on ternary inline math statements (`condition and then_val or else_val`), which works effectively but requires complex expressions inside strings:
- The ball boundary detection uses manual hardcoded comparisons `v.ballX < 0 or v.ballX >= v.gridW`.
- Keeping AI tracking within grid bounds forces a verbose clamp pattern using nested `max` and `min`: `max(1, min(v.gridH - v.paddleH - 1, v.paddle2Y))`.

### Tooling / Discoverability Gaps
No special tooling gaps for this specific exercise, though manual calculation and formatting of the multi-paddle setup required duplicating properties (e.g., `inputY` / `inputX`, `center2` / `center4`, tracking `paddle3X` instead of `paddle1Y`).

### Backend Leakage
None. The implementation only relies on integer coordinates, basic math expressions, and explicit time (`v.time.dt`), all standard semantics.

### Project Leakage
None. The test runs independently within the `scene-benchmarks` scope and does not require external assets.

### Author Legibility
Yes. Although the logic requires heavy expressions and string-embedded conditions (`max`, `min`), an event author familiar with game math can trace the variable multi-assignments and single `IF` events tracking hits. The composition cleanly distinguishes state manipulation from drawing.

### Reusable Successes
The multi-assignment `SET_VAR` block allows resolving positions, AI targets, and bounding checks in one clean, declarative engine step. The scene successfully proves Pong rules natively map to declarative engine math.

### Architecture Recommendation
no architecture change indicated
