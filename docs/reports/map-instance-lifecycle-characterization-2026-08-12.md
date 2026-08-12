# Map Instance lifecycle characterization

**Date:** 2026-08-12
**Baseline:** `main` at `24cac469`
**Scope:** headless characterization only; no Map behavior fields, Map Event Program hooks, Area, lifecycle bus, schema, production behavior, or goldens changed.

## Verdict

The executable evidence supports the architectural distinction from #340:

```text
Map Instance lifecycle = authoritative playable-world residency and replacement
Map Scene lifecycle     = Scene stack displacement and presentation/input state
```

Dialogue and Battle displace the Map Scene while the same `GameSession.currentMapData`, `mapGrid`, and `currentMapIndex` remain current. A real Map departure is the synchronous `exploration.loadMap` path, where the previous dangerous state is cached before the new Map is installed. Save restore is a separate reconstruction path: it creates a new `GameSession` and restores Map state directly instead of activating through `exploration.loadMap`.

The executable trace is `tests/test_map_instance_lifecycle.lua`, registered in the existing `unittest` suite. It uses real `exploration.loadMap`, `scene_host`, `savegame`, `love.keypressed`, Flow execution, and the real `SET_FLAG` Event command. It adds no lifecycle signal.

## Repository facts

- `engine/exploration.lua:916-1095` is the current Map activation authority.
- `cacheCurrentMap` runs from `loadMap` before `currentMapIndex` and `currentMapData` are replaced. It stores dangerous Map runtime collections, player position, and facing in `session.mapStates[mapIndex]`.
- The new Map record is a shallow copy of the authored loader record. Procedural Maps either restore `session.mapStates[mapIndex]` or call `generateDungeon`; there is no persisted Map Instance ID.
- `engine/scene_host.lua:280-307` implements Scene `pop` and `goto_scene`; `goto_scene` is synchronously pop-then-push. Scene hooks therefore report stack changes, not Map residency.
- `main.lua:1757-1768` runs the committed movement path: `exploration.step`, Map step/touch Event resolution, then dangerous-map encounter checking only when no step Event handled.
- `engine/savegame.lua:121-165,235-339` serializes the current Map and cache, creates `GameSession.new(loader)`, then calls its private restore path. It does not call `exploration.loadMap`.

## Fixture traces

### A — Map Instance vs Scene displacement

Trace:

```text
load Map 1
  -> current Scene: map
  -> save Map references: currentMapData=M, mapGrid=G, currentMapIndex=1
goto dialogue
  -> current Scene: dialogue
  -> M/G/1 unchanged
goto map
  -> current Scene: map
  -> M/G/1 unchanged
goto battle
  -> current Scene: battle
  -> M/G/1 unchanged
goto map (the same return seam used by battle resolution)
  -> current Scene: map
  -> M/G/1 unchanged
```

This proves that Scene `on_exit`/`on_enter` cannot be Map-instance departure/arrival signals. They occur for Dialogue and Battle displacement even though the playable Map remains current.

### B — Real Map replacement

Trace:

```text
load Map 2 with seed 1735689608
  -> A is current; capture A grid and arrival position
load Map 3 with seed 1735689609
  -> cache A
  -> set currentMapIndex = 3
  -> copy authored Map 3 into currentMapData
  -> generate/restore Map 3 runtime products
  -> assign Map 3 grid, then player arrival coordinates/facing
```

The exact authoritative replacement seam is the `loadMap` body: `cacheCurrentMap(session)` precedes `session.currentMapIndex = mapIdx`, followed by `session.currentMapData = mapData`. The complete activation does not finish until runtime grid resolution and player arrival assignment at lines 1060-1065. This is characterization of the current order, not a recommendation to reorder it.

The test observes that `mapStates[2]` contains A's grid and departure position after the transfer, while Map 3 is current. A subsequent `loadMap(2, { arrival = "resume" })` restores A's cached grid and position.

### C — Generated first creation vs cached return

Trace:

```text
load Map 2 with a deterministic seed
  -> no mapStates[2]
  -> generateDungeon
  -> retain generated grid/events/features
leave for Map 3
  -> mapStates[2] is created with those same runtime collections
return to Map 2 with arrival=resume
  -> restore mapStates[2]
  -> generated grid/events/features are reused
```

Today, the distinguishing data is the presence of `session.mapStates[mapIndex]` and the cached runtime collections. The generated state has no explicit `instanceId` or creation provenance field. The fixture checks reference identity for the cached grid, generated events, and generated features, and checks that no instance identity field exists.

