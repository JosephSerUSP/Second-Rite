# Passage House courtyard candidate

This editable scaffold and package are review candidates. Map 32 is added only to a
copied Project; shipping maps and the town generator remain unchanged. Owner visual
and traversal acceptance precede promotion.

From the repository root, stage the committed package without Blender or networking:

```powershell
node tools/blender/stage_courtyard_candidate.js --output out/passage-house-play
& "C:/Program Files/LOVE/lovec.exe" out/passage-house-play/game
```

Use a new output directory each time. The introduction still enters lodging map 25.
Leaving its door now reaches the court's upper landing; walk left through the court
to Cortiço. The Cortiço entrance retains its existing identity and position. Existing
saves are test artifacts: use a fresh game to review the candidate route.

`32.json` owns the walk profile: level 0–2 m, a 0.30 m rise over 2–8 m, then a level
covered landing to 12 m. `scene.json` records source/package/library inputs. Staging
writes `datum.json`: the entrance samples Cortiço's doorway height, and lodging's
local zero corresponds to the court's upper landing. No Cortiço flattening occurs.

The editable source is `../../environments/passage_house_courtyard.blend`, registered
as a scaffold in `environment-sources.json`. Never overwrite an adopted source.
The recipe refuses existing output paths. For a new scaffold copy:

```powershell
$blender = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
& $blender -b --factory-startup --disable-autoexec --python-exit-code 1 -P tools/blender/offline_blender.py -- tools/blender/recipes/passage_house_courtyard.py -- --output out/court-new-source.blend
```

Export the committed source through the existing environment package boundary:

```powershell
& $blender -b --factory-startup --disable-autoexec --python-exit-code 1 -P tools/blender/offline_blender.py -- tools/blender/export_exterior_environment.py -- --blend projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend --output out/court-new-package --span 12 --atlas-size 1024 --bake-backend eevee --source-lighting
```

EEVEE uses 0 EV and the authored light rig. Detailed doors/windows stay in the source
and project onto four receiver cards. Geometry remains for silhouette, passage posts,
roof and paving. Grass is omitted. The exporter's `sr_bake_role` contract is documented
in the exterior authoring brief; separate source/receiver roles require EEVEE.

For new captures (these do not replace goldens):

```powershell
python tools/blender/capture_courtyard.py --game-root out/passage-house-play/game --output out/court-native-review
& $blender -b --factory-startup --disable-autoexec --python-exit-code 1 -P tools/blender/offline_blender.py -- tools/blender/review_courtyard.py -- --source projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend --map projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/32.json --out out/court-source-review --quality review
```

`review/` preserves five positions at Classic/Wide sizes in the source and actual
runtime with Walker/menu, plus a full-geometry runtime comparison. Native runtime
captures retain the Project's current night sky; the static courtyard lighting is
baked. This is evidence for review, not owner PLAYED acceptance. See the dated report
for measured costs, hashes, tests and limitations.

Promotion must update the owning generator or authored-map authority. Do not promote
by copying staged JSON over generated shipping output.
