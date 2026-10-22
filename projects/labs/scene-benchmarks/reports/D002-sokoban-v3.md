# D002 — Sokoban as Scene

## Experiment

D002 — Sokoban as Scene

## Result

complete

## Authored Surface

- `projects/labs/scene-benchmarks/data/scenes/d002_sokoban.json`
- Scene uses `windows` draw mode with dynamically updated `sceneState.boardText` text elements for presentation.
- Logical input hooks (`on_up`, `on_down`, `on_left`, `on_right`) drive `dx` and `dy` state assignments, then call a `move` script and `render` script.
- Reset maps to `on_select` and exit maps to `on_cancel`.

## SCRIPT / Native Escape Hatches

- **Move script:** Handles pushing rules by querying and mutating `sceneState` variables (`px`, `py`, `c1x`, `c2x`) and coordinating wall checks.
- **Render script:** Calculates win conditions (comparing crates to goals), stringifies the map by checking all 64 coordinates and applying tokens (`#`, `@`, `O`, `.`, ` `), and assigns it to `sceneState.boardText`. No functions are saved to `sceneState`.

## Missing Reusable Semantics

- Authored collection construction/state initialization (no `SET_VAR` support for creating arrays or records) remains a gap in general, although avoided here by flattening variables.
- Generic collection mutation (indexed replace).
- Generic iteration over authored collections for occupancy checking and presentation logic.
- Generic `GET_CELL`, `COLLIDE`, or `DRAW_GRID` command.

## Awkward But Expressible

- Generating complex multi-line text strings out of collections or hardcoded geometries requires looping in `SCRIPT`.
- Checking discrete boundaries via `isWall()` functions inside every script block is brittle.

## Tooling / Discoverability Gaps

- No tooling gap blocked this experiment, but writing complex SCRIPT within JSON strings remains unergonomic.

## Backend Leakage

- Relying on `SCRIPT` (Lua) for core logic binds the core puzzle rules deeply to the Lua runtime rather than generic Thestra semantics.

## Project Leakage

- None. The benchmark is completely isolated within `projects/labs/scene-benchmarks`.

## Author Legibility

- An RPG Maker author would understand the high-level input hooks setting directional state, but the actual Sokoban rules and text generation are hidden entirely inside Lua block strings. It behaves like a "script call" rather than a composed event.

## Reusable Successes

- `SET_SCENE_STATE` nicely isolates state preparation (`dx`, `dy`) before script execution, and initializes the board declarativeley.
- Formula-driven string presentation (`{sceneState.boardText}`) perfectly consumes the derived state, eliminating the need for any bespoke UI rendering commands or native scene code.

## Architecture Recommendation

candidate reusable semantic gap

## Owner Playtest

**Status:** pending

Launch `npm run lab:benchmarks`, choose **D002 — Sokoban as Scene**, use arrows to move, Enter to reset, and B / Escape to return.

### Owner observations

Pending.

### Result after owner playtest

Pending.
