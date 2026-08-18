# Height-map triangle budget / projected usefulness study — 2026-08-18

Issue: #760

This is a bounded measurement report, not a production budget migration and not a runtime-LOD implementation.

## Question

#758 established that the authored `heightMapTriangleBudget` is not a final-triangle count. The runtime first samples a fixed dense height field and QEM-decimates the exposed relief toward that ceiling; seam/perimeter/backing geometry may then be appended. #760 asks whether the current 384-triangle production relief ceiling is actually over-authored at the real first-person projection, and whether distance-only oversubdivision warrants a separate LOD experiment.

## Method

The experiment kept the current geometry authority and renderer intact:

- the opened Project and its authored height maps were unchanged;
- dense sampling stayed fixed at the current 48×48 source grid;
- the sweep changed only the exposed-relief QEM ceiling: 64, 96, 128, 192, 256, 384;
- the renderer kept current scales, seams, affine UV interpolation, lighting, fog, depth and 1px vertex snapping;
- exact game frames were captured at representative wall steps 1 / 3 / 8;
- geometry-error probes compare the simplified surface directly with the dense sampled field, then project the maximum geometric error through the production camera before the 1px snap;
- a synthetic exact-constant field was run separately so its zero-displacement result cannot be confused with authored-material statistics.

The representative set covers:

1. Map 2 / `dungeon_default` floor, wall and ceiling;
2. Map 15 / `stillnight_bellroot_vigil` floor, wall and ceiling;
3. Map 14 / `dungeon_hand_authored_height_compare` wall;
4. Map 12 / `dungeon_ffxii_depth_explore` directory-backed floor, wall and ceiling planes.

The current-main validation rerun was GitHub Actions Verify run `32195908705` at branch head `aae82816c7fcf6a29eceababf5845903c6c9dc61`, using the repository-pinned LÖVE 11.5 Windows runtime and Mesa software OpenGL 26.1.6. The one-off CI hook used to obtain that hosted evidence is not part of the final PR.

## Geometry accounting on the current-main rerun

Atlas floors/ceilings have 4,608 dense source triangles; atlas walls have 4,800. Directory-backed FFXII-style planes use the same dense sampling but do not append the atlas perimeter seals shown below.

The table reports the authored exposed-relief ceiling, actual retained relief after QEM, post-QEM seal/perimeter triangles, final triangles, and median cold compile time where several source variants represent one class.

