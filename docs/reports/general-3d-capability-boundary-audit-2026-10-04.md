# General 3D capability boundary audit — 2026-10-04

Baseline: `main@6a3f3358f4b9c2d8dd382d59b9821bd98978c7a2`

## Owner correction / audit question

Recent 3D work has often been exercised through St. Maria rooms, exteriors, town traversal and environment baking. That production pressure is useful evidence, but it must not become the ontology of Thestra's 3D layer.

The architectural target is:

> **Improve general 3D capability and expressability. Environments are one consumer of that capability, not the category that owns it.**

This audit asks where the repository already honors that rule, where specialization is legitimate, and where a first use case has leaked into an abstraction boundary.

The correction is **not** to rename every `environment` noun to a more universal noun. An environment package really does have environment/composition-specific semantics. Turning an environment-shaped schema into `spatial_package` would merely hide the coupling. The goal is to move reusable capability *below* such adapters.

---

## Executive conclusion

The repository is not missing a general 3D direction. In fact, the accepted architecture already contains most of the right boundaries:

- `docs/design/contracts/source-semantic-compiled-boundary.md` says external OBJ/GLB/Blender/generated sources normalize into a Thestra-owned **Model** and compiled **Model Bundle** shared by LÖVE and Studio;
- `tools/blender/second_rite_asset_core.py` is already a general Blender infrastructure layer used beyond environments;
- `engine.geometry.model` + `presentation.mesh` are renderer-neutral/model-neutral lower layers;
- `WorldCamera` is already a general resolved camera contract;
- Studio's spatial-interaction work (#1126) is explicitly intended for Events, anchors, camera targets, paths, regions and later spatial objects, not only Walk Profile.

The main drift is in the **middle layer**:

1. Model Bundle exists, but ordinary world placement still principally consumes direct OBJ paths.
2. Environment packages carry a raw render OBJ/MTL/atlas path and enter runtime through town-specific session state.
3. ordinary Event/world model export still expresses placement primarily as `model path + map X/Y`, rather than a reusable transformable Model instance.
4. source-authority, bake, render-quality and provenance work has become strongest in the environment workflow, while equivalent general Model/world-prop paths remain less connected to the accepted Model/Surface boundary.

Therefore the next 3D work should **connect and deepen the general Model / Model-instance / Surface / transform substrate**, then make environment authoring compile onto it where practical. Do not make Environment the general substrate.

---

# 1. Existing architecture that is already correct

## 1.1 Source → semantic → compiled is explicitly general

The accepted contract states:

```text
OBJ / GLB / Blender / generated sources
                |
                v
       deterministic importer
     validate / normalize / diagnose
                |
                v
          authored Model identity
                |
                v
       compiled Thestra Model Bundle
           /                 \
        LÖVE                 Studio
```

It also explicitly says this is **not** a mandate for one universal compiler, schema or cache.

That distinction should remain the anchor for this correction:

- authoring formats may stay plural;
- environment production may stay specialized;
- runtime/editor consumers should converge on reusable semantic/compiled 3D capability where convergence is real.

## 1.2 The Blender low-level core is already general

`docs/asset-pipeline/BLENDER_CORE.md` describes `second_rite_asset_core.py` as the canonical infrastructure for:

- scene cleanup;
- collections;
- selection preservation;
- local transforms;
- materials;
- modifiers;
- metadata;
- bmesh objects;
- bounds;
- OBJ export.

It is used by item models and world props, not only environment scenes. This is the correct direction: Blender-specific mechanics live below asset-family workflows.

Do **not** fold this layer upward into an environment API.

## 1.3 A production-shaped Model Bundle already exists

`tools/model-import/model-contract.js` already defines:

- stable `modelId`;
- OBJ or glTF source identity;
- normalization into Z-up/map-cell units;
- semantic material-slot IDs;
- optional Surface identity per slot;
- source hash;
- recipe hash / compiler identity;
- normalized geometry groups and bounds.

