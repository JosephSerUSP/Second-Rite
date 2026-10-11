# A004 — Sokoban Benchmark Report

**Date:** 2026-10-11
**Benchmark:** A004 — Sokoban
**Version:** 3

## Current Result

complete

## Play

Launch `npm run lab:benchmarks`, choose **A004 — Sokoban**, then use arrow keys to steer and push crates. Enter resets the puzzle; B / Escape returns to the launcher.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a004_sokoban.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. The movement and collision resolution logic has been completely ported out of SCRIPT into native authored semantics, using declarative `SET_SCENE_STATE` and nested `IF` expressions to evaluate wall constraints and crate interactions. SCRIPT is now strictly bounded only to grid text rendering, as no native primitive exists for layout looping.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 1 (`render`)
- **approximate SCRIPT lines if any:** 31 lines
- **Native source files modified:** 0
- **New generic semantic commands added:** 0
- **Project-owned files required:** 1 Scene
- **RTP dependencies:** pinned neutral Thestra RTP 1.0
- **validation warnings/errors encountered:** 0
- **bespoke workarounds:** SCRIPT still handles text-grid string generation because there is no way to perform complex layout mapping natively.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** The authoring surface can now express the mechanics natively, but SCRIPT is still required for UI presentation.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- Movement and collision logic successfully rewritten from SCRIPT into purely authored commands via nested `IF` and `SET_SCENE_STATE` expressions, pushing the boundary of authored semantics.

## Improved

- Proves the computational maturity of the declarative state evaluator: complex conditional resolution like pushing boxes and checking wall bounds can now be completely described by the authored game logic without escaping to Lua.

## Regressed

- Natively expressing spatial bounds without a `function` primitive is intensely verbose. It forces redundant, massive formula expressions (copying the `isWall` equivalent) whenever a target cell needs validation (`sceneState.nx <= 0 or sceneState.nx >= 7...`).

## Still Awkward

- Collision and presentation. We still need SCRIPT for rendering text grid UI.

## New Architectural Evidence

This reconstruction proves that Thestra can technically express complex puzzle movement natively via nested `IF`s and `SET_SCENE_STATE`. However, doing so without functions or native grid primitives requires severe verbosity. It confirms the need for better spatial logic and UI loop elements, but proves the engine's core evaluator is computationally capable enough to handle state resolution without SCRIPT.

## Verdict

**Playable benchmark; architectural capabilities and limitations confirmed.** A004 completes successfully without Lua-based movement logic, demonstrating that declarative state mutation is expressive enough for Sokoban-style collisions. However, the extreme verbosity reveals that the engine still requires better spatial primitives for scale, and SCRIPT is still needed for grid UI generation.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
