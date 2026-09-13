# Benchmark Report

### Benchmark
ID: A002
Name: Breakout
Benchmark Version: Current Main Semantics
Date: 2026-09-13

### Current Result
complete

### Current Implementation Shape
A fresh reconstruction of A002 using current main semantics. Authored Scene composition leverages the fixed Scene clock and logical input hooks (`on_left`, `on_right`) to author player intent. The core physics update loop uses pure declarative commands (`SET_VAR` multi-assignments and `IF` blocks). We evaluate dynamic window dimension formulas to place the ball and paddle. The previous `SCRIPT` logic used for initializing the brick field, testing intersections, and managing rendering arrays has been completely eliminated. The bricks are now fully managed declaratively via state variables (e.g. `v.b1` through `v.b12`), and their rendering handles layout natively via 12 individual `panel` windows styled as the destructible bricks which fall offscreen when broken.

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 0
* approximate SCRIPT lines: 0
* native source files modified: 0
* new generic semantic commands added: 0
* Project-owned files required: a002_breakout.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: Unrolling the dynamic array logic into discrete windows and boolean hit-test assignments (`b1`, `hit_b1`, etc) was required to fully eliminate SCRIPT.
* unsupported benchmark requirements: None.
* whether Studio authoring surfaces were sufficient: Yes, JSON structure maps perfectly to standard semantic blocks.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
* Re-implemented freshly. Replaced the raw Lua collection mutation and string building completely.
* Each "brick" is now a standalone UI window mapped to boolean state using a ternary coordinate formula (e.g. `v.b1 and X or 100`) to toggle visibility.
* Intersection logic is now fully unrolled in `SET_VAR` assignments, aggregating into an `any_hit` condition which resolves state changes.

### Improved
* **Backend-Neutrality:** By adopting unrolled variables, the Breakout logic operates 100% via backend-neutral formulas and window abstractions, meaning `SCRIPT` is no longer technically required for this scale.

### Regressed
* **Legibility/Scalability:** While completely declarative, the required duplication to manually create state variables and collision checks for every single brick is exponentially tedious. Scaling to 100 bricks is unmanageable without dynamic iteration.

### Still Awkward
While unrolling small arrays into discrete variables works, this artifact reinforces that managing collections intrinsically scales poorly without native list variables or spatial-query commands.

### New Architectural Evidence
A002 proves that declarative arrays can technically be represented if the collection is bounded and unrolled, demonstrating the flexibility of `SET_VAR`. However, the verbose duplication required to avoid Lua reinforces the argument for first-class collection management commands (e.g., `FOR_EACH_VAR` or dynamic spatial abstractions) to achieve both purity and legibility simultaneously.

### Verdict
**Playable benchmark; SCRIPT eliminated but collection friction verified.** A002 Breakout can now be modeled entirely via declarative window formulas and `SET_VAR` collision evaluations. However, the required manual unrolling of collection data into discrete variables reinforces the evidence that generic iteration and array semantics remain the most critical capability gap for scaling complex action simulations.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: LEFT/RIGHT to move paddle, Enter to restart, B to back.

Owner observations: (pending)
Result: (pending)
