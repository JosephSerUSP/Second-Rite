# A004 — Sokoban Benchmark Report

**Date:** 2026-09-11
**Benchmark:** A004 — Sokoban
**Version:** 3

## Current Result

complete

## Play

Launch `npm run lab:benchmarks`, choose **A004 — Sokoban**, then use arrow keys to steer and push crates. Enter resets the puzzle; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a004_sokoban.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. Building on v2, it removes the `SCRIPT` block for evaluating movement and wall collisions entirely. The movement constraints and multi-box pushing rules are now expressed purely as declarative `IF` condition blocks leveraging `SET_VAR` evaluation for collision detection (`v.nx < 0 or (v.nx == 2 and v.ny == 2)`). Only the string array rendering remains in a `SCRIPT` block.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 1 (`render`)
- **approximate SCRIPT lines if any:** 42 lines across one block.
- **Native source files modified:** 0
- **New generic semantic commands added:** 0
- **Project-owned files required:** 1 Scene
- **RTP dependencies:** pinned neutral Thestra RTP 1.0
- **validation warnings/errors encountered:** 0
- **bespoke workarounds:** SCRIPT still handles the text-grid string generation because there is no way to perform complex layout mapping or looping natively. The movement collision relies on an extremely long hardcoded mathematical statement (`v.is_wall`) which acts as a brute-force constraint, heavily duplicated since `CALL_FLOW` and array primitives aren't viable.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** No, raw SCRIPT was required for presentation, and the math conditions for grid logic are barely manageable.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- Completely replaced the Lua `move` block with native `IF` commands and `SET_VAR` assignments.
- Extracted collision rules into extremely long conditional statements bound to variables (like `v.is_wall`).

## Improved

- We finally pushed movement and state resolution fully into the declarative layer. The actual step-by-step logic (check wall, check crate, move crate) is completely expressed using standard `IF` structures. The number of raw Lua scripts drops to just one.

## Regressed

- Legibility of the map constraints has plummeted. Expressing a 2D grid's collision space as a single string of `or` conditions inside a `SET_VAR` is incredibly brittle.

## Still Awkward

Grid definitions and queries. The SCRIPT escape hatch remains strictly necessary to present the 2D grid text string, as `SET_VAR` lacks looping. Defining grid collision as a declarative formula proves that it's *technically* possible, but fundamentally inappropriate for authoring without native array structures.

## New Architectural Evidence

This reconstruction demonstrates the limits of `SET_VAR` formula parsing. While it successfully handles state mutation entirely without SCRIPT, expressing spatial rules as 1D logical statements produces unmaintainable authored blocks. It confirms that "eliminating SCRIPT" is not inherently better if the resulting declarative shape is illegible. Genuine collection, array, or grid-query primitives are mandatory if we want this genre to be safely authorable.

## Verdict

**Playable benchmark; SCRIPT reduction achieved but architectural gap confirmed.** A004 completes successfully and we proved Sokoban logic can be fully declarative, but the resulting collision constraints are so hostile to authors that it underscores the necessity of native spatial/array capabilities over brute-force `IF` conditions.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
