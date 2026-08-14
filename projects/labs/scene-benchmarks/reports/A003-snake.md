# A003 — Snake Benchmark Report

**Date:** 2026-08-14  
**Benchmark:** A003 — Snake  
**Version:** 1

## Current Result

ready for owner playtest

## Play

Launch `npm run lab:benchmarks`, choose **A003 — Snake**, then use arrow keys to steer. Enter restarts the specimen; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a003_snake.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses a text-based grid displayed through `boardText`. `on_frame` provides the update loop; directional hooks manipulate the movement vector; SCRIPT owns collection/grid operations that current declarative commands cannot express cleanly.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 6 (`init`, `update`, four direction handlers)
- **Native source files modified:** 0
- **New game-specific native commands:** 0
- **Project-owned benchmark files required:** 1 Scene plus launcher registration/report
- **RTP:** pinned neutral Thestra RTP 1.0

## Still Awkward

- Ordered mutable collections force Snake body state into SCRIPT.
- Real-time loops decrement an authored timer by a fixed `0.01666` because `dt` is not directly available to ordinary Scene formulas.
- Multiline SCRIPT embedded in JSON remains substantially harder to author and inspect than Event commands.

## Architectural Evidence

Snake independently reinforces D002's collection-pressure evidence: a growing ordered body needs collection construction, indexed/ordered mutation, and iteration. It also adds distinct evidence around time semantics. This still does **not** justify Snake-specific commands or a Grid subsystem by itself.

## Owner Playtest

**Status:** pending

Machine validation/boot evidence may establish that the specimen loads and remains runnable, but it must not be described as human-playtested until the owner actually plays it.

### Owner observations

Pending.

### Result after owner playtest

Pending.
