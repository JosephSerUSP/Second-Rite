# Central environment rendering

`render_profiles.py` owns renderer and quality for maintained environment previews
and both exporters. Defaults use Cycles at 0 EV: 64 samples for draft, lookdev
and export, and 128 for review; four total bounces, two diffuse/glossy bounces,
and a fixed seed. Frame previews use OIDN. Cycles baking itself leaves denoising
off; the atlas then receives fast chart-isolated OIDN to avoid filtering across
UV islands. Cameras,
source lighting and map profiles retain their authored authority. Atlas default: 1024.

Both exporters accept `--render-profile`, `--samples`, `--cycles-device`.
AUTO uses an available GPU backend, otherwise CPU, and records the actual device.
Explicit GPU requests fail when unavailable. No preferences are saved.
`--bake-backend eevee` selects the comparison projection. EEVEE face-ID, opacity and
UV passes are technical measurements, not beauty policy. Historical comparisons,
reference recipes and the logo toolkit retain explicit selections.

Cycles batches evaluated beauty meshes once, retains named UVs and per-object
Generated/Object coordinates, excludes receiver-only proxies and bakes only the
active receiver image. Connected Object Info dependencies fail explicitly because
consolidation would change their meaning. Builds never fetch dependencies.

Approximately 60 seconds is a working target measured on the courtyard/GTX 1650,
not a hard deadline. Completed exports record effective quality and pipeline time;
use `tools/ci/time-step.js` to include source opening and export preparation.
Slow exports require profiling; never ship partial atlases to meet a timer.
Existing sources and shipping packages are not rewritten by these defaults.

Saved source settings should match effective rendering quality, including viewport
samples and denoising. The courtyard scaffold saves Cycles64, 0 EV and Classic
256x240. This does not authorize rewriting adopted sources.

## Atlas allocation and pixel boundaries

The exterior `--atlas-layout view` uses calibrated runtime poses and supports
`--atlas-view-bias` from 0 (world-area density) to 1 (peak visible camera-area
density), with a nonzero density floor. Allocation does not delete geometry.
When omitted, exterior bias and atlas size consume the source's
`export_atlas_view_bias` and `export_atlas_size` properties. Current courtyard
values are 1 and 1024. This is area-equivalent allocation, not project-from-view
UVs or guaranteed anisotropic 1:1 density; #877 tracks the wider view-envelope work.

UV chart boundaries align inward to pixel corners, not pixel centres. Whole
charts retain their original UVs if alignment would collapse/flip triangles,
escape chart bounds or introduce shared texels. Bake dilation and isolated
denoising complement these guards; none proves all receiver correspondence.

## Review and authority

Review source beauty/clay and runtime clay/atlas independently, then inspect
native Classic and Wide frames at lane ends and intermediate positions, with
and without the menu. `inspect_environment_surfaces.py` produces independent
views; `capture_courtyard.py --unobstructed` exposes the full native world frame.
Wide retains Classic's logical optics. A convincing gameplay frame alone can
hide missing surfaces or textures projected onto the wrong geometry.

Fine joinery, masonry and paving can bake down; coherent roofs, openings,
building volumes and important silhouettes must survive as geometry. Compose
the entire frame behind the menu. Foreground occluders should be separated
masses with gaps and depth, rather than continuous barriers across the player.
The current courtyard foreground is an unaccepted experiment, not a template.

The library is repository-local; acquisition is deliberate and builds never
fetch. See `vendor-library/README.md`. Scaffold/adopted authority remains in
`environment-sources.json`. For the session's evidence map and continuation
constraints, see `docs/reports/blender-workflow-consolidation-2026-10-01.md`.


## Receiver correspondence

Both environment exporters accept `--bake-bindings <json>` for a sampled geometric
preflight before beauty baking. The authored contract lists receiver names, allowed
source-name patterns and optional front-normal directions/alignment thresholds.
Receiver identity survives proxy joining and culling; detailed source identity
survives batching. Four barycentric points per bound front-facing triangle must
reach an allowed source using the configured no-cage extrusion/distance. Missing,
culled, reversed or wrongly associated receivers fail before a package is written.
`bake-correspondence.json` records successful checks and geometric failures.

The check is opt-in and covers the surfaces listed in the contract. It is not an
exhaustive texel test, shading test or owner visual acceptance. Smooth bound normals
are rejected because this implementation samples flat receiver normals. Explicit
structural box receivers carry `sr_bake_preserve`; the culler retains these faces
while still treating the boxes as closed occluders. The door family can generate
these boxes while detailed bevels remain only in the source.
