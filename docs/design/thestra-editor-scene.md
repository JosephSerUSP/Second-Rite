# Thestra Editor Scene boundary

This document defines the authoring-side scene boundary introduced by #277.
Its job is to make the map editor spatially legible and editable without turning
renderer details into a second gameplay schema.

## Authority and data flow

The authoritative project remains authored data plus the LÖVE runtime. After
#287, the browser does **not** reimplement Second Rite's tileset resolution,
height-field compilation, wall composition, weighted variants, OBJ placement,
or other static-world geometry rules.

The two relevant flows are deliberately separate:

```
authored project/map -----------------------------+
        |                                         |
        v                                         v
Second Rite project adapter              LÖVE runtime resolver/compiler
        |                                         |
        v                                         v
Thestra Editor Scene                    Map Renderable Bundle (#287)
(semantic authoring facts)              (resolved presentation facts)
        |                                         |
        +------------------+----------------------+
                           v
                    Three.js backend
                           |
                           +-- Perspective camera
                           +-- Top Orthographic camera
```

`Thestra Editor Scene` contains authored meaning: map cells, event identity,
editor annotations and stable selection keys. It does not contain Three.js
meshes, runtime materials, raycast object ids or camera objects.

The Map Renderable Bundle contains the static surfaces and material inputs that
Second Rite itself compiled. Those surfaces are what the author sees when the
runtime bridge is available. They are not authored data and are never written
back to the project.

A browser-only or currently unsupported external-project session may fall back
to neutral semantic cell proxies so spatial navigation remains possible. That
fallback is explicitly labelled `semantic fallback`; it does not interpret
project tilesets or pretend to be runtime geometry.

## Coordinate contract

Authored maps remain grid based. No new gameplay coordinates are introduced.

- authored `x` maps to editor world `x`
- authored `y` maps to editor world `z`
- editor world `y` is vertical/elevation space
- one authored map cell is one editor world unit
- an event at `(x, y)` occupies an explicit `1 x 1 x 1` editor annotation volume

The runtime bundle remains renderer-neutral and records its own Z-up,
one-based runtime grid convention. The Three.js backend performs one explicit
adapter transform into the editor's Y-up, zero-based authoring space; authored
coordinates are never rewritten to match renderer internals.

Maps with an authored `layout` project that layout directly. Procedural maps do
not pretend the browser has run the authoritative generator: the semantic scene
marks their border/interior representation as `editor-procedural-placeholder`.
The runtime bundle, when available, may still show the generator's real resolved
surfaces.

## Selection contract

Selection is semantic and stable across camera modes.

A cell is addressed as `cell:<x>:<y>`. An event is addressed by its authored
event id. Authoritative bundle surfaces carry semantic provenance, so clicking a
visible runtime surface resolves back to the same cell/event vocabulary rather
than exposing renderer mesh identity.

Perspective and Top Orthographic are two cameras over the same semantic scene
and the same visible renderable set. Top mode is not a second map representation.

## Event annotations

Every event keeps an explicit one-cell editor cube. That cube is authoring chrome,
not runtime geometry. When the runtime bundle contains an event model, that model
is visible independently of the cube; the cube remains the stable selection and
future grid-dragging affordance.

Event model/sprite metadata may remain on the semantic scene for inspectors and
fallback annotations, but it is not used to compile visible world geometry.

## Camera state is editor state

Orbit, pan, zoom, projection choice and framing are held by the viewport backend
only. They are not copied into `dbPayload`, do not mark the map dirty and do not
participate in Save.

PR1 deliberately leaves the existing 2D editor as the default editing path. The
3D workspace is read-only except for semantic selection and camera control. PR2
routes authoring gestures through the same semantic scene/command boundary.

## Backend lifecycle

Three.js is installed as an editor dependency. `npm start` prepares only the
browser modules needed by this backend under the editor's ignored `vendor/`
directory. The workspace lazy-loads the backend when Perspective or Top Ortho
is first requested; a missing WebGL/backend bundle therefore cannot disable the
existing 2D editor.

The backend owns GPU resources, cameras, controls, bundle-to-Three adaptation and
raycasting. The semantic scene model remains dependency-free and is covered by
Node tests without WebGL.
