# A003 — Snake Benchmark Report
**Date:** 2026-08-14
**Benchmark:** A003 - Snake
**Version:** 1

## Current Result
complete

## Current Implementation Shape
The implementation is an authored Scene (menu kind) using `data/scenes/snake.json`. It leverages a text-based grid representation displayed via `boardText` in a UI window frame. The logic is handled through data-driven scene hooks: `on_enter` initializes the state, `on_frame` acts as the game loop using a timer variable decremented each frame, and directional hooks (`on_up`, `on_down`, `on_left`, `on_right`) manipulate the movement vector. Grid manipulation, movement, collision detection, and array handling are offloaded to `SCRIPT` blocks as engine declarative commands lack robust array/2D grid capabilities.

## Metrics
- **Authored Scene resources:** 1 (snake.json)
- **Number of Event Programs / Flows:** 0
- **Number of SCRIPT blocks:** 6 (`init`, `update`, `input_up`, `input_down`, `input_left`, `input_right`)
- **Approximate SCRIPT lines:** ~70
- **Native source files modified:** 0
- **New generic semantic commands added:** 0
- **Project-owned files required:** 1 (data/scenes/snake.json, added to data/scenes/index.json)
- **RTP dependencies:** None (standalone Scene)
- **Validation warnings/errors encountered:** Expected sandbox audio warnings, `os.time()` nil index, but overall `VALIDATE OK`.
- **Bespoke workarounds:** Frame delta integration required tracking time inside `v.tickTimer` decremented manually by a constant (~0.01666) or handled via explicit `on_frame` decrement because the engine does not natively expose `dt` or a robust tick timer to variables directly in a way that doesn't rely on constant values or external math functions in formula.
- **Unsupported benchmark requirements:** None.
- **Whether Studio authoring surfaces were sufficient:** Hand-authored JSON required due to the heavy reliance on `SCRIPT` for array management.
- **Whether the artifact runs independently of Second Gate:** Yes.

## Changes Since Previous Attempt
This is the initial attempt documented for A003 in current main. Thus, no direct baseline comparison exists. (Comparing against Sokoban A004 architecture: Snake requires a real-time game loop which necessitated the use of `on_frame` and delta time workarounds, whereas Sokoban is strictly turn-based and driven by input hooks.)

## Improved
- Scene declarative structure successfully hosts a real-time game loop through `on_frame`, proving that custom real-time mini-games can be authored without touching native `.lua` engine code.
- Directional input bindings natively integrate into the scene without modifying input maps.

## Regressed
N/A (First run)

## Still Awkward
- The lack of native Array/Collection semantics forces grid-based logic and ordered collections (like the Snake body) into `SCRIPT` blocks.
- Real-time loops require awkward timer decrementing (e.g., `v.tickTimer - 0.01666`) because `dt` isn't injected into the formula context natively for `on_frame`.
- `SCRIPT` requires multiline string encoding in JSON, making it harder to write and maintain without external Python scripts.

## New Architectural Evidence
- The `on_frame` hook is versatile enough to act as an update loop for mini-games if state is carefully managed, but we may need a native `TICK_TIMER` or `dt` exposed to the context to make this pattern cleaner.
- `SCRIPT` remains the only viable fallback for 2D coordinate translation and array tracking.

## Verdict
Thestra's Scene semantics can successfully host real-time grid-based mini-games (Snake), but the reliance on `SCRIPT` for arrays and the awkwardness of frame-timing demonstrate that declarative collections and a native timer semantic are necessary to reduce code-behind dependency.
