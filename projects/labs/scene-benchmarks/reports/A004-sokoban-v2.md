# A004 — Sokoban Benchmark Report

**Date:** 2026-08-30
**Benchmark:** A004 — Sokoban
**Version:** Current Main Semantics

## Current Result
complete

## Current Implementation Shape
A complete fresh reconstruction of A004 using CURRENT authoring practices. The implementation uses a text-based grid displayed via `boardText` inside an authored frame. Logical hooks (`on_up`, `on_down`, `on_left`, `on_right`) evaluate input vectors natively with declarative `IF` and `SET_VAR` assignments. However, Thestra still fundamentally lacks an authored model for generic spatial iteration, grid lookups, list mutation, and win-state matching across multiple entity targets. As a result, the entirety of initialization, coordinate translation, bounds checking, and push rules are encapsulated in raw Lua `SCRIPT`.

## Metrics

- number of authored Scene resources: 1
- number of Event Programs / Flows: 0
- number of SCRIPT blocks: 2 (`init`, `move`)
- approximate SCRIPT lines: ~110
- native source files modified: 0
- new generic semantic commands added: 0
- Project-owned files required: 1 Scene (`a004_sokoban.json`) plus launcher registration.
- RTP dependencies: pinned neutral Thestra RTP 1.0
- validation warnings/errors encountered: 0
- bespoke workarounds: SCRIPT is required to manage all 2D array representation and iteration since Event commands cannot index arrays or construct multi-line strings easily.
- unsupported benchmark requirements: None.
- whether Studio authoring surfaces were sufficient: No, raw SCRIPT remains absolutely required for collection querying and bounds collision over arrays.
- whether the artifact runs independently of Second Gate: Yes.

## Changes Since Previous Attempt
- This is a fresh reconstruction, proving the previous architectural assessment still holds.
- Standardized inputs to utilize purely declarative `IF` wrappers before triggering SCRIPT, proving input encapsulation is stable.

## Improved
- No new generics have changed the nature of managing grids.

## Regressed
- Nothing regressed.

## Still Awkward
- Similar to prior findings, real-world 2D grids and unordered/ordered entity collections (like crates and goals) force an immediate escape hatch into Lua SCRIPT. The event semantics still lack the necessary generic grid traversal and nested list evaluations to determine valid push logic across independent board indices.

## New Architectural Evidence
A004 repeatedly confirms the most pressing semantic gap identified across D002 and A003: robust array manipulation, indexed queries, and grid iteration primitives. Single-entity real-time simulations (Pong, Breakout ball physics) can increasingly rely on formula evaluation, but any game requiring a persistent, querying collection (crates, bricks, snake segments) requires raw scripting to represent its model state.

## Verdict
**Complete benchmark; persisting architectural gap.** A004 completes successfully via SCRIPT, maintaining its historic evidence that Thestra's generic state abstractions still fall short when tasked with generic spatial modeling, arrays, and complex state querying without bespoke backend subsystems.

## Owner Playtest

**Status:** READY FOR OWNER PLAYTEST

Controls: Arrow keys move player and push crates. Enter resets the board. B goes back.

### Owner observations
(pending)

### Result after owner playtest
(pending)