### D — Save/load restoration

Trace:

```text
source session: Map 2 -> Map 3 (Map 2 cached)
save while sceneName = map
load JSON payload
savegame.deserialize(payload, loader)
  -> GameSession.new(loader)
  -> restoreMap(session, payload.map, loader)
  -> current Map, player position, and mapStates restored
```

The test temporarily makes `exploration.loadMap` raise if called; deserialization still succeeds. The restored session and current Map data are new runtime tables, while the decoded Map state is restored as save data. Semantically this is a new runtime host around restored Map state, not ordinary exploration activation. That is a characterization, not a proposed lifecycle contract.

### E — Committed player step

The real `love.keypressed("up")` path is driven against a deterministic generated Map and records calls to the existing Flow module:

```text
blocked movement
  -> player coordinate unchanged
  -> no exploration.step
  -> no encounter check

successful movement without a step Event
  -> coordinate commit
  -> exploration.step
  -> battle.encounter_check

successful movement onto a step Event
  -> coordinate commit
  -> exploration.step
  -> SET_FLAG Event command runs
  -> no battle.encounter_check
```

The Event is real data interpreted through the normal interactive Event path; no test-only callback is inserted. The encounter result is a non-battle probe so the test records the check without starting a presentation Battle.

## Accidental implementation coupling

- A Map Instance has no first-class identity. Current code uses the Map index as the cache key, so one dangerous Map runtime per index can be resident in `mapStates` during an expedition.
- `loadMap` combines replacement, cache, procedural generation, authored Map copying, fog setup, lighting, and arrival placement. A future host must subscribe to this seam with care because “activation started” and “activation finished” are not currently separate published facts.
- `currentMapData` is a shallow copy of authored Map data, while runtime fields such as generated events and runtime lighting are assigned onto that copy. Cache behavior depends on those runtime tables being explicitly listed in `cacheCurrentMap`.
- Scene transition code receives the same session context as Map code, but the Scene stack does not own or replace `session.currentMapData` for Dialogue/Battle detours.
- Save restore duplicates enough of Map reconstruction to restore a usable world without going through `loadMap`; future changes to Map runtime state must account for both paths.
- Successful step ordering is split across `engine.exploration` (coordinate commit) and `main.lua` (Flow/Event/encounter dispatch). A future player-step host must not be inferred from keypress receipt or from Scene updates.
- Step Event suppression is represented by the local `checkStepEvents()` boolean. Encounter processing is skipped when a matching step/touch Event had commands; this is not a generic event bus signal.

## Safe subscription seams for a future host

The current evidence safely supports observing these existing domain facts, subject to an owner-defined final contract:

- Map replacement/activation: the `exploration.loadMap` domain seam, with creation vs cached restore derived from the existing `mapStates[mapIndex]` branch.
- Real deactivation/replacement: the transfer path before the new `currentMapIndex` becomes current, where `cacheCurrentMap` is currently called.
- Scene displacement: `scene_host` Scene hooks, but only for Scene-local behavior; never as Map arrival/departure.
- Save restoration: `savegame.deserialize`/Map restore as a distinct load reason, not an inferred transfer.
- Player step: after the public movement function has committed a coordinate, with the owner deciding its precise relation to `exploration.step`, Map Event handling, and encounter checking.

No current evidence licenses an author-facing `on_instance_created`, `on_activate`, `on_deactivate`, or `on_player_step` field. Those names remain the #340 proposal surface pending owner decisions about exact timing, save-load reason, resident cache policy, and step ordering.

## Owner decisions still required

- Whether “created” means first procedural generation, first fixed Map resolution, or a broader runtime-instance construction event.
- Whether cached Maps are resident instances or serialized snapshots, and whether more than one instance per authored Map may ever exist.
- Whether activation is observed at the beginning of `loadMap` or only after grid, collections, fog, lighting, and arrival placement are complete.
- Whether save restore receives an activation-like signal with an explicit load reason, or only a distinct restore signal.
- Whether a future Map step host runs before or after the existing `exploration.step` Flow, and before or after Map step/touch Event handling and encounter checks.
- What happens if a Map transfer is initiated while a displaced Scene/interactive Event is still suspended.

## Verification

The new suite is included in `lovec . unittest`. This branch changes only the test suite registration, the headless characterization test, and this report. G2-G6 goldens and authored schemas are untouched.
