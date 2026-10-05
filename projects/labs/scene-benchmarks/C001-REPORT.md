### Experiment
C001 — Four-Paddle Pong

### Result
complete

### Authored Surface
`projects/labs/scene-benchmarks/data/scenes/c001_four_paddle_pong.json`

### SCRIPT / Native Escape Hatches
None used. Implemented solely using declarative scene state, input bindings, and conditional formula expressions natively supported by the engine.

### Missing Reusable Semantics
None explicitly blocked this experiment. The scene architecture successfully supported multiple independent paddle entities evaluating localized collision logic without structural limitation.

### Awkward But Expressible
The math for clamping paddle boundaries and processing collision via multiple parallel assignment blocks inside `IF` conditions is verbose but completely functional through `SET_SCENE_STATE` and formulas like `max()` and `min()`.

### Tooling / Discoverability Gaps
Writing complex mathematical constraints inside JSON strings remains cumbersome, but this is an established tradeoff of the declarative format.

### Backend Leakage
None. The game uses standard Thestra scene state elements (like `time.dt`) without raw Lua API usage or specific object-identity assumptions.

### Project Leakage
None. The game is self-contained within the `projects/labs/scene-benchmarks` scope and does not borrow unapproved assets.

### Author Legibility
Yes. A competent event-oriented game author could trace the paddle setup (`on_enter`), the frame-by-frame position clamping/collision checks (`on_frame`), and input processing. Adding paddles 3 and 4 followed the exact same semantic pattern as paddles 1 and 2, proving the composition survives scaling the topology.

### Reusable Successes
The scene's state and expression model (`sceneState`, formula parser) proved extremely capable. It trivially expanded from handling two paddles (Y-axis only) to four paddles (X and Y axes), demonstrating robustness in entity multiplicity.

### Architecture Recommendation
no architecture change indicated
