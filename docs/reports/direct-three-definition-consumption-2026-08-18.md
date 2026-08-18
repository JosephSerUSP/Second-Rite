# Direct Three mesh-definition consumption experiment — 2026-08-18

Issue: #765  
Draft PR: #766  
Baseline: current `main` after #761, with LÖVE 11.5 runtime authority.

## Question

After #761 reduced the Studio bridge from repeated world-space triangle soup to exact runtime-authored mesh definitions + placements, does Three still need the compatibility expansion back into one full triangle stream per placement?

The falsifier was intentionally representational, not FPS-oriented:

> If direct consumption still requires allocations equivalent to the reconstructed ~51–64 MiB world-space arrays, the representation experiment has failed.

It did not fail. It passed by a much larger margin than expected.

## Prototype

The experimental consumer keeps the #761 transport intact and builds:

- one indexed `THREE.BufferGeometry` per runtime definition;
- one ordinary independently selectable `THREE.Mesh` per placement, sharing the definition geometry;
- one ordinary geometry per literal/non-definition surface;
- the authoritative placement transform from the runtime transport;
- placement-owned source, selection, material and transport-order provenance.

It does **not** use runtime instancing, `THREE.InstancedMesh`, LOD, quantization, Int16 transport packing, or inferred geometry equivalence.

A real Three raycast is fired through representative placed geometry so the experiment proves ordinary picking and provenance rather than merely counting arrays.

## Hosted Windows result

Same runner family as #754: Windows, LÖVE 11.5 + Mesa. Both paths start from the same compact `mesh-definitions-v1` JSON returned by runtime authority.

### Map 2

| Measurement | Current compatibility path | Direct definitions |
|---|---:|---:|
| Compact bridge payload | 0.863 MiB | 0.863 MiB |
| JSON parse | 3.29 ms | 4.69 ms |
| Adapter / consumer preparation | 382.24 ms | 0.003 ms |
| Consumer-ready JS heap delta | 109.13 MiB | 1.02 MiB |
| Three scene creation | 325.96 ms | 15.26 ms |
| Total measured heap delta | 102.98 MiB | 10.42 MiB |
| Geometry objects | 639 | 210 total / 16 shared placement definitions |
| Geometry attribute storage | 20.172 MiB | 0.257 MiB |
| Selectable placement/literal objects | 639 | 639 |

Runtime representation: **16 definitions, 445 placements, 194 literal surfaces**.

Measured deletion:

- consumer-ready heap: **108.11 MiB**;
- total measured heap: **92.56 MiB**;
- geometry attribute storage: **19.915 MiB**.

Picking proof: both paths hit the same semantic `cell:12:1`, floor source, `material_001`, at the same 0.1 ray distance.

### Map 3

| Measurement | Current compatibility path | Direct definitions |
|---|---:|---:|
| Compact bridge payload | 1.028 MiB | 1.028 MiB |
| JSON parse | 3.88 ms | 4.51 ms |
| Adapter / consumer preparation | 434.87 ms | 0.002 ms |
| Consumer-ready JS heap delta | 119.89 MiB | 1.37 MiB |
| Three scene creation | 402.15 ms | 13.49 ms |
| Total measured heap delta | 177.69 MiB | 11.48 MiB |
| Geometry objects | 1110 | 421 total / 16 shared placement definitions |
| Geometry attribute storage | 27.151 MiB | 0.310 MiB |
| Selectable placement/literal objects | 1110 | 1110 |

Runtime representation: **16 definitions, 705 placements, 405 literal surfaces**.

Measured deletion:

- consumer-ready heap: **118.52 MiB**;
- total measured heap: **166.21 MiB**;
- geometry attribute storage: **26.841 MiB**.

Picking proof: both paths hit the same semantic `cell:2:4`, floor source, `material_001`, at the same 0.1 ray distance.

## What this proves

The old reconstruction is not needed for Three's spatial geometry, object identity, selection or provenance.

The current compatibility path pays two avoidable expansions:

1. #761 definition placements are expanded back into full per-placement world-space triangle streams;
2. Three then converts each expanded surface into its own independent `BufferGeometry`.

Direct definition consumption removes both while retaining the same number of ordinary selectable scene objects.

The expected ~51–64 MiB reconstruction target was conservative. On this same-runner Three benchmark, the current path's consumer preparation plus modulation retained roughly **109–120 MiB** before scene construction; the direct representation retained roughly **1–1.4 MiB** before scene construction.

This is a representation and memory result first. The large scene-creation reduction is useful corroboration, not a mandate to chase FPS.

## The production gate: per-placement authoring colour truth

The direct geometry representation is **not yet production-ready**, because both representative bundles contain resolved map lighting.

Today's adapter applies Studio vertex shading / static-light modulation after compatibility expansion, using each surface's world-space vertex positions. The viewport can also update live authoring lighting by mutating each mesh geometry's colour attribute.

If multiple placements share one `BufferGeometry`, naively mutating that shared colour attribute would make one placement's lighting leak into every other placement using the same definition.

Therefore the experiment deliberately does **not** claim visual parity yet. This is the remaining semantic gate, not evidence against shared spatial geometry.

### Exact next representation to test

Keep spatial geometry shared, but keep **colour state placement-owned**:

- shared per-definition position / normal / UV / index streams;
- an independently selectable Mesh per placement;
- a placement-owned RGB vertex-colour buffer computed through the existing Studio modulation authority using the authoritative placement transform;
- bind/swap that placement colour attribute for the Mesh at draw time, rather than cloning position/normal/UV/index geometry;
- live authoring lighting updates only the placement-owned colour buffer.

This preserves one spatial `BufferGeometry` per definition while acknowledging the actual fact that illumination is placement-dependent.

The next measurement must report the colour-buffer bytes separately. If placement-owned colours recreate an allocation close to the old full geometry volume, that is a falsifier. If they remain a small fraction while visual parity and live lighting stay exact, the compatibility expansion can be removed from the viewport path.

## Viewport-settle status

No production viewport-settle claim is made from this benchmark. Scene construction and picking are measured directly, but the direct path is intentionally not wired into Free Authoring until the placement-lighting gate above is solved. A meaningful click/load → first-useful-paint comparison must use the exact-light direct consumer, not a visually weakened benchmark mode.

## Architectural conclusion

The representation experiment is strongly positive:

- keep #761's exact definitions + placements as the Studio bridge representation;
- pursue direct Three consumption;
- preserve ordinary selectable placement objects;
- do not add runtime instancing or LOD as a consequence of this result;
- solve placement-dependent colour as a narrow Three authoring concern without cloning the full spatial geometry;
- keep LÖVE as geometry/semantic authority.
