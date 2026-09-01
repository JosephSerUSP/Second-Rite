# A004 — Sokoban Benchmark Report

**Date:** 2026-08-31
**Benchmark:** A004 — Sokoban
**Version:** 2

## Current Result

complete

## Play

Launch `npm run lab:benchmarks`, choose **A004 — Sokoban**, then use arrow keys to steer and push crates. Enter resets the puzzle; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a004_sokoban.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It abandons the single Lua `v.grid` array from the previous attempt. Instead, it natively models the small domain state using discrete variables for the player (`v.px`, `v.py`) and two individual crates (`v.c1x`, `v.c1y`, `v.c2x`, `v.c2y`). State resets in `on_enter` and `on_select` are now completely declarative `SET_VAR` blocks, leaving only movement resolution and rendering to SCRIPT.

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
- **bespoke workarounds:** SCRIPT still handles wall collision detection and text-grid string generation because there is no way to perform complex layout mapping natively.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** No, raw SCRIPT was required for complex collision and presentation.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- completely rewritten structure from a single map array to multiple discrete entities, matching the small scope of the required benchmark.
- Moved scene initialization state (variables `win`, `px`, `py`, etc) entirely into authored `SET_VAR` blocks in `on_enter` and `on_select`.

## Improved

- Initialization lifecycle is noticeably cleaner; authoring the puzzle's starting state is now declarative and easily tweakable in Studio without opening the `SCRIPT` block.

## Regressed

- While breaking apart the state array works for this *specific* small map layout with exactly 2 crates, the collision checks in `SCRIPT` become incredibly fragile and manual (hardcoding checks for `v.c1x == nnx`, etc.). It proves the limitations of the current semantics for scaling.

## Still Awkward

Collision and presentation. While the state is now stored as Scene variables, there is no generic `GET_CELL`, `COLLIDE`, or `DRAW_GRID` command. The movement intent must still be resolved via raw Lua to handle the wall constraints and multi-box pushing logic.

## New Architectural Evidence

This fresh reconstruction proves that we can represent small puzzle state declaratively, but evaluating it (did a box hit another box?) remains computationally out-of-bounds for the current `IF` and `SET_VAR` primitives. The engine continues to need robust semantic tools for querying spatial state and evaluating collisions, regardless of whether that state is stored in an array or discrete variables.

## Verdict

**Playable benchmark; architectural gap confirmed.** A004 completes successfully, but this reconstruction clearly demonstrates that pushing discrete coordinate data into variables does not solve the core requirement for generic spatial querying. The engine still requires SCRIPT escape hatches for Sokoban-style grid puzzles.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
