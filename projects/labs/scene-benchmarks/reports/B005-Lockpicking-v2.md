# B005 — Lockpicking (v2)

## Experiment
B005 — Lockpicking

## Result
complete

## Authored Surface
One authored Scene (`b005_lockpicking.json`), utilizing declarative logic via `SET_VAR`, `IF`, formula bindings for UI layout.

## SCRIPT / Native Escape Hatches
None. Removed entirely in this iteration. The previous `init`, `update`, and string-building `pick` logic was fully converted into declarative data using `SET_VAR` multi-assignments and dynamic `rect` formulas.

## Missing Reusable Semantics
None directly affecting this implementation, but a simpler UI progress bar natively supporting moving ranges would improve the ergonomics.

## Awkward But Expressible
Replicating state logic to emulate a string builder by drawing overlapping text panels using math-heavy `rect.x` formulas (e.g. `math.floor((v.sweet_spot_start / 100) * 24)`) works but isn't as nice as an explicit UI layout container. Conditional logic (`a and b or c`) inside assignment formulas had to be utilized for direction toggling without bloated `IF` conditions.

## Tooling / Discoverability Gaps
Writing complex window formulas (e.g., `4 + math.floor((v.sweet_spot_start / 100) * 24)`) by hand in raw JSON is error prone.

## Backend Leakage
The implementation leverages standard LÖVE formula evaluation safely via `clamp` and math functions but avoids arbitrary Lua features.

## Project Leakage
Isolated inside `projects/labs/scene-benchmarks`. Doesn't rely on Second Gate.

## Author Legibility
Significantly improved. A competent RPG Maker author can see clear `on_select` branches, variables like `cursor_pos` and `pins_picked`, and UI frames updating their dimensions in response.

## Reusable Successes
- Declarative UI formulas inside `rect.x` and `rect.w` are incredibly powerful to avoid writing manual SCRIPT to calculate positions.
- Multi-assignment `SET_VAR` effectively cleans up state tracking.

## Architecture Recommendation
no architecture change indicated

## Owner Playtest
- Status: READY FOR OWNER PLAYTEST
- Instructions: Launch the benchmark project, select B005 Lockpicking. Press ENTER when the `O` cursor overlaps the `====` sweet spot. Complete three times to win.
- Observations: [Pending]
- Result: [Pending]
