# C001 — Four-Paddle Pong

### Benchmark
ID: C001
Name: Four-Paddle Pong
Benchmark Version: Current Main Semantics
Date: 2026-10-06

### Current Result
complete

### Current Implementation Shape
Authored Scene composition building upon A001 (Pong). The simulation includes an extended field with 4 independent paddles. The layout relies on formula-evaluated `rect` properties in `windowLayout` for visual representation. Update and collision logic are native, purely authored commands (`SET_SCENE_STATE`, `IF`) checking 4 separate impact rectangles. The X axis inputs (Left/Right) are bound to the third (top) paddle, while the Y axis inputs (Up/Down) bound to the first (left) paddle, with simple AI controlling the bottom and right paddles.

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 0
* approximate SCRIPT lines: 0
* native source files modified: 0
* new generic semantic commands added: 0
* Project-owned files required: c001_four_paddle.json, index.json, title.json, terms.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: None.
* unsupported benchmark requirements: None.
* whether Studio authoring surfaces were sufficient: Yes, JSON structure maps perfectly to standard semantic blocks.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
N/A (First attempt at this exact mutation)

### Improved
* **Formula capability:** Using mathematical functions via formulas continues to excel. `v.time.dt` seamlessly handles smooth bounds movement across all four paddles in both vertical and horizontal directions.
* **Component scaling:** Expanding A001 to support four paddles required no engine-level abstractions, validating the compositional strength of the engine's declarative properties and logic blocks.

### Regressed
None.

### Still Awkward
Continuous simulation with repetitive branching (checking bounds/collisions across four paddles) requires verbose JSON replication of conditions and assignment blocks. We physically duplicated physics logic and collision checks rather than utilizing any looping or mapping system, which the engine lacks for scene states.

### New Architectural Evidence
The declarative semantic representation holds up under the increased structural multiplicity. While somewhat verbose to write, adding `paddle3X`, `paddle4X` properties and associated bounding logic does not degrade performance or authorability constraints.

### Verdict
**Complete architectural success.** A clean structural mutation of A001 Pong that completely avoided raw `SCRIPT` logic. The implementation reinforces that Thestra's scene logic semantics can cleanly compose complex 2D positional logic.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: UP/DOWN for left paddle, LEFT/RIGHT for top paddle.

Owner observations: (pending)
Result: (pending)
