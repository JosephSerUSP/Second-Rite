# A004 — Sokoban Benchmark Report

**Date:** 2026-10-19
**Benchmark:** A004 — Sokoban
**Version:** 3

## Current Result

complete

## Play

Launch `npm run lab:benchmarks`, choose **A004 — Sokoban v3**, then use arrow keys to steer and push crates. Enter resets the puzzle; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a004_sokoban_v3.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. State initialization in `on_enter` and `on_select` natively models the small domain state using discrete variables for the player (`px`, `py`) and two individual crates (`c1x`, `c1y`, `c2x`, `c2y`) set cleanly via `assignments` arrays for `SET_SCENE_STATE` to compact the authored node count. However, the movement resolution, collision checks, and text-grid rendering still strictly depend on raw Lua `SCRIPT` blocks.

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
- **bespoke workarounds:** SCRIPT still handles all wall collision detection, multi-box collision detection, and text-grid string generation, due to the engine lacking generic grid geometry primitives.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** No, raw SCRIPT was required for complex collision and presentation.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- Leveraged new engine `assignments` feature inside `SET_SCENE_STATE` commands to drastically compress the number of authored nodes needed for reset and initialization, making the declarative portion of the puzzle state far cleaner.
- Re-authored purely using current constraints, keeping the SCRIPT block shape largely identical to v2 due to a lack of new spatial or collection generic commands.

## Improved

- Using `assignments` with `SET_SCENE_STATE` eliminates the bloated chain of individual assignment commands, making initialization much easier to author and read declaratively.

## Regressed

- None compared to the previous attempt.

## Still Awkward

Collision and presentation. While the discrete variable initialization is cleaner, evaluating interactions between them (like box vs box or box vs wall) remains strictly computationally out-of-bounds for declarative primitives. Generic `COLLIDE`, `GET_CELL`, or `DRAW_GRID` concepts remain missing.

## New Architectural Evidence

This run cements the finding that while we can condense multi-variable state management easily via `assignments`, the engine is structurally missing the primitives to manipulate or evaluate grid layouts natively. Arrays, list filtering, and 2D spatial coordinate checking will continuously require `SCRIPT` escape hatches until generic spatial semantics are built.

## Verdict

**Playable benchmark; architectural gap confirmed.** A004 completes successfully. Using `assignments` arrays cleans up the declarative lifecycle hooks significantly, but the engine still structurally lacks the native 2D grid logic and array processing capabilities required to escape `SCRIPT` for spatial puzzle movement.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
