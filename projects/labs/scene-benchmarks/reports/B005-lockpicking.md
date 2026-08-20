# B005 — Lockpicking

## Experiment
B005 — Lockpicking

## Result
* complete;

## Authored Surface
`b005_lockpicking.json` — A custom text-based minigame using an authored Scene and variables for state, with SCRIPT blocks for the complex timing logic and string rendering.

## SCRIPT / Native Escape Hatches
- `init`: Setup the state variables.
- `update`: Implements a bouncing needle on a progress bar representing a lock's sweet spot. Authored formula logic does not easily support continuous bounce and text manipulation.
- `pick`: Checks if the needle is within the sweet spot. A hit increments pins picked, advances the sweet spot, and increases speed. A miss fails the lock. This handles state transition logic which is awkwardly expressive in JSON.

## Missing Reusable Semantics
No new semantics added. Continuous bounds checking and visual string formatting (`[--|==--]`) are generally missing from reusable hooks, pushing this into `SCRIPT`.

## Awkward But Expressible
We can store state (cursor position, sweet spot bounds) purely in authored variables, but continuously translating a float value into a visual text string within JSON formulas is incredibly awkward, leading to the use of a Lua loop in `update`.

## Tooling / Discoverability Gaps
N/A

## Backend Leakage
None. The script relies on standard `math.random` and standard `dt` times.

## Project Leakage
None. This is purely isolated within the benchmark project.

## Author Legibility
A competent RPG Maker-style event author would understand the state variables (`pins_picked`, `state`, `cursor_pos`), but the text-string visualizer in Lua would be unfamiliar to an author used to visual bar graphics. Providing a generic "gauge with sweet spot" presentation type might resolve this.

## Reusable Successes
The standard `on_frame` hook with `dt` passed natively worked smoothly for controlling speed. The `SET_VAR` patterns and window layouts easily handle standard framing.

## Architecture Recommendation
- no architecture change indicated; (Gather more evidence to see if a native 'Timing Gauge' presentation primitive is needed).

## Owner Playtest
- **Status:** READY FOR OWNER PLAYTEST
- **Instructions:** Launch the benchmark project, select `B005  Lockpicking`. Press ENTER when the needle `|` is within the `=` sweet spot. Successfully pick 3 pins.
- **Observations:** [Pending]
- **Result:** [Pending]
