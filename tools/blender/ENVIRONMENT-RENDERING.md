# Central environment rendering

`render_profiles.py` owns renderer and quality for maintained environment previews
and both exporters. Defaults use Cycles at 0 EV: 16 samples for draft, 32 for
lookdev and 128 for review/export, four total bounces, two diffuse/glossy bounces,
and a fixed seed. Frame previews use OIDN; atlas bakes leave denoising off. Cameras,
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
