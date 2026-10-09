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

Archive Antechamber and Service Annex have distinct beauty and collision meshes and distinct package-owned `walkSurface` records. They share the Project's neutral texture atlas. Both rooms leave their camera-facing wall open for the Scene's fixed camera; walkability remains independent of beauty and collision geometry.

The player uses the compiler-built surveyor described in `assets/authoring/characters/README.md`. Maps select its appearance independently of traversal geometry. The archive attendant and dormant service-floor sentinel use distinct compiled appearances through ordinary Event fields. The sentinel has dialogue only; its encounter is inactive. `tools/spikes/continuous-surface/build-fixture-sprites.py` maintains the unused sprite player fixtures and the opaque neutral environment atlas.

## Blender authoring contract

`tools/blender/semantics/environment_walk_surface.py` compiles explicit Blender semantic collections into an existing environment package:

- `TH_WALKABLE`: one or more direct planar mesh faces. Each face becomes a walk-region polygon.
- `TH_OBSTACLES`: optional direct planar mesh faces on the same ground plane. Each face becomes an obstacle polygon.

The compiler applies object transforms, preserves authored face-loop order, rejects non-planar geometry, and rejects modifiers on semantic source meshes. It does **not** infer a walk surface from `TH_COLLISION`; arbitrary 3D collision geometry does not state which face is navigable ground or how its volume should become a 2D locomotion region.

After the normal environment export, run inside Blender:

```text
blender --background room.blend \
  --python tools/blender/semantics/environment_walk_surface.py -- \
  --manifest path/to/environment.json
```

The semantic pass patches only `walkSurface` plus provenance. Beauty mesh, texture atlas, bounds, anchors and optional generic collision mesh remain the ordinary environment exporter's responsibility.

No Parasite Eve names, maps, dialogue, characters or art are used. The reference game is requirements evidence only.

## Run

Stage this Project through the ordinary Thestra Project exporter, then run the staged directory with LÖVE. It should never require `projects/hichaukitoden-game` to exist.
