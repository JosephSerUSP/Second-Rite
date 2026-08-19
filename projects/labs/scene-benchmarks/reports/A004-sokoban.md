# A004 — Sokoban

## Experiment

A004 — Sokoban

## Result

implementation complete; ready for owner playtest

## Current Implementation Shape

- The specimen is now `data/scenes/a004_sokoban.json` inside the neutral Scene Benchmark Project.
- It uses `windows` draw mode with one dynamically updated text board.
- Logical input hooks drive movement; Enter resets; B / Escape returns to the benchmark launcher.
- Scene-local `v` state survives cleanly across hooks and SCRIPT boundaries.
- Initialization and movement logic use SCRIPT blocks for array initialization, manipulation, and grid logic.

## Metrics

- number of authored Scene resources: 1
- number of Event Programs / Flows: 0
- number of SCRIPT blocks: 2
- approximate SCRIPT lines if any: 70
- native source files modified: 0
- new generic semantic commands added, if independently justified: 0
- Project-owned files required: 1
- RTP dependencies: 0
- validation warnings/errors encountered: 0
- bespoke workarounds: 0
- unsupported benchmark requirements: 0
- whether Studio authoring surfaces were sufficient: Partially (SCRIPT is required).
- whether the artifact runs independently of Second Gate: Yes.

## Changes Since Previous Attempt

N/A (First recorded benchmark attempt for A004).

## Improved

- Scene-local state and logical input fit naturally.
- Formula-driven text presentation consumes derived state without bespoke rendering code.
- The experiment remains an ordinary authored Scene.

## Regressed

N/A.

## Still Awkward

- Still lacks multidimensional array/grid semantics in native authored hooks, forcing a complete escape to SCRIPT.
- Authored collection construction/state is missing.
- Generic collection mutation (indexed replace/append/remove) is missing.
- Generic iteration over authored collections is missing.

## New Architectural Evidence

A004 Sokoban corroborates the evidence found in D002 Sokoban and A003 Snake: Thestra fundamentally lacks the necessary data structures (collections/grids) for non-trivial grid games in authored Scene hooks. This reinforces the need for architectural follow-up on generic collection and iteration semantics.

## Verdict

Thestra remains entirely dependent on SCRIPT blocks for grid-based game logic and state representation. While input and UI hook nicely into the scene model, any meaningful manipulation of board state must bypass authored commands.

## Owner Playtest

**Status:** pending

Launch `npm run lab:benchmarks`, choose **A004  Sokoban**, use arrows to move, Enter to reset, and B / Escape to return.

### Owner observations

Pending.

### Result after owner playtest

Pending.
