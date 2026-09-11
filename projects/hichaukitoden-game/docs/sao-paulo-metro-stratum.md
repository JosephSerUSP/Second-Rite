# Stratum III: Metrô de São Paulo — Architectural Design, Implementation & Critical Analysis

## 1. Executive Summary

This document serves as the authoritative architectural record and design retrospective for **Stratum III: Metrô de São Paulo** in *Second Rite* (Hichaukitoden). It synthesizes all design goals, user requests, technical implementations, and integration verification across the five underground metro lines (Linhas 1 through 5), while critically analyzing the dialogue between this feature and the Thestra engine architecture.

Stratum III reimagines the subterranean underworld of Santa Maria as the brutalist, automated, concrete transit arteries of São Paulo. Players explore multi-level subterranean stations, cross turnstiles, board 3-car electric passenger trains with transparent window apertures, experience real-time physical transit through pitch-black railway tunnels, and solve interconnected power and transit puzzles spanning five iconic metro lines.

All implementations strictly adhere to the engine's data-driven philosophy:
- **Zero SCRIPT increase**: SCRIPT usage remains strictly capped at 87 occurrences across the entire game project.
- **100% Data-Driven**: Train kinematics, waypoints, consist compositions, door animations, and station logic are authored entirely in `data/maps/*.json` and `data/tilesets/*.json`.
- **Full Gate Verification**: Validated with G1 (`VALIDATE OK`), 48/48 test suites in staged unit tests (`ALL UNIT TESTS OK`, including all 93/93 Stratum III tests), save/load round-trip (`SAVETEST OK`), and G4 doc currency (`Engine state doc matches`).

---

## 2. Synthesis of User Requests & Design Needs

Through our collaborative design exchanges and technical iterations, the requirements evolved into five core pillars:

### 2.1 Physicality and Seamless In-Game Conveyance
- **Seamless Transition**: The transit sequence must not be a black screen, cutscene, or teleportation. The player must step directly from the platform into the train wagon, stand inside the passenger compartment, and experience the train moving continuously through the environment.
- **First-Person Immersion**: From inside the wagon, the player watches the platform slide away, enters dark tunnels with flickering tunnel lights, experiences kinematic sway (pitch and roll), and sees the destination station slide into view.

### 2.2 Realistic Metro Station Architecture & Authenticity
- **Multi-Level Station Topology**: Authentic São Paulo station layouts featuring:
  - **Mezzanine / Concourse (Row 2)**: Entrance stairs, station totems, ticket booths (*bilheteria*), and stationmaster logs.
  - **Turnstiles (*Catracas*) (Row 3)**: Faregate boundary separating the paid transit concourse from the street level.
  - **Platform Concourse (Rows 4–7)**: Wide grey granite tile platforms with reinforced concrete structural columns (*pilares de concreto armado*).
  - **Continuous Yellow Tactile Paving (Row 8)**: An unbroken 24-tile tactile warning strip along the platform edge without gaps, orientation flips, or procedural interruptions.
  - **Sunken Track Trench (Row 9)**: Depressed railway bed at $Z = -0.50$ with ballasted track, wooden sleepers/ties, steel rails, and vertical platform curb.
  - **Straight Railway Line**: A continuous 32-tile railway extending infinitely into dark tunnel portals on both the East and West ends, rather than an awkward closed box.
  - **South Tunnel Wall (Row 10)**: Heavy cast-iron tunnel liner plates with yellow/black hazard warning diagonal signs.

### 2.3 Train Scale, Multi-Car Consist & Transparent Apertures
- **Car Dimensions**: Train cars must not be a claustrophobic 1-tile box. Each car spans 3 full tiles in length ($X \in [-1.5, +1.5]$) and 0.88 tiles in width ($Y \in [-0.44, +0.44]$), allowing the player to view the doors from slightly afar ($Y=7$) and stand comfortably inside the aisle ($Y=9$).
- **Multi-Car Consist**: Trains are 3-car articulated consists (9 tiles total length) composed of:
  - **Rear Cab Car (offset $-3$)**: Aerodynamic rear cab, red LED taillights, and passenger seating.
  - **Center Car (offset $0$)**: Passenger car with central sliding double doors, passenger seating, and ceiling lighting.
  - **Lead Cab Car (offset $+3$)**: Aerodynamic front cab, high-intensity white headlights, windshield frame, and destination rollsign.
- **Interconnected Gangways**: Cars are connected by open rubber bellows gangways (*fole de intercirculação*), allowing the player to freely walk between cars along the central aisle ($X \in [11, 19]$) while docked.
- **Transparent Window Apertures**: Windows are framed open geometry apertures cut through the 3D OBJ meshes rather than opaque textures. The player can see through the windows into the train from the platform, and see out to the platform and tunnel walls from inside the train.
- **Line-Specific Color Schemes**: Each line features its authentic livery stripe and matching interior seats:
  - *Linha 1 - Azul*: Electric Blue (`#1461EB`)
  - *Linha 2 - Verde*: Emerald Green (`#19A640`)
  - *Linha 3 - Vermelha*: Carmine Red (`#D92626`)
  - *Linha 4 - Amarela*: Solar Yellow (`#F2CC1A`)
  - *Linha 5 - Lilás*: Deep Lilac (`#A640BF`)

