# Height-map triangle budget / projected usefulness study — 2026-08-18

Issue: #760  
Draft PR: #769  
Runtime baseline: LÖVE 11.5, same hosted Windows + Mesa runner family used by the surrounding representation/process experiments.

## Question

How much geometry should a Second Rite displaced wall/floor/ceiling actually have, once the decision is judged at the game's real projection rather than in a high-resolution authoring viewport?

The experiment deliberately does **not** change dense source sampling. It holds the height field, source art, camera and renderer fixed and varies only the existing QEM `heightMapTriangleBudget` / plane `triangleBudget` ceiling:

**64 / 96 / 128 / 192 / 256 / 384**

Representative sources:

- Map 2 — `dungeon_default` atlas wall/floor surfaces;
- Map 15 — `stillnight_bellroot_vigil` atlas wall/floor surfaces;
- Map 14 — `dungeon_hand_authored_height_compare` hand-authored wall comparison;
- Map 12 — `dungeon_ffxii_depth_explore` directory-backed FFXII-style floor/wall geometry.

## Method

The probe does not implement a geometry compiler.

For every case it runs the ordinary Project map -> tileset resolver -> `viewport_3d` -> `engine.geometry` -> `engine.geometry.plane` path. After the real geometry schema/parser has resolved the plane, the experiment substitutes only its exposed-relief triangle ceiling. Each case receives a unique compiler-cache identity so persisted/prebaked geometry cannot turn a supposed cold compile into a cache hit.

The runtime profiler then records:

- fixed dense sample columns/rows and dense triangle count;
- retained QEM relief triangles;
- triangles appended **after** relief reduction for perimeter/backing seals;
- final triangles;
- profiler-owned cold compiler span;
- exact sampled displacement extrema.

### Accounting detail: wall skirts are relief topology

Wall bottom skirts are generated before simplification and participate in the same QEM surface, so they are part of the budgeted exposed-relief triangle count. `perimeterSealTriangles` below means only geometry appended after QEM reduction.

This distinction matters for authoring language: the budget is an **exposed relief triangle ceiling**, not a hard final-mesh triangle budget.

## Exact-game visual capture

Every budget is also rendered through the real `viewport_3d.draw()` path into the game's **256 x 240 logical render surface while retaining the established 256 x 144 camera pixel scale**.

For each Map the benchmark selects deterministic floor poses facing the first in-grid wall at approximately near / mid / far distances. In the final run all three target depths were exact: **1 / 3 / 8 cells**.

The captures therefore include the real:

- world shader and depth test;
- fog and lighting;
- affine texture mapping;
- 1 px vertex snap;
- game camera/projection;
- resolved runtime geometry.

The benchmark stores PNGs and raw RGBA, and compares every budget against the 384 control *after* all of those presentation effects.

## Geometry results

The table uses representative final-triangle ranges when multiple cold definitions exist for the same surface class. `compile` is median profiler-owned cold compile time for that surface group.

| Source | Ceiling | Exposed relief | Post-QEM seal | Final triangles | Median cold compile |
|---|---:|---:|---:|---:|---:|
| Map 2 floor | 64 | 64 | 102 | 166 | 80.1 ms |
| Map 2 floor | 192 | 192 | 166 | 358 | 71.8 ms |
| Map 2 floor | 256 | 256 | 182 | 438 | 70.8 ms |
| Map 2 floor | 384 | 384 | 206 | 590 | 72.6 ms |
| Map 2 wall | 64 | 64 | 42–46 | 106–110 | 85.0 ms |
| Map 2 wall | 192 | 192 | 66–74 | 258–266 | 82.5 ms |
| Map 2 wall | 256 | 256 | 74–78 | 330–334 | 87.7 ms |
| Map 2 wall | 384 | 384 | 94–102 | 478–486 | 91.3 ms |
| Stillnight floor | 64 | 64 | 18–98 | 82–162 | 105.6 ms |
| Stillnight floor | 192 | 192 | 18–182 | 210–374 | 103.8 ms |
| Stillnight floor | 256 | 256 | 18–202 | 274–458 | 118.1 ms |
| Stillnight floor | 384 | 384 | 26–218 | 410–602 | 105.3 ms |
| Stillnight wall | 64 | 63 | 14–66 | 77–129 | 102.3 ms |
| Stillnight wall | 192 | 192 | 26–106 | 218–298 | 96.2 ms |
| Stillnight wall | 256 | 255–256 | 26–122 | 282–377 | 102.2 ms |
| Stillnight wall | 384 | 383–384 | 26–134 | 410–517 | 99.0 ms |
| Hand-authored wall | 64 | 63 | 38–42 | 101–105 | 73.8 ms |
| Hand-authored wall | 192 | 191 | 66–82 | 257–273 | 94.3 ms |
| Hand-authored wall | 256 | 256 | 86–94 | 342–350 | 89.8 ms |
| Hand-authored wall | 384 | 383 | 94–110 | 477–493 | 88.7 ms |
| FFXII floor | 64 | 64 | 0 | 64 | 142.1 ms |
| FFXII floor | 192 | 192 | 0 | 192 | 187.2 ms |
| FFXII floor | 256 | 256 | 0 | 256 | 129.1 ms |
| FFXII floor | 384 | 384 | 0 | 384 | 92.7 ms |
| FFXII wall | 64 | 64 | 0 | 64 | 138.8 ms |
| FFXII wall | 192 | 192 | 0 | 192 | 261.2 ms |
| FFXII wall | 256 | 256 | 0 | 256 | 138.3 ms |
| FFXII wall | 384 | 383 | 0 | 383 | 112.0 ms |

