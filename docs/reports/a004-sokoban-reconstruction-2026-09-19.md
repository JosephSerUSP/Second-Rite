# A004 — Sokoban — 2026-09-19 Reconstruction

## Benchmark

**ID:** A004
**Name:** Sokoban
**Version:** frozen benchmark

## Current Result

complete

## Current Implementation Shape

The scene was rewritten to completely eliminate its native Lua SCRIPT payload. Entities (walls, goals, crates, player) are represented by individual text windows instead of composing a single `v.boardText` string inside a script block. State transitions (grid collisions, pushes) are modeled natively via declarative `SET_VAR` multi-assignments and `IF` logic hooks for movement directions.

## Metrics

* Number of authored Scene resources: 1
* Number of Event Programs / Flows: 0
* Number of SCRIPT blocks: 0
* Approximate SCRIPT lines: 0
* Native source files modified: 0
* New generic semantic commands added: 0
* Project-owned files required: 1 (a004_sokoban.json)
* RTP dependencies: standard scene architecture
* Validation warnings/errors encountered: 0
* Bespoke workarounds: none
* Unsupported benchmark requirements: none
* Whether Studio authoring surfaces were sufficient: yes, using standard scene nodes
* Whether the artifact runs independently of Second Gate: yes

## Changes Since Previous Attempt

* The `goldenScript` received explicit `wait` times to satisfy automated replay execution.
* The rendering architecture transitioned from a `SCRIPT` building a monolithic `v.boardText` block to using declarative windows with dynamically bound formulas for coordinates (`x: "6 + v.px"`, etc.).
* The input keys replaced their SCRIPT delegates with fully declarative SET_VAR / IF flow logic for pushing bounds.

## Improved

* Eliminating the manual `boardText` buffer logic makes presentation more naturally declarative.
* Grid math and collision are now composed of simple `IF` checks natively evaluated by the Engine rather than arbitrary script escapes.

## Regressed

* Wall configuration is relatively verbose (requiring multiple discrete `wall_N` windows) when manually configured without a map tilemap surface.
* The collision expressions (combining grid bounds checks with inner wall conditions) are extremely long strings within the `IF` logic due to the lack of an array/in-bounds helper function in pure authored formula.

## Still Awkward

* Simulating physics/grid collision in pure `SET_VAR` multi-assignments requires deep nested `IF` statements and repetitive evaluation (e.g., repeating the `isWall` condition inline for crates) because there is no built-in `move_and_slide` or `push` primitive for declarative Scenes.

## New Architectural Evidence

* Individual styled `invisible` windows for elements of a small grid (40+ windows) successfully act as sprites without perceivable overhead or semantic mismatch in the declarative renderer.

## Verdict

The engine successfully supports complex collision interactions (multi-crate push tests) natively with `IF` and `SET_VAR` formulas, confirming that SCRIPT is largely obsolete for grid-based minigames, though at the cost of high manual logic verbosity.