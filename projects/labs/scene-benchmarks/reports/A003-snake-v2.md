# A003 — Snake Benchmark Report

**Date:** 2026-09-06
**Benchmark:** A003 — Snake
**Version:** 2

## Current Result

complete

## Play

Launch `npm run lab:benchmarks`, choose **A003 — Snake**, then use arrow keys to steer. Enter restarts the specimen; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a003_snake.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses a text-based grid displayed through `boardText`. `on_frame` provides the update loop using a custom delta-time accumulator `timer` tracked via `v.time.dt` directly inside `SET_VAR` instead of a blocking WAIT. Directional hooks (`on_up`, `on_down`, `on_left`, `on_right`) declaratively update movement vectors via `IF` and `SET_VAR` multi-assignments. Initialization was rewritten to inline all flat variable setups into the authored `SET_VAR` assignments array inside `on_enter` and `on_select`, bypassing `run_hook` failures in CI and significantly shortening the `init` script payload. Raw Lua SCRIPT blocks still handle the grid drawing, snake coordinate array, and collision logic because Thestra lacks authored semantic capabilities for mutable ordered collections and spatial checks.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 2 (`init`, `update`)
- **approximate SCRIPT lines if any:** ~65 lines across two blocks.
- **Native source files modified:** 0
- **New generic semantic commands added:** 0
- **Project-owned files required:** 1 Scene
- **RTP dependencies:** pinned neutral Thestra RTP 1.0
- **validation warnings/errors encountered:** 0
- **bespoke workarounds:** SCRIPT handles all 2D array representation and iteration since no semantic commands exist.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** No, raw SCRIPT was required for collections.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- Fresh reconstruction. Removed all flat variable initialization (like `dirX`, `dirY`, `stepTime`, `lost`) from the SCRIPT `init` block and brought them cleanly into the authored JSON `SET_VAR` multi-assignment array in `on_enter` and `on_select`.

## Improved

- **Initialization legibility:** By leveraging `SET_VAR` with `assignments`, the flat initialization state is now natively authored. This correctly shields it from CI hook-dropping errors and reduces the `SCRIPT` footprint down to only the logic that strictly requires arrays.

## Regressed

- Nothing regressed.

## Still Awkward

- Ordered mutable collections force Snake body state into SCRIPT. The logic to handle shifting the array and evaluating intersections cannot be reasonably modeled with simple scalar variables like A004 Sokoban attempted. Multiline SCRIPT embedded in JSON remains substantially harder to author and inspect than Event commands.

## New Architectural Evidence

This run confirms that `v.time.dt` and declarative multi-assignments continue to work gracefully and have successfully consumed the flat-state initialization. However, it provides more evidence that generic iteration, list manipulation, and querying primitives are strictly missing from the semantic vocabulary. Reusing raw Lua for the primary game state in this benchmark highlights a persistent gap.

## Verdict

**Playable benchmark; persistent semantic gap.** A003 successfully leverages state variables for input handling and setup, but continues to expose the lack of native collections. SCRIPT remains mandatory for variable-length arrays and grid querying.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