Dense source topology remains fixed throughout: the atlas floors begin at **4,608 dense triangles** and walls at **4,800 dense triangles** before QEM.

### Seals are not a rounding error

The post-QEM geometry can be a substantial fraction of the final mesh. At ceiling 384:

- Map 2 floor: 384 relief + 206 seals = **590 final**;
- one Stillnight floor variant: 384 relief + 218 seals = **602 final**;
- Map 2 wall variants: 384 relief + 94–102 seals = **478–486 final**.

This strongly validates the #758 authoring-language correction: `heightMapTriangleBudget` must not be presented to authors as “final triangles”.

### Lower budgets do not imply cheaper cold compilation

QEM simplification performs collapse work to reach the requested target. Aggressive reduction can therefore cost **more** compiler time, not less.

The FFXII-style source is the clearest example:

- floor ceiling 384: 92.7 ms median;
- floor 256: 129.1 ms;
- floor 192: 187.2 ms;
- floor 128: 565.9 ms;
- floor 96: 493.1 ms.

Likewise some FFXII wall targets become slower than 384. Therefore the reason to lower a fixed budget is **runtime representation / memory / projected usefulness**, not an assumption that cold QEM compilation becomes faster.

## Exact displacement

None of these representative cold plane surfaces is exactly flat.

Representative sampled displacement ranges include:

- Map 2 floor: -0.026118 .. +0.031608;
- Map 2 wall: -0.081647 .. +0.045412;
- Stillnight floors: -0.082118 .. +0.084471;
- Stillnight walls: -0.109098 .. +0.142353;
- hand-authored compare wall: -0.068941 .. +0.096549;
- FFXII floor: -0.067020 .. +0.089843;
- FFXII wall: -0.110196 .. +0.118196.

So this study provides no evidence for an exact-flat fast path. A future flat-path experiment needs a genuinely flat authored fixture and should use exact displacement truth rather than inventing an epsilon here.

## Projected visual differences against ceiling 384

`changed %` counts RGB pixels that differ after the production renderer. `MAE` is mean absolute RGB channel delta across the whole 256x240 frame. Because the final image is snapped/quantized, changed pixels commonly move by at least 8 channel values; changed-percentage therefore exaggerates small-but-widespread interpolation changes. Read it together with MAE and the screenshots.

### Ceiling 256 vs 384

| Source | Near changed / MAE | Mid changed / MAE | Far changed / MAE |
|---|---:|---:|---:|
| Map 2 | 0.55% / 0.07 | 39.40% / 3.22 | 28.75% / 1.79 |
| Stillnight | 21.15% / 1.32 | 26.75% / 1.58 | 38.47% / 2.37 |
| Hand-authored compare | 14.49% / 1.80 | 15.37% / 1.38 | 13.20% / 1.37 |
| FFXII-style | 31.22% / 5.71 | 47.58% / 7.59 | 46.60% / 7.38 |

### Ceiling 192 vs 384

| Source | Near changed / MAE | Mid changed / MAE | Far changed / MAE |
|---|---:|---:|---:|
| Map 2 | 0.75% / 0.08 | 50.30% / 4.46 | 40.49% / 2.50 |
| Stillnight | 29.17% / 1.78 | 33.07% / 1.95 | 50.27% / 3.07 |
| Hand-authored compare | 16.60% / 2.13 | 20.81% / 2.09 | 15.56% / 1.60 |
| FFXII-style | 43.91% / 8.69 | 60.08% / 10.24 | 62.66% / 11.29 |

### Ceiling 64 vs 384