`runtime/presentation/model_bundle.lua` validates the same static bundle and converts it into the neutral CPU model shape expected by renderer code.

This is not yet the complete #668 target (hierarchy/animation remain to be earned), but it is already a much better home for general 3D geometry semantics than an environment package.

## 1.4 The renderer already has reusable lower primitives

`presentation.obj_model` describes itself as one producer of `engine.geometry.model`'s neutral representation, with image-authored geometry as another producer. `presentation.mesh` then owns material binding, texture caching, vertex format and GPU upload.

Likewise, `viewport_3d`'s environment render mesh is ultimately queued through the same placed-model machinery used by other model placements.

This is important: the renderer does **not** need to be rebuilt around a new universal `Environment` abstraction. The generic seam is already lower.

---

# 2. Specialization that is legitimate and should remain

Not every `environment`, `map`, `walk`, or `town` noun is architectural leakage.

The following are domain semantics and should remain specialized unless a second use case proves a genuinely shared primitive:

### Environment package composition

The current package owns environment/composition facts such as:

- render mesh;
- collision mesh;
- bounds;
- named anchors;
- baked-lighting status;
- optional layered pre-render data;
- player projection facts for that pre-render.

Those facts do not describe an arbitrary sword, monster Model or prop. `environment_package.lua` should therefore **remain an environment adapter**, not be globally renamed to `spatial_package`.

### Traversal

`bounded_lane`, walk profiles, grid topology, collision meshes and future nav providers are gameplay/spatial capabilities. A Model must not become a traversal ontology simply because it has geometry.

### Bake strategy

Selected-to-active Cycles baking, EEVEE projection baking, pre-render slicing, receiver/source roles and environment-atlas construction are production workflows. They can share low-level render/bake primitives without pretending every Model needs to be "an environment bake".

### Map source families

#695's principle remains correct: plural at the authoring boundary, shared only where consumers benefit. Grid Dungeon Map, layered tile map and freeform composition need not become one universal authoring schema.

---

# 3. First-use-case leakage found on current main

## F1 — Model Bundle is not yet the ordinary world-model consumption path

The repository has a Model Bundle reader and importer, but `viewport_3d` still imports `presentation.obj_model` inside placed-model materialization, and the normal model spec is a source path.

`meshSource(spec)` identifies a model as:

```text
obj:<path>
```

not as a stable semantic Model identity / compiled Model resource.

This leaves the accepted source/semantic/compiled boundary beside the main world renderer instead of underneath it.

### Consequence

General model improvements risk landing in parallel places:

- direct OBJ parser;
- Model Bundle importer/adapter;
- environment exporter;
- Studio model preview.

That is exactly the fragmentation the accepted #666/#668 direction was meant to stop.

### Direction

Introduce one general runtime Model acquisition boundary. World placements ask for a Thestra Model / Model Bundle identity. OBJ remains an import/source compatibility path during migration, not the permanent semantic identity of a placed object.

---

## F2 — environment rendering is town-session-specific above an otherwise general model queue

`viewport_3d` checks:

```text
session.townTraversal.environment
```

for pre-render behavior, baked-lighting behavior and the environment render mesh.

The live render mesh is then converted to a plain `{ model = environment.renderMesh }` spec and sent through the ordinary placed-model queue.

This shows that the **drawing primitive is already general**, while ownership/plumbing above it is specialized.

### Consequence

A new authored 3D composition that is not a St. Maria bounded-lane town has no equally direct general composition path, despite using the same renderer primitives once it reaches them.

### Direction

Keep town/environment semantics in their adapter, but have the adapter emit ordinary resolved 3D instances/resources into a general world/scene composition boundary. Town should not be a privileged doorway into the renderer.

---

## F3 — Event/world model placement is still weaker than the desired general 3D instance concept

`map_renderable_bundle.lua` currently exports an Event model approximately as:

```lua
{ model = placement.model }, placement.x, placement.y, "x"
```

That is useful for Second Gate's grid-shaped Event semantics, but it is not a general model-instance contract.

