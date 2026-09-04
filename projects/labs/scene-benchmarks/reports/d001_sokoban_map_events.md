### Experiment
D001 — Sokoban as Map Events

### Result
complete

### Authored Surface
A Map (`2.json`) loaded from the title menu via `LOAD_MAP`. The Sokoban crates and the exit are authored directly as Map Events embedded in the map JSON.

### SCRIPT / Native Escape Hatches
Every crate event uses a `SCRIPT` block to implement movement logic. This was necessary because the Thestra engine currently lacks a native, declarative command for moving Map Events (e.g., `MOVE_EVENT`). The `SCRIPT` block directly mutates `ctx.event.x` and `ctx.event.y` and accesses `ctx.session.mapGrid` and `ctx.session.currentMapData.events` to compute collisions and win states.

### Missing Reusable Semantics
- A native command to dynamically move a Map Event relative to its current position or to specific coordinates (e.g., `MOVE_EVENT` or `SET_EVENT_LOCATION`).
- A declarative way to query collisions with walls or other Map Events without dropping into Lua to scan `session.mapGrid` and `session.currentMapData.events`.
- A mechanism for an Event to query or broadcast state changes globally (e.g., counting how many crates are currently over goals) without looping over all map events in SCRIPT.

### Awkward But Expressible
Checking the win condition (crates on goals) requires manually looping through the map's event list inside `SCRIPT` every time a crate is pushed, as there is no native Map-level state variable listener or event broadcast system to aggregate these changes declaratively.

### Tooling / Discoverability Gaps
It is not immediately obvious that Map Events do not support a `MOVE_EVENT` command, given that `MOVE_IMAGE_PICTURE` and similar commands exist.

### Backend Leakage
The implementation relies heavily on raw Lua `SCRIPT` to access internal `ctx.session.currentMapData.events` array and `ctx.session.mapGrid` structures. It assumes 1-based indexing for `mapGrid` and explicitly loops over Lua tables (`ipairs`). If the backend changed how map data or events were structured (e.g., moving to an ECS or a spatial hash grid), this `SCRIPT` logic would break.

### Project Leakage
None. The experiment is fully isolated within the `labs/scene-benchmarks` project, utilizing its own maps, events, and `terms.json`.

### Author Legibility
An RPG Maker-style event author would understand the *intent* of using map events for crates, but they would be blocked by the lack of a "Set Event Location" or "Move Route" command. The resulting composition relies almost entirely on Lua scripting for the core mechanic, which breaks the legibility test for event-oriented authors who expect to use declarative semantic primitives for movement and coordinate checks.

### Reusable Successes
The interaction triggering system (`trigger: "interact"`) and the integration into the Map structure worked perfectly. Transitioning between the title Scene and the Map via `LOAD_MAP` was clean and seamless.

### Architecture Recommendation
candidate reusable semantic gap

### Owner Playtest

- **Current Status**: READY FOR OWNER PLAYTEST
- **Instructions**: Launch the Scene Benchmarks project, select "D001 Sokoban (Map Events)" from the menu. Move next to a crate and face it. Press A/Enter to push the crate. Push both crates onto the '.' goals.
- **Owner Observations**: (pending)
- **Result**: (pending)
