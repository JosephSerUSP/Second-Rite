# A004 — Sokoban Benchmark Report

**Date:** 2026-10-23
**Benchmark:** A004 — Sokoban
**Version:** 3

## Current Result

complete

## Play

Launch `npm run lab:benchmarks`, choose **A004 — Sokoban**, then use arrow keys to steer and push crates. Enter resets the puzzle; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a004_sokoban.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. Building off of version 2, state initialization has been cleanly broken out into declarative assignments using `SET_SCENE_STATE` within `on_enter` and `on_select` hooks. However, movement, grid constraints, pushing behavior, and visual presentation are still bound strictly to generic Lua `SCRIPT` blocks as there are no matching declarative semantic engine features.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 2 (`move`, `render`)
- **approximate SCRIPT lines if any:** 75 lines across two blocks.
- **Native source files modified:** 0
- **New generic semantic commands added:** 0
- **Project-owned files required:** 1 Scene
- **RTP dependencies:** pinned neutral Thestra RTP 1.0
- **validation warnings/errors encountered:** 0
- **bespoke workarounds:** `SCRIPT` blocks completely contain and govern 2D layout constraints, logic around collision, and logic for determining puzzle success.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** No, raw SCRIPT was required for complex collision and presentation.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- Leveraged new `assignments` array semantics within `SET_SCENE_STATE` commands to group variable initialization compactly in `on_enter` and `on_select` hooks.
- Refactored Lua SCRIPT slightly for succinctness.

## Improved

- Initialization lifecycle is noticeably cleaner due to `assignments` blocks inside `SET_SCENE_STATE`, allowing declarative definition in a single command instead of a command per variable.

## Regressed

- N/A

## Still Awkward

Collision and presentation. While the state is now stored as discrete Scene variables, there is no generic `GET_CELL`, `COLLIDE`, or `DRAW_GRID` command. The movement intent must still be resolved via raw Lua to handle the wall constraints and multi-box pushing logic. Evaluating positional intent against other elements manually feels increasingly unwieldy in Lua.

## New Architectural Evidence

This fresh reconstruction heavily utilizes recent semantic additions (multiple assignments) for cleaner bootstrapping. Yet, it conclusively reiterates previous evidence: moving past initialization into execution remains completely bottlenecked by lack of declarative spatial querying and grid array primitives. Adding variable assignment syntactic sugar does nothing to help evaluate actual board state.

## Verdict

**Playable benchmark; architectural gap confirmed.** A004 completes successfully once again. However, it continues to validate that while state representation can be somewhat modeled via discrete variables, robust event semantics for grids and querying spatial layouts are structurally missing from the engine. Sokoban necessitates raw SCRIPT escapes.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
