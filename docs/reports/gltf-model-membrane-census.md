# glTF / Model-Bundle Membrane Census

**Issue:** #639  
**Date:** 2026-08-16  
**Scope:** current model ownership and interchange seams only. This report does **not** select a production source format, remove OBJ, or decide the #558 Surface/material ontology.

## Executive finding

Thestra does **not** need to invent a new renderer-neutral static mesh representation before experimenting with glTF.

That representation already exists in `engine/geometry/model.lua`:

```text
source producer
    |
    v
engine.geometry.model
  groups -> material identity + neutral CPU vertices
  bounds
  vertexCount
    |
    v
presentation.mesh.finalize
  GPU mesh / texture / material attachment
```

`engine.geometry.model` is already shared by image-authored geometry and the runtime OBJ producer. It is Z-up, uses one map cell as one world unit, knows nothing about `love.graphics`, textures, or GPU state, and expands triangles into a deterministic 12-float vertex record.

The important duplication therefore lives **before** this seam:

```text
runtime                    Studio
------                     ------
custom Lua OBJ/MTL         Three OBJLoader/MTLLoader
      \                     /
       \                   /
        semantically similar source assets
```

For future glTF/GLB support, the strongest hypothesis remains:

```text
Blender / generators / external tools
                 |
              glTF/GLB
                 |
       import-time normalization
                 |
          Thestra Model Bundle
           /             \
        LÖVE            Studio
```

The first implementation spike should extend the existing neutral model seam rather than introduce a second parallel static-geometry ontology.

---

## Current ownership census

| Current behavior | Location | Classification | Preserve? | glTF implication |
|---|---|---|---|---|
| Z-up world coordinates | `engine/geometry/model.lua` | **Thestra semantic/runtime truth** | Yes | Every importer converts once at the boundary. |
| One world unit = one map cell | `engine/geometry/model.lua` | **Thestra semantic/runtime truth** | Yes | Source meters/units must normalize explicitly. |
| Material-grouped static triangle geometry | `engine/geometry/model.lua` | **Thestra neutral model truth** | Yes for static mesh core | Natural target for static glTF normalization. |
| Flat 12-float runtime-neutral vertex record | `engine/geometry/model.lua` | **Current normalized representation** | Preserve initially; may evolve for skin/index efficiency | Do not redesign merely because glTF is indexed. |
| Missing-normal generation / degenerate-face rejection | `engine/geometry/model.lua` | **Thestra geometry policy** | Yes | Importer should fail or normalize before bundle publication. |
| OBJ Y-up -> Thestra Z-up conversion | `presentation/obj_model.lua` | **Source-format adapter** | Behavior yes; location/source vocabulary no | Coordinate conversion should move to one explicit import normalization rule. |
| OBJ UV V flip | `presentation/obj_model.lua` | **Source-format adapter** | Preserve only as needed for equivalent visual semantics | glTF has its own texture-coordinate convention; do not cargo-cult the OBJ flip. |
| OBJ triangulation / negative indices | `presentation/obj_model.lua` | **Commodity source parsing** | No need to own long term | A mature importer should own source syntax. |
| `mtllib` / `usemtl` | `presentation/obj_model.lua` | **OBJ/MTL interchange artifact** | Compatibility only | Must not leak into Model Bundle. |
| MTL `Kd` / `map_Kd` | `presentation/obj_model.lua` | **Source material adapter** | Meaning maps into Thestra color/albedo | Translate supported source material properties into Thestra material references. |
| standard MTL sphere `refl` mapped to retro sheen | `presentation/obj_model.lua` | **Thestra material policy expressed through source syntax** | Yes, semantics matter | Do not expect glTF PBR to replace this. Need an explicit Thestra material mapping/extension path. |
| custom MTL `pass <uvSource> <blend> <strength> <path>` | `presentation/obj_model.lua` | **Thestra-owned material semantics embedded in MTL** | Yes | Strong evidence that persisted runtime material truth must be Thestra vocabulary, not raw glTF material vocabulary. |
| GPU mesh creation / texture acquisition / nearest filtering | `presentation/mesh.lua` | **Renderer implementation detail** | Yes as presentation behavior, not bundle schema | Importer must remain graphics-free. |
| `texturePath` provenance on finalized groups | `presentation/mesh.lua` | **Useful cross-boundary provenance** | Yes | Model Bundle should retain source/material provenance without requiring a live texture. |
| overlay-pass texture binding | `presentation/mesh.lua` | **Thestra presentation/material policy** | Yes | Bundle/material contract needs semantic pass references, not source-format sampler objects. |
| item fallback question-mark model | `presentation/item_model_view.lua` | **Presentation/product policy** | Yes | Fallback should resolve a Thestra model identity; it should not care which source format produced it. |
| item model cache keyed by source path | `presentation/item_model_view.lua` | **Current implementation / compatibility detail** | Revisit | Compiled bundle identity/hash is a stronger long-term cache key. |
| item `model` fields constrained to `.obj` | validator / existing item contract | **Compatibility surface and source-format leak** | Preserve while OBJ remains first-class | Eventually validate a Thestra model asset identity, not an interchange extension. Owner review required before migration. |
| Studio `OBJLoader` + `MTLLoader` preview | `tools/editor/js/model-picker.js` | **Authoring implementation detail** | Not as final truth | Final architecture should preview normalized Model Bundle semantics; source-GLB preview is acceptable only as import diagnostics. |
| Studio model stats from Three object graph | `model-picker.js` | **Authoring diagnostic convenience** | Useful | Import diagnostics may stay richer than runtime bundle, but runtime identity comes from normalization output. |
| runtime renderable bundle calls `obj_model.load` for `spec.model` | `presentation/map_renderable_bundle.lua` | **Current source-parser dependency in export/inspection path** | Needs compatibility adapter | Bundle/export should ultimately consume normalized model semantics rather than reparsing authoring source. |
| procedural model census requires `.obj` and hashes OBJ/MTL dependencies | `engine/model_census_review.lua` | **Verification harness coupled to current source format** | Preserve test intent, not extension | Convert census from “is OBJ” to “resolves to canonical Thestra model” when production migration happens. |

