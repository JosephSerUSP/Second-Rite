# Resolved spatial boundary experiment — 2026-09-09

Issue: [#1088](https://github.com/JosephSerUSP/Second-Rite/issues/1088).

## Recommendation

**Hybrid convergence.** Keep a small, typed physical boundary and retain typed
source-family structural products beside it. The experiment supports common XYZ
positions, identified physical bodies and bounded spatial features. It does not
support flattening dungeon topology and tactical lattice semantics into one
universal Map or deriving them from art meshes.

`ResolvedSpatialScene` should remain an experiment name for now. No production
engine name, persisted Map schema, migration, Studio rewrite or new runtime
consumer is introduced. Review these results before opening production work.

## Evidence and authority

The executable experiment is `tests/fixtures/spatial/`. It contains four source
inputs, four deterministic `resolved_spatial.json` products, typed structural
companions where needed, gameplay/view products, focused tests, and a live LÖVE
probe. The probe uses the canonical Project exporter in a disposable stage.

Authoring evidence is pinned to commit
`2fe51c223807fda0930799084d0ba2da5d143ad7`, the checkout HEAD at investigation.
Pre-existing dirty town changes are preserved and excluded from the captured
map/environment sources. The probe executes local runtime modules; its five
principal module hashes are recorded separately. It loads normal staged Project
dependencies, substitutes captured dungeon policy, and passes explicit fixture
inputs. This is not an assertion that the entire dirty checkout is a clean,
reproducible release. `docs/ENGINE-STATE.md` and SPEC §1.1.2 remain the production
status and authority guidance; this report records experimental observations.

| Fixture | Authoring authority | Observed product |
| --- | --- | --- |
| Dungeon | Captured floor-2 dimensions/anchors/profile and dungeon policy; real `exploration.generateDungeon`, seed 97531; separate Event JSON | 289 coordinate-addressed cells/bodies, five rooms, 17 generated openings plus the authored opening, explicit edges/corridors, semantic entry-room feature |
| Praca | Hash-bound adopted modelled blend and its existing exported geometry/collision; map 17 owns Events, transfers, traversal and camera | One mesh body with separate render/collision references; collision-derived surface-center feature; separately joined Child Event |
| Tactics | Tiny procedural lattice source owns site geometry, occupancy and explicit connections; tactical policy owns legality/cost | Two elevations, gaps, bridge, blocked site, stair connection and primitive steps; deployment volume; independently derived move graph |
| Metroidvania | Primitive spatial source; project JSON owns planar motion, Event, progression and camera choice | Three XYZ platforms with elevation/depth distinctions, exit and trigger volumes, Event placement and actual orthographic WorldCamera correction |

The compact dungeon source is 1,880 bytes. It remains procedural; expanded JSON
is a derived artifact, not the new source format. The runtime probe repeats the
generator with the same seed and checks a changed seed produces different rows.
The Node checks additionally prove connected open topology and retain every
neighbor edge, token, room and corridor record. Openings are structural
thresholds: movable door leaves and door gameplay state are not tested here.

## Small concepts that survived

The common product has exactly `coordinateSystem`, `bodies`, and `features`.
Bodies and features each have globally unique IDs, finite XYZ positions and
closed shape variants. Boxes have positive full extents; segments have absolute
endpoints; mesh references bind exported OBJ paths to SHA-256 content. The
existing runtime OBJ importer owns transport-axis conversion. Binary source
files are never runtime dependencies.

Bodies provide physical/display geometry; features provide identified points,
volumes and connections. This is more constrained than an untyped scene graph:
unknown keys, unknown shapes, duplicate IDs, nonfinite coordinates, invalid
extents and misplaced gameplay fields fail validation. Mesh bodies use separate
render and collision references; the fixture does not pretend render triangles
are authoritative collision. Primitive boxes supply both in these small cases.

Positions suffice here. A parent graph, quaternion/scale stack, inherited
transforms, freeform tags and redundant role flags did not earn their cost.
Rotated/instanced geometry is not proved; transforms can be baked by the source
adapter for these fixtures. This is a bounded result, not permission to assume
translation-only geometry will serve all future sources.

An anchor is an identified point. An exit is a bounded feature selected by
external transfer policy. A trigger region is a bounded feature selected by
external Event logic. A stair connection is a segment. None needed its own
genre-specific top-level array. General splines were removed: no fixture needed
one, and a segment is not a claim to support every path representation.

## Concepts kept outside the common physical product

Dungeon cell/edge token semantics, room/corridor records and tactical lattice
occupancy/connectivity remain typed `resolved_structure.json` companions.
Tactical movement policy consumes the companion directly; arbitrary art meshes
have no vote. The same scene can yield a different legal move graph when
`maxStep` or climb cost changes. Explicit connections, blocked sites and gaps
are independently tested.

Event identity and placement expressions remain in project-owned JSON. A join
may derive a world position from a physical feature plus offset; the feature
does not acquire the Event. Offset/position edits cannot alter the physical
product. Conversely, changing an anchor changes the joined view while leaving
the Event source unchanged. Missing references fail loudly.

Camera selection/correction, planar movement constraints, transfer destinations,
trigger behavior, dialogue and ability requirements remain outside physical
data. `rpg_ortho` is resolved by the real `WorldCamera` code, yielding 45-degree
pitch and `[sqrt(0.5), 1]` anisotropic projection scale. This uses the correction
already exercised in `tests/test_chest_3d.lua`. It changes presentation, not XYZ
positions or gameplay ownership. The fixture is oblique 2.5D, not a claimed
match for a specific side-view game's art direction.

## Falsifier answers

| Acceptance question | Answer and practical limit |
| --- | --- |
| One XYZ convention? | Yes: existing right-handed Z-up, XY-ground world space. Grid indices become cell centers once; OBJ transport goes through the existing importer once. No genre-specific world frame is added. |
| Nominally 2D stays 3D? | Yes: distinct Y-depth platforms remain distinct under planar gameplay and orthographic presentation. No second Map ontology appears. |
| Event placement remains project-owned? | Yes in both dungeon and Praca. Mutation tests isolate JSON placement from physical products and reject missing/ambiguous anchors. Existing production generator behavior is not migrated. |
| Compact deterministic procedural dungeon? | Yes on the installed LÖVE/Lua implementation: fixed-seed repeat plus semantic drift checks. Cross-RNG-implementation stability is not claimed. |
| Explicit tactical elevation/lattice without mesh-derived rules? | Yes, using a separate typed structural companion. This falsifies the stronger hypothesis that the common physical product alone is sufficient. |
| Platforms/portals/regions without progression rules? | Yes: boxes and identified bounded features; `double_jump`, transfer targets and trigger behavior remain in gameplay JSON. |
| Blender geometry without runtime dependency or Event authority? | Yes for consuming existing exported products. Collision-derived `lane_surface.center` is geometry-owned; Child placement comes from map JSON. No live Blender session is required. |
| Inspectable output from binary source? | Yes: source hashes, text mesh references, parsed collision vertices, feature coordinates and gameplay joins can be diffed. A fresh blend-to-export equivalence proof is not performed. |
| Fields wanted by only one genre? | Lattice and grid topology stay behind source-specific products. General paths/scene hierarchy were dropped. Point/volume/segment features supply spatial meaning without tactical or progression flags. |
| Avoid giant sparse Map union? | Yes. There is no Map replacement, no grid/mesh/track/voxel super-record, and no freeform component bag. The small shape union is closed and validated. |

## Warnings found by the experiment

The existing Praca scaffold (`tools/blender/recipes/st_maria_praca.py`) populates
`TH_ANCHORS` from map Events. Importing all exported anchors as geometry-owned
facts would therefore reverse semantic authority. This spike deliberately uses
an independent feature derived from collision bounds instead. A future Blender
Event proxy must reload from JSON and transactionally write that same field;
deleting editor proxy state must not delete the Event. Full editor integration
and conflict handling are documented, not prototyped.

The pinned map snapshot also contains transfer Event Z=-1.5 positions alongside
a Z=0 collision top and selected Child Event. This is preserved as historical
evidence, not silently corrected or generalized into a global coordinate offset.
The result proves that facts can share a coordinate convention; it does not
prove every captured authored fact agrees physically or that current Praca is
playable. Binary provenance is not a fresh re-export certificate.

## Open capability questions and migration impact

The most useful next decision is the minimum required operations for a consumer:
identity lookup, physical geometry access, optional structural adjacency and
revision binding. The spike intentionally does not freeze capability discovery,
cross-product invalidation, mesh-provider packaging, large-world streaming,
rotated instances or topology IDs across generator revisions. Hash-bound mesh
references require a product consumer that uses the existing importer; no new
renderer or physics host was built here.

Procedural anchors still need an explicit authorable semantic-ID policy if they
must survive room reordering or generator redesign. This fixture's
`entry_room.center` is tied to its first authored anchor by adapter choice; it
is stable for the claimed fixed input, not a general persistent attachment
solution. No such promise is made for generated room ordinals.

Migration impact is zero: no production Map data, schema, runtime files, Studio
files, adopted blends or golden references changed. No broad implementation
issue was filed before review. The recommendation is to review the hybrid
boundary and its limitations, rather than promote the experimental JSON verbatim.

## Validation

`node --test tests/fixtures/spatial/spatial.test.js` passes eight focused contract,
negative-input, topology/reachability, ownership, tactical policy and planar
presentation checks. `node tests/fixtures/spatial/build.js --probe --check`
passes a fresh LÖVE process and byte/semantic comparison of all derived products.
Recorded local wall times via `tools/ci/time-step.js`: 317 ms for the Node suite
and 3.7 s for canonical staging plus the runtime probe and artifact checks.
These are compiler/architecture checks. They are not G5/G6, a gameplay traversal,
visual acceptance, or a claim that the pre-existing dirty checkout passes every
production gate. No renderer or production behavior is changed by this spike.
