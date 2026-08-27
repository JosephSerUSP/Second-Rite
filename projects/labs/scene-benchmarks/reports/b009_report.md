### Experiment
B009 — Parasite-Eve-Like Positioning Proof

### Result
complete;

### Authored Surface
One JSON file (`b009_positioning.json`) driving standard authored scene features (a UI layout defining standard bounds and coordinate-mapped elements using `resolveDim`-capable expressions, an `on_enter` and `on_frame` hook for logical initialization and update logic handling). Input maps `on_up/down/left/right` hooks to logical intent variables `inputX` and `inputY`.

### SCRIPT / Native Escape Hatches
Used `SCRIPT` primarily for updating variables frame-by-frame (`inputX/Y` applied via `time.dt`) and computing Manhattan distance for the attack. No native engine lua or Battle overrides were required since the visual spatial rules mapped nicely into simple formulas evaluated within `on_frame`.

### Missing Reusable Semantics
None blocking. The use of variables explicitly storing logical input states between frame reads replicates standard entity movement but requires resetting the variables explicitly inside `on_frame` to support discrete keypress checks without continuous holds bleeding.

### Awkward But Expressible
Writing dense multi-conditional state logic (movement and ATB boundary limits, checking distance) directly in a single `SCRIPT` chunk string inside a JSON config is workable but syntactically awkward to write cleanly. A pure declarative state machine inside Thestra could achieve this but `SCRIPT` was more concise for rapid real-time loop prototyping.

### Tooling / Discoverability Gaps
Writing complex movement bounds inside `SCRIPT` without editor intellisense is prone to syntax errors.

### Backend Leakage
Standard Lua `math.min`, `math.max`, and `math.abs` functions used in the string block are strictly Lua-oriented.

### Project Leakage
None. The benchmark scene runs entirely within `projects/labs/scene-benchmarks/`.

### Author Legibility
Yes. The scene consists entirely of familiar concepts (timers, bounding variables, x/y position integers, a simple state machine). An event-author could look at the `SCRIPT` bindings and quickly parse how positional state drives UI.

### Reusable Successes
- The `v.px`, `v.py` evaluation mapping in `rect` properties (`"x": "2 + 1 + v.px"`) cleanly handles continuous positions natively in the presentation layer without needing customized redraw code.
- `on_frame`'s fixed tick behavior (`dt = time.dt`) works flawlessly for consistent ATB building and speed calculation.
- Logical input hooks map cleanly onto logical variables without needing raw keyboard access.

### Architecture Recommendation
gather more evidence;
