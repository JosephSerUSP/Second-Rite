# D002 — Sokoban as Scene

## Experiment

D002 — Sokoban as Scene

## Result

complete

## Authored Surface

- `projects/labs/scene-benchmarks/data/scenes/d002_sokoban.json`
- Scene uses `windows` draw mode with dynamically updated `v.boardText` text elements for presentation.
- Logical input hooks (`on_up`, `on_down`, `on_left`, `on_right`) compute new directional state assignments inside an unrolled `IF`/`SET_VAR` evaluation graph.
- Reset maps to `on_select` and exit maps to `on_cancel`.

## SCRIPT / Native Escape Hatches

- None. The previous SCRIPT escapes have been entirely replaced by an authored formula representation.

## Missing Reusable Semantics

- Generating complex strings with spatial semantics out of formulas still feels awkward.

## Awkward But Expressible

- Formula-driven logic required completely unrolling 2D coordinate loops into massive, statically-evaluated condition structures within JSON (`v.nx == 1 and v.ny == 2...`). This allows Lua-free checking of goals, crates, and walls, but the authored JSON becomes extraordinarily dense.

## Tooling / Discoverability Gaps

- The tooling gap remains that authoring such massive unrolled logical graphs by hand inside JSON is basically impossible. An engine helper for grids or array processing inside formulas would be more ergonomic.

## Backend Leakage

- None. Logic is entirely pure `SET_VAR` and `IF` command formulas.

## Project Leakage

- None. The benchmark is completely isolated within `projects/labs/scene-benchmarks`.

## Author Legibility

- A standard event-author would immediately understand the structure (IF commands setting variables) but be horrified by the explicit, statically-unrolled nature of the grid coordinates.

## Reusable Successes

- Replacing SCRIPT blocks with standard Scene formulas and IF blocks demonstrates the deep plasticity of the engine's declarative commands. Everything Sokoban-related is now native to the Scene semantics.

## Architecture Recommendation

candidate reusable semantic gap
## Owner Playtest

**Status:** pending

Launch `npm run lab:benchmarks`, choose **D002 — Sokoban as Scene**, use arrows to move, Enter to reset, and B / Escape to return.

### Owner observations

Pending.

### Result after owner playtest

Pending.
