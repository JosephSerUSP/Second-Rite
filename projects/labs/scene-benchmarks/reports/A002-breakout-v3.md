# Benchmark Report

### Benchmark
ID: A002
Name: Breakout
Benchmark Version: Current Main Semantics

### Current Result
complete

### Current Implementation Shape
A fresh reconstruction of A002 replacing all raw Lua `SCRIPT` blocks with declarative logic. Entities are represented with discrete variables (`v.b1` through `v.b24`) to represent a collection of bricks without native collections semantics. State is updated exclusively via `SET_VAR` multi-assignments and `IF` conditions. The bricks are rendered as individual windows whose visibility and width/height are controlled dynamically via formulas (`rect.w = "v.b1 and 3 or 0"`).

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 0
* approximate SCRIPT lines if any: 0
* native source files modified: 0
* new generic semantic commands added: 0
* Project-owned files required: a002_breakout.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: Simulated array/collection semantics by declaring 24 discrete variables (`v.b1` to `v.b24`) and manually unrolling their collision logic into individual `IF` statements.
* unsupported benchmark requirements: None.
* whether Studio authoring surfaces were sufficient: No, declaring 24 discrete windows and IF statements is extremely tedious in a UI, though mechanically supported.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
* Replaced all raw Lua `SCRIPT` blocks with declarative commands.
* Eliminated the string-building rendering logic for the brick array.
* Used dynamic formulas in window rect dimensions (`v.bN and 3 or 0`) to render multiple distinct brick entities.
* Expanded collision checks and initialization directly into authored multi-assignment blocks.

### Improved
* **Total Declarative Purity:** The entire game loop (physics, bounds, collisions, collection rendering) is now 100% authored through declarative engine commands (`SET_VAR`, `IF`) without a single line of Lua script.
* **Component Presentation:** The bricks render as standard declarative windows, avoiding the hacky ASCII art string concatenation from the previous version.

### Regressed
* **JSON Bloat and Legibility:** Because Thestra lacks native commands for array mutation or dynamic sub-element rendering, a simple 24-brick field requires generating 24 distinct windows and 24 individual collision `IF` blocks, exploding the JSON file size and making the scene highly illegible for a human author.

### Still Awkward
* **Collection Management:** Dealing with arbitrary collections of similar entities remains the largest point of friction. Discrete variable generation is functionally effective but architecturally brittle.

### New Architectural Evidence
* The success of `rect.w = "v.b1 and 3 or 0"` proves that declarative formulas can robustly handle per-entity visibility and bounds without native scene orchestration. However, the sheer verbosity of unrolling loops into discrete variables highlights the critical need for a native collection/iterator primitive in authored state semantics.

### Verdict
**Playable benchmark; fully declarative but excessively verbose.** The engine successfully supports a 100% declarative reconstruction using dynamic window formulas, proving the flexibility of the `SET_VAR`/`IF` paradigm. However, the absence of generic collection-management commands forces authors to manually unroll loops and entities, sacrificing maintainability for purity.
