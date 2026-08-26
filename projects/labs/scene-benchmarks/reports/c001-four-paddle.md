# C001 — Four-Paddle Pong

### Experiment
C001 — Four-Paddle Pong

### Result
complete

### Authored Surface
Authored JSON Scene (`c001_four_paddle.json`), index registration, and terms registration.

### SCRIPT / Native Escape Hatches
None required. All behavior expressed via declarative logic and formulas.

### Missing Reusable Semantics
None needed for this implementation.

### Awkward But Expressible
None.

### Tooling / Discoverability Gaps
None encountered.

### Backend Leakage
None. Handled seamlessly by Thestra Scene declarative semantics.

### Project Leakage
None. Standard benchmark project boundaries maintained.

### Author Legibility
Yes. The scene is authored primarily via standard `SET_VAR` and `IF` logic, relying heavily on declarative rules evaluated on each frame, familiar to visual-scripting or generic event authors.

### Reusable Successes
The continuous updating pattern for `time.dt` works beautifully here for mapping real-time movement onto Thestra variables, proving that arbitrary coordinate calculations inside layout properties cleanly decouple presentation from logic.

### Architecture Recommendation
no architecture change indicated

### Owner Playtest

- **Status:** READY FOR OWNER PLAYTEST
- **Instructions:** Launch the lab benchmarks cartridge (`npm run lab:benchmarks`), select C001 Four-Paddle Pong. Arrows move both sets of paddles (Up/Down for vertical paddles, Left/Right for horizontal paddles).
- **Observations:** [pending]
- **Result:** [pending]
