### Experiment
B004 — Rain / Distance / Embarrassment

### Result
complete

### Authored Surface
The experiment was implemented entirely as a single menu Scene (`b004_rain_distance.json`) relying heavily on `SET_VAR` and `IF` commands to manage conversational and emotional state.

### SCRIPT / Native Escape Hatches
None.

### Missing Reusable Semantics
None directly encountered; basic math and logical checks handled the abstract state well.

### Awkward But Expressible
Updating multiple variables per turn currently requires stacking many `IF` and `SET_VAR` nodes in `on_select`, making the JSON tree quite deep. Using Lua-style ternary operators (`v.val and X or Y`) inside string formulas works great to keep it readable, but nesting the logical flows for different choices takes effort.

### Tooling / Discoverability Gaps
Constructing ternary string formulas for bounds-checking (like clamping variables between 0 and 100) is somewhat obscure but very effective when discovered.

### Backend Leakage
The reliance on string evaluation for `value` properties assumes the backend's formula parser will handle standard math and logical operators exactly as authored, mirroring the LÖVE backend's Lua integration.

### Project Leakage
Fully isolated in `projects/labs/scene-benchmarks`.

### Author Legibility
A competent event-oriented game author would understand the state checks (`IF v.idx == 1` -> `SET_VAR distance - 1`), as this is a classic RPG maker variable-branching pattern applied to abstract concepts instead of health points.

### Reusable Successes
The formula integration into `SET_VAR` along with the `v.` variable scope makes mapping conceptual states (rain intensity scaling up wetness over time) surprisingly easy to model using standard declarative UI windows.

### Architecture Recommendation
no architecture change indicated
