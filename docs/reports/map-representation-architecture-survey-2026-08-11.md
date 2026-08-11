# Map and level representation architecture survey

**Date:** 2026-08-11
**Scope:** architecture evidence only. This report proposes neither a schema nor a migration.

## Finding

A level is not universally “a grid of cells.” Mature tools make different
primitives authoritative: semantic fields, placed modules, boundaries enclosing
spaces, solids, or a hierarchy of instances. Cells are therefore a good present
Second Rite *project capability*, not evidence that they are the neutral
Thestra Studio primitive.

The reusable pattern is a separation of authored intent from resolved structure
and renderer geometry:

```text
authored semantic representation
        -> deterministic resolver/compiler
resolved/compiled structural representation
        -> renderer/GPU adaptation
renderer/GPU geometry
```

## Current Second Rite evidence

Fixed maps store `layout` as compact strings. `engine/exploration.lua`
expands them into one-indexed `session.mapGrid`; authored map/event/light/
override coordinates are zero-indexed. The characters carry more than graphics:

| Character | Current structural and gameplay meaning | Current resolved presentation |
| --- | --- | --- |
| `#` | solid wall; a `wallEvent` must occupy it and use `bump` | wall cell/faces; authoring may retain exterior faces and top caps |
| `.` | ordinary non-solid floor | floor and, when applicable, ceiling |
| `o` | non-solid structural doorway/gate/arch | axis inferred from wall neighbours; frame/model geometry |

The representation therefore combines topology, passability, geometry
derivation, opening semantics, selection address and event legality. The
separate `overrides` records can alter visual feature, passability and pending
raw-character mutation; `MUTATE_TILE` changes the runtime grid. Maps also
hold tileset, ceiling style, fog, optional vertex-light grid, grid-positioned
`lightObjects`, spawn and gameplay events. Events are separate objects, except
that wall events have a cell constraint. Where present, `materials` is also
layout-shaped per-cell data.

This is a useful small topology language, but it is an accidental union of
concerns: an opening is an occupied cell instead of a boundary, its axis is
inferred, and there is no direct authored home for two materials on opposite
wall sides.

The current lower seams are already valuable:

- `presentation/viewport_3d.lua` resolves floor/wall/opening cells and faces;
  `engine/geometry/visibility_profile.lua` makes play versus authoring
  visibility explicit.
- `presentation/map_renderable_bundle.lua` exports runtime-resolved static
  surfaces/materials with semantic provenance and explicit coordinate metadata.
- Image-authored geometry compiles deterministically to a neutral model before
  presentation materialization; caches/prebakes store geometry, not GPU state.
- #277 defines semantic editor selections/annotations separately from resolved
  visible surfaces. #279 preserves that bundle boundary; #280 only writes
  existing `#`, `.`, `o` cells and grid `x/y`. #237 separately requires
  project-root/resource ownership rather than repository-relative assumptions.

Thus a future authoring representation can feed existing resolved-structure,
geometry and bundle seams; it need not preserve character rows, browser meshes,
or renderer-face IDs as authority.

## Representative architectures

