# D002 — Sokoban as Scene

## Experiment

D002 — Sokoban as Scene

## Result

implementation complete; ready for owner playtest

## Review status

The prototype is preserved as the experiment actually authored it. The prior architecture review remains valid: current Formula supports read-only record access, 1-based list indexing (`value[index]`), and `#list`; the demonstrated gap is narrower. Event Programs cannot currently materialize populated collection values, mutate an authored collection by index, or iterate an arbitrary authored collection without escaping into SCRIPT.

## Authored Surface

- The specimen is now `data/scenes/d002_sokoban.json` inside the neutral Scene Benchmark Project rather than root Second Gate data.
- It uses `windows` draw mode with one dynamically updated text board.
- Logical input hooks drive movement; Enter resets; B / Escape returns to the benchmark launcher.
- Scene-local `v` state survives cleanly across hooks and SCRIPT boundaries.

## SCRIPT / Native Escape Hatches

- Initialization uses SCRIPT to construct populated collection state (`v.grid`, `v.goals`) and build the initial display string.
- Movement uses SCRIPT for indexed mutation, goal iteration, crate pushing, completion checks, and redraw.
- No Sokoban-specific native command or source file is required.

## Missing Reusable Semantics

- Authored collection construction/state.
- Generic collection mutation (indexed replace/append/remove).
- Generic iteration over authored collections.

D002 alone does **not** justify special multidimensional/Grid semantics. The board remains representable as a flat list plus computed index. Its architectural follow-up remains #472, now reinforced by A003 Snake rather than treated as a one-specimen demand.

## Reusable Successes

- Scene-local state and logical input fit naturally.
- Formula-driven text presentation consumes derived state without bespoke rendering code.
- The experiment remains an ordinary authored Scene.

## Owner Playtest

**Status:** pending

Launch `npm run lab:benchmarks`, choose **D002 — Sokoban as Scene**, use arrows to move, Enter to reset, and B / Escape to return.

### Owner observations

Pending.

### Result after owner playtest

Pending.
