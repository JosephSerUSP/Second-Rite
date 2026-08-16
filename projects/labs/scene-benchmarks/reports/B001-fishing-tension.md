### Experiment
B001 — Fishing Tension

### Result
complete

### Authored Surface
`b001_fishing.json` registered in `projects/labs/scene-benchmarks`. Uses declarative windows for gauges (`Catch Progress`, `Tension`), textual updates, and fixed update hooks.

### SCRIPT / Native Escape Hatches
2 explicit SCRIPT uses for `init` and `update` logic due to no built-in mechanics for:
- Frame-level continuous logic loops with delta-time (`time.dt`) accumulation.
- Arbitrary continuous input state querying (`_G.love.keyboard.isDown`) not tied to standard button hooks (`on_up`/`on_down` etc).
- Real-time continuous gauge changes requiring non-linear interpolations (mock fish pull randomized intervals, input modifiers).

### Missing Reusable Semantics
- **Continuous input reading:** The current logical input system maps discrete actions to hooks (`on_select`, `on_up`). A continuous minigame requires checking if a button *remains* held across frames.
- **Continuous timers:** A way to say `WAIT_ASYNC dt` or tick handlers outside `SCRIPT` to author non-blocking time-varying states like the fish pull changing every 1 second.

### Awkward But Expressible
- **Gauge coloring conditions:** Formula logic allows `v.tension > 80 and [1, 0, 0] or ...`, which functionally changes the color but is slightly awkward for artists to define thresholds.

### Tooling / Discoverability Gaps
No direct UI to preview color formula transitions in Studio.

### Backend Leakage
`_G.love.keyboard.isDown('return')` bypasses the Thestra logical input mapping entirely. A backend replacement wouldn't have `love.keyboard`.

### Project Leakage
None. Sandboxed to the benchmark project context.

### Author Legibility
Yes. The scene structure, windows, and gauge bindings clearly separate logic from presentation. An event author would understand `v.tension` and `v.progress` feed into the gauges.

### Reusable Successes
- Declarative gauge blocks bind instantly to `v.tension` and scale/color perfectly based on formula conditions without manual draw code.
- `update: { mode: "fixed" }` cleanly provides predictable `time.dt` intervals, enabling stable physics-like logic in hooks/scripts.

### Architecture Recommendation
candidate reusable semantic gap: Exposing continuous logical input state to formulas/hooks (`INPUT_HELD 'return'`), avoiding `love` namespace access.

### Owner Playtest
- **Status:** READY FOR OWNER PLAYTEST
- **Instructions:** Launch the benchmark project, select "B001 Fishing Tension". Hold ENTER to reel in, keep tension out of the red/blue zones.
- **Observations:** pending
- **Result:** pending
