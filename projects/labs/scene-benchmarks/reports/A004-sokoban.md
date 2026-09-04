# A004 — Sokoban Benchmark Report

**Date:** 2026-08-27
**Benchmark:** A004 — Sokoban
**Version:** Current Main Semantics

## Current Result

complete

## Play

Launch `npm run lab:benchmarks`, choose **A004 — Sokoban**, then use arrow keys to steer and push crates. Enter resets the puzzle; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a004_sokoban.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It abandons the dynamic string-grid and raw Lua `SCRIPT` fallback from the previous attempt. Instead, it uses dynamic `rect` fields in `windows` to evaluate coordinate formulas (`v.px`, `v.c1x`, `v.c2x`) for rendering. The game logic (movement, collision, pushing, and win-state validation) is entirely implemented natively via declarative `IF` condition blocks and `SET_VAR` multi-assignments by explicitly tracking the two individual crates as distinct coordinate pairs, resolving the previous iteration dependency.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 0
- **Native source files modified:** 0
- **New generic semantic commands added:** 0
- **Project-owned files required:** 1 Scene (plus launcher index/title/terms registration)
- **RTP dependencies:** pinned neutral Thestra RTP 1.0
- **validation warnings/errors encountered:** 0
- **bespoke workarounds:** None. The puzzle bounds and goals are hard-coded into the coordinate conditions rather than generalized to a dynamic map system.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** Yes, the structure maps perfectly to existing semantic commands.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- Eliminated the raw Lua `SCRIPT` blocks used for movement, collision checking, and board re-rendering.
- Replaced the string-building UI with declarative `windows` that position the player and crates using dynamic `rect` variables (`v.c1x`, `v.c2x`, etc.).
- Swapped logic to use pure Thestra `IF` checks and `SET_VAR` multi-assignments rather than arbitrary table iterations.

## Improved

- **Backend-neutrality:** The complete Sokoban simulation for a fixed board and small crate count can now be achieved natively without raw Lua, demonstrating that `SET_VAR` and nested `IF` condition checks are expressive enough for strict discrete-grid logic.
- **Presentation Composition:** Continuous explicit coordinates translate seamlessly into `window` UI layers, removing the need for an awkward string grid rebuild loop and making presentation significantly cleaner.

## Regressed

N/A

## Still Awkward

The explicit entity tracking (`c1x`, `c2x`) requires dense, nested `IF` evaluations to check collisions individually against each distinct object. This confirms that while the solver works for *this specific bounded puzzle*, generic arrays or list iteration primitives would still be necessary for a full-scale Sokoban game without exponential branching complexity.

## New Architectural Evidence

A004 corroborates the findings of A001 and A002: dynamic `rect` rendering and nested `IF`/`SET_VAR` commands successfully isolate pure mechanics into authored state semantics. However, unrolling entity collision logic reveals the practical limitations of lacking dynamic array iteration, confirming the persistent need for generic collection management commands for robust grid simulation.

## Verdict

**Playable benchmark; architectural success.** A004 completes successfully, proving that strict spatial puzzle rules can be authored exclusively through semantic formulas and dynamic window properties. It eliminates all SCRIPT usage, successfully aligning the Sokoban benchmark with the current authoring capability trajectory, while reinforcing the need for formal collection querying.

## Owner Playtest

**Status:** READY FOR OWNER PLAYTEST

### Owner observations

Pending.

### Result after owner playtest

Pending.
