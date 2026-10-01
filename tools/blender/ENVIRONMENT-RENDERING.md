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
