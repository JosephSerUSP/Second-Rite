### Benchmark
A003, Snake, Version 2

### Current Result
complete

### Current Implementation Shape
The implementation is an authored Scene (`data/scenes/a003_snake.json`) inside the neutral `projects/labs/scene-benchmarks/` Project. The SCRIPT blocks from the previous version have been entirely eliminated. The grid is represented by 144 discrete step variables (`c0_0` through `c11_11`), storing the absolute step number when a cell was occupied. Self-collision and rendering are calculated by taking the difference between the current `step` and each cell's step value against the snake's `len`. Movement, collision, grid state, and apple-eating are now entirely implemented using pure `IF`, `SET_LOCAL`, and `SET_SCENE_STATE` commands.

### Metrics
- number of authored Scene resources: 1
- number of Event Programs / Flows: 0
- number of SCRIPT blocks: 0
- approximate SCRIPT lines if any: 0
- native source files modified: 0
- new generic semantic commands added: 0
- Project-owned files required: 1 Scene plus launcher registration/report
- RTP dependencies: pinned neutral Thestra RTP 1.0
- validation warnings/errors encountered: 0
- bespoke workarounds: The grid uses 144 discrete variables rather than an array, generating 144 explicit `IF` assignments per frame, and the text rendering formula relies on a large concatenated string of 144 ternary operators.
- unsupported benchmark requirements: None
- whether Studio authoring surfaces were sufficient: The absence of array commands means generating the JSON by script was the only practical way to write out 144 variables.
- whether the artifact runs independently of Second Gate: Yes

### Changes Since Previous Attempt
- Completely removed all SCRIPT logic (down from 2 blocks).
- Replaced the `init` and `update` SCRIPTs with an explicit grid of 144 discrete variables tracking the `step` of visitation.
- Text rendering is now natively handled by a pure formula string concatenating the grid state dynamically using `sceneState.boardText`.
- Replaced arbitrary object/table inserts with declarative `IF` multi-assignments and difference equations (`step - c_x_y < len`) for trailing tails.

### Improved
- Snake is now a 100% pure declarative Scene with zero raw Lua code.
- State mutation and grid logic is cleanly expressed using current `SET_SCENE_STATE` and `IF` command vocabulary.

### Regressed
- Generating the JSON required Python scripting due to the sheer verbosity of unrolling a 12x12 grid into 144 explicit assignments. The resulting Scene JSON is larger and much harder to read or maintain manually.

### Still Awkward
- Ordered mutable collections and arrays are still missing from the engine semantics. Using 144 variables to simulate an array requires massive copy-pasted IF blocks or Python generation to create.
- String concatenation of 144 discrete ternary evaluations works cleanly but exposes the same need for generic list iteration.

### New Architectural Evidence
This benchmark update provides striking new evidence: a grid-based collection (like Snake) can be entirely implemented with 100% declarative `IF` and `SET_SCENE_STATE` by leveraging discrete variables and step tracking. While verbose, it demonstrates that the engine's declarative state primitives are Turing-complete enough to replace SCRIPT for dynamic collections. However, it also strongly solidifies the argument for exposing generic lists and arrays, as maintaining 144 independent variable assignments by hand is not a feasible long-term authoring path.

### Verdict
Playable benchmark; SCRIPT eliminated, authorability pushed to extreme limits. A003 proves that the engine's current declarative state system can fully replace SCRIPT for grid-based collections, completely eliminating raw Lua. However, the extreme verbosity of unrolling 144 variables reinforces the pressing need for generic array/list commands to make authoring practical.