---

## Existing neutral static-model contract

`engine/geometry/model.lua` already provides the static core a future Model Bundle needs:

```text
Model
  groups[]
    material        semantic material identity
    vertices[]      x y z u v nx ny nz r g b a
  vertexCount
  bounds
```

Properties already earned by this contract:

- deterministic CPU-side geometry;
- renderer independence;
- Z-up / map-cell coordinates;
- material grouping;
- generated normals where source normals are absent;
- hard failure for degenerate triangles;
- shared consumption by multiple geometry producers;
- graphics materialization only after the neutral representation exists.

### What it does *not* yet represent

The #639 animated-character gauntlet requires semantics beyond this static contract:

- named nodes / hierarchy;
- skins and bone identity;
- inverse bind transforms;
- per-vertex joints and weights;
- named animation clips;
- translation / rotation / scale animation channels;
- clip duration / interpolation policy;
- potentially indices, if retaining indexed source geometry is materially useful.

These should be added as a **versioned extension around the existing static mesh core**, not by turning the runtime into a generic glTF scene graph.

---

## Candidate Model Bundle v0 shape

This is a pressure-test vocabulary, **not a frozen schema**.

```jsonc
{
  "version": 0,
  "source": {
    "kind": "gltf",
    "path": "assets/models/people/agnes.glb",
    "hash": "..."
  },
  "coordinate": {
    "up": "z",
    "unit": "mapCell"
  },
  "geometry": {
    "groups": [
      {
        "id": "body",
        "material": "agnes_body",
        "vertices": "runtime-oriented vertex stream"
      }
    ],
    "bounds": {}
  },
  "rig": {
    "nodes": [],
    "skins": []
  },
  "clips": [
    { "id": "idle", "duration": 1.2, "channels": [] },
    { "id": "walk", "duration": 0.7, "channels": [] }
  ],
  "materials": [
    { "id": "agnes_body", "surface": "...Thestra material/surface identity..." }
  ]
}
```

Key boundary rules:

1. `source` is provenance, not runtime ontology.
2. source node/material names may inform import diagnostics but do not become Event command vocabulary automatically.
3. `clips[].id` is the semantic bridge animation controllers may reference.
4. materials point toward the resolved Thestra visual/material contract decided with #558; the bundle does not embed an unrestricted glTF PBR graph.
5. a static model may omit `rig` and `clips` entirely and remain close to today's neutral geometry model.

---

## Material-boundary finding

The current OBJ path is deceptively more than an OBJ parser.

The custom MTL `pass` directive and sphere-reflection handling carry Thestra's retro material behavior through MTL syntax. That means a source-format migration cannot be evaluated by asking only whether a glTF loader preserves triangles, UVs and `baseColorTexture`.

The actual membrane needs to distinguish:

### External-source material facts

Examples:

- base color / albedo texture;
- emissive texture or factor when deliberately supported;
- double-sided intent when relevant;
- named source material for diagnostics/provenance.

### Thestra material facts

Examples:

- retro overlay passes;
- blend operation;
- UV source such as sphere mapping;
- pass strength;
- nearest-filter / retro sampling policy;
- eventual #558 Surface identity and semantic source maps.

The importer may map supported source facts to Thestra facts. Unsupported PBR features must produce an explicit diagnostic or a documented degradation. They must not silently expand the player renderer into a generic PBR engine.

---

## Current dual-parser problem

Studio's `model-picker.js` explicitly uses Three's OBJ/MTL loaders as an authoring preview and warns that LÖVE remains authoritative for presentation. This is a sensible short-term architecture, but it becomes dangerous for animated GLB because hierarchy, skin and animation interpretation are much richer than static OBJ.

The production target should therefore **not** be:

```text
Studio -> Three GLTFLoader -> source scene graph
LÖVE   -> independent Lua glTF parser -> source scene graph
```

