# Source → Semantic → Compiled Boundary

Status: **Accepted**

Owner decision: 2026-08-16

Tracking decision: #666

Production follow-ups: #667, #668, #669

## Decision

Thestra adopts one shared architectural rule across authored Project data, imported 3D models, and environmental visual resources:

> **Source formats are for authors. Semantic resources are for Thestra. Compiled representations are for consumers.**

This is an ownership boundary, not a mandate for one universal compiler, file format, cache, or schema.

The source side should optimize for authorability, readability, provenance, ordinary external tools, multimodal inspection, and precise source diagnostics. The semantic side should express Thestra-owned meaning without leaking source-format accidents. The compiled side should optimize for the needs of the player, Studio preview, exporters, and other consumers without turning those optimizations back into authored ontology.

Derived artifacts are disposable. Where persisted or cached, they should be reproducible from source identity + relevant compile/import settings + compiler/version identity, with sufficient provenance to map diagnostics back to authored sources.

## Why this decision exists

The build/borrow/bridge/generate audit found the same category error in several otherwise unrelated systems:

- the LÖVE player understood authored fragment/index/registry storage because source representation crossed the Project runtime boundary;
- LÖVE and Studio independently interpreted OBJ/MTL source assets because source interchange crossed the renderer boundary;
- Tileset authoring was constrained by one-atlas runtime packing even though the renderer already resolved richer visual semantics.

The experiments showed that none of those source representations need to remain consumer ontology.

The chosen direction is therefore not "compile everything because compilation is good." It is narrower:

> Stop source/interchange/packing vocabulary at the last boundary where it is meaningful.

Thestra continues to own the unusual semantics inside that boundary. Commodity interchange and packing mechanisms remain implementation details around it.

---

## Decision A — Project data compiles to semantic runtime resources

Accepted production direction: **Candidate A+** from #632/#638, implemented by #667.

Readable authored Project storage may continue to use representations chosen for authoring needs, including monoliths, ordered fragments, keyed registries, semantic-config modules, and future source-side forms.

After exact Project + pinned RTP/package/default resolution, a neutral compiler produces one resolved runtime representation per semantic resource plus provenance/source mapping.

Conceptually:

```text
Project authoring source
    |
    +--> source validation / migrations / Studio
    |
    v
Project + pinned RTP/package resolution
    |
    v
source -> runtime projection
    |
    +--> data/units.json
    +--> data/maps.json
    +--> data/flows.json
    +--> data/scenes.json
    +--> data/tilesets.json
    +--> provenance/source mapping
    |
    v
ordinary player loader
```

### Consequences

- The final player should not know whether Units were authored as ordered fragments or Tilesets as a keyed registry.
- Physical authored-storage mode is not gameplay/runtime state.
- Source-only modules or records are explicit compiler projection rules rather than hidden loader policy.
- Test Play, export, and unsaved Studio preview should converge on the same semantic compiler boundary.
- Unsaved Studio preview may compile transient authored state; it must not require an authoring save merely to obtain runtime truth.
- Source validation and migration tools remain source-aware where that awareness is genuinely required.
- After migration, do not preserve indefinite physical-runtime dual readers merely for compatibility.

### Rejected alternative

One universal combined runtime database blob is not chosen merely for compactness. Per-semantic-resource output preserves inspection, diffability, independent cache/invalidation units, and existing semantic boundaries. A combined bundle would need concrete profiling evidence before replacing that granularity.

---

## Decision B — 3D source formats normalize into a Thestra Model

Accepted production direction: #639 evidence feeding #668.

**glTF/GLB is the preferred rich import/interchange membrane.** OBJ remains a supported source/import path during migration and compatibility work.

Neither LÖVE nor Studio should independently grow into a general-purpose glTF scene/material runtime. External formats are imported, validated, normalized, and projected into a deliberately small Thestra-owned Model representation and compiled Model Bundle shared by consumers.

Conceptually:

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

### Model ownership

A Model owns geometry and, when applicable:

- stable Thestra model identity;
- hierarchy / skin semantics required by the runtime;
- named semantic animation clips;
- material slot identities;
- import provenance.

A Model does **not** automatically inherit a generic source-format material graph.

Material slots resolve into Thestra Surface identities from Decision C.

### Import recipe

Production import needs a deterministic recipe or equivalent authored metadata capable of separating source vocabulary from Thestra vocabulary, for example:

- source asset identity;
- scale / basis policy;
- source material slot -> Surface mapping;
- source clip name -> semantic clip identity mapping;
- explicit bake/degradation choices.

Therefore an external clip called `WalkCycle`, `mixamo.com|Layer0`, or similar does not become permanent Event authoring vocabulary merely because a source tool emitted it.

