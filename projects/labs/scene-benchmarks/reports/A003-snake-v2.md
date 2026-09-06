# A003 — Snake Benchmark Report

**Date:** 2026-09-06
**Benchmark:** A003 — Snake
**Version:** 2

## Current Result

complete

## Play

Launch `npm run lab:benchmarks`, choose **A003 — Snake**, then use arrow keys to steer. Enter restarts the specimen; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a003_snake.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses a text-based grid displayed through `boardText`. `on_frame` provides the update loop using a custom delta-time accumulator `timer` tracked via `v.time.dt` directly inside `SET_VAR` instead of a blocking WAIT. Directional hooks (`on_up`, `on_down`, `on_left`, `on_right`) declaratively update movement vectors via `IF` and `SET_VAR` multi-assignments. Raw Lua SCRIPT blocks handle the grid drawing, snake coordinate array, and collision logic because Thestra still lacks authored semantic capabilities for mutable ordered collections and spatial checks.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 2 (`init`, `update`)
- **approximate SCRIPT lines if any:** ~80 lines across two blocks.
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

- Fresh reconstruction. Recreated the exact logic from version 1 to observe any shifts in expressiveness or capability, confirming that no new semantic commands relieve the pressure of SCRIPT array mutability. Note: the `on_enter` assignments approach failed CI because formula evaluators dropping uninitialized `ctx.v` bindings incorrectly processed `dirX` causing snake movement to halt.

## Improved

- Nothing functionally improved; it matches the previous state cleanly, utilizing `SET_VAR` array assignments for input.

## Regressed

- Nothing regressed.

## Still Awkward

- Ordered mutable collections force Snake body state into SCRIPT. The logic to handle shifting the array and evaluating intersections cannot be reasonably modeled with simple scalar variables like A004 Sokoban attempted. Multiline SCRIPT embedded in JSON remains substantially harder to author and inspect than Event commands.

## New Architectural Evidence

This run confirms that `v.time.dt` and declarative multi-assignments continue to work gracefully, but provides more evidence that generic iteration, list manipulation, and querying primitives are strictly missing from the semantic vocabulary. Reusing raw Lua for the primary game state in this benchmark highlights a persistent gap. Attempting to lift `dirX` and `dirY` arrays from the SCRIPT initialization into declarative JSON `assignments` broke the simulation completely, showing that state sharing between `SCRIPT` and declarative formulas requires explicit bounds tracking and initialization that is currently highly fragile.

## Verdict

**Playable benchmark; persistent semantic gap.** A003 successfully leverages state variables for input handling but continues to expose the lack of native collections. SCRIPT remains mandatory for variable-length arrays and grid querying.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