| Source | Near changed / MAE | Mid changed / MAE | Far changed / MAE |
|---|---:|---:|---:|
| Map 2 | 1.30% / 0.31 | 62.30% / 6.88 | 55.72% / 3.78 |
| Stillnight | 47.06% / 3.33 | 48.68% / 3.25 | 61.21% / 4.06 |
| Hand-authored compare | 40.03% / 5.70 | 27.73% / 3.82 | 23.20% / 3.76 |
| FFXII-style | 72.94% / 18.70 | 83.22% / 19.68 | 81.57% / 20.74 |

## Visual reading

The same-runner contact sheets make the numeric result easier to interpret.

### `dungeon_default`

The one-cell wall is surprisingly tolerant: even aggressive ceilings preserve most of the apparent wall relief at game resolution. Mid/far floor and ceiling are more sensitive than the near wall, however. By 256 the 384 control is visually close, but affine texture interpolation still shifts across broad floor areas.

### Stillnight

256 is close to 384 in ordinary reading distance while retaining substantially less geometry. Lower targets increasingly alter both relief and the triangulation through which the floor texture is interpolated. The far frame still has broad quantized pixel churn despite the image remaining recognizably the same scene.

### Hand-authored comparison wall

256 is close to 384 and 192 is a plausible asset-specific choice. 64/96 are visibly faceted in the near wall. This fixture supports the idea that some deliberately chunky relief does not need 384 exposed triangles.

### FFXII-style directory geometry

This is the counterexample to a tiny universal budget. It carries high-frequency shape/texture information and remains visibly sensitive even at 256. 192 and below materially change the foreground floor and wall. A 256 general default may be acceptable as a compromise, but fidelity-sensitive FFXII-style assets have a defensible reason to stay at 384.

## The affine-texture result changes the LOD decision

This is the most important architectural result of #760.

Second Rite intentionally uses affine texture mapping. The triangles are therefore not only a geometric approximation of relief; **the triangulation is part of texture interpolation**.

Changing QEM ceiling changes triangle edges. At runtime that changes how texture coordinates interpolate across the image. Consequently even far views can show broad pixel differences when the relief silhouette itself seems nearly unchanged.

That makes naive runtime LOD by swapping independently simplified triangulations unattractive: distance transitions would risk visible texture popping/shimmer as both geometry **and affine UV interpolation** switch.

The experiment therefore argues **against implementing ordinary runtime geometry LOD now**.

If LOD is revisited later, it needs a design that preserves triangulation/UV continuity across levels (or another explicit visual strategy). Simply choosing 384 near / 192 mid / 64 far is not supported by this renderer.

## Defensible fixed-budget answer

There is no single “PS1 polygon count” that should be imposed on every Second Rite surface. The useful variable is projected visual information under this renderer and source asset.

The evidence supports this authoring policy:

- **256** is a defensible *general ceiling candidate* for displaced surfaces. It removes one third of the exposed relief triangles relative to 384 and often brings final geometry down materially while remaining close to the 384 control on the atlas/hand-authored fixtures.
- **192** is a credible asset-specific choice for simpler/chunkier wall relief after visual inspection; it should not be a universal default.
- **384** remains justified for high-frequency/deep-relief assets such as the FFXII-style set when their exact authored appearance matters.
- **64–128** are useful deliberate low-poly styles / stress points, not a defensible global quality setting for the representative project assets.

Do **not** automatically migrate every authored budget to 256 from this experiment. The right production follow-up is #768's Resolution Inspection language: let authors see exposed relief, seals, final triangles, compile cost, placement count and exact-game projected usefulness for the selected surface.

## Recommendations

1. Keep dense source sampling independent from simplification quality. The current two-stage architecture is useful.
2. Keep `heightMapTriangleBudget` schema compatibility, but present it as **Exposed relief triangle ceiling** in Studio.
3. Seed new/general authoring around **256** only if/when a default policy is explicitly changed; preserve per-asset overrides and make 384 easy for fidelity-sensitive surfaces.
4. Do not implement runtime LOD from #760. The affine-interpolation discontinuity is a concrete reason not to.
5. Do not claim compile-time savings from lower QEM targets; measure them, because aggressive collapse can be slower.
6. Add a genuinely exact-flat fixture before pursuing a flat plane fast path.
7. Keep Free Authoring high fidelity. Put game-resolution/projected usefulness evidence in an opt-in Resolution Inspection surface rather than making the authoring viewport uglier.

## Scope boundary

#760 does not justify runtime instancing either. Runtime shared-definition instancing remains a separate larger-map/mobile/memory question and can be prototyped on LÖVE 11.5 if later measurements warrant it.