A reusable 3D instance eventually needs, as earned by concrete use cases:

- Model identity;
- translation in XYZ;
- orientation;
- scale;
- stable instance identity/provenance;
- optional parent/hierarchy binding where required;
- Surface/material overrides where semantically legitimate;
- visibility/presentation policy where required.

The grid adapter can compile existing integer Event X/Y into such an instance without changing current authored Map semantics.

### Direction

Do not migrate every Event to arbitrary XYZ. Add a resolved **Model Instance / transform** representation below Map/Event source semantics, so grid Events, freeform placements and environment composition can converge *after* authoring.

---

## F4 — environment package material transport bypasses the newer Model/Surface direction

The current environment manifest directly requires:

- `renderMesh`;
- `materialLibrary`;
- `textureAtlas`.

That contract was useful and should not be broken casually, but it predates/skirts the accepted direction where Model material slots resolve to semantic Surfaces and runtime packing is derived.

### Direction

Treat environment package v1 as an adapter/compiled legacy product. Do **not** add new general material semantics to its MTL/atlas contract.

Once the general Model + Surface consumption path is production-proven, a future package revision may reference compiled Model/Surface products or emit the same resolved instance/bundle representation. That migration must be evidence-driven and need not happen before general consumers work.

---

## F5 — source authority is strong but asset-family-specific

Environment sources now have a detailed `environment-sources.json` authority/provenance system. Per-item Blender sources have a separate read-only compilation and hash discipline. World props have another staged build manifest.

The policies legitimately differ:

- adopted environment documents must not be regenerated;
- candidate environments have review-state rules;
- item sources compile read-only to products;
- generated world props may be recipe products.

The reusable primitive underneath them is not "Environment Source". It is closer to:

```text
source identity
+ source authority kind
+ read/write policy
+ compiler identity
+ product provenance
+ source hash / dependency evidence
```

### Direction

Do not replace the family registries with one giant source registry now. First extract common provenance/refusal/hash helpers where they are genuinely duplicated. Keep family policy adapters explicit.

---

## F6 — Blender render/bake quality has been generalized internally more than its public workflow language suggests

Recent EEVEE/Cycles work centralizes renderer settings, emissive-light reconstruction, fixture-light handling, projection baking and source-safe evaluation. These are useful capabilities.

Some entry points/documentation still describe them primarily through "environment rendering" because rooms/exteriors were their first production subjects.

### Direction

Low-level operations should be callable by any suitable Model/scene review workflow:

- configure renderer/quality;
- evaluate a source read-only;
- capture a camera/view;
- derive render-time emissive helpers;
- inspect material/geometry diagnostics;
- bake/project where a caller explicitly needs it.

The environment exporter can remain the high-level orchestration that supplies environment-specific receiver/source rules and package outputs.

---

## F7 — Studio already has the right interaction direction; future 3D objects should consume it

#1126 defines a reusable spatial interaction core with:

- semantic axes independent of Three.js internals;
- hover/selected/active state;
- modal transforms;
- constraints;
- confirm/cancel;
- transaction-shaped edits.

Walk Profile is explicitly the first consumer, not the ontology.

### Direction

The next general 3D Studio consumer should be a normal transformable Model instance / Event presentation, not another environment-only editing mode. That will prove the spatial core generalizes in the direction the owner actually wants.

---

# 4. Target layering

The desired architecture is approximately:

```text
AUTHORING / INTERCHANGE

Blender       GLB       OBJ       generated geometry
   \           |         |             /
    \          |         |            /
     +---- deterministic import / source evaluation ----+
                              |
                              v
SEMANTIC 3D RESOURCES

                Thestra Model
          geometry / hierarchy* / clips*
             material-slot identities
                       |
                       +----> Thestra Surface identities
                       |
                       v
COMPILED / RESOLVED 3D

                 Model Bundle
                       |
             Model Instance + Transform
              /          |           \
             /           |            \
        grid Event    freeform     environment
         adapter      placement      adapter
             \           |            /
              \          |           /
               +---- resolved scene/world ----+
                              |
                              v
                 shared renderer / Studio
```