| Family | Primitive; density/dimension | Authority and derivation | Reusable lesson; imposed constraint |
| --- | --- | --- | --- |
| Semantic grid — [LDtk IntGrid/layer instances](https://ldtk.io/docs/game-dev/json-overview/layer-instances/) | dense 2D integer field; definitions separate meaning from instances | IntGrid is semantic source; [auto-layer tiles](https://ldtk.io/docs/general/auto-layers/auto-layer-rules/) are rule-derived; entities have typed fields | Paint intent and derive visuals. Still assumes rectangular 2D cell identity. |
| Layer-oriented — [Tiled JSON](https://doc.mapeditor.org/en/stable/reference/json-map-format/) | tile, object, image and group layers; fixed arrays or sparse infinite chunks | GID tiles are visual placement; properties/classes add metadata; object templates are reusable definitions | Layers, groups, chunks and templates are broadly useful. Tiled itself does not define gameplay topology, so semantics can decay into properties. |
| Layer-oriented — [Ogmo](https://ogmo-editor-3.github.io/documentation/) | project-defined grid, tile and entity layers | project definitions declare layer/value kinds; instances carry data | One level may deliberately mix grid and entity layers rather than forcing one primitive. |
| Modular 3D grid — [Godot GridMap](https://docs.godotengine.org/en/stable/tutorials/3d/using_gridmaps.html) and [MeshLibrary](https://docs.godotengine.org/en/stable/classes/class_meshlibrary.html) | sparse 3D cell -> module plus orthogonal orientation | module identity is source; mesh/material/collision/navigation are module definitions; navigation may be generated per cell | Strong for reusable modules, vertical cells and deterministic placement. It couples visual module with collision/navigation and makes irregular geometry awkward. |
| Constructive solid — [TrenchBroom/Quake](https://trenchbroom.github.io/manual/latest/index.html) | entities contain brushes; brushes contain faces/planes; 3D | brushes/faces and properties are authored; geometry/collision are compiled | Face-level materials/selection, arbitrary solids and grid snapping without grid identity. CSG validity and broad face diffs cost more. |
| Sector topology — [ZDoom Line](https://www.zdoom.org/wiki/Structs:Line), [Side](https://www.zdoom.org/wiki/Structs:Side), [Vertex](https://www.zdoom.org/wiki/Structs:Vertex) | vertices, directed boundaries, sides, sectors; things separate | boundaries explicitly connect spaces; one/two-sidedness and per-facing-side surface records are explicit | Best evidence that doors/walls can be boundary facts, with different side materials. Topology editing/validation is harder. |
| Scene graph — [Godot TSCN](https://docs.godotengine.org/en/3.0/development/file_formats/tscn.html) / [PackedScene instances](https://docs.godotengine.org/en/3.0/getting_started/step_by_step/instancing.html) | typed hierarchy with resources/transforms/instances; 2D or 3D | hierarchy and component properties are authored; instances expand a reusable scene | Strong for props, lights and imported meshes. It has no inherent topology/passability/navigation model. |
| Voxel/block | sparse/dense 3D cells, block state, chunks | cell/module state is source; mesh/physics are derived | Chunking and derived mesh scale block worlds; it overcommits a dungeon to volume occupancy and is weak for independently-sided walls. |
| JRPG tilemap — [RPG Maker MZ Map](https://rpgmakerofficial.com/product/MZ_help-en/01_07.html) / [Events](https://rpgmakerofficial.com/product/MZ_help-en/01_09.html) | 2D tile layers plus grid events | tileset settings bundle appearance/passability; events carry processes separately | Confirms grid-paint productivity and event separation, but tile-owned collision/visual assumptions constrain a neutral 3D ontology. |

All representatives support per-instance metadata somehow. LDtk, Tiled and
Godot text scenes are most inspectable/diffable by default; compressed payloads,
generated tiles and broad brush edits weaken review. Tiled chunks and GridMap
show dense authoring need not require dense runtime storage. Tiled/LDtk/GridMap
select cells or modules; UDMF selects boundaries/sides; brushes select faces;
scene graphs select nodes. That difference should be explicit in neutral
selection semantics, never replaced by renderer mesh identity.

## Pressure cases

| Case | Semantic grid + derived structure | Explicit boundary/space topology | Grid modules + scene objects | Brush/scene authority |
| --- | --- | --- | --- | --- |
| Corridor, enclosing wall, ordinary event | excellent | good, more records | good | overpowered |
| Door/opening, exterior edge, one/two-sided wall, side material | needs edge layer/inference | excellent | special modules or edge overlay | excellent, higher cost |
| Floor/ceiling/material choice | separate semantic surfaces | space attributes + sides | module definitions | excellent |
| Light, event/model, map override | typed object/annotation layers | typed things/entities | scene nodes | entities/nodes |
| Irregular room/custom structural mesh | needs escape hatch | natural plan topology | custom module/node | natural |
| Multi-height, stairs/ramp | deliberate extension | heights; slopes specialized | natural stacks/modules | natural |
| Large spanning prop | footprint object | footprint object | instance + declared footprint | transform; gameplay footprint still separate |
| Procedural dungeon/deterministic export | excellent | possible, harder generator | good grammar/modules | poor for ordinary generation |
| Top/perspective editing | same semantics | strong | strong | strong perspective, slower paint |

## Implications for #277, #279, #280 and #237

#277's cell-first selection is correct for the current Second Rite adapter,
whose legal authored units are cells, events, lights and overrides. It should
not become a Thestra-wide invariant. A neutral scene can retain stable semantic
keys while supporting `cell`, `edge`, `space`, `module`, `node` or
`face` as project-authoritative kinds. A picked surface remains useful context.

#279/#280's Map Renderable Bundle boundary is the right guardrail: the viewport
must not become a second terrain compiler. A new authoring compiler can replace
only map-data-to-resolved-structure input; the existing bundle can remain
authoritative for resolved surfaces/material inputs and renderer adaptation.

#237 means definitions/templates/resource paths must resolve through an opened
project/resource provider. This report does not select that ownership design.

## Three credible hypotheses to prototype

### A. Semantic grid plus authored edge overlays

**Advantage:** preserves current procedural generation, grid events and compact
topology while making openings, wall state and side-specific surfaces explicit.

**Cost:** cell and edge data can drift without strict compiler precedence and
validation.

**Current-data change:** replace character rows with named cell semantics and add
canonical oriented edges; floors/ceilings/per-side materials/opening state become
separate. Events/lights/overrides remain objects.

**Pipeline that can remain:** runtime-grid projection, face resolver, visibility
profiles, neutral geometry compiler and Map Renderable Bundle.

**PR implication:** Second Rite remains cell-primary; pick results can add edge
context; the adapter owns edge writes.

**Smallest falsifier:** a 3x3 fixture with one opening, one exterior boundary
and distinct wall-side materials, compiled through the current bundle and picked
in top/perspective without browser geometry compilation.

### B. Grid-snapped spaces and explicit boundaries

**Advantage:** directly represents what separates spaces: doors, exteriors,
one/two-sidedness, side materials, irregular rooms and future heights.

**Cost:** routine painting becomes planar-graph maintenance; editor ergonomics,
generation and validation need proof before replacing simple maps.

**Current-data change:** cells no longer author walls/openings; authored spaces,
vertices and boundaries replace them. Events retain grid anchors only if the
project chooses that capability.

**Pipeline that can remain:** a resolver rasterizes/query-projects current grid
and faces, then uses the same visibility, geometry and bundle seams.

**PR implication:** neutral selection needs `space` and `boundary`; present
Second Rite remains cell-only.

**Smallest falsifier:** one rectangular room, irregular annex, exterior edge and
two-sided doorway; compile to current grid/face inputs and test stable selection
plus event placement.

### C. Grid topology plus reusable modules and scene objects

**Advantage:** preserves readable dungeon topology while adding oriented doors,
stairs, large props and imported structural meshes with footprint/attachment
semantics; least disruptive route to future verticality.

**Cost:** modules can smuggle gameplay behavior into visual meshes. Collision,
navigation and occupancy must stay declared/project-owned, not inferred.

**Current-data change:** retain named topology; add module definitions and
placements (anchor, orientation, footprint, optional level); keep events/lights
typed and separate.

**Pipeline that can remain:** tileset resolution, geometry compiler, provenance,
visibility profiles and bundle; resolver adds module expansion upstream.

**PR implication:** Second Rite exposes only legal cell-snapped placements;
another project may expose transforms through its own capabilities.

**Smallest falsifier:** one oriented doorway module, one two-cell prop and one
imported mesh over a fixed-map fixture; verify declared footprint/collision,
semantic picks and deterministic bundle IDs.

## Guardrails

- Do not make a scene graph the sole map authority: it cannot alone answer
  topology, passability, procedural generation or grid event legality.
- Do not make mesh/triangle IDs authored selection keys; they are derived and
  backend-specific.
- Do not universalize GridMap's mesh/collision/navigation coupling.
- Do not add arbitrary transforms, stacked floors or ramps because references
  support them; they are pressure tests, not current Second Rite scope.
- Do not choose a schema before a prototype demonstrates authoring,
  validation, deterministic compilation, top/perspective selection, Git review
  and generated-dungeon behavior together.

## Source note

Primary/vendor documentation was used where available: LDtk’s IntGrid and
auto-layer documentation; Tiled’s JSON format; Godot’s GridMap, MeshLibrary,
TSCN and PackedScene documentation; TrenchBroom’s map grammar; ZDoom’s
engine-facing topology documentation; and RPG Maker MZ’s official map/event
help, linked inline above. Tiled documents format/version fields and historical
format additions; Godot text scenes have format/resource records. The portable
conclusion is to version authored and compiled outputs explicitly, validate
strictly, and make deterministic compilation—not a renderer—where migration
and compatibility policy lives.
