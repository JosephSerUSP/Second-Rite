# A004 — Sokoban Benchmark Report

**Date:** 2026-08-15
**Benchmark:** A004 — Sokoban
**Version:** 1

## Current Result

ready for owner playtest

## Play

Launch `npm run lab:benchmarks`, choose **A004 — Sokoban**, use arrows to move, Enter to reset, and B / Escape to return.

## Current Implementation Shape

The implementation is an authored Scene (`data/scenes/a004_sokoban.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. It uses a text-based grid displayed through `boardText`. Logical input hooks drive movement. SCRIPT owns the Sokoban grid state, bounds checks, movement rules, crate pushing logic, goal iteration, and redrawing.

## Metrics

- **Authored Scene resources:** 1
- **Event Programs / Flows:** 0
- **SCRIPT blocks:** 2 (`init`, `move`)
- **Native source files modified:** 0
- **New game-specific native commands:** 0
- **Project-owned benchmark files required:** 1 Scene plus launcher registration/report
- **RTP:** pinned neutral Thestra RTP 1.0

## Changes Since Previous Attempt

This is the first canonical attempt at A004 (previous D002 was a genre-translation experiment). The implementation is functionally similar to D002, translated into the canonical A004 framework without altering its basic architecture.

## Improved

- Scene-local state and logical input fit naturally.
- Formula-driven text presentation consumes derived state cleanly without requiring bespoke rendering code.

## Still Awkward

- Sokoban's state requires populated grid collections (`v.grid`, `v.goals`). Event Programs cannot currently materialize populated collection values, mutate an authored collection by index, or iterate an arbitrary authored collection.
- Because of this, the core game loop (movement, bounds checking, crate pushing, checking win states) completely escapes into SCRIPT.

## Architectural Evidence

A004 provides further canonical evidence that while declarative menus and formulas are strong, authored collections and collection mutation are a notable capability gap. It aligns exactly with evidence from A003 (Snake) and D002 (Sokoban as Scene). However, this gap does not justify special multidimensional/Grid semantics on its own, nor A004-specific commands. The board remains representable as a flat list plus computed index, emphasizing the need for generic collection features.

## Verdict

The implementation is functionally clean but heavily reliant on SCRIPT for all state manipulation, confirming that the current lack of generic authored collection semantics is a consistent source of friction for tile/grid games.

## Owner Playtest

**Status:** pending

### Owner observations

Pending.

### Result after owner playtest

Pending.