### 2.4 Elimination of the Player Carrying Bug
- **The Problem**: In initial attempts, when the train departed the platform, the player was dropped onto the tracks and left behind in the station.
- **The Requirement**: The player must be securely and smoothly carried by the moving car throughout the closing, moving, and opening phases. The player's offset within the car must be preserved so they can board the rear, center, or lead car, remain in that exact car during transit, and disembark cleanly at the destination platform.

### 2.5 Interlocking Narrative, Puzzle & Exploration Progression
- **Five Real-World Metro Lines**:
  - *Map 32 (Linha 1 - Azul: Luz)*: Starting hub connected to Cathedral of Santa Maria above; transfer point to Linhas 2 and 3; locked shortcut back from Linha 5.
  - *Map 33 (Linha 2 - Verde: Consolação / Paraíso)*: Connecting transit artery; locked gate at Chácara Klabin requiring the Brás Track Key.
  - *Map 34 (Linha 3 - Vermelha: Sé / Brás)*: Substation blackout puzzle; player flips the auxiliary breaker at Brás to restore power to the network and retrieve the key.
  - *Map 35 (Linha 4 - Amarela: Paulista / Faria Lima)*: Automated corporate line; high-security vault containing 10,000 gold and the *Metro Master Pass*.
  - *Map 36 (Linha 5 - Lilás: Santa Cruz)*: Deepest terminal; boss arena guarding the ancient tunneling titan *O Tatuzão*; unlatches the permanent shortcut back to Luz (Map 32).

---

## 3. Technical Implementation & Architecture

### 3.1 Generic `mover` Component (`runtime/engine/mover_runtime.lua`)
Rather than creating a hardcoded subsystem, mover functionality is integrated as a generic `mover` component on standard engine `Event` instances in `data/maps/*.json`.

Key runtime mechanics:
- **Consist Placements**: `mover_runtime.getPlacements(session)` calculates the real-time world coordinates for each car in the consist and passes unique `cacheKey` identifiers (`tostring(mover.eventId) .. "_car_" .. ci`), allowing multiple 3D models to render simultaneously per mover.
- **Robust Player Carrying**:
  - `mover.onboard` is engaged when the player steps onto any car door tile while docked.
  - `mover.playerOffset` stores whether the player is in the rear car ($-3$), center car ($0$), or lead car ($+3$).
  - During `"closing"`, `"moving"`, and `"opening"` phases, `mover.onboard` is never reset.
  - `session.playerX` and `session.playerY` continuously update to track `mover.curX + mover.playerOffset` and `mover.curY`.
  - Camera pitch/roll sways are published to `session.moverCameraOverride`, smoothly applied by `viewport_3d.lua`.
- **Disembarking Interlock**: While moving or with doors closed, movement outside the car is strictly blocked. When docked with doors open, the player can step forward onto the platform edge at $Y=8$.

### 3.2 3D OBJ & MTL Asset Pipeline
Generated via `scratch/generate_metro_consist_models.py`:
- `metro_rails.obj` / `metro_rails.mtl`: Depressed ballast bed at $Z = -0.50$, curb rising to $Z = 0$, wooden ties, and dual extruded steel rails.
- `metro_column.obj` / `metro_column.mtl`: Structural reinforced concrete column with pedestal base, fluted shaft, and capital.
- `metro_wagon_*.obj`: 3-tile car with transparent window apertures, open doors, bogies, seats, poles, ceiling lights, and gangways.
- `metro_wagon_*_half.obj` & `metro_wagon_*_closed.obj`: Animated sliding doors with framed transparent glass.
- Line-specific models for all 5 lines (`_l1`, `_l2`, `_l3`, `_l4`, `_l5`) referencing line MTLs.

### 3.3 Fixing Stray Procedural Feature Injections
During initial testing, random tactile paving tiles appeared across platform floors (e.g. at $X=14, Y=7$). Investigation revealed that the engine's `exploration.injectTilesetFeatures` applies a default 10% injection probability (`prob = 0.1`) to any tileset feature lacking an explicit `injectProbability`.

We explicitly authored `"injectProbability": 0` on all floor features (`metro_column`, `metro_rails`, `metro_tactile_edge`, `metro_tactile_edge_v`) and wall features (`metro_tunnel_wall`, `metro_tunnel_wall_warning`, `metro_sign_exit`, `metro_sign_transfer`) across all metro tileset JSON files. This guaranteed that platform floors remain completely uniform granite tile, with tactile paving appearing exclusively on the authored platform edge along Row 8.

---

## 4. Critical Analysis

