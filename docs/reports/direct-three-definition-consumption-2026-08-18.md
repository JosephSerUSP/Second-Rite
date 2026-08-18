# Direct Three mesh-definition consumption — final experiment report (2026-08-18)

Issue: #765  
Draft PR: #766  
Baseline: current `main` `726eabcd`, after #761, with LÖVE 11.5 runtime authority.

## Decision

**YES: `mesh-definitions-v1` is now safe to consume directly in the production Studio viewport.**

The remaining placement-dependent colour gate is solved without cloning spatial geometry and without weakening picking, provenance, authoring lighting, vertex shading, or fidelity semantics.

#766 now uses direct definitions as Studio's normal renderable consumer while retaining an explicit expanded compatibility control long enough for parity/debugging:

```js
window.THESTRA_MAP_RENDERABLE_CONSUMER = 'expanded'
```

The production hot path no longer expands definition placements into duplicated world-space triangle streams.

## Final representation

For each runtime-authored mesh definition, Three creates one shared spatial `BufferGeometry` containing:

- position;
- normal;
- UV;
- index.

Each placement remains an ordinary independently selectable `THREE.Mesh`.

Each placement owns a lightweight geometry view that references the **same spatial BufferAttribute objects and index** as the definition geometry, while owning only its RGB colour attribute. Therefore two placements can share exact topology and spatial data without sharing mutable lighting state.

This avoids a draw-time colour-attribute swap and avoids cloning position/normal/UV/index arrays per placement.

The direct consumer uses an ordinary wide Three index buffer (`Uint32Array`) unconditionally. #765 does not perform index-width packing or claim any benefit from Int16/binary packing.

## Colour authority and live authoring

Placement colour remains placement-dependent.

Studio reuses its existing authoring modulation authority rather than reimplementing it. For each compact placement it presents a transient sample containing **one world-space sample per unique definition vertex** to the existing vertex-shading/static-light modulation path. It does not expand definition indices into triangles and does not copy normals, UVs, or topology for this pass.

The retained placement colour state is:

- unlit RGB;
- authoritative resolved RGB;
- the current Three colour attribute used for live authoring updates.

Live light edits transform the shared local vertex positions by the authoritative placement matrix, sample the authoring light grid, and mutate only that placement's RGB attribute. Placements that share one spatial definition cannot leak colour state into each other.

This is intentionally conservative. Reducing the three RGB copies may be a later optimization, but is not required to remove the duplicated spatial reconstruction.

## Hosted production-shaped proof

The final proof ran on the repository's standard hosted Windows verify environment with LÖVE 11.5 + Mesa. The benchmark fails unless topology/colour parity, live-light parity, no-leak, no-compatibility-expansion, and ordinary picking all pass.

### Map 2

Runtime representation: **16 definitions, 445 placements, 194 literal surfaces, 639 ordinary scene objects**.

| Measurement | Previous compatibility path | Final production direct path |
|---|---:|---:|
| Compact bridge payload | 0.863 MiB | 0.863 MiB |
| Consumer preparation | 382.24 ms | **387.276 ms** |
| Consumer-ready JS heap delta | 109.13 MiB | **0.376 MiB** |
| Three scene creation | 325.96 ms | **28.885 ms** |
| Total measured JS heap delta | 102.98 MiB | **0.844 MiB** |
| Shared spatial attributes | n/a | **0.204 MiB** |
| Placement colour semantic state | n/a | **8.705 MiB** |
| Placement Three colour attributes | n/a | **4.353 MiB** |
| Placement-owned RGB total | n/a | **13.058 MiB** |
| Literal geometry attributes | n/a | **0.019 MiB** |
| Unique Three attribute storage | 20.172 MiB | **4.575 MiB** |
| Placement geometry views | n/a | **445** |
| Shared definition geometries | n/a | **16** |
| Full live-light update | n/a | **46.437 ms** |

Parity proof:

- 479,544 indexed placement tuples checked;
- 1,438,632 RGB components checked;
- **0 mismatches**;
- max floating error: `2.9802322387695312e-8`;
- live-light RGB: **0 mismatches** at the same max error;
- colour leak between placements sharing one definition: **none**;
- ordinary raycast hit: `cell:12:1`, floor, `material_001`, transport order 1, distance 0.1;
- compatibility expansion reintroduced: **no**.

### Map 3

Runtime representation: **16 definitions, 705 placements, 405 literal surfaces, 1,110 ordinary scene objects**.

| Measurement | Previous compatibility path | Final production direct path |
|---|---:|---:|
| Compact bridge payload | 1.028 MiB | 1.028 MiB |
| Consumer preparation | 434.87 ms | **430.413 ms** |
| Consumer-ready JS heap delta | 119.89 MiB | **0.541 MiB** |
| Three scene creation | 402.15 ms | **44.442 ms** |
| Total measured JS heap delta | 177.69 MiB | **1.222 MiB** |
| Shared spatial attributes | n/a | **0.204 MiB** |
| Placement colour semantic state | n/a | **11.356 MiB** |
| Placement Three colour attributes | n/a | **5.678 MiB** |
| Placement-owned RGB total | n/a | **17.034 MiB** |
| Literal geometry attributes | n/a | **0.038 MiB** |
| Unique Three attribute storage | 27.151 MiB | **5.947 MiB** |
| Placement geometry views | n/a | **705** |
| Shared definition geometries | n/a | **16** |
| Full live-light update | n/a | **63.451 ms** |

