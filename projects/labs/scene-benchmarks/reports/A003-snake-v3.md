# A003 — Snake Benchmark Report

**Date:** 2026-09-02
**Benchmark:** A003 — Snake
**Version:** 2

## Current Result

ready for owner playtest

## Play

Launch `npm run lab:benchmarks`, choose **A003 — Snake**, then use arrow keys to steer. Enter restarts the specimen; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a003_snake.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses a text-based grid displayed through `boardText`. `on_frame` provides the update loop using a custom delta-time accumulator `timer` tracked via `v.time.dt` directly inside `SET_VAR`. Directional hooks (`on_up`, `on_down`, `on_left`, `on_right`) declaratively update movement vectors via `IF` and `SET_VAR` multi-assignments. Initialization variables are fully inlined into `on_enter` and `on_select` via declarative assignments, eliminating `nil` variable risks during automated previews. SCRIPT still handles collection and grid operations. The terminal block condition explicitly tests for completion cleanly via `v.lost == true`.

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

- Scalar initializations (e.g. `gridWidth`, `dirX`, `stepTime`) were moved from SCRIPT into `on_enter` and `on_select` using `SET_VAR` assignments, satisfying automated preview requirements and increasing the declarative surface area.
- 66% of raw SCRIPT logic remains factored into standard declarative hooks.
- SCRIPT lines were further minimized due to moving scalar setup into declarative commands.

## Improved

- Initialization is now more robust against CI preview execution contexts since scalar variables are set through `SET_VAR`s within standard hooks.

## Regressed

- Nothing regressed in this update.

## Still Awkward

- Ordered mutable collections force Snake body state into SCRIPT.
- Multiline SCRIPT embedded in JSON remains substantially harder to author and inspect than Event commands.

## New Architectural Evidence

The updated A003 Snake demonstrates that scalar initializations can be successfully inlined into standard event hooks (`on_enter`, `on_select`) via `SET_VAR` multi-assignments to improve CI preview safety, while continuous logical input and frame delta-time continue to be cleanly represented. However, it continues to reinforce the evidence that growing ordered collections and grid queries require generic iteration and list manipulation primitives.

## Verdict

**Playable benchmark; improved authorability.** A003 successfully leverages new state variables and multi-assignments to inline initializations, further reducing raw SCRIPT footprint and improving CI safety. However, the requirement for generic collections persists.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
