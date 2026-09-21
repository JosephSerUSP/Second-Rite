# Benchmark Report

### Benchmark
ID: A002
Name: Breakout
Benchmark Version: Current Main Semantics
Date: 2026-09-21

### Current Result
complete

### Current Implementation Shape
A completely fresh reconstruction of A002. The entire core game loop—paddle movement, ball movement, bounds checking, paddle collision, and block collision—has been implemented using purely authored semantic commands (`SET_VAR` multi-assignments and `IF` blocks). The presentation uses dynamic `rect` fields in `windows` to evaluate coordinate formulas for the paddle, ball, and each individual brick. Bricks are now rendered as individual panels toggled via declarative boolean visibility rather than relying on a raw Lua `SCRIPT` block string builder.

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
* bespoke workarounds: The bricks are not a true collection; they are hardcoded as separate boolean variables (`b0_0`, `b0_1`, etc.) and separate window elements, since Thestra lacks semantic commands for dynamic collections.
* unsupported benchmark requirements: None.
* whether Studio authoring surfaces were sufficient: Yes, entirely declarative.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
* Re-implemented freshly, proving that the declarative `IF` and `SET_VAR` commands can completely eliminate the raw Lua `SCRIPT` block previously used for managing bricks.
* Replaced the string-rendered brick grid with individual declarative UI panels for each brick.
* Converted the brick array into individual boolean state variables to allow declarative intersection logic.

### Improved
* **Total Declarative Shift:** The entire simulation, including the collection of bricks, is now 100% declarative. The raw Lua `SCRIPT` block is gone.
* **Declarative Visibility:** The presentation cleanly handles brick destruction by toggling window dimensions/visibility based on inline formula conditions (`v.b0_0 and 3 or 0`).

### Regressed
* **Legibility and Scalability:** Because there is no semantic command for dynamically iterating collections or performing arbitrary array mutation, each brick requires its own dedicated `IF` block for collision and its own `panel` window for rendering. This approach does not scale to a 50-brick field.

### Still Awkward
The requirement to manage a collection of entities (bricks) forces an unrolled, hardcoded approach. Without semantic commands for `foreach` or generic spatial querying, simulating multiple destructible entities declaratively requires repeating the collision and rendering logic for every single entity.

### New Architectural Evidence
A002 Breakout demonstrates that the expressive power of declarative window styling and inline formulas is sufficient to model complete game state rendering without raw Lua string-building. However, the resulting implementation highlights a missing foundational piece in Thestra's semantic vocabulary: backend-neutral commands for instantiating, iterating, and querying collections (arrays of entities).

### Verdict
**Playable benchmark; SCRIPT eliminated but collections remain unaddressable.** A002 Breakout proves that declarative formulas and dynamic window dimensions can fully subsume both the physics and presentation of the game, completely eliminating raw Lua `SCRIPT`. However, having to manually unroll every brick into its own discrete state variable, intersection condition, and window element proves that managing true dynamic collections remains a critical gap in Thestra's authoring model.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: LEFT/RIGHT to move paddle, Enter to restart, B to exit.

Owner observations: (pending)
Result: (pending)
