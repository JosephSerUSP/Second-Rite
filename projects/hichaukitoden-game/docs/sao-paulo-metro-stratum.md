---
type: retrospective
scope: game
status: active
---

# São Paulo Metro Stratum & Generic Mover Runtime

## 1. Overview & Architectural Shift

The São Paulo Metro stratum (Stratum III) represents a major expansion of the Labyrinth, introducing modern subterranean transit infrastructure into the world of Second Rite.

In Draft PR #1101, an initial implementation coupled the physical movement of trains directly to hardcoded metro-specific logic (hardcoded model filenames, hardcoded 1D consist offsets `dx in {-3, 0, 3}`, fixed east/west boarding assumptions, and rail coordinates baked into Lua).

This fresh reimplementation completely replaces that bespoke design with a **project-agnostic generic mover runtime** (`runtime/engine/mover_runtime.lua`) alongside declarative Project content (`data/maps/`, `data/tilesets/`, `data/troops.json`, and `tools/metro/`).

---

## 2. Generic Mover Engine Architecture

### 2.1 Declarative Event Schema
Movers are authored entirely as map event properties under `event.mover`. The engine reads this definition without any baked-in asset paths or world assumptions:

- **`consist`**: Defines multi-car or multi-element assemblies. Each part specifies relative spatial offsets (`dx, dy, dz`), an optional role (`lead`, `standard`, `rear`), and model overrides.
- **`stateModels`**: Maps runtime mover states (e.g. `open`, `half`, `closed`) to 3D OBJ model paths.
- **`footprint`**: Defines the physical bounding footprint occupied by the mover, preventing invalid entity collisions and out-of-bounds movement.
- **`boarding`**: Declarative boarding zones specifying valid entry coordinates, required player orientation, and passenger transfer points.
- **`barrierMaterials`**: Dynamic collision and passability barriers that activate or deactivate during different mover states (doors open vs. in-transit), integrated directly with `exploration.tryMove`.
- **`doorAnimation`**: Configurable dwell times and transition models for opening and closing cycles.

### 2.2 Kinematic Lifecycle & Interpolation
- **Smooth Trajectory**: Movement along waypoints uses smooth cubic easing (`t * t * (3 - 2 * t)`), eliminating abrupt linear motion artifacts.
- **Passenger Synchronization**: When the player is boarded, the player's world position tracks the mover coordinates exactly.
- **Kinematic Pitch & Sway**: During motion, `mover_runtime` computes real-time camera sway and pitch based on velocity vector and direction, published to `session.moverCameraOverride` for `viewport_3d.lua` to project.
- **Generic Coordinate System**: Movers operate in 3D grid space, supporting arbitrary directions (North, South, East, West, vertical elevation) without directional hardcoding.

---

## 3. Save / Load State Contract

### 3.1 Serialization
In-flight mover state is fully serialized within `session.movers` by `runtime/engine/savegame.lua`:
- Mover phase (`idle_at_stop`, `moving`, `boarding`, `dwell`).
- Current waypoint index and target waypoint.
- Exact floating-point coordinates `(x, y, z)`.
- Transit progress `t` and velocity vector.
- Door animation step and dwell timer.
- Passenger attachment status.

### 3.2 Restoration & In-Transit Round-Trip
On save deserialization:
1. `savegame.restoreMap` sets `session.restoredMovers = data.movers`.
2. When the map loads, `mover_runtime.init` consumes `session.restoredMovers`, matching movers by ID.
3. Mid-transit mover positions are reconstructed immediately without snapping back to initial waypoints or dropping onboard players into void tiles.
4. The transit lifecycle resumes smoothly to destination arrival, door opening, and passenger disembarking.
5. This contract is rigorously verified by `tests/test_metro_stratum.lua` (Section 3).

---

## 4. 3D Viewport & Render Integrity

### 4.1 Viewport Isolation
In the initial draft, an attempt to alter UV mapping in `runtime/presentation/viewport_3d.lua` (`prepareResolvedWallFaces`) broke golden screen captures across every pre-existing map in the game (reddening G5 and G6).

In this reimplementation:
- `prepareResolvedWallFaces` and base world-geometry UV calculations are strictly preserved from `origin/main`.
- Mover models and station features are rendered entirely through the dynamic placed-model pipeline via `ensureMoverPlacedModel` and `mover_runtime.getPlacements`.
- All baseline scene and world-view golden tests (G5) remain byte-identical.

---

## 5. Deterministic Asset Generation Pipeline

Located in `tools/metro/`:
- **`generate_metro_models.py`**: A deterministic, portable Python generator producing low-poly retro OBJ/MTL models for:
  - Metro columns and structural arches.
  - Dual-gauge electrified third-rail tracks.
  - Wagons across all 5 São Paulo Metro line liveries (Line 1 Azul, Line 2 Verde, Line 3 Vermelha, Line 4 Amarela, Line 5 Lilás).
  - Lead, standard, and rear car variants.
  - Door state geometry (`closed`, `half`, `open`).
- Uses portable relative paths and standard Python 3 without external heavy dependencies.

---

## 6. Content Design: Stratum III (São Paulo Metro)

### 6.1 Maps
- **Map 32 (Santa Cruz Station)**: Line 1 (Azul) and Line 5 (Lilás) transfer hub. Connects the Labyrinth upper descent to deep transit tunnels.
- **Map 33 (Chácara Klabin Station)**: Line 2 (Verde) / Line 5 (Lilás) interchange. Features security turnstiles, platform screen doors, and gate locking mechanisms.
- **Map 34 (Line 5 Maintenance Tunnels)**: Dark service tracks, hazardous third-rail geometry, electrical breaker puzzle, and Talos security sentinels.
- **Map 35 (Tatuzão Excavation Chamber)**: Massive circular cavern containing the abandoned Tunnel Boring Machine (`boss_tatuzao`).
- **Map 36 (Alto dos Moinhos Station)**: Ghost station with shortcut passages returning to Santa Cruz.
- **Map 37 (Wagon Interior)**: Cinematic moving consist interior used during deep stratum transit sequences.

### 6.2 Narrative & Atmosphere
Consistent with `docs/world/strata-and-return.md`, the Metro stratum is not presented as a novelty dungeon or parody. It is an impossible manifestation of real-world municipal infrastructure swallowed into the strata of the Labyrinth, retaining authentic bilingual signage, authentic line color identities, and desolate industrial loneliness.
