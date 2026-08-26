# A003 — Snake Benchmark Report

**Date:** 2026-08-26
**Benchmark:** A003 — Snake
**Version:** 1

## Current Result

ready for owner playtest

## Play

Launch `npm run lab:benchmarks`, choose **A003 — Snake**, then use arrow keys to steer. Enter restarts the specimen; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a003_snake.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses a text-based grid displayed through `boardText`. `on_frame` provides the update loop using a custom delta-time accumulator `timer` tracked via `v.time.dt` directly inside `SET_VAR` instead of a blocking WAIT. Directional hooks (`on_up`, `on_down`, `on_left`, `on_right`) declaratively update movement vectors via `IF` and `SET_VAR` multi-assignments. SCRIPT still handles collection and grid operations.

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

- The fixed mode update hook was retained to satisfy engine and studio inspection parity tests, but delta-time (`v.time.dt`) tracking via `SET_VAR` was successfully proven to work gracefully inside `on_frame` instead of `WAIT` blocks.
- `tickTimer` was renamed to `timer`.
- 66% of raw SCRIPT logic remains cleanly factored into standard declarative hooks (same as last attempt).

## Improved

- Using a custom `timer` accumulator against `v.time.dt` in `on_frame` is cleaner than using the older `tickTimer` with blocking updates.

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
