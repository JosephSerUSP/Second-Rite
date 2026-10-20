# Benchmark Report: A001 — Pong (2026-10-20)

### Benchmark
ID: A001
Name: Pong
Version: Canonical

### Current Result
complete

### Current Implementation Shape
The game is completely authored as a single self-contained JSON Scene (`projects/labs/scene-benchmarks/data/scenes/a001_pong.json`). It uses `on_enter`, `on_frame`, `on_up`, `on_down`, and `on_select` to drive initialization, user input, main update loop, and round restarts. Engine declarative `windows` are used to render the score, boundaries, paddles, ball, and help text.

The update loop handles continuous collision (with grid boundaries and paddles) and computes movement using frame delta time (`sceneState.time.dt`), relying on standard `IF` and `SET_SCENE_STATE` commands.

### Metrics
- **number of authored Scene resources:** 1 (standalone Scene)
- **number of Event Programs / Flows:** 0
- **number of SCRIPT blocks:** 0
- **approximate SCRIPT lines if any:** 0
- **native source files modified:** 0
- **new generic semantic commands added:** 0
- **Project-owned files required:** 1 (the scene JSON itself)
- **RTP dependencies:** None (aside from engine defaults)
- **validation warnings/errors encountered:** 0
- **bespoke workarounds:** 0
- **unsupported benchmark requirements:** 0
- **whether Studio authoring surfaces were sufficient:** Yes, could be fully modeled in the JSON format used by Studio.
- **whether the artifact runs independently of Second Gate:** Yes

### Changes Since Previous Attempt
- SCRIPT block count (0) remains the same, showing that the continuous movement and math evaluation capabilities using declarative semantic commands (`IF` and `SET_SCENE_STATE`) have remained stable and do not strictly require escape-hatch Lua scripting.
- Variables were thoughtfully renamed for clarity (e.g. `score1` to `scoreLeft`, `paddle1Y` to `paddleLeftY`, `center2` to `aiCenter`), improving authorability.

### Improved
- Consolidating logic into parallel assignment blocks via `SET_SCENE_STATE` allows complex game data to be efficiently defined declaratively. Bounding variable calculations effectively replaces branching via `min()` and `max()`.

### Regressed
- Nothing noted.

### Still Awkward
- The Thestra engine currently prevents `SCENE_EVENT` from acting as a generic function or event dispatcher (its vocabulary is strictly closed to `push`, `pop`, `goto`, `map`, etc.). Therefore, resetting the board must be duplicated across `on_enter`, scoring bounds within `on_frame`, and `on_select`. This limitation makes authored macros or function reusability within a single scene cumbersome without raw `SCRIPT` or moving logic entirely into Event Programs outside the Scene payload.
- Bounding variables to limits (e.g. `max(0, min(max_val, current + delta))`) within formula strings works well but remains visually noisy in data payloads.

### New Architectural Evidence
- The inability to route a custom internal event (e.g. `reset_round`) within the same scene via a native command forces repetition of resetting formulas. This highlights a gap where single-scene authorability would benefit significantly from a scoped `CALL_HOOK` or arbitrary event dispatching mechanism to avoid duplicated payload definitions.

### Verdict
The purely declarative model (`SET_SCENE_STATE` + `IF`) demonstrates mature expressive power for continuous Arcade-style logic, cementing a clear and portable authorability trajectory for games resembling this benchmark constraint profile, though internal logic reuse across hooks remains awkward.