It should be:

```text
                 import tool
source GLB --------------------------> canonical bundle
                                          |
                              +-----------+-----------+
                              |                       |
                           Studio                    LÖVE
                     authoring preview         runtime presentation
```

A source-scene preview remains useful inside an importer inspector for debugging why a source failed normalization. It is not persisted game truth.

---

## Import-tool hypothesis

A Node-side glTF normalizer is a strong fit because model import is an authoring/build operation, not frame-time gameplay.

The spike should require the chosen external library to own commodity glTF mechanics:

- GLB/glTF parsing;
- accessors / buffers / indices;
- node transforms;
- skin structures;
- animation channel decoding;
- extension-aware validation where supported.

Thestra owns the normalization rules:

- coordinate conversion;
- map-cell scale;
- static mesh flattening/grouping;
- allowed material projection;
- semantic clip names;
- runtime-oriented skin/animation representation;
- unsupported-feature policy;
- source hash/provenance;
- deterministic bundle serialization.

`@gltf-transform/core` is a suitable candidate for the spike because it is an authoring-side glTF 2.0 read/write SDK rather than a renderer. Dependency selection and pinning should occur on the implementation branch, after the concurrent package-file work in #649 is settled.

---

## Compatibility surfaces that block an immediate OBJ removal

OBJ is currently more than a replaceable implementation detail because several live contracts explicitly name the extension or parser:

- item model validation;
- item fallback model path;
- model picker source enumeration/loading;
- runtime `obj_model.load` call sites;
- Renderable Bundle model placements;
- model-census validation/hash collection;
- tests asserting OBJ-specific behavior;
- existing authored `model` values.

Therefore the safe migration sequence is additive:

1. establish canonical Model Bundle semantics;
2. normalize one static OBJ fixture into it without changing current runtime behavior;
3. normalize equivalent GLB into the same semantics;
4. add hierarchy/skin/clip extensions using a neutral character fixture;
5. make Studio preview the normalized semantics in the spike;
6. prove LÖVE consumes the same normalized semantics;
7. only then decide whether authored `model` points at source assets, compiled bundles, or a source-format-neutral model resource;
8. owner review before `.obj` ceases to be a first-class source/runtime path.

---

## Spike gauntlet refinement

The #639 gauntlet should test these properties independently so one attractive character does not conceal a broken membrane.

### Static equivalence pair

Author the same simple low-poly prop as OBJ/MTL and GLB.

Mechanical assertions:

- same Thestra-space bounds within tolerance;
- same triangle count after normalization;
- same UV orientation;
- same material-group identity after source-to-Thestra mapping;
- deterministic serialized bundle hash across repeated imports;
- source provenance differs while normalized geometry does not materially differ.

### Transform fixture

Include a parent node with rotation/translation and a child mesh with non-uniform scale.

Assert the normalization policy explicitly: either bake static node transforms into geometry or retain a deliberately supported node transform. Do not leave the answer dependent on whichever library happened to traverse the graph.

### Character fixture

One low-poly skinned character with exactly two required named clips initially:

- `idle`;
- `walk`.

Mechanical assertions:

- stable bone/node ids;
- normalized bind pose;
- deterministic weights/order;
- clip names survive without exposing source-file scene traversal to Event authoring;
- playback reaches the same sampled pose at pinned timestamps in import-side verification and LÖVE-side bundle consumption.

### Material fixture

Include:

- base-color texture;
- emissive property that has an intentional Thestra mapping;
- one deliberately unsupported metallic/roughness/transmission-style property.

The unsupported property must yield a named diagnostic or an explicit documented degradation. Silent feature loss is a failing fixture.

### Naming/provenance fixture

Use a source path containing spaces and Unicode. The compiled identity must remain portable and provenance must survive normalization without making local absolute paths game data.

---

## Decisions intentionally deferred to owner / #558

The census provides evidence but does **not** have enough authority to decide:

- whether `model` eventually points at a source asset, a compiled artifact, or a first-class Model resource id;
- the final Surface/material resource schema;
- whether model-local material overrides live inside Model, Surface, or another resource;
- whether indexed geometry is worth introducing into the runtime-neutral mesh contract;
- the final skeleton/clip JSON/binary serialization layout;
- when OBJ may cease to be a direct runtime source path.

Those are production-ontology decisions. The next no-owner-input step is a reversible importer spike against neutral fixtures, not migration of authored Projects.

---

## Recommended next implementation slice

After #649's package dependency work lands or otherwise settles:

1. pin an authoring-only glTF SDK on the #639 spike branch;
2. add neutral generated fixtures under a lab/test fixture root, never Second Gate authored content;
3. implement `glTF -> static Thestra model` normalization first;
4. serialize the result deterministically;
5. compare it mechanically against an equivalent OBJ-derived neutral model;
6. then extend the bundle with transform/skin/clip semantics;
7. keep current OBJ runtime path untouched throughout the spike.

That sequence tests the membrane rather than prematurely shipping a new model format.