| Source / surface | ceiling | retained relief | seals | final triangles | cold compile |
|---|---:|---:|---:|---:|---:|
| Map 2 floor | 64 | 64 | 102 | 166 | 140.4 ms |
| Map 2 floor | 192 | 192 | 166 | 358 | 125.6 ms |
| Map 2 floor | 256 | 256 | 182 | 438 | 125.7 ms |
| Map 2 floor | 384 | 384 | 206 | 590 | 120.8 ms |
| Map 2 wall | 64 | 64 | 42–46 | 106–110 | 139.1 ms |
| Map 2 wall | 192 | 192 | 66–74 | 258–266 | 132.4 ms |
| Map 2 wall | 256 | 256 | 74–78 | 330–334 | 130.4 ms |
| Map 2 wall | 384 | 384 | 94–102 | 478–486 | 129.0 ms |
| Map 2 ceiling | 64 | 64 | 34 | 98 | 143.7 ms |
| Map 2 ceiling | 192 | 192 | 50 | 242 | 111.9 ms |
| Map 2 ceiling | 256 | 256 | 50 | 306 | 108.7 ms |
| Map 2 ceiling | 384 | 384 | 62 | 446 | 105.8 ms |
| Stillnight floor | 64 | 64 | 18–98 | 82–162 | 188.3 ms |
| Stillnight floor | 192 | 192 | 18–182 | 210–374 | 174.4 ms |
| Stillnight floor | 256 | 256 | 18–202 | 274–458 | 174.6 ms |
| Stillnight floor | 384 | 384 | 26–218 | 410–602 | 167.5 ms |
| Stillnight wall | 64 | 63–64 | 14–66 | 77–129 | 168.7 ms |
| Stillnight wall | 192 | 192 | 26–106 | 218–298 | 146.0 ms |
| Stillnight wall | 256 | 255–256 | 26–122 | 282–377 | 146.1 ms |
| Stillnight wall | 384 | 383–384 | 26–134 | 410–517 | 147.4 ms |
| Stillnight ceiling | 64 | 64 | 82 | 146 | 155.5 ms |
| Stillnight ceiling | 192 | 192 | 130 | 322 | 157.7 ms |
| Stillnight ceiling | 256 | 256 | 146 | 402 | 117.4 ms |
| Stillnight ceiling | 384 | 384 | 178 | 562 | 156.9 ms |
| Hand-authored wall | 64 | 63 | 38–42 | 101–105 | 136.2 ms |
| Hand-authored wall | 192 | 191 | 66–82 | 257–273 | 129.1 ms |
| Hand-authored wall | 256 | 256 | 86–94 | 342–350 | 129.6 ms |
| Hand-authored wall | 384 | 383 | 94–110 | 477–493 | 122.5 ms |
| FFXII floor | 64 | 64 | 0 | 64 | 148.1 ms |
| FFXII floor | 192 | 192 | 0 | 192 | 138.5 ms |
| FFXII floor | 256 | 256 | 0 | 256 | 137.2 ms |
| FFXII floor | 384 | 384 | 0 | 384 | 136.6 ms |
| FFXII wall | 64 | 64 | 0 | 64 | 170.6 ms |
| FFXII wall | 192 | 192 | 0 | 192 | 160.3 ms |
| FFXII wall | 256 | 256 | 0 | 256 | 144.9 ms |
| FFXII wall | 384 | 383 | 0 | 383 | 142.8 ms |
| FFXII ceiling | 64 | 64 | 0 | 64 | 151.0 ms |
| FFXII ceiling | 192 | 192 | 0 | 192 | 145.7 ms |
| FFXII ceiling | 256 | 256 | 0 | 256 | 121.5 ms |
| FFXII ceiling | 384 | 384 | 0 | 384 | 117.6 ms |

### Seals are not a rounding error

At ceiling 384:

- Map 2 floor: 384 relief + 206 seals = **590 final**;
- one Stillnight floor variant: 384 relief + 218 seals = **602 final**;
- Map 2 wall variants: 384 relief + 94–102 seals = **478–486 final**;
- Map 2 ceiling: 384 relief + 62 seals = **446 final**.

This validates #758's authoring-language correction: the setting is an **Exposed relief triangle ceiling**, not a final-triangle budget.

### Cold compile time is not a reason to lower the ceiling

The current-main rerun does not show useful proportional compile savings from aggressive simplification. For example, FFXII floor median cold compile is 148.1 ms at ceiling 64, 138.5 ms at 192, 137.2 ms at 256 and 136.6 ms at 384. The wall class likewise trends from 170.6 ms at 64 to 142.8 ms at 384.

An earlier experimental run contained much larger low-budget FFXII timing outliers. They did not reproduce on the current-main rerun and are therefore not used as decision evidence. The durable statement is narrower: **a smaller retained mesh does not imply a cheaper cold QEM compile; measure the current implementation rather than inferring compile cost from final triangle count.**

## Exact sampled displacement

The representative authored surfaces are all genuinely displaced:

| Source / surface | min | max |
|---|---:|---:|
| Map 2 floor | -0.026118 | +0.031608 |
| Map 2 wall | -0.081647 | +0.045412 |
| Map 2 ceiling | -0.014196 | +0.026588 |
| Stillnight floor | -0.082118 | +0.084471 |
| Stillnight wall | -0.109098 | +0.142353 |
| Stillnight ceiling | -0.011686 | +0.076157 |
| Hand-authored wall | -0.068941 | +0.096549 |
| FFXII floor | -0.067020 | +0.089843 |
| FFXII wall | -0.110196 | +0.118196 |
| FFXII ceiling | -0.012902 | +0.089843 |

Those rows must not be used to infer how exact-constant input behaves, so the rerun added a separate synthetic fixture.

## Exact-constant field check

The synthetic fixture uses a constant source field and the existing runtime geometry authority. Every budget reports exact `minDisplacement = 0` and `maxDisplacement = 0`.

Topology is independent of the authored ceiling after QEM:

