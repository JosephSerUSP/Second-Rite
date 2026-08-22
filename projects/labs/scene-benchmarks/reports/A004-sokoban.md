# A004 — Sokoban Benchmark Report

**Date:** 2026-08-21
**Benchmark:** A004 — Sokoban
**Version:** 1

## Current Result

ready for owner playtest

## Play

Launch `npm run lab:benchmarks`, choose **A004 — Sokoban**, then use arrow keys to steer and push crates. Enter resets the puzzle; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a004_sokoban.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses a text-based grid displayed through `boardText` within a window. Logical hooks (`on_up`, `on_down`, `on_left`, `on_right`) drive movement vectors into SCRIPT. The actual grid state, initialization, collision checks, push logic, and win-state validation are entirely handled inside raw Lua `SCRIPT` blocks.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 2 (`init`, `move`)
- **Native source files modified:** 0
- **New generic semantic commands added:** 0
- **Project-owned files required:** 1 Scene (plus launcher index/title/terms registration)
- **RTP dependencies:** pinned neutral Thestra RTP 1.0
- **validation warnings/errors encountered:** 0
- **bespoke workarounds:** SCRIPT handles all 2D array representation and iteration.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** No, raw SCRIPT was required.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

First attempt for A004.

## Improved

N/A (First attempt)

## Regressed

N/A (First attempt)

## Still Awkward

Similar to the D002 genre-translation experiment and A003 Snake, real-world 2D grids and unordered/ordered entity collections (like crates and goals) force the author to retreat into SCRIPT. Current Event semantics cannot handle nested lists or generic iteration well enough to evaluate win predicates or grid updates purely declaratively.

## New Architectural Evidence

A004 fully corroborates the evidence found in D002 and A003. Complex grid queries, pushing items, and verifying that multiple targets match multiple dynamic entities continue to exceed the declarative formula and event-handling capacity. This indicates a robust need for array manipulation, indexed queries, and grid iteration primitives, without building a Sokoban-specific backend subsystem.

## Verdict

**Playable benchmark; architectural gap confirmed.** A004 completes successfully via SCRIPT escape hatches, adding to the growing body of longitudinal evidence that Thestra's current Event system needs generic collection and grid semantics to cleanly express board and puzzle states.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
