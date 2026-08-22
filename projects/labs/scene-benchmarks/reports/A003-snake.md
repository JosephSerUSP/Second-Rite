# A003 — Snake Benchmark Report

**Date:** 2026-08-22
**Benchmark:** A003 — Snake
**Version:** 1

## Current Result

ready for owner playtest

## Play

Launch `npm run lab:benchmarks`, choose **A003 — Snake**, then use arrow keys to steer. Enter restarts the specimen; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a003_snake.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses a text-based grid displayed through `boardText`. `on_frame` provides the update loop using `v.time.dt` directly inside `SET_VAR`; directional hooks (`on_up`, `on_down`, `on_left`, `on_right`) declaratively update movement vectors via `IF` and `SET_VAR` multi-assignments. SCRIPT still handles collection and grid operations.

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

- Directional input `SCRIPT` hooks were replaced by declarative `IF` and `SET_VAR` multi-assignments.
- Fixed the `dt` reference in the `on_frame` loop to correctly access delta-time via `v.time.dt` instead of statically decrementing or using invalid `time.dt`.
- Reduced SCRIPT block count from 6 to 2.

## Improved

- Logical input maps directly to declarative vector mutations, eliminating the need to use raw Lua script for simple variable conditional assignments.
- Scene state variables like `v.time.dt` provide a much cleaner native mechanism for frame delta-time processing within authored formulas.

## Regressed

- Nothing regressed in this update.

## Still Awkward

- Ordered mutable collections force Snake body state into SCRIPT.
- Multiline SCRIPT embedded in JSON remains substantially harder to author and inspect than Event commands.

## New Architectural Evidence

The updated A003 Snake demonstrates that continuous logical input and frame delta-time can now be cleanly represented purely via current state semantics like `v.time.dt` and `IF` with `SET_VAR` multi-assignments. However, it continues to reinforce the evidence found in D002 and A004: growing ordered collections and grid queries require generic iteration and list manipulation primitives.

## Verdict

**Playable benchmark; improved authorability.** A003 successfully leverages new state variables and multi-assignments to reduce raw SCRIPT by 66%, proving continuous inputs and delta-time are gracefully handled by current semantics. However, the requirement for generic collections persists.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
