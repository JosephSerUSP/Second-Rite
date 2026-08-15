# Batch B item → editable Blender source migration

**Date:** 2026-08-15  
**Accepted materialization run:** GitHub Actions `31910193811`  
**Review artifact:** `9253449487` / `b-item-source-migration-review`

## Question

The earlier Batch-B experiment proved that a polygonal-fabrication vocabulary was useful for item models whose identity lives in silhouette, holes, thin layered material, frames and plates. Once per-item editable `.blend` documents became the production source-authority model, the remaining question was whether B still needed a project-specific external geometry backend.

This migration tested the stronger alternative:

> represent the useful B construction directly with ordinary Blender source geometry and modifiers, then compile the committed `.blend` read-only through the existing item-source boundary.

The eight migrated items are:

- Greatsword
- Death Sickle
- Silver Glasses
- Gas Mask
- Moth Cloak
- Mirror Armor
- Angel Feather
- Rear Mirror

## Result

**All eight Batch-B items now have viable editable Blender source authority. A separate production Batch-B geometry backend is not required.**

The native construction vocabulary is deliberately small:

```text
editable planar outline / open-frame mesh
        ↓
MIRROR where symmetry is meaningful
        ↓
SOLIDIFY where live thickness is useful
        ↓
optional low-segment BEVEL
        ↓
read-only evaluation / runtime OBJ + MTL
```

Open frames keep real inner/outer boundaries. Bilateral objects can keep one authored side and a live Mirror relationship. Individual plates, vanes and structural pieces remain selectable rather than becoming one anonymous baked mesh.

## Baselines

The migration deliberately rendered two pre-migration boards through the real LÖVE item viewer:

1. the branch's current canonical runtime products;
2. the preserved `agent/polygonal-item-cohort` Batch-B products.

Those two boards were **byte-identical**:

```text
SHA-256
05d04810edce29564960d450b905e55e2436855c23fd24fbfb8629cb11386a2b
```

This is important: the old Batch-B visual designs had already become the canonical target somewhere in the integration history. This migration is therefore principally a **source-authority migration**, not an attempt to replace the accepted item art with a new redesign.

The accepted Blender-source board was then rendered through the same viewer. It preserves the target closely. The visible differences are localized construction/readability differences rather than identity changes: Moth Cloak exposes some rib/fabrication structure more strongly, Angel Feather's vane thickness reads slightly differently, and Rear Mirror's explicit thin surfaces alter minor edge highlights.

No item was rejected on visual grounds.

## What the sources preserve

### Greatsword

The blade is an editable planar silhouette with explicit layered parts, thickness and restrained beveling. Its identity remains an outline problem rather than being forced through a volumetric primitive grammar.

### Death Sickle

The crescent is represented as one editable hollow band with meaningful inner and outer boundaries rather than a row of disconnected arc bars. The contour remains the important source handle.

### Silver Glasses

The glasses preserve **live bilateral symmetry**: one authored side drives the other through Blender's Mirror modifier. This is a genuine authoring improvement over baking both halves into generated vertices.

### Gas Mask

Shell details, lens/frame/filter pieces and straps retain meaningful separate fabrication pieces, with bilateral structure expressed by Mirror rather than duplicated source geometry.

### Moth Cloak

One side's wing panels and ribs remain independently editable and mirror structurally. The resulting source reads like assembled fabric/plate construction rather than one opaque mesh.

### Mirror Armor

Shoulder/facet construction is authored once and mirrored, while the central body remains independently editable.

### Angel Feather

The feather remains a deliberately graphic B-style construction with separate vane pieces. It was not forced into the C curve/profile vocabulary merely because curves are now available; multiple authoring vocabularies remain legitimate inside Blender.

### Rear Mirror

The mirror keeps explicit planar frame/glass/handle/ornament construction. Its important design geometry remains directly editable even where thickness had to be materialized for deterministic export.

## Runtime result

Every migrated output passed the strict runtime OBJ validator:

| Item | Vertices | Face records | Triangles |
|---|---:|---:|---:|
| Greatsword | 134 | 248 | 248 |
| Death Sickle | 168 | 316 | 316 |
| Silver Glasses | 296 | 572 | 572 |
| Gas Mask | 364 | 696 | 696 |
| Moth Cloak | 184 | 324 | 324 |
| Mirror Armor | 160 | 288 | 288 |
| Angel Feather | 354 | 648 | 648 |
| Rear Mirror | 242 | 464 | 464 |
| **Total** | **1,902** | **3,556** | **3,556** |

