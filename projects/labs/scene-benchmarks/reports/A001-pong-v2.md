# Benchmark Report

### Benchmark
ID: A001
Name: Pong
Benchmark Version: Current Main Semantics
Date: 2026-09-04

### Current Result
complete

### Current Implementation Shape
A fresh reconstruction of A001 Pong that takes advantage of recent engine evolution. Authored Scene composition using dynamic `rect` fields evaluates coordinate formulas for the paddles and ball. The fixed Scene clock (`step=0.0166`) and logical input hooks (`on_up`, `on_down`) are used to author intent natively. The game loop (movement and collision) entirely uses pure declarative semantic commands (`SET_VAR` multi-assignments and `IF` blocks), replacing Lua completely. Scene state encapsulation uses duplicated `SET_VAR` blocks in `on_enter` and `on_select` to avoid `run_hook` CI fall-throughs. Inline `clamp()` formula helper is used for cleaner bounds restrictions.

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 0
* approximate SCRIPT lines: 0
* native source files modified: 0
* new generic semantic commands added: 0
* Project-owned files required: a001_pong.json, index.json, title.json, terms.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: Scene reset duplication required due to run_hook behavior in CI.
* unsupported benchmark requirements: None.
* whether Studio authoring surfaces were sufficient: Yes, JSON structure maps effectively to semantic blocks.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
* Reconstructed natively to prove continued viability of declarative commands over raw Lua.
* Used inline `clamp()` formula helper inside the `SET_VAR` string formulas for simpler, more declarative boundary constraints, avoiding manually written min/max logic.
* Setup formulas remain explicitly duplicated in `on_enter` and `on_select` to ensure CI reliability, as automated validation scenes silence custom hooks via `run_hook`.
* Maintained `goldenScript` metadata for proper automated testing validation.
* Maintained the original `terminal` block to preserve the frozen behavioral specification intact.

### Improved
* **Formula Elegance:** Utilizing the native `clamp()` helper inside `SET_VAR` formulas noticeably cleans up paddle boundary constraints.

### Regressed
* **CI Validation Gap & Initialization Duplication:** Similar to A002, `SCENE_EVENT` commands with kind `run_hook` are silently dropped during automated scene previews in CI, leading to nil-variable errors. To preserve the reset capability (`on_select`) without breaking CI, the `SET_VAR` setup block remains duplicated across both hooks rather than shared via an external script or hook.

### Still Awkward
Continuous simulation remains moderately taxing on authored presentation. Writing continuous game physics with standard discrete nodes is verbose without visual graph tools.

### New Architectural Evidence
The ability for `resolveDim` to evaluate formulas natively for `rect` dimensions and the addition of `clamp()` make writing bounds-checked simulations much more compact. The workaround forced by CI event-dropping, however, continues to highlight the need for an engine-level `init` lifecycle hook or stable shared hook execution for purely state-initializing commands.

### Verdict
**Complete architectural success.** The evolution of generic engine facilities (robust formula evaluation, `v.time.dt`, and dynamic window dimensions) continues to absorb `SCRIPT` pressure entirely. A001 Pong proves that a backend-neutral real-time action simulation can be fully authored in Thestra natively, and `clamp()` makes it more elegant.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: UP/DOWN to move paddle, Enter to restart, B to back.

Owner observations: (pending)
Result: (pending)
