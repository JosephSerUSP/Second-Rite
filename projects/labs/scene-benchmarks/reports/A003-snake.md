# A003 — Snake Benchmark Report

**Date:** 2026-10-18
**Benchmark:** A003 — Snake
**Version:** 1

## Current Result

ready for owner playtest

## Play

Launch `npm run lab:benchmarks`, choose **A003 — Snake**, then use arrow keys to steer. Enter restarts the specimen; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a003_snake.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses a text-based grid displayed through `boardText`. `on_frame` provides the update loop using a custom delta-time accumulator `timer` tracked via `v.time.dt` directly inside `SET_VAR` instead of a blocking WAIT. Directional hooks (`on_up`, `on_down`, `on_left`, `on_right`) declaratively update movement vectors via `IF` and multiple `SET_SCENE_STATE` commands. SCRIPT still handles collection and grid operations.

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

- Reimplemented freshly without `assignments` array. Memory dictated that multi-assignments are unsupported by `SET_SCENE_STATE`, so individual variables are updated by separate nodes.
- Delta-time tracking and raw SCRIPT hooks for collections were retained.

## Improved

- None.

## Regressed

- Multi-assignments were removed according to engine rules, forcing multiple `SET_SCENE_STATE` commands for vectors.

## Still Awkward

- Ordered mutable collections force Snake body state into SCRIPT.
- Multiline SCRIPT embedded in JSON remains substantially harder to author and inspect than Event commands.

## New Architectural Evidence

The updated A003 Snake demonstrates that `SET_SCENE_STATE` must be used multiple times to update several variables in one hook due to the lack of an assignments array. It continues to reinforce the evidence found in D002 and A004: growing ordered collections and grid queries require generic iteration and list manipulation primitives.

## Verdict

**Playable benchmark; slightly regressed authorability.** A003 requires slightly more verbose node chains to handle variable updates because the `assignments` array is no longer permitted by Thestra conventions. The requirement for generic collections persists.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
