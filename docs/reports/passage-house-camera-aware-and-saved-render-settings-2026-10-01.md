# Passage House camera-aware allocation and saved render settings

Revision 16 remains a staged scaffold. Paving extends from x=-24 to 8 and
lane-axis y=-16 to 32. Perimeter and background street volumes extend past the
review envelope. Player movement retains its 12 m lane and authored elevation.
The extension supplies geometry; owner acceptance of foreground composition is
still pending.

The exterior exporter now exposes `--atlas-view-bias` on the existing `view`
layout. Zero uses uniform world-area density; one uses peak visible footprint
across eleven calibrated lane poses, with a nonzero floor for unseen islands.
The command defaults to the source's `export_atlas_view_bias`, and atlas size
similarly consumes `export_atlas_size`; explicit CLI values override both.
The candidate saves bias 0.5 and a 1024 atlas. Geometry culling stays separate.
Legacy layout remains a distinct fixed-ground-share historical control.

Visibility measurement now uses a one-sample Cycles emission ID pass. Each
package records poses, bias, density floor, demand and packed density statistics.
These are area-equivalent texels per peak screen pixel before guarded corner
snapping, not anisotropic/projective 1:1 UVs. Issue #877 remains open for richer
view envelopes, expected demand and accessibility weighting.

| Bias | p10 | Median | p90 | Whole export seconds |
|---|---:|---:|---:|---:|
| 0 | 0.450 | 0.940 | 3.036 | 61.14 |
| 0.5 | 0.793 | 0.919 | 1.987 | 59.42 |
| 1 | 0.910 | 0.912 | 0.919 | 84.75 |

Each run uses the same source and 1024/64 quality. First control preceded explicit
AUTO device selection in the ID adapter; tiny-face counts differ slightly across
CPU/GPU. Timings include allocation, are not controlled cache-cold comparisons,
and do not enforce a cap. Native matched poses support judging the visual change.

Bounds-based admission now preserves a long loose wall intersecting the envelope,
where centre-based admission discarded it. A negative control verifies this while
excluding an unrelated off-range object. Whole-building admission remains intact.

Opening the saved source yields Cycles, GPU scene mode, final and viewport samples
64, denoising enabled, 0 EV and Classic 256x240 output. Viewport sampling previously
inherited Blender's heavier default. Hardware availability remains process-local;
the explicit launch configures available devices without saving global preferences.
Source hash and reopened settings are recorded in candidate review/measurements.json.

Selected runtime: 5,785 triangles, 3,430 vertices; atlas UV occupancy 49.5507%.
Source beauty: 213,298 triangles. Occupancy alone is not a quality verdict: view
allocation changes chart shapes and priorities relative to the historical layout.
Complete controls, 42 native frames and eighteen independent source/runtime surface inspections live in review/camera-aware/.

An additional source-default export (no atlas-size or bias flags) resolves the saved
1024/0.5 settings, takes 59.0009 seconds and reproduces mesh/collision bytes.
Twenty atlas pixels differ by at most one byte; no deterministic bake claim.

G1, staged units, source registry, town checks, two editor/geography tests, seven
atlas tests, nineteen exporter/profile tests and three recipe/assembly tests pass.
The saved-settings assertion was moved before test camera studies changed the
in-memory resolution; reopened source settings were verified independently.
Seven native Effekseer assertions remain unavailable. No runtime viewport code or
goldens changed this revision; prior absolute G5 baseline mismatches remain open.
Narrow window/head-strip correspondence remains Issue #1301. PLAYED acceptance is
owner-bound.

Reproduce with a fresh output directory:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --disable-autoexec --python-exit-code 1 -P tools/blender/offline_blender.py -- tools/blender/export_exterior_environment.py -- --blend projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend --output out/court-view-review --span 12 --margin 6 --atlas-layout view --keep-full-ground --source-lighting --camera projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/camera.json --bake-bindings projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/bake-bindings.json
```

Source-owned defaults select 1024 and bias 0.5. Add `--atlas-view-bias 0` or `1`
for the endpoints. Scripts deny Python networking; this is not a machine-wide
network isolation claim. Existing adopted source files and shipping topology are
unchanged.
