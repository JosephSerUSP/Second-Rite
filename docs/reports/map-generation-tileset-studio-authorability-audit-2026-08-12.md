# Map, Generation, Tileset, and Studio Authorability Audit

**Date:** 2026-08-12
**Scope:** Second Rite map representation, procedural generation, tileset and geometry authoring, and Studio authorability
**Status:** Architecture and authorability audit; no production implementation decision
**Evidence baseline:** `main` at `8fdb95b1`, issue [#277](https://github.com/JosephSerUSP/Second-Rite/issues/277), merged PR [#322](https://github.com/JosephSerUSP/Second-Rite/pull/322)

## 1. Executive summary

The live engine is further along than the current Studio suggests. It already has a coherent pipeline for both fixed and generated maps: authored map fragments are loaded, a runtime map instance is resolved, tileset variants and fixture predicates are applied, geometry is compiled through an engine-owned renderable bundle, and the resulting runtime state is saved with generated structure and lighting. The current editor exposes useful portions of that system, but mostly as a 2D map form and canvas plus a largely atlas-oriented Tileset Studio.

The strongest architectural conclusion is not a new schema. It is an ownership boundary:

> authored intent is stored as Map and tileset data; the engine deterministically resolves that data into runtime structure, geometry, fixtures, lighting, and presentation facts; Studio must author and inspect the former through the latter without becoming a second compiler.

The current repository does not contain a persisted Location hierarchy, reusable anchor/prefab registry, first-class Area/Region/Terrain model, or a Studio surface for the full geometry contract. Those are genuine authorability or vocabulary gaps, not evidence that the existing Map or generation pipeline should be replaced. The ratified direction is that layout production is compositional within a Map: fixed structure, multiple independently generated spatial scopes, and other authored structure may coexist, with each generated scope eventually able to use its own policy.

The main unresolved vocabulary question is the relationship between Area, Region, Zone, and Terrain. The evidence supports keeping them separate until a small cross-cutting prototype demonstrates the need for a shared concept. In particular, `map.zones` and generated per-cell zone tags are already real predicate inputs, but they are not yet a general world-region hierarchy.

`Location` is the ratified owner direction for a real non-playable compositional node. It may parent Locations and Maps, with policy/default inheritance cascading through multiple semantic levels and descendants able to override or interrupt that inheritance. It has no geometry and is not itself a playable Map. A named subdivision does not automatically create another Map: St. Maria may remain one Map even when it contains districts or subareas.

### Audit verdict by layer

| Layer | Finding | Classification |
| --- | --- | --- |
| Map runtime | Fixed and procedural maps share a real load/resolve/save path, with clear runtime products | Further along than Studio implies |
| Procedural generation | Anchors, profiles, openings, generated zones, fixture predicates, reachability protection, events, and lighting are implemented | Further along than Studio implies |
| Tilesets | Registry fragments, immutable base-plus-delta resolution, weighted pools, fixtures, models, height maps, glow maps, and geometry metadata are implemented | Further along than Studio implies |
| Map hierarchy | Only Map records and Studio presentation folders exist; no persisted Location/parent ontology exists | Genuine data/architecture gap |
| Area/Region/Terrain | Zone predicates are real; broader vocabulary and scope are not settled | Partial / unresolved |
| Map Studio | Useful authoring exists, but several authored fields and runtime products are hidden, raw JSON, or not previewable | Genuine Studio gap |
| Tileset Studio | Atlas/pool editing is usable; full geometry and compiled-result authoring is not represented | Genuine Studio and verification gap |
| #277 / #322 | The 3D work is evidence and a spike, not canonized replacement architecture | Reconciled; no implementation decision |

### Ratified owner direction added after the original audit

- **Recursive Location inheritance:** Location policy/default inheritance may cascade through multiple semantic hierarchy levels, such as The Gate → First Stratum → Floor 2. A descendant may explicitly override or interrupt/reset inherited policy. Exact representation, field vocabulary, merge mechanics, diagnostics, and Studio implementation remain open.
- **Compositional Map layout production:** one playable Map may combine fixed structure, multiple independently generated Areas/scopes, fixed landmarks, and other authored structure. Exact Area representation and generation-scope schema remain open.

## 2. Current Map ontology

### 2.1 The implemented Map boundary

The current authored Map is a single record with a stable `id` and map-owned gameplay, presentation, generation, and authoring fields. Maps are ordered collection fragments under `data/maps/index.json`; the numeric filenames are storage names, not the identity model. `data/authored_storage_manifest.json` classifies maps as `ordered_collection` fragments and tilesets as a separate `keyed_registry` fragment collection.

The loader reads the ordered map collection through [`data/authored_storage.lua`](../../data/authored_storage.lua) and builds `loader.mapsById`. The current repository contains 13 Map records. There is no `data/locations/` collection, Map parent field, Location reference, or hierarchy manifest.

At runtime, the Map record is not the whole playable state. `engine.exploration` combines it with a session-owned runtime instance:

```text
authored Map record
        |
        v
fixed layout OR procedural resolver
        |
        +--> mapGrid, events, mutations
        +--> generated features, lights, zones
        +--> resolved tileset and geometry inputs
        +--> runtime lighting and presentation overrides
        |
        v
saved Map instance / engine-owned renderable bundle
```

The distinction matters. `mapGrid`, generated events, generated features, generated zones, and runtime light are resolved instance state. They are not currently authored Map Definition fields and should not be mistaken for a second authored hierarchy.

### 2.2 Current authored Map fields and roles

| Field or group | Current role | Confidence |
| --- | --- | --- |
| `id`, `title` | Map identity and display label | Implemented |
| `category` | Current Studio grouping and metadata; not a persisted parent relationship | Implemented, limited |
| `layout`, `width`, `height` | Fixed map structure and dimensions; compact authored `#`, `.`, `o` rows | Implemented |
| `generationProfile`, `anchors`, `generateOpenings` | Procedural resolver inputs | Implemented |
| `generation` | Studio-facing Fixed/Procedural metadata; runtime branching uses `safe`, not this field | Partial / conflated |
| `safe` | Expedition danger/cache/encounter policy and currently also the fixed-vs-generated branch | Implemented, overloaded |
| `tileset`, `tilesetOverride` | Base tileset selection plus sparse map-local delta | Implemented |
| `zones` | Authored tag regions used by fixture predicates; rectangle or explicit cell list | Implemented, narrow |
| `materials` | Optional layout-shaped material lookup consumed by the renderer; rarely authored in current data | Implemented, low-use |
| `ceilingStyle`, `fog`, ambient fields | Map presentation policy | Implemented |
| `light`, `lightObjects` | Baked vertex light and authored light sources | Implemented |
| `events`, `encounters`, `recruits`, `treasures` | Map-owned content and pools; event commands remain data-driven | Implemented, unevenly surfaced |
| `spawn`, `depth`, `intro`, music/BGM, image, encounter policy fields | Gameplay, transition, or metadata inputs with uneven Studio coverage | Implemented or partial by field |

The most important semantic warning is `safe`. It currently affects whether the map is loaded from an authored layout or generated, but it also means dangerous/safe expedition policy. A future authoring vocabulary must not assume that gameplay danger and layout-production mode are one concept. The existing `generation` field appears to be the beginning of a separate authoring concept, but the runtime does not currently use it as the authority.

### 2.3 Fixed, procedural, and hybrid scopes are already one Map family

Fixed structure uses compact authored layout and may still receive tileset feature injection, lighting, events, and mutations. Generated structure begins from dimensions/profile/anchors and produces the same runtime products. An anchor is therefore not a different Map kind, and a generated scope is not a different authored ontology. The distinction is how each spatial scope is resolved.

The current data already provides partial evidence for compositional layout production: an authored anchor or fixed entry structure can be placed into a generated dungeon, while the resolver supplies interstitial rooms, corridors, openings, fixtures, and generated metadata around it. The owner direction extends this principle beyond one generated whole: a future Map may contain multiple independently generated Areas/scopes, each using different generation policy, alongside fixed landmarks and other authored structure. The current implementation does not yet provide the Area schema or multiple-scope resolver, so this is a requirement, not a status claim.

## 3. Current procedural-generation pipeline

The live pipeline is in [`engine/exploration.lua`](../../engine/exploration.lua). In simplified form:

1. Resolve the generation profile from `mapData.generationProfile` or the system dungeon default for the current generated scope.
2. Choose scope dimensions from the Map or the scope's future policy/default.
3. Initialize or claim the scope's solid/topological space.
4. Copy inline anchors into the relevant space and reserve their cells.
5. Place random rooms around anchors, with collision and a one-cell border check.
6. Use an L-shaped corridor to connect room records in sequence.
7. Derive entrance/exit stair and wall slots for the resolved scope where applicable.
8. Optionally convert corridor-carved thresholds into `o` openings.
9. Create generated per-cell zone tags such as `room`, `corridor`, `anchor`, `entrance`, and `exit`.
10. Resolve the selected tileset, inject deterministic features and fixture prefabs through predicates, and protect spawn/event/anchor/stair cells from invalid blocking placements.
11. Inject entrance/exit and authored fixed/random events, recruits, and other generated content.
12. Bake or restore lighting and retain generated runtime collections.
13. Cache dangerous-map state and serialize the resolved Map instance through [`engine/savegame.lua`](../../engine/savegame.lua).

The current implementation performs this as one generator path for a Map. The owner direction requires the architecture to grow toward compositional scopes rather than assuming one generator owns the whole playable Map.

The output is not merely a layout string. It is a resolved structure with gameplay events, feature placements, light sources, zones, and cacheable runtime state. This is exactly the separation identified by the merged [map representation survey](map-representation-architecture-survey-2026-08-11.md): authored intent, deterministic resolver/compiler, resolved structure, and renderer geometry are separate seams.

### 3.1 What the current generator can express

- fixed authored rooms or structures embedded through anchors;
- profile-controlled room count and room size;
- deterministic generation when a seed is supplied;
- corridor-connected room topology;
- openings as structural `o` cells rather than event-only decoration;
- entrance/exit placement and authored event placement modes;
- map and generated zone predicates;
- tileset-driven feature pools and fixture prefabs;
- weighted variants and deterministic probability checks;
- movement-blocking fixtures guarded by reachability invariants;
- generated light sources and baked runtime light;
- cached dangerous-map instance state;
- authored map overrides and structural mutation.
- a future Map composition in which multiple generated scopes use independent generation policy alongside fixed structure; this is a requirement, not currently implemented.

### 3.2 Current generator limits

The generator does not currently expose a reusable anchor library, semantic room/area identity beyond generated tags, connector contracts, explicit authored seed policy in the Map Studio, multiple independently generated Map scopes, multi-map Location composition, or a general terrain grammar. Anchor layouts are inline per Map and are placed as fixed cell patches. They are not a first-class reusable prefab registry with ports, variants, inheritance, or Studio preview provenance.

The current `generatedZones` collection is also intentionally modest: one tag record per generated non-wall cell, with room/corridor and special tags. It is a runtime predicate index, not a general region graph or a replacement for future authored Area/Region vocabulary.

## 4. Anchor / prefab analysis

### 4.1 Anchors today

An anchor contains an inline position, compact layout, and an `allowRandomEvents` control. Generation copies its cells, marks them occupied, and records the source room as an anchor room. The anchor can therefore constrain topology and provide a stable authored landmark within a generated map.

It is best described as a **placed fixed structure seed**. It is not yet:

- a reusable global asset;
- a named room definition with a stable identity independent of its Map;
- a prefab with typed entrances or connection ports;
- a scene graph node;
- an Area, Region, Terrain, or Location;
- an authorable geometry object with a compiled preview.

### 4.2 Fixture prefabs today

`tileset.fixturePrefabs` is a different but related concept. It defines fixture placement recipes selected by predicates, probability, model/atlas representation, blocking behavior, and light emission. `engine/fixture_predicates.lua` evaluates authored and generated zone tags plus adjacency and distance conditions. This is already a useful general decoration mechanism, and it belongs to the tileset/variant vocabulary rather than a second map-decoration database.

### 4.3 Recommended distinction for future work

Keep these names distinct until a prototype proves a need to merge them:

| Concept | Current or proposed meaning |
| --- | --- |
| Anchor | A Map-local fixed structure seed used during generation |
| Fixture prefab | A tileset-owned placement recipe for a feature or object |
| Map fragment/prefab | A possible future reusable authored structure with explicit identity and connectors; not implemented |
| Area/Region | Possible semantic grouping above individual cells; unresolved |
| Location | Non-playable compositional owner for Maps and policy; ratified direction |

The smallest useful next experiment is a single reusable room with two typed doorway ports, placed once in a fixed map and once in a generated map, while retaining the current grid as the gameplay authority. That experiment should test authoring, deterministic placement, event provenance, fixture predicates, renderable bundle output, picking, and save/reload before any schema is adopted.

## 5. Tileset architecture

### 5.1 Implemented data and resolution

Tilesets are keyed registry fragments under `data/tilesets/`. The base selection is `mapData.tileset` or `dungeon_default`; `mapData.tilesetOverride` is a sparse immutable delta resolved by [`engine/tileset_resolver.lua`](../../engine/tileset_resolver.lua). Pools merge by stable `id`, nested objects merge, and arrays replace. This gives the project an existing inheritance-like seam without introducing a new general inheritance system.

Current tileset vocabulary includes:

- base weighted wall, floor, ceiling, and sky variants;
- doors;
- algorithmic `features` with predicates, weights, probabilities, model/atlas presentation, blocking, and light emission;
- `fixturePrefabs` for reusable placement rules;
- atlas textures and optional model-backed variants;
- optional `heightMap`, `glowMap`, surface-specific height scales, height operations, mesh/sample densities, triangle budgets, and offsets;
- sky panorama and fog/lighting-adjacent presentation data where applicable.

The runtime and validator already treat height maps as a real contract. `presentation/map_renderable_bundle.lua` resolves height-map metadata, geometry quality, material provenance, model surfaces, wall caps, openings, floor/ceiling surfaces, and feature surfaces into an engine-owned bundle. The bundle is a resolved presentation fact, not authored data.

### 5.2 Variant model

The current variant-pool approach is stronger than the old atlas-cell-painting mental model. A base wall click or feature variant can carry atlas selection, edge halves, model, weight, height offset, predicates, effect/light metadata, and blocking policy. The engine applies the same resolved tileset to runtime and editor bridge paths.

The design documents [`tileset-and-events-redesign.md`](../design/studio/tileset-and-events-redesign.md), [`image-authored-geometry.md`](../design/runtime/rendering/image-authored-geometry.md), and [`renderer-3d-roadmap.md`](../design/runtime/rendering/renderer-3d-roadmap.md) describe intended extensions and art direction. Their prose is not status evidence. The live validator, resolver, bundle, and current data are the status evidence.

### 5.3 Tileset architecture risks

The current architectural risk is not that tilesets lack power. It is that the authoring surface exposes only part of the power and therefore teaches a misleading model:

- the Studio presents an RPG Maker-style atlas picker while runtime tilesets include procedural features, predicates, fixtures, models, and geometry metadata;
- raw JSON is used for fixture prefab libraries and some map-level deltas;
- height/glow inputs can affect compiled geometry and shading but lack a first-class editor surface;
- the Studio preview is primarily a 2D composite/atlas view, not a real engine-resolved geometry preview;
- the editor does not expose the provenance and quality profile that the renderable bundle already carries.

## 6. Area / Region / Zone / Terrain analysis

### 6.1 What exists

`map.zones` is authored map-local data. The validator accepts either a rectangle (`x`, `y`, `width`, `height`) or an explicit cell list, with `id`/`tags`. It is consumed by fixture predicates. Current authored examples include named areas such as `colonnade`, `shrine`, `dais`, `prop`, and `gallery`.

`generatedZones` is runtime data emitted by the procedural resolver. It tags cells with generator facts such as room, corridor, anchor, entrance, and exit. `fixture_predicates.buildZoneIndex` combines both sources into a cell lookup.

`materials` is a separate optional per-cell material lookup. It is not a zone, and it should not become one merely because both are cell-shaped. Light objects and generated features can also contribute material identity to renderer lookup.

### 6.2 What does not exist

There is no first-class Area or Region registry, no nested zone hierarchy, no terrain surface/biome vocabulary, no authored terrain transition grammar, and no contract saying whether an Area owns gameplay policy, generation constraints, visual material, or only labels. `zone` is currently a predicate tag, not a universal spatial ontology.

### 6.3 Audit conclusion

The relationship among Area, Region, Zone, and Terrain remains unresolved. The safest current vocabulary is:

- **Zone:** the existing map-local or generated predicate tag attached to cells.
- **Terrain:** a future surface/material/topology concept only if it needs semantics beyond `materials` and tileset resolution.
- **Area:** a possible authored semantic subdivision inside a Map, especially for narrative or authoring identity.
- **Region:** a possible broader grouping or generated partition, but not yet distinct enough from Area to ratify.

Do not promote the current `zones` array into a universal hierarchy without testing nested ownership, generator output, fixture predicates, map editing, runtime save state, and the renderable bundle together.

## 7. Location/world hierarchy analysis

### 7.1 Current repository

The current repository has Maps, events, scenes, system configuration, and static location-art presentation. It does not have real non-playable Location records. The Map tree in [`tools/editor/js/map-editor.js`](../../tools/editor/js/map-editor.js) synthesizes a `Second Rite` root and `Town`/`Dungeon Floors` folders from `category` and index position. Those folders are Studio presentation, not persisted hierarchy.

There is no current evidence of:

- a Location identity registry;
- parent-child Location relationships;
- Map membership under a Location;
- inherited defaults or policy;
- a non-rendering compositional node;
- a rule that named districts must become Maps.

### 7.2 Ratified owner direction

`Location` is the ratified owner direction for a real non-playable node. It may own authored identity, parent Locations and Maps, and inherited defaults or policy. Location inheritance is intentionally recursive: a Location may parent another Location, which may parent another Location or Map, and policy/default inheritance may cascade through that chain. A descendant may explicitly override or interrupt/reset inherited policy. It has no geometry and is not a playable Map. It should therefore behave more like a compositional/organizational node than like a hidden Map.

The practical consequence is that St. Maria may remain one Map even if it grows internal districts, neighborhoods, or rooms. Map boundaries should follow runtime and spatial semantics—movement, collision, save/instance lifecycle, generation, and event scope—not a narrative label alone.

When a Location chain exists, Studio authorability must include effective-value provenance. An author should be able to inspect a result such as `Tileset: first_stratum` inherited from First Stratum, whose ambient defaults derive from The Gate, or `Fog: crimson` overridden on Floor 2. The UI and final data shape are unresolved, but provenance across the complete chain is a settled authoring requirement.

### 7.3 What a future hierarchy must not do

It must not make a scene graph the sole authority for gameplay, use renderer triangle identity for selection, or infer collision/navigation from presentation geometry. These are explicit guardrails from [#322’s survey](map-representation-architecture-survey-2026-08-11.md) and the current renderer design.

## 8. Inheritance candidates and recursive semantics

Inheritance is already present in narrow, explicit forms. The owner decision now ratifies recursive semantic inheritance for Location policy/defaults, while leaving its representation and mechanics open.

| Candidate | Evidence | Audit position |
| --- | --- | --- |
| System generation profile → Map override | `data/system.json` profiles and `map.generationProfile` | Keep as explicit default/override; do not generalize yet |
| Base tileset → Map sparse tileset delta | `tileset_resolver.lua` and `tilesetOverride` | Existing and useful; document as tileset resolution, not universal inheritance |
| Tileset variant/prefab → generated placement | Feature predicates and fixture prefabs | Existing composition model; preserve |
| Location → child Map defaults/policy | Owner direction; no data yet | **Ratified recursive semantic direction**; exact fields, override/reset rules, and serialization remain open |
| Location → child Location defaults/policy | Owner direction; no data yet | **Ratified recursive semantic direction**; may cascade through multiple Location levels, not geometry inheritance |
| Map/Area → generation constraints | Anchors and zones are evidence, but not a unified model | Prototype before schema |
| Tileset → geometry visibility profile | `play` and `authoring` are consumer profiles in the engine | Keep consumer-specific; not authored Map inheritance |

The settled semantic rule is: **Location inheritance may cascade through multiple semantic hierarchy levels; descendants may explicitly interrupt or override that inheritance.** The audit does not choose the final serialization, field-by-field inheritance vocabulary, merge mechanics, reset/null syntax, validation diagnostics, or Studio UI. Every inherited field will need an owner, an override/interruption rule, an effective-value inspection path with chain provenance, validation, and save/load semantics. A generic deep merge is not a decision and should not be assumed.

## 9. Studio authorability matrix

The criterion is not merely whether a field exists in JSON. A mechanic is authorable only when Studio can reveal, explain, author, fully edit, preview, round-trip, and validate it through the real engine path.

| Concept | Current engine/data support | Current Studio surface | Authorability verdict | Gap class |
| --- | --- | --- | --- | --- |
| Map identity/title | `id`, `title`, loader identity | Map properties/title | Good for existing fields | None / uneven |
| Map category | Used mainly for grouping/metadata | Category dropdown and synthetic tree folders | Visible but not hierarchy | Misleading partial |
| Fixed authored layout | Compact `layout`, `#`/`.`/`o`, parser and renderer | 2D canvas paint modes | Authorable | None |
| Procedural layout mode | Runtime branch is currently tied to `safe` | Fixed/Procedural dropdown writes `generation` | UI and runtime authority diverge | Engine/data + Studio |
| Safe/dangerous policy | Expedition/cache/encounter behavior | Safe checkbox | Visible, but overloaded with layout semantics | Engine/data vocabulary |
| Width/height | Runtime generator and fixed-map resize | Dimension fields | Authorable with fixed-map caveats | Partial |
| Generation profile | Runtime profile lookup | Profile dropdown | Authorable | None |
| Seed/deterministic reseed | Generator accepts seed; save/cache preserve result | No seed or reseed workflow | Not authorable/inspectable | Studio |
| Anchors | Inline fixed room seeds | Anchor list/dialog | Partially authorable; no reusable registry/ports | Studio/data |
| Generated rooms/corridors | Runtime resolver | No generated provenance/preview in current Studio | Not inspectable | Studio/verification |
| Generated openings | `generateOpenings`, structural `o` | Checkbox and canvas result only for fixed maps | Partial | Studio |
| Authored zones | Rect/cell records and predicate tags | Raw JSON textarea | Technically writable, not explainable or ergonomic | Studio |
| Generated zones | Runtime per-cell tags | Not exposed | Not inspectable or previewable | Studio |
| Area/Region/Terrain | No settled first-class model | No surface | Correctly absent, but unresolved | Data/architecture |
| Material lookup | Optional `materials`, light/feature contributions | No authored material grid field; visual paint is indirect | Partial and low-use | Studio |
| Tileset selection | Base registry id | Dropdown | Authorable | None |
| Tileset sparse override | Resolver supports per-map delta | Raw JSON textarea | Writable but not author-friendly | Studio |
| Weighted wall/floor/ceiling pools | Resolver and validator support pools | Pool tabs and variants | Mostly authorable | Partial |
| Doors/openings | Structural `o`, door pool, wall events | Door pool and map opening paint | Split across surfaces; explainability gap | Studio |
| Features/predicates | Runtime predicates and placement | Feature form has predicate JSON/raw controls | Partial; insufficient semantic preview | Studio |
| Fixture prefabs | Runtime pool and reachability protection | Raw JSON library | Not schema-guided | Studio |
| Models | Runtime model/OBJ path for supported variants | Model picker for doors/features | Partial; no resolved scene preview | Studio/verification |
| Height maps | Validator and bundle compile atlas geometry | No first-class height fields | Not authorable in Studio | Studio |
| Glow maps/emission | Renderer shader and tileset data | Light fields exist for fixtures; no glow-map controls | Partial | Studio |
| Geometry density/budget | Bundle and validator metadata | No quality/mesh controls or diagnostics | Not inspectable | Studio/verification |
| Visibility profiles | `play` and `authoring` profiles in engine | No profile selector or authoring viewport | Runtime-ready, Studio-hidden | Studio |
| Ceiling style | `solid`/`sky` and visibility behavior | Dropdown | Authorable | None |
| Lighting | `light`, `lightObjects`, runtime bake | Light mode and light-object editing | Authorable, bake/result inspection limited | Partial |
| Fog | Inline/preset and real preview endpoint | Preset/custom editor and 3D preview | Good | None / verify |
| Ambient effects | Map/camera world effect data | Fields in properties | Partial; real-engine preview coverage should be checked | Verification |
| Events | Event records, pages, commands, wall-event behavior | Shared event editor/canvas placement | Strong for common event fields | Partial |
| Fixed/random event spawn | Runtime placement rules | Spawn field and map canvas | Partial; generated result not previewed | Studio |
| Map spawn | `mapData.spawn` and system fallback | Player start tool edits `system.spawn` | Map-local spawn is hidden | Studio |
| Entrance/exit stairs | Generator and generated event/stair facts | No generated stair authoring/inspection | Not inspectable | Studio |
| Encounters | Map pool and generator/runtime use | Encounter list | Mostly authorable | Partial |
| `encounterTroop` | Present in data/runtime paths | No clear first-class property control | Hidden | Studio |
| Recruits | Map pool and generated recruitment event | Recruit list | Authorable | None / verify |
| Treasures | Present in map records or event-driven content | No obvious Map property surface | Hidden/unclear | Studio |
| Intro/music/BGM/image/depth | Data/runtime/transition roles vary | Some BGM, not all fields | Uneven | Studio |
| Map instance save/cache | Saves generated state, features, zones, lights | No state inspector | Not inspectable, though runtime-correct | Studio |
| Renderable bundle | Engine-owned resolved geometry/material/provenance | No current map 3D bundle viewport on main | Not inspectable | Studio/verification |
| Location hierarchy | No data model | Synthetic folders only | Not authorable; UI could mislead | Data/Studio |
| Recursive Location inheritance | Ratified semantic direction; no data model yet | No effective-value chain/provenance view | Not authorable or inspectable | Data/Studio |
| Round-trip/validation | G1 and storage writers validate data | Save path uses server/validator, but raw fields can be opaque | Strong engine gate, uneven UX | Verification/Studio |

## 10. Tileset Studio gap analysis

### 10.1 What Tileset Studio does well

The current Studio exposes the pool-based model: walls, floors, ceilings, fixtures, and doors; weighted variants; atlas coordinates; edge halves; models for supported variants; feature effects; fixture predicate/probability controls; blocking; and light emission. That matches the current runtime variant vocabulary better than a simple atlas editor would.

The shared registry writer and the runtime resolver are also a strong foundation. The editor does not need to become a second tileset compiler.

### 10.2 What it hides

The current Studio does not provide first-class controls for the tileset-level geometry contract represented in data and consumed by the bundle:

- `heightMap` and its atlas/tile interpretation;
- `glowMap` and `glowStrength`;
- `heightMapScale` by wall/floor/ceiling;
- `heightMapOperation`;
- mesh and sample columns/rows;
- triangle budget and offset;
- sky panorama and geometry-facing material metadata;
- a diagnostic view of composed albedo beside composed heightfield;
- the resolved `play` versus `authoring` visibility profile;
- semantic surface provenance and compiled-bundle statistics.

Raw JSON for fixture prefabs is a particularly clear authorability gap: the runtime and validator know the schema, but the Studio does not explain it or provide guided editing.

### 10.3 Smallest useful Tileset Studio prototype

The smallest useful prototype is not a full 3D asset suite. It is a single engine-backed “resolved surface” inspector for one selected wall/floor/ceiling variant:

1. select the real resolved variant and map context;
2. show albedo, height, glow, material id, model/atlas source, scale, operation, and geometry budget;
3. preview the real bundle using the authoring geometry profile;
4. show provenance back to tileset variant and map cell/feature;
5. fail visibly on invalid height/glow/mask inputs;
6. round-trip one field through the real writer and validator.

This prototype would answer whether the remaining authoring problem is primarily form design, bundle diagnostics, or a missing data concept.

## 11. Map editor gap analysis

### 11.1 Current strengths

The Map editor has a real 2D canvas and map properties surface, plus shared event editing, light-object editing, fog preview, encounter/recruit lists, anchor editing, authored-zone JSON, and tileset overrides. It is not an empty shell. It already supports the most important fixed-map operations and several procedural inputs.

### 11.2 Current gaps

The current editor does not give an author a coherent view of the Map Definition → resolved Map Instance pipeline. In particular:

- the Fixed/Procedural control writes `generation`, while engine branching uses `safe`;
- no seed/reseed or deterministic generated-layout preview is exposed;
- generated rooms, corridors, openings, stairs, zones, features, and generated lights have no provenance or inspection view;
- anchors are inline JSON-like structures, not reusable authorable assets with connectors;
- authored zones are a raw textarea rather than an explainable cell/region tool;
- there is no first-class map-local spawn field in the visible properties flow;
- `materials`, `encounterTroop`, treasures, depth, intro, map image, and some audio/policy fields lack a clear surface;
- `tilesetOverride` is raw JSON;
- the map editor has no current main-branch 3D renderable-bundle viewport;
- the current synthetic tree can make categories look like persisted hierarchy;
- no Location, Area, Region, or Terrain authoring surface exists—which is acceptable while those vocabularies remain unsettled, but should be explicit in the UI language.

### 11.3 Authoring viewport requirement

The evidence from #277 and #322 supports a semantic authoring viewport backed by the real engine bundle. The editor should select authored cells, events, lights, overrides, anchors, and future semantic objects—not triangles or renderer identities. The `authoring` visibility profile already encodes the needed distinction: wall caps are visible, walkable ceilings are hidden, and exterior walls remain inspectable. That profile should be treated as a current engine capability awaiting a Studio surface, not as a reason to add browser-side geometry logic.

The #277 spike also identified one continuous camera, an in-game front camera, event labels/graphics, ceiling/wall-cap visibility, and browser vendor-import testing as open concerns. Those are useful acceptance criteria for a future prototype, not decisions made by this audit.

## 12. Storage decomposition implications

The current authored-storage architecture is already aligned with Map Definition as a semantic authoring unit:

- `data/maps/index.json` owns explicit order;
- each Map is one fragment named by a safe storage filename;
- Map identity remains the record `id`, not the filename;
- tilesets are keyed registry fragments without a shared index;
- the shared loader/writer/validator/storage manifest define the boundary;
- editor writes must preserve the resource token and fragment contract.

The audit does not recommend splitting Maps into additional files merely because they contain generation, events, zones, or presentation fields. Those fields are currently Map-owned concerns with a coherent runtime lifecycle. A future Location hierarchy, reusable anchor registry, or Area registry may justify new resource types, but only when the semantic ownership and editor workflow are clear.

The existing storage boundary does imply an important future rule: a Location should not be smuggled into Map fragments through a synthetic category or filename convention. If Location becomes real, it needs its own identity, ordering/parent semantics, validation, editor surface, and resolved inheritance contract.

## 13. Reconciliation with #322

The merged survey is confirmed by the live implementation in several ways:

1. The current grid is compact authored structure, not the final renderer geometry.
2. Runtime expands authored coordinates into an internal grid and applies mutations/overrides.
3. The engine resolves tileset variants, features, fixtures, lighting, and models before rendering.
4. `presentation.map_renderable_bundle` is an engine-owned semantic renderable output with source provenance.
5. `engine.geometry.visibility_profile` demonstrates consumer-specific geometry profiles.
6. Selection and gameplay remain cell/event/light/override based rather than triangle based.
7. The map representation survey's candidate architectures remain hypotheses; the current repository does not justify choosing explicit spaces/boundaries, a universal scene graph, or a new map schema.

The survey's guardrails therefore stand. A future prototype should be judged across authoring, validation, deterministic compilation, semantic picking, save/load, and generated dungeons. A rendered screenshot alone is insufficient.

## 14. What is further along than the UI makes it appear

The following are implemented or substantially real even though the current Studio does not present them as a unified system:

- Map fragments and ordered storage, with a shared loader/writer boundary;
- fixed and procedural maps through one runtime loader;
- generation profiles and inline anchors;
- structural openings distinct from wall events;
- generated room/corridor/anchor/entrance/exit tags;
- authored and generated zone predicates, adjacency, and distance predicates;
- weighted tileset pools and sparse map-local resolution;
- fixture prefabs and reachability-protected blocking placement;
- model-backed features and doors in the same variant vocabulary as atlas surfaces;
- tileset height maps, glow maps, geometry scales, mesh density, and triangle budgets;
- engine-owned renderable bundles with semantic provenance;
- separate play and authoring visibility profiles;
- fixed/procedural lighting, light objects, generated lights, and saved runtime light;
- dangerous-map instance caching and save/load of generated structure;
- real fog preview and map-level ambient presentation data;
- shared event command editing rather than a second map-specific command language.

The conclusion is that the next value is authorability and inspection, not another parallel implementation of resolution or geometry.

## 15. Genuine engine/data gaps

These are gaps in the architecture or data vocabulary, not requests to fix them inside this docs-only branch:

1. **Layout-production mode is not separate from danger policy.** The runtime still uses `safe` for both, while `generation` is not the runtime authority.
2. **Location does not exist as a persisted non-playable node.** The recursive inheritance semantics are ratified, but there is no parent/child data model, effective-value chain, or inherited policy contract in the live repository yet.
3. **Anchors are not reusable structures.** They lack stable reusable identity, connectors, variants, and cross-Map provenance.
4. **Area/Region/Terrain are not ratified.** Existing zones and materials do not answer the broader semantic question.
5. **Generated structure has no authored provenance contract.** The runtime has useful generated collections, but authors cannot inspect why a specific room, opening, fixture, or light exists.
6. **Map-level ownership is uneven.** Fields such as map-local spawn, encounter troop, treasures, depth, intro, and some presentation metadata do not have one obvious authoring contract.
7. **Geometry asset authoring has a data contract but no complete authoring lifecycle.** The validator and bundle understand height/glow/mesh metadata; the Studio does not.

These should be addressed only through focused prototypes and reviewed schema changes. Do not patch them by adding aliases, compatibility reads, or ad hoc editor-only fields.

## 16. Genuine Studio gaps

1. The Map editor needs an explicit distinction between layout-production mode and safe/dangerous gameplay policy.
2. Maps with generated scopes need deterministic seed/reseed and generated-result inspection before compositional layout can be authorable rather than merely selectable. The surface must be able to distinguish fixed structure, multiple generated scopes, fixed landmarks, and other authored structure.
3. Anchors and zones need semantic forms and previews, while retaining raw-data escape hatches only where justified.
4. The Studio needs a real-engine resolved Map/tileset preview backed by `map_renderable_bundle`, not browser-side geometry compilation.
5. Tileset Studio needs guided height/glow/geometry controls and diagnostics.
6. Both editors need provenance: selected authored source → resolved runtime fact → presentation geometry. For recursive Locations, this must include effective-value provenance across every parent Location and the descendant's explicit override/interruption.
7. The synthetic Map tree needs language that does not imply persisted Location hierarchy.
8. G6 coverage should eventually include any new Map 3D workspace and Tileset geometry inspector. Current G6 coverage can validate the existing editor surfaces, but cannot claim surfaces that are not on `main`.
9. Round-trip verification should cover every newly exposed field and the no-op/empty/null cases already present in current Map data.

## 17. Proposed vocabulary with confidence levels

| Term | Proposed working meaning | Confidence |
| --- | --- | --- |
| Location | Non-playable compositional node with identity; may parent Locations and Maps; may own recursively inherited defaults/policy; descendants may override or interrupt inheritance; no geometry | **Ratified owner direction** |
| Map | Playable spatial world/definition with an instance lifecycle, grid/runtime structure, events, generation, and presentation inputs | High; current implementation |
| Map Instance | Resolved runtime state for a Map, including grid, events, mutations, generated collections, lighting, and cache/save state | High; current implementation |
| Anchor | Map-local fixed structure seed placed during generation | High; current implementation |
| Fixture prefab | Tileset-owned placement recipe resolved by predicates and probability | High; current implementation |
| Zone | Existing authored or generated cell tag used by predicates | High; current implementation |
| Generated scope / Area candidate | A fixed or generated spatial scope inside one Map; not necessarily another Map; multiple scopes may use independent generation policy | **Ratified compositional direction; exact Area meaning unresolved** |
| Region | Candidate broader or generated grouping; currently not distinct from Area | Low; unresolved |
| Terrain | Candidate gameplay/surface/topology concept beyond material lookup and tileset decoration | Low; unresolved |
| Map Definition | Authored Map record and its referenced assets/policies before runtime resolution | High; useful boundary |
| Renderable bundle | Engine-owned resolved presentation fact consumed by a renderer or editor | High; current implementation |
| Geometry profile | Consumer-specific visibility/mesh presentation policy such as `play` or `authoring` | High; current implementation |

St. Maria may remain one Map even if internal districts are introduced. A district name is not, by itself, evidence for a new Map boundary.

The two owner decisions represented here are **Ratified owner direction**: Location policy inheritance may recurse through multiple semantic hierarchy levels with descendant override/interruption, and Map layout production is compositional so fixed and independently generated scopes may coexist. This does not settle Area representation, Area versus Region, zone membership, Terrain, connector schemas, prefab serialization, or inheritance mechanics.

## 18. Things explicitly not yet decided

This audit does not decide:

- whether `safe` and layout-production mode should become separate fields, only that they should not be assumed equivalent;
- whether Area and Region are separate concepts;
- the exact Area representation, including whether multiple generated scopes are represented as Areas, scopes, fragments, or another vocabulary;
- whether generated zones become Area membership or remain runtime predicate tags;
- whether Terrain is gameplay topology, surface material, biome, or a future composition layer;
- whether anchors should become reusable Map fragments, fixture prefabs, or a distinct structure asset;
- the exact Location serialization, field-by-field inheritance vocabulary, merge mechanics, reset/null syntax, validation diagnostics, and Studio UI;
- whether current grid topology remains the canonical authored representation for every future room/door/height case;
- whether the 3D workspace spike becomes the main Map editor;
- whether the editor becomes 3D-first, 2D-plus-3D, or retains 2D as the primary authoring view;
- whether there should be one continuous camera, two discrete modes, or another camera model;
- whether a full tileset geometry asset authoring tool belongs in Studio or in asset pre-press tooling;
- whether a scene graph may exist as a presentation representation, provided it is not the sole gameplay authority;
- any production schema, migration, renderer rewrite, Map editor rewrite, or Tileset Studio rewrite.

## 19. Smallest useful prototypes / follow-up issues

The following are candidate follow-up scopes, not implementation commitments from this audit.

### Prototype A: compositional Map scope inspection

Acceptance criteria:

- choose a Map and explicit seeds/policies for its generated scopes;
- resolve through the real engine path;
- show fixed structure, generated Area/scope A, fixed landmark, generated Area/scope B with different rules, and other authored structure as distinct semantic sources;
- show authored anchors, generated rooms/corridors, openings, stairs, generated zones, features, and lights for each generated scope;
- select a semantic cell and show source/provenance plus resolved geometry bundle material;
- save/reload the same instance and confirm deterministic result;
- no browser-side generator or geometry compiler.

### Prototype B: reusable anchor with connectors

Acceptance criteria:

- one reusable authored structure has stable identity, layout, two typed doorway ports, and a deterministic placement;
- it can be used in one fixed and one generated Map;
- event and fixture provenance survives placement;
- gameplay remains grid-based;
- validator, editor writer, bundle, and save/load all agree.

### Prototype C: resolved Tileset surface inspector

Acceptance criteria:

- inspect one resolved wall/floor/ceiling variant with albedo, height, glow, material, scale, operation, mesh density, and triangle budget;
- preview through the engine-owned bundle and `authoring` profile;
- show source variant and map-cell provenance;
- expose one guided write and round-trip it through storage and G1;
- present failure diagnostics for invalid geometry inputs.

### Prototype D: Location policy proof

Acceptance criteria:

- create The Gate → First Stratum → Floor 2 as Location/Location/Map semantic nodes, with one inherited policy;
- parent two Maps without forcing either Map to change its runtime spatial boundary;
- show recursive effective defaults, explicit descendant override, and explicit interruption/reset behavior without choosing their final syntax;
- show provenance for each effective value across the complete chain;
- validate ordering, identity, storage tokens, save behavior, and Studio round-trip;
- keep geometry and gameplay authority on Maps/instances.

These prototypes should be kept small and compared with a fixed rubric derived from [#277](https://github.com/JosephSerUSP/Second-Rite/issues/277) and [#322](https://github.com/JosephSerUSP/Second-Rite/pull/322): authorability, validation, deterministic resolution, semantic selection, runtime parity, generated dungeons, and save/load. No prototype should be allowed to silently become a schema decision.

## Evidence map

- [`docs/SPEC.md`](../SPEC.md): current data and runtime contracts, including openings, overrides, tileset pools, predicates, features, and renderer constraints.
- [`docs/ENGINE-STATE.md`](../ENGINE-STATE.md): generated current-state authority and gate contract.
- [`docs/design/authored-data-storage.md`](../design/contracts/authored-data-storage.md): storage ownership and fragment/registry rules.
- [`docs/design/tileset-and-events-redesign.md`](../design/studio/tileset-and-events-redesign.md): design intent for structure, decoration, overrides, pools, fixtures, and zones.
- [`docs/design/editor-renderable-bundle.md`](../design/studio/editor-renderable-bundle.md): editor/runtime renderable-bundle contract.
- [`docs/design/image-authored-geometry.md`](../design/runtime/rendering/image-authored-geometry.md): design intent for height-field and geometry asset authoring.
- [`docs/design/renderer-3d-roadmap.md`](../design/runtime/rendering/renderer-3d-roadmap.md): renderer constraints and model/tileset direction.
- [`docs/reports/editor-3d-workspace-spike-2026-08-10.md`](editor-3d-workspace-spike-2026-08-10.md): spike findings; not implementation status.
- [`engine/exploration.lua`](../../engine/exploration.lua): live generation, map loading, caching, fixtures, zones, events, and lighting.
- [`engine/fixture_predicates.lua`](../../engine/fixture_predicates.lua): authored/generated zone predicate resolution.
- [`engine/tileset_resolver.lua`](../../engine/tileset_resolver.lua): base tileset plus sparse map override resolution.
- [`engine/geometry/visibility_profile.lua`](../../engine/geometry/visibility_profile.lua): play/authoring geometry profiles.
- [`presentation/map_renderable_bundle.lua`](../../presentation/map_renderable_bundle.lua): engine-owned resolved renderable bundle.
- [`tools/editor/js/map-editor.js`](../../tools/editor/js/map-editor.js): current Map tree, properties, canvas, anchors, lights, and save surface.
- [`tools/editor/js/tileset-editor.js`](../../tools/editor/js/tileset-editor.js): current Tileset Studio pool and variant surface.
- [`data/authored_storage_manifest.json`](../../data/authored_storage_manifest.json): live resource storage classification.