| Surface | dense triangles | retained relief | seals | final triangles |
|---|---:|---:|---:|---:|
| wall | 4,800 | 4 | 10 | **14** |
| floor | 4,608 | 10 | 26 | **36** |
| ceiling | 4,608 | 10 | 26 | **36** |

But the collapse is computationally expensive on the hosted current-main run:

| ceiling | wall cold compile | floor cold compile | ceiling cold compile |
|---:|---:|---:|---:|
| 64 | 13,597.5 ms | 726.5 ms | 684.3 ms |
| 96 | 13,553.8 ms | 759.0 ms | 759.4 ms |
| 128 | 12,666.4 ms | 667.1 ms | 721.3 ms |
| 192 | 12,271.9 ms | 660.3 ms | 684.9 ms |
| 256 | 11,434.7 ms | 667.8 ms | 606.8 ms |
| 384 | 11,762.0 ms | 708.6 ms | 670.0 ms |

So the decimator eventually discovers a very small exact-flat topology, but only after paying dense sampling/QEM work. This is evidence for a bounded **exact-constant** fast-path experiment if exact-constant fields occur in useful authoring/runtime paths. It is **not** evidence for inventing a near-flat epsilon: no projection-derived tolerance has been established for replacing non-constant fields analytically.

## Geometry-only projected error against the dense field

The runtime probe samples the dense source field, evaluates the simplified mesh at those points, and records maximum world-space error plus its projected maximum pixel displacement at wall steps 1 / 3 / 8 before the existing 1px vertex snap. Unlike the frame A/B below, this metric is not contaminated by affine UV interpolation changing when triangulation changes.

The table focuses on the decision range 192 / 256 / 384. For classes with several variants, the values are the worst projected maximum among those variants. QEM minimizes an aggregate error objective, so the single maximum is not guaranteed to decrease monotonically at every intermediate ceiling.

| Source / surface | ceiling | near px | mid px | far px |
|---|---:|---:|---:|---:|
| Map 2 floor | 192 | 6.108 | 2.036 | 0.764 |
| Map 2 floor | 256 | 6.001 | 2.000 | 0.750 |
| Map 2 floor | 384 | 5.425 | 1.808 | 0.678 |
| Map 2 wall | 192 | 7.325 | 0.770 | 0.106 |
| Map 2 wall | 256 | 7.325 | 0.770 | 0.106 |
| Map 2 wall | 384 | 3.716 | 0.401 | 0.056 |
| Map 2 ceiling | 192 | 2.816 | 0.939 | 0.352 |
| Map 2 ceiling | 256 | 2.153 | 0.718 | 0.269 |
| Map 2 ceiling | 384 | 1.200 | 0.400 | 0.150 |
| Stillnight floor | 192 | 13.372 | 4.457 | 1.672 |
| Stillnight floor | 256 | 13.834 | 4.611 | 1.729 |
| Stillnight floor | 384 | 14.424 | 4.808 | 1.803 |
| Stillnight wall | 192 | 13.812 | 1.385 | 0.189 |
| Stillnight wall | 256 | 12.702 | 1.284 | 0.176 |
| Stillnight wall | 384 | 12.702 | 1.284 | 0.176 |
| Stillnight ceiling | 192 | 11.538 | 3.846 | 1.442 |
| Stillnight ceiling | 256 | 10.161 | 3.387 | 1.270 |
| Stillnight ceiling | 384 | 7.503 | 2.501 | 0.938 |
| Hand-authored wall | 192 | 10.067 | 1.037 | 0.143 |
| Hand-authored wall | 256 | 10.067 | 1.037 | 0.143 |
| Hand-authored wall | 384 | 5.825 | 0.619 | 0.086 |
| FFXII floor | 192 | 23.712 | 7.904 | 2.964 |
| FFXII floor | 256 | 23.740 | 7.913 | 2.968 |
| FFXII floor | 384 | 20.241 | 6.747 | 2.530 |
| FFXII wall | 192 | 8.325 | 0.869 | 0.120 |
| FFXII wall | 256 | 7.905 | 0.827 | 0.114 |
| FFXII wall | 384 | 4.591 | 0.492 | 0.069 |
| FFXII ceiling | 192 | 4.148 | 1.383 | 0.518 |
| FFXII ceiling | 256 | 2.605 | 0.868 | 0.326 |
| FFXII ceiling | 384 | 1.777 | 0.592 | 0.222 |