`*` Hierarchy/animation are not required merely for diagram symmetry. They are added when real consumers earn them, under the Model contract rather than an environment contract.

Environment authoring then looks like:

```text
Blender environment source
  = composition of Models/materials/lights/guides/collision/anchors/etc.
                         |
                         v
             environment-specific compiler
                /                    \
   ordinary resolved 3D content      environment-only facts
   Model instances / Surfaces        collision / anchors / pre-render / traversal adapter
                \                    /
                 \                  /
                  runtime composition
```

The environment compiler may still flatten/bake for performance or visual reasons. Flattening is a **compiled optimization/product**, not the source ontology of all 3D.

---

# 5. Architectural rules for future 3D work

## Rule A — capability before content category

When a feature is requested through an environment use case, ask whether the operation itself is generic.

Examples:

| Requested through | Generic capability | Legitimate specialization |
|---|---|---|
| move a house mesh | transform Model instance | town transition meaning |
| edit material | Surface/material-slot binding | environment bake receiver role |
| parent lamp to fixture | hierarchy/attachment | light baking policy |
| select prop in Studio | semantic selection + transform gizmo | traversal profile edit mode |
| frame room | WorldCamera / camera record | room-review preset |
| inspect bounds | Model/instance bounds | environment playable bounds |
| bake room atlas | render/bake primitives | UV receiver/source/package contract |

## Rule B — adapters may specialize; primitives must not

A Map adapter may output Model instances.
An Environment adapter may output Model instances.
An Event adapter may output a Model instance.

The Model instance should not care which one emitted it.

## Rule C — no semantic rename as a substitute for extraction

Do not rename `environment_package` to `spatial_package` while retaining environment-only fields. Extract or consume actual reusable primitives first.

## Rule D — plural authoring remains allowed

General 3D capability does **not** mean one general authoring format. #695 remains correct: different map/environment families may have different authored grammars.

The convergence point should be the smallest useful consumer contract.

## Rule E — Blender is an authoring environment, not the runtime ontology

Blender may expose richer construction history than Thestra needs at runtime. Preserve authorable source, normalize what Thestra owns, and compile what consumers need.

## Rule F — Second Gate remains a pressure test, not the definition

A feature can be justified by Second Gate and still be implemented as a general Thestra primitive. Conversely, Thestra should not implement speculative engine-general complexity with no demonstrated consumer.

The target is **earned generality**, not environment special cases and not universal-engine maximalism.

---

# 6. Recommended implementation sequence

## R1 — Make Model Bundle the ordinary general model-consumption boundary

**Highest priority.** Continue #668 from its existing static implementation.

Prove one static Model Bundle through both real consumers:

- LÖVE world placement;
- Studio/Three world placement.

Then migrate one representative existing OBJ-backed Event/prop through it without changing visible output.

Required properties:

- stable Model identity instead of source-path identity at the resolved consumer boundary;
- material slots retained as semantic identities;
- source OBJ remains importable;
- no new environment dependency;
- no direct general-purpose glTF runtime parsing;
- current OBJ path can remain temporarily as explicit migration compatibility until representative assets move.

## R2 — Introduce a renderer-neutral Model Instance / Transform record

Add the smallest resolved placement contract needed by current cases:

```text
instance identity
model identity
translation XYZ
orientation
scale
provenance/source semantic owner
```

Do not require every field in authored Map JSON.

Adapters compile existing semantics:

```text
Grid Event x/y + grounding -> Model Instance transform
wall fixture orientation   -> Model Instance transform
town environment root      -> Model Instance transform
freeform future source     -> Model Instance transform
```

This is the key step that prevents `Event model`, `environment model`, `item preview model`, etc. from becoming separate render ontologies.

## R3 — Put environment live geometry on the same Model/instance path