### Explicitly deferred

The experimental `thestra-static-model-spike` schema is not production authority. The following must be earned by real consumers:

- final Model Bundle JSON/binary layout;
- target-space inverse-bind / skin-matrix convention;
- influence pruning/renormalization policy;
- treatment of cubic animation, morphs, and unsupported glTF extensions;
- final import recipe syntax.

OBJ runtime parsing may disappear only after equivalent OBJ import remains available and representative current assets have migrated successfully.

---

## Decision C — Surface Library + Tileset Palette

Accepted production direction: strongest candidate from #558/#559/#560/#561, implemented by #669.

### Surface

A **Surface** owns visual/material meaning. It may reference semantic source properties such as:

- albedo;
- height / relief;
- emission;
- bounded semantic masks/layers;
- per-property visual animation.

One authored image should have one visible semantic meaning by default. Runtime channel packing is allowed as derived optimization; arbitrary authored RGBA channel ontology is not the default source contract.

Surface must remain narrow. It is not the universal home for arbitrary topology, fixtures, Model hierarchy, or every future visual concept.

### Tileset

Keep the author-facing word **Tileset**.

A Tileset is no longer semantically "one atlas." It is an **environment palette** assigning reusable Surface identities to weighted semantic roles such as walls, floors, ceilings, doors, and appropriate environmental/decorative vocabulary.

Legacy atlas regions remain valid Surface source descriptors and migration inputs. They stop being the semantic identity of the environment merely because the current renderer happens to pack them together.

### Structural Profile

Presentation-only structural shape is independent of Surface appearance.

Examples include:

- square;
- chamfer;
- low-segment round with explicit radius/segment policy;
- exceptional authored junction/model override where procedural profiles are insufficient.

Logical Map topology and collision remain authoritative. A visual profile must not silently invent a second traversal ontology.

### Reuse and packing

Reuse happens primarily at semantic Surface and palette-role boundaries, not through a general whole-Tileset inheritance graph.

The #559 real-runtime proof showed that independent dungeon and Bellroot visual families can be assembled semantically and packed into the unchanged current single-atlas renderer. Therefore:

> one runtime atlas does not imply one authored tileset image/family.

Runtime atlas/array/channel packing belongs after semantic composition.

### Deferred

Zone-local palette policy is not ratified. Shared-boundary ownership should not be invented merely to enable texture variation; local palette semantics need an independent Map/generation reason before becoming ontology.

Animated height remains animated geometry and is not implied by ordinary visual-property animation.

---

## Shared relationship between Models and Surfaces

The Model and Surface decisions intentionally converge without collapsing geometry and material semantics into one resource.

Conceptually:

```text
GLB material/source slot "Dress"
              |
              v
Model material slot "dress"
              |
              v
Surface "agnes_dress"
```

A creature Model, an item Model, and a wall Surface can therefore share the same bounded visual/material vocabulary where it is genuinely the same semantic concept, without pretending their geometry is the same kind of resource.

This avoids both extremes:

- four unrelated implementations of albedo/emission/material-layer semantics;
- one universal Unity-like Model/Material/Shader graph that absorbs Thestra's simpler authored vocabulary.

---

## What this decision rejects

This decision explicitly rejects the following as default architectural directions:

- player awareness of authored fragment/index/registry storage;
- independently parsing rich source 3D formats in both LÖVE and Studio;
- making glTF itself the runtime Model ontology;
- generic PBR/material-graph inheritance merely because glTF contains it;
- whole-Tileset inheritance/import graphs as the primary reuse mechanism;
- authored source organization dictated by current GPU/atlas/channel packing;
- animated height being implied by animated albedo/emission;
- structural presentation geometry silently changing Map collision/topology;
- preserving experimental dual paths indefinitely after a production migration is ratified.

## Evidence retained, not merged wholesale

The investigation branches remain valuable because they isolate hypotheses and contain executable gauntlets. They should not be merged merely to preserve their conclusions:

- Project runtime data: #632, draft #638;
- Model import: #639, merged census #652, drafts #655/#658/#659/#660;
- Surface/Tileset format: #558, drafts #559/#560/#561.

Production work starts from current `main` under #667, #668, and #669 and carries forward the proven invariants rather than blindly copying spike schemas.

## Review rule for future systems

When a new format or subsystem appears, ask three questions in order:

1. **What is merely source/interchange/packing vocabulary?**
2. **What meaning does Thestra actually own?**
3. **What representation does the consumer actually need?**

If the same representation happens to answer all three, keep it simple. If not, normalize at the semantic boundary instead of teaching every consumer the source format.
