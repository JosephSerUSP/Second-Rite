# B004-rain-distance

### Experiment
B004 — Rain / Distance / Embarrassment

### Result
complete

### Authored Surface
A single new JSON scene `b004_rain.json` using the window renderer, along with an update to `title.json` and `terms.json` to reach it.

### SCRIPT / Native Escape Hatches
We used SCRIPT in `on_enter` to initialize state, and in `on_frame` to handle the continuous state evolution (rain increasing over time, and embarrassment increasing based on distance and rain). We could not purely rely on declarative commands because `on_frame` formula updates involving multiple conditions and variables over time (dt) are too verbose to express purely in `MATH` and `IF` command nodes, and native RNG is not exposed cleanly in formula strings.

### Missing Reusable Semantics
- No declarative way to continuously evolve values over time (e.g. an "interpolate over time" or "tick based on dt" command that runs autonomously).
- Random numbers are not exposed to formulas without a SCRIPT escape hatch.

### Awkward But Expressible
Using `on_up` and `on_down` to mutate a `next_dist` state variable, which is then consumed in `on_frame`, works well for input buffering but feels indirect.

### Tooling / Discoverability Gaps
No specific gap observed.

### Backend Leakage
None. `math.random` and `time.dt` are standard, and we avoid raw LÖVE calls.

### Project Leakage
The scene is fully isolated and does not use Second Gate resources.

### Author Legibility
A competent author would understand the declarative gauges and input hooks, but the `on_frame` SCRIPT block requires programming knowledge rather than just event sequencing.

### Reusable Successes
The `gauge` UI elements mapped to `sceneState` variables worked flawlessly to present the abstract concepts without bespoke rendering logic. Input buffering translated perfectly.

### Architecture Recommendation
candidate reusable semantic gap: Expose a declarative way to increment/decrement state variables by time (dt), and provide a safe random number primitive in formula strings.

### Owner Playtest
- **Playtest Status**: READY FOR OWNER PLAYTEST
- **Launch/Control Instructions**: Launch from the benchmark menu, choose B004. Use UP/DOWN to change distance.
- **Owner Observations**: (pending)
- **Result**: (pending)