Once R1/R2 are proven, have the live environment adapter emit the same resolved Model/instance representation.

Do **not** remove collision, anchor, prerender or traversal metadata from the environment package. Only stop its visual mesh from requiring a privileged renderer doorway.

A package-format revision is optional; an adapter can initially translate v1 into the new resolved representation.

## R4 — Make general Model instances the second Studio spatial-core consumer

After Walk Profile proves #1126, use the same semantic transform grammar for an ordinary Model instance/Event presentation:

- select;
- G move;
- semantic X/Y/Z constraints;
- rotate/scale only when their authoring contracts are defined;
- Inspector transform values;
- transaction/cancel semantics.

This directly tests that Studio's 3D workflow is becoming a general modeling/composition surface rather than a collection of feature-specific gizmos.

## R5 — Extract reusable Blender provenance/render helpers where actual duplication exists

Keep item/environment/world-prop policy separate, but consolidate shared operations such as:

- source-safe open/evaluate/no-save guards;
- dependency capture;
- compiler/product provenance records;
- render-quality setup;
- camera capture;
- material/geometry diagnostics.

Do not merge family registries merely for naming symmetry.

## R6 — Add hierarchy/animation through Model only when a real consumer requires it

The accepted Model design already reserves hierarchy/skin/clips. Finish those under #668 when a representative animated actor/prop is ready.

Do not add animation first to an `environment` object and later retrofit it onto Models.

---

# 7. Things this audit explicitly does **not** recommend

- no universal `SpatialObject` mega-schema;
- no rename-only `environment -> scene` migration;
- no replacement of specialized Map authoring formats with a scene graph;
- no conversion of current grid Event authored coordinates to arbitrary transforms;
- no requirement that every Blender object survive as a runtime node;
- no forced environment-package v2 before general Model consumers work;
- no deletion of the current environment source-authority system;
- no environment/actor renderer taxonomy merely because fake-pre-render work used those words;
- no speculative ECS/component system;
- no generic PBR graph;
- no Unity/Blender clone.

---

# 8. Audit classification of current surfaces

| Current surface | Classification | Action |
|---|---|---|
| `second_rite_asset_core.py` | **general primitive** | preserve/deepen |
| `engine.geometry.model` | **general primitive** | preserve |
| `presentation.mesh` | **general primitive** | preserve |
| Model import + Model Bundle | **general primitive, incompletely adopted** | make default consumer path |
| `WorldCamera` | **general primitive** | preserve/deepen |
| Studio #1126 spatial core | **general primitive** | prove with Model-instance consumer |
| `obj_model.lua` | **source/interchange adapter still in runtime** | migrate behind Model boundary over time |
| `environment_package.lua` | **specialized composition adapter** | keep specialized; stop growing generic semantics here |
| `environment-sources.json` | **specialized source-policy adapter** | keep; extract only genuinely common helpers |
| bounded-lane Walk Profile | **specialized traversal semantics** | keep; use general interaction core |
| pre-render slices | **specialized presentation product** | keep |
| EEVEE/Cycles setup helpers | **mostly reusable render capability** | expose below environment exporters |
| room/exterior exporters | **specialized compiler/orchestration** | keep; consume general primitives |
| Event model X/Y placement | **source semantic adapter** | compile to general Model Instance below Map layer |
| town live render mesh special session path | **adapter leakage** | translate to general resolved scene/model-instance path |

---

# 9. Decision

The recent environment-heavy work should be understood as **production pressure that exposed missing general 3D primitives**, not as a mandate for an environment-centric 3D pipeline.

The durable direction is:

> **Thestra owns Models, Surfaces, transforms/instances, cameras, render semantics and Studio spatial interaction as general 3D capabilities. Maps, Events, environments, traversal systems and bake workflows adapt or compose those capabilities according to their own semantics.**

The first implementation lane should therefore be Model Bundle consumption + a general resolved Model Instance/transform contract, not another environment-package feature.

Related: #666 #668 #695 #841 #1126 #1127.
