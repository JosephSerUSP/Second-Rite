# Courtyard Cycles and geometry-loss studies (2026-10-01)

The owner observed missing runtime roofs and roof textures transferred onto background houses during full-geometry inspection. These studies keep the registered source and production candidate package unchanged. Source SHA-256 is `2484856271cfba2b321515a7bf674f2aa5a728efaaf52844e93a6f8e3094c7ec`.

## Frame budgets

Native 426x240 renders use the complete beauty geometry, authored lighting, runtime camera at lane y=5, AgX, 0 EV and OpenImageDenoise. Adaptive sampling is disabled and the sample ceiling is deliberately high so the requested time limit controls termination. The GTX 1650 uses OptiX; the first Cycles frame is cold and later frames reuse persistent data. The budgets are integration time, not a whole-process deadline: setup and denoising contribute to actual wall time.

| Cycles budget | Actual render-call wall time | Mean absolute 8-bit RGB difference to 120 s |
|---|---:|---:|
| 30 s | 38.4 s | 0.196 |
| 60 s | 69.8 s | 0.099 |
| 120 s | 120.8 s | Reference |

For both shorter outputs, the 95th-percentile maximum-channel difference is one 8-bit value. Only 0.122% of 30-second pixels differ by more than four values in any channel. This supports a 30-second look-development budget for this view; one denoised view is not an all-scene quality guarantee. Differences to a longer render are not error against ground truth. The matched EEVEE 64-sample reference took 28.6 seconds.

The images omit Walker and HUD to inspect architecture. They show the full 240-pixel source frame, including ground extent below the normal world/menu boundary. Their lower background is not a new runtime capture. Classic geometry composition occupies the first 256 columns under this authored canonical center.

## Export geometry loss

The audit retains original object identities on faces, admits the same proxy objects for each case, disables ground clipping and uses legacy UV layout to isolate culling. Each of the sleeping, arrival, service, west-street and rear-street roofs starts with 20 triangles; current culling leaves 2. Correcting only their closed-mesh normals in memory leaves 18 under the same culler. The veranda goes from 12 to 4 to 8. Open gables still need appropriate surface semantics. This reproduces geometry destruction rather than inferring it from images.

The roof recipe winds its outer skin inward. The culler offsets along face normals and performs closed-solid parity, so it classifies the reversed roof exterior as interior. Turning all culling off is a useful control, not the proposed permanent fix.

The projection bake has a separate correspondence problem: rich source beauty and simplified target UV passes can see different surfaces at the same pixel. It transfers color by pixel location without checking source/receiver identity or depth. That permits roof color to land on a wall behind a missing roof. Switching EEVEE beauty rendering to Cycles would still preserve this invalid transfer if the same projection scheme were used.

[Issue #1301](https://github.com/JosephSerUSP/Second-Rite/issues/1301) records the reproduced roof and correspondence defects. The safer next experiment is retained, correctly wound envelope geometry with rich detail baked onto matching surfaces. Cycles selected-to-active baking is a candidate, but the current pipeline explicitly forces CPU. These GPU frame timings do not establish whole-atlas bake cost or prove that 16 camera renders fit a 120-second whole-build budget.

## Reproduction and evidence

Run the two scripts through `offline_blender.py`, with a fresh output directory:

```powershell
& $blender -b --factory-startup --disable-autoexec --python-exit-code 1 -P tools/blender/offline_blender.py -- tools/blender/study_cycles_courtyard.py -- --source projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend --camera projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/camera.json --out out/new-cycles-study --budgets 30 60 120
& $blender -b --factory-startup --disable-autoexec --python-exit-code 1 -P tools/blender/offline_blender.py -- tools/blender/study_courtyard_geometry_loss.py -- --source projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend --out out/new-geometry-study
```

Images, frame hashes, device/settings, measured wall times and per-object triangle counts are in candidate `review/cycles-study/`. No goldens, shipping data, global preferences, registered source or production package were changed.

The prior hosted scaffold-parity failure came from rounding-bin equality across Windows/Linux floating-point rotations. The gate now compares geometry numerically within 10 micrometres, retains strict nonnumeric/topology equality, and proves that a planted millimetre displacement fails. Local source parity is rerun; hosted status is reported separately.
