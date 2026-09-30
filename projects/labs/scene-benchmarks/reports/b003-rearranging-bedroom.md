# Experiment

B003 — Rearranging a Bedroom

# Result

complete; PLAYABLE PROTOTYPE

# Authored Surface

- `projects/labs/scene-benchmarks/data/scenes/b003_rearranging.json`
- `projects/labs/scene-benchmarks/data/scenes/title.json` (launcher updated)
- `projects/labs/scene-benchmarks/data/terms.json` (launcher options updated)

# SCRIPT / Native Escape Hatches

Used SCRIPT solely for invoking a shared sub-hook (`on_update_narrative`). Since hook calling isn't exposed as a native Scene command, `require('engine.hooks').call_hook('on_update_narrative', {})` was used after every directional move when `mode == 1`. This allowed re-evaluating narrative conditions cleanly without copying condition logic across four directional hooks.

# Missing Reusable Semantics

- **Hook Dispatch:** There is no declarative way to invoke another hook/sub-routine from within a hook. `CALL_HOOK` would be a very useful generic command.

# Awkward But Expressible

- Updating positional variables conditionally requires repetitive boilerplate per-item because there is no abstraction like "current item's x/y".

# Tooling / Discoverability Gaps

- Hook invocation from within a hook requires knowing `require('engine.hooks').call_hook(...)`.

# Backend Leakage

- Calling `require('engine.hooks')` exposes the Lua module hierarchy and execution environment explicitly. A native command would solve this.

# Project Leakage

- None. Completely isolated to the benchmark project context.

# Author Legibility

A competent event author would understand this. It is a straightforward composition of local state variables (`bed_x`, `mode`, etc.), conditionals checking those states, and declarative presentation (`rect`, `formula`, `content`). The only tricky part is the raw `SCRIPT` invocation of the update hook.

# Reusable Successes

- **Formula UI:** The `formula: true` flag in `content` blocks made it incredibly easy to create dynamic UI ("Mode: SELECT" vs "Mode: MOVE") and layout coordinates without requiring native render overrides.
- **Scene State:** Using discrete local state variables (`v.bed_x`, `v.desk_y`) mapping to entity positions worked smoothly.

# Architecture Recommendation

candidate reusable semantic gap

Consider adding a generic `CALL_HOOK` (or similar subroutine/dispatch) Scene command so authors can re-evaluate blocks of logic without dropping into `SCRIPT`.
