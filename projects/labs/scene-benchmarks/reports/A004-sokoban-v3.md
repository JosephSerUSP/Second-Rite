# A004 — Sokoban Benchmark Report

**Date:** 2026-10-15
**Benchmark:** A004 — Sokoban
**Version:** 3

## Current Result

complete

## Play

Launch `npm run lab:benchmarks`, choose **A004 — Sokoban**, then use arrow keys to steer and push crates. Enter resets the puzzle; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a004_sokoban.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. State initialization is handled via discrete `SET_SCENE_STATE` commands for player and crate coordinates, while the actual game logic (validating moves, wall collisions, crate pushes, and board string generation) remains completely reliant on raw Lua SCRIPT blocks, due to the engine still lacking native spatial arrays or conditional layout query primitives.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 2 (`move`, `render`)
- **approximate SCRIPT lines if any:** 75 lines across two blocks.
- **Native source files modified:** 0
- **New generic semantic commands added:** 0
- **Project-owned files required:** 1 Scene
- **RTP dependencies:** pinned neutral Thestra RTP 1.0
- **validation warnings/errors encountered:** 0
- **bespoke workarounds:** SCRIPT handles all collision detection, push validation, and text grid generation.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** No, raw SCRIPT was required for complex collision and presentation.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- Fresh implementation using the current state and formula semantics.
- SCRIPT blocks re-authored from scratch while faithfully preserving the original frozen Sokoban puzzle layout and starting positions.

## Improved

- None. The core spatial constraints that forced logic into SCRIPT in previous versions remain unaddressed by current declarative commands.

## Regressed

- None.

## Still Awkward

Collision and presentation. The engine still requires SCRIPT escape hatches to evaluate grid collisions and push rules (e.g., checking if a crate is hitting a wall or another crate). Dynamically constructing the visual string for the grid also continues to demand SCRIPT.

## New Architectural Evidence

This third attempt reaffirms that while small domain states can be declared discretely, evaluating spatial logic and conditional rendering intrinsically demands array manipulation, indexed queries, or grid semantics that Thestra currently lacks natively.

## Verdict

**Playable benchmark; architectural gap confirmed.** A004 completes successfully, but remains highly dependent on `SCRIPT`. The repeated evidence confirms that generic spatial querying and string-building primitives are required to bring Sokoban-style games into the declarative authoring fold.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
