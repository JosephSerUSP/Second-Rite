# Thestra Editor Scene boundary

This document defines the authoring-side scene boundary introduced by #277.
It is intentionally narrower than the game renderer: its job is to make the
map editor spatially legible and editable without turning renderer details into
a second gameplay schema.

## Authority and data flow

The authoritative project remains authored data plus the LÖVE runtime. The new
browser viewport is an **authoring renderer**, not a second implementation of
runtime presentation. Runtime/fidelity preview stays with LÖVE; the editor may
approximate shaders, fog, effects, billboarding and other presentation details
when that improves authoring clarity.

The dependency direction is:

```
opened project data
        |
        v
Second Rite project adapter
        |
        v
Thestra Editor Scene (neutral semantic scene)
        |
        +------------------+
        |                  |
        v                  v
Three.js backend       future backend
        |
        +-- Perspective camera
        +-- Top Orthographic camera
```

`Thestra Editor Scene` contains authored meaning: map cells, event identity,
resolved project asset paths, editor annotations and stable selection keys. It
does not contain Three.js meshes, materials, raycast object ids or camera
objects. The Three.js backend consumes the scene; replacing that backend must
not require changing the project adapter.

This is a deliberate narrow exception to the older rule that editor previews
must be engine-rendered. That rule continues to apply to **fidelity/runtime
preview**. It does not apply to this interactive spatial authoring viewport,
whose approximation is explicit and whose output is never authoritative game
state.

## Coordinate contract

Authored maps remain grid based. No new gameplay coordinates are introduced.

- authored `x` maps to world `x`
- authored `y` maps to world `z`
- world `y` is editor vertical/elevation space
- one authored map cell is one world unit
- an event at `(x, y)` occupies an explicit `1 x 1 x 1` editor volume centered
  on that authored cell

The initial scene adapter does not write free XY/Z event position, rotation,
scale, pivots or height. Those capabilities must remain unavailable until the
gameplay schema intentionally gains them.

Maps with an authored `layout` project that layout directly. Procedural maps do
not pretend the browser has run the authoritative generator: PR1 marks their
border/interior representation as `editor-procedural-placeholder` so the
viewport remains useful without claiming runtime parity.

## Selection contract

Selection is semantic and stable across camera modes.

A cell is addressed as `cell:<x>:<y>`. An event is addressed by its authored
event id. Renderer mesh identity is private to the backend and must never leak
into map editing state.

Perspective and Top Orthographic are two cameras over the same scene graph and
the same semantic selection. Top mode is not a second renderer and not a
special 2D map representation.

## Project asset resolution

The adapter resolves the map's tileset using the same authored-data rule as the
runtime: `map.tileset` or `dungeon_default`, followed by `map.tilesetOverride`
using id-based pool merging. It reads the editor's existing `/api/tilesets`
endpoint, which already resolves against the opened project/campaign.

The Three.js backend prefers the resulting project texture and event model or
sprite paths. Fallback geometry is editor chrome, not game content:

- walls/floors use neutral fallback materials when the authored texture is
  missing or cannot be decoded;
- every event keeps an explicit one-cell editor cube;
- when an event resolves a real model, the model is fitted inside that volume;
- when only a sprite resolves, the sprite is shown inside the same volume;
- missing project art remains visibly represented rather than borrowing a fake
  game asset.

## Camera state is editor state

Orbit, pan, zoom, projection choice and framing are held by the viewport backend
only. They are not copied into `dbPayload`, do not mark the map dirty and do not
participate in Save. This keeps view state from becoming accidental gameplay
data.

PR1 deliberately leaves the existing 2D editor as the default editing path.
The 3D workspace is read-only except for semantic selection and camera control.
That allows the scene/adapter/backend seam to prove itself before PR2 routes
authoring gestures through it.

## Backend lifecycle

Three.js is installed as an editor dependency. `npm start` prepares only the
browser modules needed by this backend under the editor's ignored `vendor/`
directory. The workspace lazy-loads the backend when Perspective or Top Ortho
is first requested; a missing WebGL/backend bundle therefore cannot disable the
existing 2D editor.

The backend owns disposal of renderer resources, project-model loading, camera
controls and raycasting. The scene model remains dependency-free and is covered
by Node tests so spatial semantics can be verified without WebGL.
