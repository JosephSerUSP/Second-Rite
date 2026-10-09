# Continuous Surface Gauntlet

A self-contained Thestra Project used to pressure-test continuous authored-room traversal and, later, a continuous arena combat host.

This Project is intentionally **not Second Gate**. It owns its own data, maps, scenes, environment assets and character art under this directory. The only shared dependency is the Thestra installation/runtime (plus the pinned neutral RTP revision).

The current spatial slice proves the Lane A / Lane B substrate from #1402:

- a Map selects `traversal.provider = "continuous_surface"`;
- environment packages own the physical planar `walkSurface` (ground plane, walk-region polygons and obstacle polygons);
- Maps own gameplay traversal policy/tuning (`speed`, `maxStep`, interaction radius) rather than duplicating room geometry;
- the environment package also contributes render geometry and stable anchors;
- the Map Scene selects `world = "continuous_surface"`;
- held canonical directions drive free 8-way locomotion;
- diagonal speed is normalized by the shared semantic;
- package-authored polygon obstacles and irregular walk boundaries constrain motion;
- ordinary world-space Map Events use the existing Thestra Event program host;
- `Archive Antechamber` and `Service Annex` form a two-way room loop through ordinary `LOAD_MAP` commands;
- the existing `LOAD_MAP.arrival` string selects named environment anchors for provider-backed Maps, just as it already does for bounded-lane town Maps;
- provider-owned world position, facing, distance state and arrival-anchor identity survive save/load;
- presentation uses the existing fixed-eye WorldCamera math without giving camera ownership to traversal.

Archive Antechamber and Service Annex have distinct beauty and collision meshes and distinct package-owned `walkSurface` records. Each room has a lit atlas baked from its adopted Blender source. Both rooms leave their camera-facing wall open for the Scene's fixed camera; walkability remains independent of beauty and collision geometry.

The player uses the compiler-built surveyor described in `assets/authoring/characters/README.md`. Maps select its appearance independently of traversal geometry. The archive attendant and dormant service-floor sentinel use distinct compiled appearances through ordinary Event fields. The sentinel's ordinary Event starts a one-enemy arena encounter. Confirm with full AT opens Command, another confirm chooses Attack and opens Targeting, and confirm resolves an in-range attack. Cancel backs out without spending the action. A red ground ring telegraphs the enemy attack; the blue targeting ring shows the player's exact circular range. Command/Targeting pause simulation while UI presentation continues. Victory hides the sentinel through an Event page; loss runs authored party recovery. Both return to exploration, and saves are rejected during the encounter. `tools/spikes/continuous-surface/build-fixture-sprites.py` maintains the unused sprite player fixtures.

## Blender authoring contract

`tools/blender/semantics/environment_walk_surface.py` compiles explicit Blender semantic collections into an existing environment package:

- `TH_WALKABLE`: one or more direct planar mesh faces. Each face becomes a walk-region polygon.
- `TH_OBSTACLES`: optional direct planar mesh faces on the same ground plane. Each face becomes an obstacle polygon.

The compiler applies object transforms, preserves authored face-loop order, rejects non-planar geometry, and rejects modifiers on semantic source meshes. It does **not** infer a walk surface from `TH_COLLISION`; arbitrary 3D collision geometry does not state which face is navigable ground or how its volume should become a 2D locomotion region.

After the normal environment export, run inside Blender:

```text
python tools/blender/run.py tools/blender/semantics/environment_walk_surface.py --blend room.blend -- \
  --manifest path/to/environment.json
```

The semantic pass patches only `walkSurface` plus provenance. Beauty mesh, texture atlas, bounds, anchors and optional generic collision mesh remain the ordinary environment exporter's responsibility.

The adopted sources live in `assets/authoring/environments/`, with authority
recorded in `environment-sources.json`. Edit these documents directly. The
Project's `tools/light_environments.py` exports them through the shared
environment pipeline without writing the sources:

```text
python tools/blender/run.py projects/experiments/continuous-surface-gauntlet/tools/light_environments.py -- --output out/gauntlet-lighting
python projects/experiments/continuous-surface-gauntlet/tools/check_lighting.py
```

The output is a candidate: inspect native staged frames before copying it into
the Project. `--create-sources` was the one-time adoption route from the original
neutral OBJ fixtures; it refuses existing sources. Sprite-fixture generation
does not own the environment atlases anymore. CI checks source and product
fingerprints to reject stale bakes.

Test rooms need readable lighting even when they represent no particular place:
a lit floor, volume readable on walls/obstacles, and enough ambient fill to see
characters and hostile effects. These sources use warm/cool area lights and low
ambient fill, baked with Cycles. Character shading remains the runtime's existing
path. This is a test-environment minimum, not final art or dynamic lighting.

No Parasite Eve names, maps, dialogue, characters or art are used. The reference game is requirements evidence only.

## Run

Stage this Project through the ordinary Thestra Project exporter, then run the staged directory with LÖVE. It should never require `projects/hichaukitoden-game` to exist.

Player controls use the authored Scene camera basis: Left/Right move across the screen and Up/Down move into/toward the foreground. Enter interacts or confirms; Esc cancels arena selection. NPC dialogue uses the ordinary dialogue dock and retains the Map camera behind it. Confirm completes the text reveal, then closes the line. The real-main-host playthrough proof covers directional movement, visible dialogue state and return to exploration.

Talk to the Archive Attendant and advance the instructions with Enter to travel directly into the Sentinel encounter. The attendant and Sentinel use the same authored Common Event.

Attack confirmation now commits to anticipation, contact and recovery. Movement
and further command input hold until recovery finishes; contact resolves once
through the shared executor. Enemy advancement also holds during player
execution. The Sentinel locks a destination during its red windup, lunges through
ordinary collision, then recovers. Lethal contact holds a short fade/aftermath
before exploration resumes. These are experimental arbitration rules and timing
values, not measured reference-game parity. Current attack feedback is a tracer,
flash and damage label; compiled skeletal attack clips are still absent.

Baked room textures use perspective-correct interpolation (`affineTextures: false`)
so shadows remain registered to their geometry; repository-wide follow-up is #1488.
Visible door panels/frames mark the transfer Events. The fixture check compares
exported box footprints with package walk blockers to catch planar axis drift.
