# C001 — Four-Paddle Pong

### Experiment
C001 — Four-Paddle Pong

### Result
complete

### Authored Surface
Authored via a single scene JSON (`c001_four_paddle_pong.json`), which defines window elements for 4 paddles, one ball, and boundaries, along with logic to handle movement of horizontal (paddles 1 & 2) and vertical (paddles 3 & 4) elements, and the collision mechanics for the added dimension. The terms JSON is updated to show this benchmark on the launcher.

### SCRIPT / Native Escape Hatches
None used. All features are fully expressed within Thestra's semantic declarative commands (`SET_VAR` and `IF`) and built-in formulas, such as `max`, `min`.

### Missing Reusable Semantics
There isn't a natively defined collision boundary or object intersection formula in Thestra's expressions. Bounding box intersections must be manually authored and hardcoded into `IF` checks for each paddle, checking ballX, ballY, paddle position and paddle size manually. This works for 2 or 4 paddles but is highly verbose.

### Awkward But Expressible
Writing collision detection using nested bounds logic inside a single frame hook expression gets very large. Duplicating collision detection and resolving bounce velocities in separate manual `IF` blocks for 4 independent paddles is verbose but expressible.

### Tooling / Discoverability Gaps
No specific tooling gaps noted; configuring 4 panel rectangles and setting logic manually was straightforward in the raw JSON layer.

### Backend Leakage
None. The code uses only abstract scene update concepts (`v.time.dt`), semantic inputs (`inputX` and `inputY`), variables, and abstract window layouts without assuming how the backend executes them.

### Project Leakage
None. Complete isolation inside `projects/labs/scene-benchmarks/`.

### Author Legibility
Yes, a competent author using RPG Maker variables would understand this structure. The state tracks positions (`paddle1Y`, `paddle3X`, `ballX`, `ballY`, etc), and each frame updates positions using input and velocity, and then handles bounces or misses with explicit conditions.

### Reusable Successes
The `IF` and `SET_VAR` semantics gracefully scale from 2 to 4 objects. Native `v.time.dt` access in formulas handles frame-independent movement perfectly. The generic `windows` concept in UI layouts smoothly accommodates an arbitrary number of dynamically positioned objects acting as paddles, independent of explicit entity frameworks.

### Architecture Recommendation
candidate reusable semantic gap; A standardized way to check overlap between two `rect` areas from authored state could reduce the boilerplate math for simple collision scenarios.

## Owner Playtest

* **Status**: READY FOR OWNER PLAYTEST
* **Launch/Control Instructions**: Select C001 on the Benchmark Launcher. Arrow keys control input (Up/Down for vertical paddles, Left/Right for horizontal). Enter to reset, B to return.
* **Owner Observations**: (pending)
* **Post-Playtest Result**: (pending)
