# A003 — Snake Benchmark Report

**Date:** 2026-10-14
**Benchmark:** A003 — Snake
**Version:** 2

## Current Result

ready for owner playtest

## Play

Launch `npm run lab:benchmarks`, choose **A003 - Snake**, then use arrow keys to steer. Enter restarts the specimen; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a003_snake.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses a text-based grid displayed through `boardText`. `on_frame` provides the update loop using a custom delta-time accumulator `timer` tracked via `sceneState.time.dt` directly inside `SET_SCENE_STATE`. Directional hooks buffer inputs using `nextDirX` and `nextDirY` via `SET_SCENE_STATE` nodes instead of an `assignments` array, preventing rapid-input reversal bugs. SCRIPT still handles collection and grid operations.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 2 (`init`, `update`)
- **Native source files modified:** 0
- **New generic semantic commands added:** 0
- **Project-owned benchmark files required:** 1 Scene plus launcher registration/report
- **RTP dependencies:** pinned neutral Thestra RTP 1.0
- **validation warnings/errors encountered:** 0
- **bespoke workarounds:** SCRIPT handles all 2D array representation and iteration.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** No, raw SCRIPT was required for collections.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- Directional input hooks now buffer inputs (`nextDirX`/`nextDirY`) to prevent rapid-input reverse-into-oneself bugs, committing them during the frame update hook.
- Replaced the unsupported `assignments` array in `SET_SCENE_STATE` with multiple individual `SET_SCENE_STATE` commands per engine constraints.

## Improved

- Input buffering fixes the classic Snake bug where rapid inputs could reverse direction into the player's own body.
- Adherence to engine constraints regarding `SET_SCENE_STATE` assignments improves correctness.

## Regressed

- Nothing regressed in this update.

## Still Awkward

- Ordered mutable collections force Snake body state into SCRIPT.
- Multiline SCRIPT embedded in JSON remains substantially harder to author and inspect than Event commands.
- String building for the grid display still requires SCRIPT.

## New Architectural Evidence

The updated A003 Snake demonstrates that buffering inputs for logical grid games is possible entirely within declarative hooks and state variables (`nextDirX`, `nextDirY`), leaving only the actual commitment and collection logic to SCRIPT. The requirement for multiple `SET_SCENE_STATE` blocks rather than a single `assignments` array increases verbosity but functions correctly. The core need for generic list manipulation and string building primitives persists.

## Verdict

**Playable benchmark; improved authorability and correctness.** A003 successfully leverages new state variables to buffer inputs and prevent bugs, proving logical input states are gracefully handled by current semantics. However, the requirement for generic collections and string construction persists.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
