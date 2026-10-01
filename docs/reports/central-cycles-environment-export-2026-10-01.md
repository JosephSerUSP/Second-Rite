# Central Cycles environment export — 2026-10-01

The maintained environment previews and room/exterior exporters now consume the
shared Cycles quality policy in `tools/blender/render_profiles.py`. Review/export
use 128 samples, draft uses 16, lookdev 32, exposure is neutral, total bounces four,
diffuse/glossy bounces two, and the seed is fixed. Native image previews use OIDN;
atlas baking does not denoise across UV islands. Atlas defaults are centralized at
1024. Explicit comparison overrides remain available.

The study's source batching is now a shared production step. It evaluates modifiers,
preserves world placement, named UV layers and Generated/Object coordinates,
excludes receiver proxies, and bakes only to the selected active target image.
Connected Object Info dependencies fail rather than silently changing appearance.
Device selection uses available GPU backends or CPU and records the selection;
explicit unavailable GPU requests fail. No global preferences are saved.

Derived export copies repair closed-body winding and automatically mark boundary
or zero-volume sheets as open before parity culling. This retains roof geometry and
fanlight/reveal surfaces previously lost to invalid closed-body assumptions. Source
files remain byte-identical. This does not establish complete ray correspondence:
missing/wrong receivers and entrance shading remain visual/promotion concerns in #1301.

## Measurements

All measured packages use 128 samples and 1024 atlases on GTX 1650 OptiX.
Whole-process timings include Blender startup, source opening, preparation and export.

| Package | Whole process | Runtime triangles | Vertices | Rasterized UV coverage |
|---|---:|---:|---:|---:|
| Courtyard, first timed export | 66.6 s | 3,675 | 2,693 | 91.942% |
| Courtyard, repeated fresh process | 64.9 s | 3,675 | 2,693 | 91.942% |
| Alicia's bakery | 21.4 s | 3,208 | see measurements | 77.077% |

These are fresh Blender workers. The repeat follows prior GPU/file-cache use;
no isolated persistent-worker warm-cache measurement is claimed. Approximately
60 seconds remains a working target, not an enforced cap or a partial-atlas timeout.
UV coverage is polygon coverage rasterized with Pillow at atlas resolution; it is
not a lit-pixel fraction and differs from earlier allocator measurements.
Full hashes, actual pipeline intervals and package statistics are in candidate
`review/central-cycles/measurements.json`.

Source SHA-256:

- Courtyard: `2484856271cfba2b321515a7bf674f2aa5a728efaaf52844e93a6f8e3094c7ec`.
- Adopted bakery: `8453c716b259d494b3ddf1391cd1dd9a47aa641a4f1c38c194bd5aaaa7a960ed`.

Both source files were compared byte-for-byte against HEAD. The current staged
candidate package uses Cycles. Previous EEVEE package/captures/measurements are
preserved under `review/eevee-before-central-cycles/`. Shipping packages, maps,
topology, the town generator and adopted sources were not changed.

## Verification and visual limits

Passed: 25 focused Blender tests; 16 additional pipeline/source/profile checks;
six final profile/Cycles checks; source-manifest check; offline vendor-library
check; town generator check; staged G1 and full staged units on the delivered
candidate, including 1,455 courtyard assertions. Seven native Effekseer assertions
were unavailable because the shim is missing. No golden references were recaptured.

Regression checks include inverted closed-body winding, single/double-sided open
sheets, retained named UVs/object-local coordinates, target-only baking, immutable
source sentinel image and receiver-proxy exclusion. Prior tests expecting broken
untagged-sheet or inverted-source behavior were changed to assert corrected behavior.

Courtyard native Classic/Wide captures cover seven positions with Walker/menu;
bakery inspection renders show lane positions 2 and 5.5. Native entrance, middle
and bounds were inspected. The entrance still has harsh/dark shading, and the
bakery inspection is Blender's unlit package view, not a native gameplay acceptance
claim. Art quality and owner PLAYED acceptance remain open. Technical EEVEE
mask/UV/face-ID passes and historical renderer comparisons retain explicit engines;
this change does not migrate the separate logo toolkit or every historical recipe.

## Reproduction

```powershell
$blender = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
& $blender -b --factory-startup --disable-autoexec --python-exit-code 1 -P tools/blender/offline_blender.py -- tools/blender/export_exterior_environment.py -- --blend projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend --output out/court-central-export --camera projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/camera.json --span 12 --atlas-layout legacy --keep-full-ground --source-lighting
node tools/blender/stage_courtyard_candidate.js --output out/court-central-play
& "C:/Program Files/LOVE/lovec.exe" out/court-central-play/game
```

Policy and overrides: `tools/blender/ENVIRONMENT-RENDERING.md`.
