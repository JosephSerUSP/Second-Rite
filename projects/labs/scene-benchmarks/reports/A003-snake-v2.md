# A003 — Snake Benchmark Report

**Date:** 2026-09-30
**Benchmark:** A003 — Snake
**Version:** 2

## Current Result

complete

## Play

Launch `npm run lab:benchmarks`, choose **A003 — Snake**, then use arrow keys to steer. Enter restarts the specimen; B / Escape returns to the launcher.

## Current Implementation Shape

A completely fresh reconstruction of A003. The implementation is an authored Scene (`data/scenes/a003_snake.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. State variables representing discrete properties (e.g., `gridWidth`, `stepTime`, `dirX`, `lost`) have been extracted from SCRIPT and are now fully initialized via declarative `SET_SCENE_STATE` multi-assignments in `on_enter` and `on_select`.

To eliminate a longstanding rapid-input bug where successive directional presses within a single step could cause the snake to reverse into itself, directional hooks now set `nextDirX`/`nextDirY`. The update block synchronously commits these to `dirX`/`dirY` exactly at the moment of movement. `on_frame` continues to manage the step accumulator via `v.time.dt`. SCRIPT is restricted solely to ordered collection manipulation (the snake body array) and text grid rendering.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 2 (`init`, `update`)
- **approximate SCRIPT lines if any:** 55 lines across two blocks.
- **Native source files modified:** 0
- **New generic semantic commands added:** 0
- **Project-owned files required:** 1 Scene
- **RTP dependencies:** pinned neutral Thestra RTP 1.0
- **validation warnings/errors encountered:** 0
- **bespoke workarounds:** SCRIPT handles all 2D array representation and iteration.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** No, raw SCRIPT was required for collections.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- Fresh implementation.
- Shifted initialization of all discrete state variables from SCRIPT into authored `SET_SCENE_STATE` multi-assignments in `on_enter` and `on_select`.
- Separated `dirX`/`dirY` and `nextDirX`/`nextDirY` state to safely buffer input intents between visual frames and logical update ticks, eliminating the snake self-collision bug caused by rapid consecutive inputs.

## Improved

- Initialization lifecycle is noticeably cleaner and fully legible to Studio authoring surfaces.
- Input buffering via `nextDirX` and `nextDirY` demonstrates that semantic state variables are sufficiently flexible for robust frame/tick separation without requiring new engine abstractions.

## Regressed

- Nothing regressed in this attempt.

## Still Awkward

- Ordered mutable collections force the snake body state into SCRIPT. Multi-line text board rendering also remains heavily coupled to Lua string concatenation, as semantic layout iteration does not exist.

## New Architectural Evidence

The updated A003 Snake continues to validate the power of `SET_SCENE_STATE` multi-assignments and custom `v.time.dt` frame timers. Extracting discrete initialization variables out of Lua reveals that Thestra's current authoring boundaries are sufficient for input and scalar state orchestration. However, the absolute necessity for SCRIPT to perform grid rendering and body array updates reinforces the conclusion that generic semantic primitives for iteration and list manipulation remain the largest missing piece for declarative game logic.

## Verdict

**Playable benchmark; improved authorability.** A003 successfully leverages expanded state commands to push almost all scalar logic into native semantics, significantly clarifying the initialization lifecycle. The specimen proves that frame input can be robustly decoupled from logical tick updates using purely authored variables. However, the requirement for generic collections persists.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
