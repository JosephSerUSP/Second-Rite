# Benchmark Report: A001 — Pong (2026-10-20)

### Benchmark
ID: A001
Name: Pong
Version: Canonical

### Current Result
complete

### Current Implementation Shape
The game is completely authored as a single self-contained JSON Scene (`projects/labs/scene-benchmarks/data/scenes/a001_pong.json`). It uses `on_enter`, `on_frame`, `on_up`, `on_down`, `on_select`, and an authored `reset_round` trigger event to drive initialization, user input, main update loop, and round restarts. Engine declarative `windows` are used to render the score, boundaries, paddles, ball, and help text.

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
- A custom Scene trigger event (`reset_round`) has been introduced to consolidate resetting logic, replacing copy-pasted positional reset blocks across both initialization and scoring checks.
- Variables were thoughtfully renamed for clarity (e.g. `score1` to `scoreLeft`, `paddle1Y` to `paddleLeftY`, `center2` to `aiCenter`), improving authorability.

### Improved
- **Code Reuse:** Introducing an authored event `reset_round` triggered via `SCENE_EVENT` allows logic for resetting ball position, input, and paddle locations to be written once and cleanly invoked from `on_enter`, `on_select`, and scoring events.

### Regressed
- Nothing noted.

### Still Awkward
- Updating two variables simultaneously still requires nesting them within an `assignments` array under `SET_SCENE_STATE`, which can add slightly higher visual density than simple single-variable assignments.
- Bounding variables to limits (e.g. `max(0, min(max_val, current + delta))`) within formula strings works well but remains visually noisy in data payloads.

### New Architectural Evidence
- The ability to freely define and dispatch custom string events (e.g., `reset_round`) internally within a Scene's `hooks` using `SCENE_EVENT` provides a valuable, robust macro/function-like pattern for Scene configuration.

### Verdict
The purely declarative model (`SET_SCENE_STATE` + `IF` + custom `SCENE_EVENT` triggers) demonstrates mature expressive power for continuous Arcade-style logic, cementing a clear and portable authorability trajectory for games resembling this benchmark constraint profile.