Two cautions matter when reading this table:

1. ceiling 384 is the current production control, **not dense geometric truth**; some high-frequency sources retain measurable dense-field error even at 384;
2. the 1px snap can erase sufficiently small projected geometric motion, but it does not make the lower ceilings globally equivalent at close range, especially for floors/ceilings and the FFXII-style source.

This makes a universal lower budget hard to defend from geometry alone. It also explains why a visual comparison against current 384 is a regression test, not an absolute-fidelity metric.

## Projected visual differences against ceiling 384

`changed %` counts RGB pixels that differ after the production renderer. `MAE` is mean absolute RGB channel delta across the whole 256×240 frame. Because the final image is snapped/quantized, changed pixels commonly move by at least 8 channel values; changed percentage therefore exaggerates small-but-widespread interpolation changes. Read it together with MAE and the screenshots.

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

The exact-game captures make the numerical result less binary than a changed-pixel percentage suggests.

- **256** is close to 384 on several atlas and hand-authored views and is a credible general authoring candidate, but it is not globally equivalent.
- **192** can be credible for simpler/chunkier relief after inspection, not as a universal migration target.
- The FFXII-style source remains materially sensitive even at 256 and is a concrete counterexample to a blind global downgrade.
- **64–128** remain useful deliberate low-poly/stress settings rather than a production-wide quality target for these fixtures.

## Why naive runtime LOD is rejected by this evidence

The large mid/far frame deltas are not only silhouette or displacement error. Second Rite intentionally uses **affine texture mapping**. QEM changes triangulation, and triangulation therefore changes affine UV interpolation across the surface.

A runtime policy that independently swaps 384-near / 192-mid / 64-far meshes would change both geometry and texture interpolation. That creates a concrete risk of texture popping/shimmer even when geometric displacement has become subpixel.

**Decision: do not build naive runtime LOD from #760.** A future LOD experiment would need triangulation/UV continuity or another mechanism that preserves the intended affine appearance across variants. #760 does not supply that mechanism.

## Decision

There is no evidence for a production-wide mass retune in this PR.

- **256**: defensible general ceiling *candidate*, especially for new/default authoring if an explicit policy change is later desired; one-third fewer exposed-relief triangles than 384.
- **192**: credible per-asset choice for simpler surfaces after exact-game inspection.
- **384**: remains justified for high-frequency/deep-relief assets such as the FFXII-style set when exact authored appearance matters.
- **64–128**: deliberate low-poly/stress choices, not a global quality target.

Do **not** automatically migrate existing authored data to 256 from this experiment. Feed the evidence into #768 Resolution Inspection so authors can see exposed relief, seals/final triangles, compile cost, placement count and exact-game projected usefulness for the selected surface.

## Recommendations

1. Keep dense source sampling independent from simplification quality. The current two-stage architecture remains useful.
2. Keep `heightMapTriangleBudget` schema compatibility, but present it as **Exposed relief triangle ceiling** in Studio.
3. Seed new/general authoring around **256** only if/when a default policy is explicitly changed; preserve per-asset overrides and make 384 easy for fidelity-sensitive surfaces.
4. Do not implement naive runtime LOD from #760; affine-interpolation discontinuity is a concrete blocker to simple distance-swapped triangulations.
5. Do not claim compile-time savings from lower QEM targets. The current-main rerun shows no proportional saving, and exact-constant input can be extremely expensive despite collapsing to very small final topology.
6. A bounded **exact-constant** fast-path is now justified as follow-up territory if exact-constant fields occur in useful paths. Preserve exact equality/semantics; do not invent a near-flat epsilon without a projection-derived tolerance.
7. Keep Free Authoring high fidelity. Put game-resolution/projected-usefulness evidence in an opt-in Resolution Inspection surface rather than making the authoring viewport uglier.

## Scope boundary

#760 does not ship a budget migration, runtime LOD, runtime instancing or a flat-plane fast path. Runtime shared-definition instancing remains a separate larger-map/mobile/memory question. The only durable product of this PR is the measurement harness/probes and this evidence report.

Agent-Signature:
  platform: ChatGPT Web
  model: GPT-5.6 Sol
  role: research
  task: "#760"
