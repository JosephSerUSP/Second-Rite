# A004 — Sokoban Benchmark Report

**Date:** 2026-09-07
**Benchmark:** A004 — Sokoban
**Version:** 3

## Current Result

complete

## Play

Launch `npm run lab:benchmarks`, choose **A004 — Sokoban**, then use arrow keys to steer and push crates. Enter resets the puzzle; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a004_sokoban.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses multi-assignment in `SET_VAR` to improve declarative initialization. However, both movement/collision and presentation are still strictly inside raw `SCRIPT` blocks.

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
- **bespoke workarounds:** SCRIPT still handles wall collision detection and text-grid string generation.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** No, raw SCRIPT was required for complex collision and presentation.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- Refactored `on_enter` and `on_select` state initialization to use the supported `SET_VAR` `assignments` array.
- Fixed the previous implementation incorrectly leaving the automated test input script as a top-level `goldenScript` array rather than inside the `terminal` object.

## Improved

- Initialization lifecycle is even cleaner by batching declarations into a single multi-assignment `SET_VAR` instead of sequence of singular `SET_VAR` blocks.

## Regressed

- None.

## Still Awkward

Collision and presentation. While the state is stored as discrete Scene variables, there is no generic `GET_CELL`, `COLLIDE`, or `DRAW_GRID` command. The movement intent must still be resolved via raw Lua to handle the wall constraints and multi-box pushing logic, because evaluating collision and constraints with purely declarative logic via `IF` conditionals is prohibitively complex without spatial queries.

## New Architectural Evidence

This run attempted to further push declarative logic. While `SET_VAR` multi-assignment cleans up setup, it confirms that complex collision and grid mapping remains un-authorable through pure formula-based `IF`/`SET_VAR` blocks. Spatial logic strictly demands SCRIPT or new bespoke spatial commands.

## Verdict

**Playable benchmark; architectural gap confirmed.** A004 completes successfully, but spatial querying and collision resolution for grids remains stubbornly tied to SCRIPT escape hatches.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