The historical Batch-B generator reported 918 vertices / 961 authored faces. The new evaluated Blender products are roughly 2.1× the vertex count. Face totals are not directly apples-to-apples because the production OBJ path exports triangulated evaluated surfaces, while the historical number counted authored polygon faces.

This migration deliberately does **not** add runtime decimation. Resolved geometry can be optimized later—including through the project's existing decimation capability—without changing the authoritative Blender source representation.

## UV and deterministic-export investigation

The geometry migration itself was unusually clean: all eight first-pass Blender products were runtime-valid. The first corpus gate rejected them for one reason only: the new source meshes had no UV layers.

That exposed a more interesting production constraint.

### Why simple planar UVs were not enough

After adding source UVs, Blender 5.0's OBJ exporter occasionally emitted different `vt` tables for otherwise identical source documents. Geometry, face topology and normals remained unchanged, but coincident UV corners could be deduplicated differently between exports. In one Rear Mirror comparison, a UV value also differed at the sixth decimal place before later UV indices shifted.

Weakening `compile_item_blends.py --check` was rejected. Checked-in runtime products must remain byte-reproducible from authoritative source.

### Cohort migration UV rule

These eight items currently use material shading rather than painted image textures, so their migrated source meshes use a **deterministic unique-per-corner UV atlas**. Each source mesh loop gets its own stable UV coordinate, removing ambiguous coincident corners from the exporter.

This is a migration layout, not a permanent restriction on texturing. If an item later receives painted textures, author conventional UVs directly in its authoritative `.blend`.

### Live Mirror rule

For live `MIRROR` sources, the generated side's UVs are offset by +1 U tile. This preserves the useful edit-one-side authoring relationship without overlapping the authored side's UV set.

The important result is that **live structural symmetry survived the determinism gate**.

### Narrow explicit-thickness exceptions

Three sources required more than the general UV rule:

- **Death Sickle:** the crescent's Solidify thickness is materialized once after the editable hollow contour is authored.
- **Silver Glasses:** authored-half Solidify thickness is materialized, but the Mirror relationship stays live.
- **Rear Mirror:** Solidify thickness on its fabrication pieces is materialized while planar design geometry remains editable.

These are source-specific Blender OBJ determinism decisions, not a new rule that B should bake all modifiers.

The preferred hierarchy is:

1. keep meaningful modifiers live;
2. separate generated UV domains where possible;
3. materialize only the modifier output proven to make the runtime product nondeterministic;
4. never weaken runtime validation or source read-only guarantees merely to retain a modifier cosmetically.

## Validation

Accepted run `31910193811` established all of the following in one lane:

- both pre-migration viewer baselines rendered;
- all eight authoritative `.blend` sources materialized;
- all eight compiled products passed runtime OBJ validation;
- the full item corpus remained green (`duplicate_geometry: 11`, `no_uvs: 124`, `shared_file: 1`);
- Death Sickle, Silver Glasses and Rear Mirror passed explicit repeated-export byte comparisons;
- the production `compile_item_blends.py --check` passed across **all 16 current Blender-authority item sources**;
- source `.blend` hashes remained unchanged during read-only compilation;
- the post-migration board rendered successfully through the real item viewer.

## Architectural conclusion

Batch B survives, but primarily as a **way of thinking about construction**, not as a separate code backend.

In production Blender terms:

- B outline → editable planar mesh;
- B frame/hole → explicit inner/outer topology;
- B thickness → Solidify or explicit thin mesh when determinism requires it;
- B bilateral duplication → live Mirror;
- B layered fabrication → separate named child objects;
- B edge treatment → restrained Bevel.

That is simpler and more inspectable than keeping an external `poly_parts.py`-style compiler in authority over the artist's source document.

The strongest production boundary remains below authoring choice:

```text
editable Blender document
        ↓
read-only evaluated duplicate
        ↓
deterministic runtime-valid geometry
```

This lets A, B and C coexist inside one `.blend` when an item needs them without asking Thestra to invent a universal modeling language first.