### 4.1 Strengths and Architectural Successes
1. **Physicality Without Breaking the Engine**: Seamless transit was achieved without adding bespoke C/Lua hardcoding or violating the engine's 2.5D raycaster constraints.
2. **First-Person Immersion**: Walking through a train's gangway into an adjacent car, looking out the windows, and watching the dark tunnel slide past provides an unprecedented level of physical atmosphere in a grid-based dungeon crawler.
3. **Data-Driven Elegance**: Adding another metro line or moving platform requires zero Lua changes—an author creates a map JSON with an Event containing a `mover` block.

### 4.2 Trade-Offs & Edge Cases
1. **Discrete Grid vs. Continuous Kinematics**:
   - The engine operates on discrete integer `(x, y)` cells for collision, events, and interactions.
   - While the train moves continuously in floating-point space (`curX`), the player's logical coordinate updates to the nearest rounded tile cell. To prevent visual stuttering, `moverCameraOverride` applies smooth camera offsets while the engine preserves logical cell invariants.
2. **Raycaster Floor Plane & Sunken Geometry**:
   - The engine's base floor plane is flat at $Z = 0$.
   - The sunken track bed ($Z = -0.50$) was achieved by authoring `coversFace: true` on `metro_rails`, replacing the default quad with custom OBJ geometry featuring depressed ballast and vertical platform curbs.
3. **Collision Bounds**:
   - While the train is 3 tiles long, standard events occupy a single tile. `mover_runtime.isBlocked` bridges this by querying the mover's consist extent and dock status dynamically.

---

## 5. Dialogue with Current Thestra Architecture & Authoring Challenges

### 5.1 Eventing as the Backbone
*Second Rite* is rooted in RPG Maker 2003 design principles where complex game mechanics are composed of event blocks. In RPG Maker, moving platforms are often hacked using moving events with custom movement routes. 

In Thestra, rather than building a detached "transportation system", `mover` was implemented as a declarative property of an `Event`. This aligns perfectly with:
- **Clipboard compatibility**: Movers can be copy-pasted across maps using the editor's command and event clipboard.
- **Savegame persistence**: Mover states (position, phase, onboard status) round-trip cleanly through `session.movers` without altering save schema.
- **Zero SCRIPT policy**: No embedded Lua scripts were introduced, maintaining the strict project-wide limit of 87 SCRIPT usages.

### 5.2 What Makes Authoring This in Thestra Challenging
1. **Absence of True 3D Verticality**:
   Standard Thestra dungeon maps have no height coordinate (no $Z$ grid). Creating a multi-level station (mezzanine -> platform -> sunken tracks) required creative visual partitioning:
   - Upper concourses and platforms share the same horizontal grid plane ($Z = 0$).
   - Sunken tracks utilize negative OBJ vertex space ($Z = -0.50$) on walkable floor cells.
   - Tunnel ceilings maintain uniform clearance while wagon models fit tightly within the 1-unit ceiling height.
2. **Camera Override Ownership**:
   The engine strictly enforces that presentation observes resolved game state rather than mutating it. Synchronizing camera sway, player carrying, and first-person viewports required routing motion through `moverCameraOverride` into `viewport_3d.lua` without altering the authoritative simulation clock.
3. **Procedural vs. Authored Collision**:
   Because Thestra maps support both hand-authored layouts and procedural feature injection, any tileset feature intended solely for manual layout placement must be authoring-safe (`injectProbability: 0`), or procedural generators will sprinkle tracks or columns into unrelated dungeon rooms.

---

## 6. Verification Results

| Gate / Test Suite | Command / Target | Result | Status |
|---|---|---|---|
| **G1 Validation** | `tools/golden/check-validate.ps1 -GameRoot out/stage` | SCRIPT usages: 87 (0 increase), Deprecated: 0 | **PASS (VALIDATE OK)** |
| **Unit Test Suite** | `tools/ci/run-staged-unit.ps1 -GameRoot out/stage` | 48/48 suites passed, 0 failed | **PASS (ALL UNIT TESTS OK)** |
| **Stratum III Tests** | `tests/test_metro_stratum.lua` | 93/93 integration tests passed | **PASS (93/93 OK)** |
| **Save/Load Test** | `lovec.exe out/stage savetest` | Session save/load round-trip identity | **PASS (SAVETEST OK)** |
| **G4 Doc Currency** | `tools/golden/check-state.ps1` | `docs/ENGINE-STATE.md` currency | **PASS (Doc Matches)** |
| **Native Render Captures** | `scratch/capture_metro_views_v2.py` | 8 multi-angle native frames captured | **VERIFIED (Artifacts generated)** |

---

## 7. Future Extensibility

The generic `mover` component developed for Stratum III provides an extensible foundation for other dungeon environments:
- **Vertical Elevators**: Setting waypoint movement along $Z$ or linking multi-floor transfers.
- **Moving Floating Platforms**: Stepping stones across chasms or lava in platformer-style dungeons.
- **Minecarts & Freight Trains**: Cargo wagons that carry treasure chests or explosives through industrial strata.
- **Interactive Doors**: Usable on drawbridges, blast doors, and security gates throughout future campaigns.
