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

The map view switcher and 3D viewport are **map-workspace chrome**, not global
Studio chrome. Studio deliberately keeps the map editor mounted behind many
full-screen dialogs/tools, and those overlays do not share one activation
mechanism: newer surfaces use an `active` class while older ones such as Tileset
Studio toggle `display` directly. The workspace therefore keys visibility from
whether a known modal/overlay is actually visible, not from one CSS convention.
This prevents map-only controls from bleeding through Database, Engine, picker,
preferences, export, tileset and other modal surfaces while still preserving the
2D/3D swap inside the unobstructed map editor.

## PR1 verification note

Hosted repeat-controlled G6 was used as a regression detector, not as a golden
recapture mechanism. The repeat control was stable, and after fixing the
workspace lifecycle all non-map Studio frames returned to exact base pixels.
The only remaining PR1 differences are the four primary Map Editor layer frames,
where the new `2D Edit / Perspective / Top Ortho` switcher is intentionally
visible. Those committed reference updates remain an owner-signoff action.

## PR2 authoring contract

Interactive editing never turns Three.js objects into project authority. The
browser backend reports semantic cells/entities to a project-specific command
layer, and that command layer performs the only authored writes.

For Second Rite, PR2 deliberately exposes only capabilities the current schema
already owns:

- Map painting replaces an authored layout cell with `#`, `.`, or `o`.
- Event movement writes integer grid `x/y` only and rejects occupied event cells.
- Light movement writes integer grid `x/y` only and rejects occupied light cells.
- Procedural browser placeholders cannot be painted into `map.layout`.
- Event/light/override property editing continues through the existing Studio
  inspectors and modals rather than creating renderer-owned duplicate forms.
- Lights, overrides, spawn and event cubes are semantic editor annotations; they
  are not promoted into runtime mesh or gameplay schemas.

Perspective and Top Orthographic use the same interaction model. Left mouse is
reserved for authoring; Perspective uses right-drag orbit, Top uses right-drag
pan, and wheel/middle remain zoom controls. Event/light drags preview legal and
illegal destination cells before committing.

### Immediate visible authoring, asynchronous presentation

An authored gesture must produce a truthful visible response without waiting for
LÖVE, process creation, disk staging, an HTTP round trip, or Map Renderable
Bundle compilation. Semantic state remains the immediate authoring surface;
runtime geometry is an asynchronous correction/verification product rather than
the interaction loop.

Structural/topology edits therefore invalidate any in-flight bundle immediately,
remove stale authoritative geometry from the viewport, and expose the existing
semantic 3D fallback while the next runtime bundle compiles. The semantic scene
refreshes on the next animation frame, so the fallback reflects the newly
authored wall/floor/opening before LÖVE returns. When the newest authoritative
bundle arrives it atomically replaces that fallback. An older response is never
allowed to overwrite a newer authored mutation merely because the replacement
request was still inside its debounce window.

Event and Light movement already have frame-local semantic/Three feedback, and
Light properties feed the local authoring-light preview. Those interactions do
not wait for runtime compilation before the author sees the edit. The current
Map Renderable Bundle can still contain event-model surfaces and resolved static
light, however, so this first responsiveness slice continues to enqueue a
background authoritative refresh for those mutations. That synchronization is a
correction step, not the feedback path, and it does not clear the current view.
Vertex shading likewise updates the current bundle locally before any unrelated
runtime synchronization is needed.

This timing split is intentional: authoring should not wait on a LÖVE process,
and visual responsiveness must not justify reintroducing a second JavaScript
geometry compiler. The current whole-map semantic fallback during topology sync
is deliberately simple; finer dirty-region presentation may replace it later
without changing the authority boundary.

Semantic scene rebuilds preserve camera framing unless the map identity/bounds
change. Runtime bundle replacement is independent of semantic rebuild, so a
material refresh does not reset the author's view or become the source of legal
placement decisions.
