# A004 — Sokoban Benchmark Report

**Date:** 2026-09-15
**Benchmark:** A004 — Sokoban
**Version:** 3

## Current Result

complete

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a004_sokoban.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses discrete variables for player and crate coordinates, similar to version 2, but completely eliminates raw Lua `SCRIPT` blocks. All state initialization, movement logic, boundary and collision checks, pushing rules, and victory conditions are expressed using declarative `SET_VAR` assignments with complex string formulas and the `SCENE_EVENT` call mechanism. The board presentation is handled declaratively using position formulas in independent window definitions instead of constructing a concatenated grid string.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 0
- **approximate SCRIPT lines if any:** 0
- **Native source files modified:** 0
- **New generic semantic commands added:** 0
- **Project-owned files required:** 1 Scene
- **RTP dependencies:** pinned neutral Thestra RTP 1.0
- **validation warnings/errors encountered:** 0
- **bespoke workarounds:** Large concatenated boolean formula expressions for wall collisions.
- **unsupported benchmark requirements:** None.
- **whether Studio authoring surfaces were sufficient:** Yes, raw SCRIPT is no longer required, though the wall definitions in the formula remain verbose.
- **whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt

- Completely removed all Lua `SCRIPT` blocks.
- Movement, wall collision, pushing crates, and win validation are now solved by `SET_VAR` multi-assignments and `IF` logic using declarative inline formulas (`v.hit_wall`, `v.push_c1`, `v.can_move`, etc.).
- Rendering the board via string concatenation was removed. We now present the fixed walls and background in one window, and dynamically position 1x1 windows for the player and crates using inline formulas (`"7 + v.px"`, `"8 + v.py"`).

## Improved

- The implementation has achieved 100% declarative authoring semantics.
- We no longer rely on backend leakage or Lua escape hatches.
- Presentation leverages composed, data-driven window rendering instead of generating ASCII map strings.
- Scene variables successfully carry complex interaction states for discrete items.

## Regressed

- Hardcoding grid layouts (like checking walls via long `(v.nx == 2 and v.ny == 2) or ...` strings) in formulas is extremely verbose and visually illegible compared to the raw Lua equivalent or a real 2D array representation.

## Still Awkward

- Checking collisions against static unchangeable geography still demands manually tracking coordinates in text formulas, making level design painful.
- Scaling this approach beyond a handful of crates or a small map is practically impossible due to the explosion of discrete variable queries needed.

## New Architectural Evidence

This fresh reconstruction proves that `SET_VAR` string formulas are powerful enough to evaluate discrete grid-based physics and collision rules, eliminating the strict requirement for Lua `SCRIPT` for small puzzles. It also proves that dynamic formula-based window sizing and positioning (`v.px`) successfully decouples semantic game state from presentation. However, it confirms that without native array or spatial querying capabilities, declarative authoring of spatial puzzles remains highly tedious and unscalable for authors.

## Verdict

**Playable benchmark; fully declarative but ergonomically hostile.** A004 completes successfully without any raw SCRIPT blocks. However, simulating a 2D spatial puzzle with long string formulas and discrete variables underscores the persistent need for native collection primitives or grid querying to make this pattern realistically authorable.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
