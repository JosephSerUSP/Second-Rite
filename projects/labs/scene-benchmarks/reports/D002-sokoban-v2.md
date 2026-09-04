# D002 — Sokoban as Scene

## Experiment

D002 — Sokoban as Scene

## Result

complete

## Authored Surface

- `projects/labs/scene-benchmarks/data/scenes/d002_sokoban.json`
- Scene uses `windows` draw mode with dynamically updated `v.boardText` text elements for presentation.
- Logical input hooks (`on_up`, `on_down`, `on_left`, `on_right`) drive `dx` and `dy` state assignments, then call a movement script.
- Reset maps to `on_select` and exit maps to `on_cancel`.

## SCRIPT / Native Escape Hatches

- **Initialization script:** Sets up a 1D Lua table `v.grid` representing the 2D grid, calculates player start position, sets up goals, and creates the display string mapping grid tokens to text characters (`#`, `@`, `O`, `.`, ` `).
- **Movement script:** Handles pushing rules by querying and mutating `v.grid` indexes (`v.px`, `v.py` and coordinate calculations), checks win conditions by comparing `v.grid` against `v.goals`, and recomputes the display string.

## Missing Reusable Semantics

- Authored collection construction/state initialization (no `SET_VAR` support for creating arrays or records).
- Generic collection mutation (indexed replace).
- Generic iteration over authored collections for occupancy checking and presentation logic.

## Awkward But Expressible

- Generating complex multi-line text strings out of collections requires looping in `SCRIPT`.
- Keeping 2D coordinates tracked on top of a 1D state array works but requires manual modulus and integer division math in scripts.

## Tooling / Discoverability Gaps

- No tooling gap blocked this experiment, but writing complex SCRIPT within JSON strings remains unergonomic.

## Backend Leakage

- Relying on `SCRIPT` (Lua) for core logic (1-based array indexing, table concatenation) binds the core puzzle rules deeply to the Lua runtime rather than generic Thestra semantics.

## Project Leakage

- None. The benchmark is completely isolated within `projects/labs/scene-benchmarks`.

## Author Legibility

- An RPG Maker author would understand the high-level input hooks setting directional state, but the actual Sokoban rules and text generation are hidden entirely inside Lua block strings. It behaves like a "script call" rather than a composed event.

## Reusable Successes

- `SET_VAR` nicely isolates state preparation (`v.dx`, `v.dy`) before script execution.
- Formula-driven string presentation (`{v.boardText}`) perfectly consumes the derived state, eliminating the need for any bespoke UI rendering commands or native scene code.
- Scene-local state (`v`) easily bridges the gap between discrete input hooks and script boundaries.

## Architecture Recommendation

candidate reusable semantic gap