Parity proof:

- 644,616 indexed placement tuples checked;
- 1,933,848 RGB components checked;
- **0 mismatches**;
- max floating error: `2.9802322387695312e-8`;
- live-light RGB: **0 mismatches** at the same max error;
- colour leak between placements sharing one definition: **none**;
- ordinary raycast hit: `cell:2:4`, floor, `material_001`, transport order 1, distance 0.1;
- compatibility expansion reintroduced: **no**.

## What the timings mean

The earlier spatial-only prototype reported effectively zero direct-consumer prep because it deliberately stopped before solving placement colour.

The final exact path does **not** eliminate semantic colour preparation: Maps 2/3 still spend about 387/430 ms deriving placement-dependent authoring RGB through the existing Studio modulation authority.

The win is therefore not "all adapter work disappeared." It is:

1. the ~109–120 MiB pre-scene compatibility reconstruction is gone;
2. duplicated spatial Three geometry is gone;
3. scene construction falls from ~326/402 ms to ~29/44 ms;
4. placement-dependent RGB stays exact and isolated.

That distinction matters to the broader cross-runtime architecture: semantic work can remain where it is authoritative/appropriate without forcing the authoritative compiled representation through a lossy or enormous compatibility shape.

## Required proof matrix

| Required proof | Result |
|---|---|
| geometry/topology equivalence | **PASS** — indexed direct tuples match expanded control |
| placement transforms | **PASS** — world positions match expanded control |
| material/provenance | **PASS** |
| ordinary raycast/picking | **PASS** |
| static resolved lighting | **PASS** — RGB zero mismatches |
| live authoring light edits do not leak | **PASS** |
| vertex-shading/tint semantics exact | **PASS** — existing modulation authority reused |
| placement colour memory acceptable | **PASS** — 13.058/17.034 MiB total conservative RGB state, far below duplicated full geometry |
| compatibility expansion absent from hot path | **PASS** |
| viewport visual parity | **UNAVAILABLE AT PIXEL LEVEL** — G6 cannot complete base-A; G5 exact only confirms the unchanged LÖVE renderer |

## Visual machinery

The relative visual workflow was run against the production direct-consumer candidate.

**G5 relative A/B passed exactly.** Classic and Wide both reported zero base-repeat changes and zero candidate changed pixels; the candidate was decoded-pixel identical to base. This confirms that #766 did not alter the LÖVE game renderer. Because #766 changes only Studio's Three consumer, G5 is **not** evidence of Studio viewport pixel parity.

**G6 did not produce a candidate verdict.** Its editor recorder failed to reach a complete comparison on **base-A (`main`) before candidate capture**. This is therefore unavailable evidence, not evidence of a #765 visual regression. No G6 golden was recaptured or weakened.

The direct consumer's focused geometry/lighting/raycast parity checks and the hosted Map 2/3 proof are exact representation-level evidence. The Studio-specific pixel verdict remains unavailable until G6 base capture is healthy; no golden was changed or weakened.

## Production wiring and fallback

Studio requests compact instance transport explicitly for the direct consumer. The bridge owns that execution/transport choice per request and clears stale encoding state for the expanded control.

The workspace defaults to direct definitions. Compatibility expansion remains available only through the explicit expanded consumer control for parity/debugging; it is no longer the production hot path.

No runtime instancing, LOD, binary packing, Int16 packing, drawInstanced work, geometry inference, or visual-fidelity reduction was added.

## Authority split after #765

### Runtime/compiler-authored authority

The runtime/compiler remains authoritative for:

- `mesh-definitions-v1` definition identity;
- indexed topology;
- local positions;
- normals;
- UVs;
- base vertex RGBA;
- definition material;
- placement → definition reference;
- placement transform / raster origin;
- placement order;
- placement source/provenance;
- literal surfaces;
- material descriptors;
- coordinate-system metadata;
- resolved runtime static-light grid transported to Studio.

Three does **not** compile geometry, infer geometry identity, compare floats to discover duplicates, or reconstruct runtime topology semantics.

### Studio-owned execution/authoring state

Studio owns only host-specific work that is legitimately placement/editor dependent:

- the centralized runtime-Z-up → Three-Y-up execution mapping;
- existing authoring vertex-shading/tint + static-light modulation;
- placement-owned unlit/resolved/live RGB state;
- live authoring light edits;
- Three Mesh/BufferGeometry/material/texture execution and editor selection objects.

This is the intended architectural result:

> **one semantic authority does not require one execution host.**

LÖVE and Three now consume the same authoritative compiled spatial representation, while Studio retains only the editor-specific mutable colour/execution state it actually owns.

## Conclusion

The falsifier did not fire.

Placement-dependent colour does **not** require reconstructing or cloning full spatial geometry. Ordinary selectable objects, provenance, raycasting, static lighting, live lighting, vertex shading and tint remain exact.

#766 can therefore evolve from experiment into the narrow production Studio direct-consumer path, with the expanded control retained until the remaining G6 harness limitation is independently resolved.