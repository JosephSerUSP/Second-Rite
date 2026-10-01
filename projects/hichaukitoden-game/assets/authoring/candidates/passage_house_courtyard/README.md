# Passage House courtyard candidate

This editable scaffold and package are review candidates. Map 32 is added only to a
copied Project; shipping maps and the town generator remain unchanged. Owner visual
and traversal acceptance precede promotion.

The current review revision keeps the passage facade and covered entry, opens a central roof lightwell, and raises a backstreet skyline behind the lodging. The side court walls tie into the near Cortico dwelling. The saved camera uses the live town pitch of -17.5 degrees; `camera.json` is resolved from Map 32 by the runtime camera-calibration contract, and the shared town-camera solver pins the Walker at 48 px tall with flat-ground feet at y=128. The runtime package records that same calibration. `tools/blender/recipes/opening_families.py`
provides adjustable shared door/window families used by both the courtyard and the
existing exterior vocabulary. Fine joinery stays editable in source and bakes onto named runtime receivers.
Recessed casements retain jambs, sills and shutter silhouettes; shallow panels and
hardware bake into the atlas. Sage joinery, quiet limewash and a warm timber entry
define revision 8. The preserved EEVEE revision used supersampling 2 at 0 EV. The current candidate package uses the central Cycles export profile. The owner-rejected v1 screenshots and package are preserved under
`review/rejected-v1/`; current native Classic/Wide frames are under `review/runtime/`.

From the repository root, stage the committed package without Blender or networking:

```powershell
node tools/blender/stage_courtyard_candidate.js --output out/passage-house-play
& "C:/Program Files/LOVE/lovec.exe" out/passage-house-play/game
```

Use a new output directory each time. The source/review renders are a composition claim only; the courtyard remains staged and owner visual/traversal acceptance is still required. Revision 8 was captured natively at five lane positions in Classic and Wide; see `review/measurements.json` for the camera pin, package hashes, and gates.

The introduction still enters lodging map 25.
Leaving its door now reaches the court's upper landing; walk left through the court
to Cortiço. The Cortiço entrance retains its existing identity and position. Existing
saves are test artifacts: use a fresh game to review the candidate route.

`32.json` owns the walk profile: level 0–2 m, a 0.30 m rise over 2–8 m, then a level
covered landing to 12 m. `scene.json` records source/package/library inputs. Staging
writes `datum.json`: the entrance samples Cortiço's doorway height, and lodging's
local zero corresponds to the court's upper landing. No Cortiço flattening occurs.

The editable source is `../../environments/passage_house_courtyard.blend`, registered
as a scaffold in `environment-sources.json`. Never overwrite an adopted source.
The recipe refuses existing output paths. The complete scene, including context and skyline, builds in one run; no follow-up
refinement scripts are required. For a new scaffold copy:

```powershell
$blender = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
& $blender -b --factory-startup --disable-autoexec --python-exit-code 1 -P tools/blender/offline_blender.py -- tools/blender/recipes/passage_house_courtyard.py -- --output out/court-new-source.blend
```

Export the committed source through the existing environment package boundary:

```powershell
& $blender -b --factory-startup --disable-autoexec --python-exit-code 1 -P tools/blender/offline_blender.py -- tools/blender/export_exterior_environment.py -- --blend projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend --output out/court-new-package --camera projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/camera.json --span 12 --atlas-size 1024 --atlas-layout legacy --keep-full-ground --source-lighting --bake-bindings projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/bake-bindings.json
```

Cycles uses 0 EV and the authored light rig. Fine door/window detail stays in the source
and bakes onto receiver surfaces using selected-to-active. Geometry remains for silhouette, passage posts,
roof and paving. Grass is omitted. The exporter's `sr_bake_role` contract is documented
in the exterior authoring brief; separate source/receiver roles are supported by Cycles.

For new captures (these do not replace goldens):

```powershell
python tools/blender/capture_courtyard.py --game-root out/passage-house-play/game --output out/court-native-review
& $blender -b --factory-startup --disable-autoexec --python-exit-code 1 -P tools/blender/offline_blender.py -- tools/blender/review_courtyard.py -- --source projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend --map projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/32.json --out out/court-source-review --quality review
```

`review/` preserves seven positions, including both bounds at Classic/Wide sizes in the source and actual
runtime with Walker/menu, plus before/after comparisons against rejected revision 8. The original full-geometry
comparison remains under `review/rejected-v1/`. Native runtime
captures retain the Project's current night sky; the static courtyard lighting is
baked. This is evidence for review, not owner PLAYED acceptance. See [the refinement report](../../../../../../docs/reports/passage-house-courtyard-refinement-2026-10-01.md)
for measured costs, hashes, tests and limitations.

Promotion must update the owning generator or authored-map authority. Do not promote
by copying staged JSON over generated shipping output.

The Cortico return is an edge exit at lane y=0, with a visible opening through the low court wall. Edge transfers use the shared fade without the wall-door camera approach. Camera projection offsets stop at -72/+72 canonical pixels; the actor continues to the bounds.

Runtime camera samples feed both source review and atlas projection. After changing the authored camera, regenerate these records before exporting:

```powershell
& "C:/Program Files/LOVE/lovec.exe" tools/blender/runtime_lane_cameras . projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/32.json projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/camera-views.json
```

`inspect_architectural_assembly.py` provides neutral front, oblique, side and rear source studies, plus a roof-cut plan for room volumes. These are editable-source inspections, distinct from the native runtime captures.


The current package was exported through the regular Cycles exporter at 128 samples.
`review/central-cycles/` contains native courtyard comparisons and bakery inspection
renders; `review/eevee-before-central-cycles/` preserves the preceding EEVEE package
and captures. Central policy and explicit comparison overrides are documented in
`tools/blender/ENVIRONMENT-RENDERING.md`. Source and shipping maps remain unchanged.
The courtyard's entrance shading still needs visual authoring work and owner review.


Revision 12 corrects the portal's outward fanlight above the door header and gives
its masonry reveals a closed section ending at the jamb fronts. Simple structural
frame receivers retain the doorway volume while source bevels bake into the atlas.
`bake-bindings.json` owns critical portal receiver/source associations; export checks
sampled front-facing coverage before baking. This is not a full-texel or visual gate.
The light rig and 0 EV remain unchanged. Source authority remains scaffold.
