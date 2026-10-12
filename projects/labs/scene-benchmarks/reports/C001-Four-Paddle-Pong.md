# C001 - Four-Paddle Pong Autopsy

## Experiment
C001 — Four-Paddle Pong

## Result
complete

## Authored Surface
Authored primarily through `c001_four_paddle_pong.json`. Modified `index.json`, `title.json`, and `terms.json` to append the scene in the specimen menu index.

## SCRIPT / Native Escape Hatches
None. All logic is driven natively through formula commands (`SET_SCENE_STATE`, `IF`).

## Missing Reusable Semantics
No genuinely reusable gaps were noticed. The math formula capabilities (`min`, `max`, `and/or`) support simple AI and logical layout constraints effectively.

## Awkward But Expressible
Using nested and/or expressions in `value` formula properties to represent ternary conditionals can get visually noisy and awkward to read but it works correctly.

## Tooling / Discoverability Gaps
None immediately apparent for JSON-level hand-authoring; the engine structure is predictable.

## Backend Leakage
None. The scene relies purely on standard formula variables like `sceneState.time.dt`.

## Project Leakage
None. All assets/logic are contained independently within the scene benchmarks project.

## Author Legibility
A competent author could likely parse this setup given familiarity with the base A001 Pong implementation. Adding top and bottom paddles followed exactly the same mental model as left/right paddles.

## Reusable Successes
The stateless UI generation alongside hook-driven formulas (`on_frame`, `on_up`, `on_left`, `on_select` to restart) handles state mutation and rendering extremely well.

## Architecture Recommendation
no architecture change indicated

## Owner Playtest
- **Playtest Status:** READY FOR OWNER PLAYTEST
- **Launch Instructions:** Launch the scene lab project and select "C001  Four-Paddle Pong". Use Up/Down and Left/Right arrows to control paddles 1 and 4 respectively.
- **Observations:** [Pending]
- **Result:** [Pending]
