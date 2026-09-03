# A004 — Sokoban Benchmark Report

**Date:** 2026-09-03
**Benchmark:** A004 — Sokoban
**Version:** 3

## Current Result

complete

## Play

Launch `npm run lab:benchmarks`, choose **A004 — Sokoban**, then use arrow keys to steer and push crates. Enter resets the puzzle; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a004_sokoban.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It natively models the small domain state using discrete variables for the player (`v.px`, `v.py`) and two individual crates (`v.c1x`, `v.c1y`, `v.c2x`, `v.c2y`). State resets and multi-variable initialization in `on_enter` and `on_select` are now completely declarative using `SET_VAR` multi-assignments (`assignments` array), resolving some previous verbosity. Movement resolution and rendering is still left to SCRIPT.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 2 (`move`, `render`)
- **approximate SCRIPT lines if any:** 110 lines across two blocks.
- **Native source files modified:** 0
- **New generic semantic commands added:** 0
- **Project-owned files required:** 1 Scene
- **RTP dependencies:** pinned neutral Thestra RTP 1.0
- **validation warnings/errors encountered:** 0
- **bespoke workarounds:** SCRIPT still handles wall collision detection and text-grid string generation because there is no generic spatial querying or rendering primitives.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** No, raw SCRIPT was required for complex collision and presentation.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- Switched scene initialization and movement assignments to the native `SET_VAR` array-based multi-assignment syntax, reducing repetitive JSON nodes in `on_enter`, `on_select`, and movement hooks.
- Preserved `terminal` blocks are fixed to correctly house `script` entries as expected by automated CI testing inputs.

## Improved

- Initialization lifecycle is noticeably cleaner due to `SET_VAR` multi-assignment usage.

## Regressed

- No regressions; SCRIPT usage remains constant as grid querying capabilities have not fundamentally changed.

## Still Awkward

Collision and presentation. While the state is stored as Scene variables, there is no generic `GET_CELL`, `COLLIDE`, or `DRAW_GRID` command. The movement intent must still be resolved via raw Lua to handle the wall constraints and multi-box pushing logic.

## New Architectural Evidence

This fresh reconstruction confirms the v2 findings: we can represent small puzzle state declaratively, and now initialize it much cleaner via multi-assignments, but evaluating it remains computationally out-of-bounds for the current `IF` primitives. The engine continues to need robust semantic tools for querying spatial state and evaluating collisions natively.

## Verdict

**Playable benchmark; architectural gap confirmed.** A004 completes successfully, utilizing the `SET_VAR` array multi-assignments to clean up the JSON state definition, but confirms that evaluating discrete coordinate data still requires SCRIPT escape hatches for grid puzzles.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
