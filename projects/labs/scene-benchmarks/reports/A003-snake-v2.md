# A003 — Snake Benchmark Report (v2)

**Date:** 2026-09-10
**Benchmark:** A003 — Snake
**Version:** 2

## Current Result

ready for owner playtest

## Play

Launch `npm run lab:benchmarks`, choose **A003 — Snake**, then use arrow keys to steer. Enter restarts the specimen; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a003_snake.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses a text-based grid displayed through `boardText`. `on_frame` provides the update loop using a custom delta-time accumulator `timer` tracked via `v.time.dt` directly inside `SET_VAR`. Directional hooks (`on_up`, `on_down`, `on_left`, `on_right`) declaratively update movement vectors. For initialization, primitive variables are pulled out of the SCRIPT block into a declarative `SET_VAR` multi-assignment array in the `on_enter` and `on_select` hooks (utilizing JSON boolean primitives). SCRIPT handles the `snake` body list and grid generation.

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

- Primitive variable initialization (e.g. `gridWidth`, `lost`, `dirX`) was extracted from raw SCRIPT and placed into declarative `SET_VAR` multi-assignment arrays using JSON boolean primitives in both `on_enter` and `on_select` hooks. This allows CI preview tests to avoid `nil` variable errors (since `SCENE_EVENT` commands with kind `run_hook` are dropped).
- The raw Lua script initialization was reduced to just setting the initial `snake` table and performing the initial draw.

## Improved

- Initialization is now more coherent and fully leverages multi-assignment arrays. Raw SCRIPT is minimized. Declarative properties are explicitly expressed using engine commands rather than SCRIPT logic.

## Regressed

- Nothing regressed in this update.

## Still Awkward

- Ordered mutable collections force Snake body state into SCRIPT.
- Multiline SCRIPT embedded in JSON remains substantially harder to author and inspect than Event commands.

## New Architectural Evidence

The updated A003 Snake demonstrates that primitive setup can be cleanly represented purely via `SET_VAR` multi-assignments and boolean primitives inline within `on_enter` and `on_select`. However, it continues to reinforce the evidence found in D002 and A004: growing ordered collections and grid queries require generic iteration and list manipulation primitives before we can fully excise SCRIPT.

## Verdict

**Playable benchmark; improved authorability.** A003 successfully leverages declarative `SET_VAR` multi-assignments and JSON primitives for state initialization, further isolating raw SCRIPT to just the collection loop, confirming that we can migrate initial setup logic gracefully. However, the requirement for generic collections persists.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
