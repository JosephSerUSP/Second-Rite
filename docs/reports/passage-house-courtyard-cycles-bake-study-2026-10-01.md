# Courtyard Cycles texture-bake study (2026-10-01)

This supersedes the preceding Cycles frame study as evidence for the owner's requested baking-time comparison. The old study rendered previews; the current shipping candidate still uses EEVEE projection. These separate packages use actual Cycles Combined selected-to-active surface baking on the GTX 1650 through OptiX. They are not preview screenshots presented as bake evidence.

## Measured whole-export budgets

All three use a 1024 atlas, identical corrected study geometry, neutral exposure, two diffuse/two glossy bounces within four total bounces, deterministic legacy UV layout and no camera-projection bake. Sample counts were calibrated to approximate total wall-time budgets; the preview `time_limit` property is not used as a bake deadline.

| Target | Samples | Preparation | Bake and packaging | Total |
|---|---:|---:|---:|---:|
| 30 s | 1 | 22.8 s | 5.8 s | 28.6 s |
| 60 s | 128 | 25.5 s | 34.7 s | 60.2 s |
| 120 s | 400 | 23.3 s | 97.0 s | 120.2 s |

A 16-sample calibration took 34.1 s total and 9.1 s for baking/packaging. The per-call intervals exclude Blender process launch; totals include source opening, mesh preparation and packaging. Each run starts a fresh process. Timings are observations on this machine, not hard deadlines or all-scene guarantees.

The 128-sample atlas differs from 400 samples by 0.297/255 per channel on average, versus 2.354/255 for one sample. This compares full encoded atlas images, including unused/unlit texels; it is not ground-truth accuracy or a native perceptual score. Classic and Wide native captures cover seven positions with Walker and menu for each study package.

## Reducing overhead and preserving source authority

One-sample unbatched runs exceeded 120 seconds and were stopped. Python stack dumps showed they were inside the bake operator, not spending that interval in mesh construction. Consolidating the roughly 1,800 detailed source objects into one temporary beauty mesh reduced the completed one-sample run to the 28.6-second total above. The batch realizes modifiers, transforms positions into world space, retains source UVs/material bindings and stores per-object generated/object texture coordinates as attributes. World-position procedural textures keep their coordinates. This batching is a derived study adapter, not a replacement editable source.

The shared pipeline now accepts explicit CPU/GPU selection, keeps receiver proxies out of the source selection, selects the destination mesh and passes selected-to-active mode explicitly to the bake operator. The receiver's image remains unlinked during baking. Bake metadata records backend, device, samples and mode. No global preferences are saved.

Roof normals and open gable orientation are corrected only in memory for the study. The exported study meshes have 3,649 triangles and 2,680 vertices. Registered source SHA-256 remains `2484856271cfba2b321515a7bf674f2aa5a728efaaf52844e93a6f8e3094c7ec`; the original source and production package are unchanged.

## Quality limits and verification

The sixty-second surface bake is the useful working target in this comparison: one sample is noisy, and doubling the whole-export time adds little native-size benefit. Roof textures stay on physical roof surfaces rather than being transferred by screen pixel to background walls.

Entrance defects remain at all sample counts. The existing culler retains only 5 of the fanlight's 16 triangles and deletes the right splayed reveal's two triangles. More samples cannot restore those surfaces. Receiver winding, open-surface semantics and corresponding bake rays require the remaining #1301 work before promotion. The study packages are review evidence, not accepted content.

Thirteen focused regression checks passed: a new actual CPU Cycles bake verifies the correct receiver gets red source emission, an intentionally green receiver proxy cannot contaminate it, and the active upstream sentinel image remains unchanged; existing exterior and EEVEE receiver checks also passed. The bake-metadata extension is checked by the same fixture. Candidate stage G1 passed for the sixty-second study. No goldens were recaptured.

Evidence lives under candidate `review/cycles-bake-study/`: each budget includes a full offline environment package, settings/timings and native captures. Reproduce with `study_cycles_surface_bake.py` through `offline_blender.py`, using `--samples 1`, `128` or `400`, the registered courtyard source and a fresh output directory. Unlike the prior frame experiment, these commands perform actual atlas baking.

To play the sixty-second Cycles study without changing shipping content:

```powershell
node tools/blender/stage_courtyard_candidate.js --output out/cycles-sixty-play --package projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/review/cycles-bake-study/60s/package
& "C:/Program Files/LOVE/lovec.exe" out/cycles-sixty-play/game
```
