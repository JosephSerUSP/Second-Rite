# Benchmark Report

### Benchmark
ID: A001
Name: Pong
Benchmark Version: Initial Implementation
Date: 2026-08-16

### Current Result
playable with backend-specific authoring escape hatch

### Current Implementation Shape
Authored Scene composition renders a text-built `boardText` inside a window frame and uses the merged fixed Scene clock (`step=0.0166`). Logical `on_up` / `on_down` hooks author input intent, but initialization plus the continuous movement/collision/scoring loop are implemented by raw Lua `SCRIPT` blocks. The specimen is therefore a legitimate playable Scene benchmark, but it is not backend-neutral authored orchestration.

### Metrics
* number of authored Scene resources: 1
* number of Event Programs / Flows: 0
* number of SCRIPT blocks: 2
* approximate SCRIPT lines: ~70
* native source files modified: 0
* new generic semantic commands added: 0
* Project-owned files required: a001_pong.json, index.json, title.json, terms.json
* RTP dependencies: 1.0
* validation warnings/errors encountered: 0
* bespoke workarounds: String-based tile rendering plus raw Lua SCRIPT for mutable simulation state/collision/scoring.
* unsupported benchmark requirements: None at the behavioral level; backend-neutral expression of the implementation is not achieved.
* whether Studio/normal authored surfaces were sufficient without raw backend code: No. The Scene JSON can contain SCRIPT, but SCRIPT is explicitly a Lua/backend escape hatch rather than portable Thestra semantics.
* whether the artifact runs independently of Second Gate: Yes.

### Changes Since Previous Attempt
First attempt.

### Improved
N/A (First Attempt)

### Regressed
N/A (First Attempt)

### Still Awkward
The text-grid presentation is functional but indirect for continuous objects. More importantly, the actual Pong simulation is concentrated in raw Lua SCRIPT: movement integration, collision, score mutation, reset state, and board-string rebuilding are not expressed through backend-neutral Event/Scene operations. This makes the specimen useful as pressure evidence rather than evidence that the current authoring vocabulary already solves Pong cleanly.

### New Architectural Evidence
The fixed Scene clock and logical input hooks are useful reusable pieces: the engine can host a deterministic real-time authored Scene without adding `PONG_*` native commands. What remains unresolved is the state-manipulation/presentation vocabulary between those hooks. A001 adds evidence alongside the collection-heavy A003/D002 specimens that richer authored value/collection mutation and a more direct reusable presentation primitive may reduce SCRIPT pressure, but one Pong attempt is not enough evidence to freeze new generic commands.

### Verdict
**Playable benchmark; architectural partial success.** The Scene host, fixed timing, logical input, Project isolation, launcher lifecycle, and ordinary validation path all carry the specimen successfully. The gameplay implementation itself still crosses the authored/backend boundary through ~70 lines of Lua SCRIPT, so this attempt does **not** prove backend-neutral Pong authorability. Land it as longitudinal benchmark evidence and use future A001 attempts to measure whether generic capabilities introduced for independently demonstrated needs reduce that SCRIPT footprint without introducing Pong-specific engine words.

## Owner Playtest

status: READY FOR OWNER PLAYTEST

Controls: UP/DOWN to move paddle, Enter to restart.

Owner observations: (pending)
Result: (pending)
