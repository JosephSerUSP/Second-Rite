# Blender authoring routes

Start with the intended result. Commands run from the installation root.
`assets/...` and `data/...` in authoring records belong to the selected Project.
Python asset tools consume `tools/semantic-roots.js` through
`tools/shared/project_paths.py`; set `SECOND_RITE_PROJECT` to select another
Project. Tools and contracts remain installation-owned; review output belongs
in `out/`. Node is required. Set `BLENDER_EXECUTABLE` to the exact version in
`blender-pin.json`; `python tools/blender/blender_locator.py` verifies it.

Start every Blender-side script with the launcher, never a hand-typed
`blender --python` command (Blender exits **0** when the script raises, so a
crash reads as success):

```text
python tools/blender/run.py tools/blender/<script>.py [--blend FILE.blend] -- <script arguments>
```

[SCRIPTS.md](SCRIPTS.md)'s **Run with** column says whether a tool runs inside
Blender (`run.py`), on the host (`python`, `node`) or is import-only.

| Intent | Entry point | Check before promotion | Lane brief |
|---|---|---|---|
| Choose a furnishing and its parameters | [Generated catalogue](recipes/FURNISHINGS.md); `furnishings_catalogue.py --check` | Dimensions include the complete built assembly; review placement context and material bindings | [Interior brief](../../docs/design/st-maria-interior-authoring.md) |
| Place scaffold props by relationship | `compile_room_spec.py`; [serving-corner example](recipes/examples/README.md) | Actual support face, measured gaps and declared keep-clear volumes; native visual review still required | [Interior brief](../../docs/design/st-maria-interior-authoring.md) |
| Edit or give an item useful source structure | Open its existing `.blend`; scaffold only a new item; `compile_item_blends.py --check` | Source hashes unchanged, runtime OBJ valid, corpus check, real item viewer | [Item source contract](../../projects/hichaukitoden-game/assets/authoring/items/README.md) |
| Author a St. Maria interior scaffold | `recipes/interior.py` + `recipes/furnishings.py`; edit an adopted source directly | Source record check; native capture across lane positions and surfaces | [Interior brief](../../docs/design/st-maria-interior-authoring.md) |
| Author a St. Maria exterior scaffold | `recipes/exterior.py`; structure example in `recipes/examples/exterior_reference.py` | Source record check; ground, near stack and native capture | [Exterior brief](../../docs/design/st-maria-exterior-authoring.md) |
| Bake an existing environment | `run.py` with `export_room_environment.py` or `export_exterior_environment.py`, output under `out/` | Package/source provenance and runtime capture; G1 and applicable G5 after integration | [Environment/export contract](../../docs/asset-pipeline/BLENDER_CORE.md) |
| Render a room plate from source | `stage_room_model.py` | Native composition at the supported surfaces | [Plate workflow](../../docs/design/town-authoring-known-good.md) |
| Build First Stratum props or depth-conditioned surfaces | `tools/asset-production/build_world_prop.py` or `generate_surface.py`; start with `--dry-run` | Asset-set checks and staged products; provider generation needs its own task authorization | [Production adapters](../asset-production/README.md) |
| Generate canonical scalar surface baselines | `tools/asset-gen/surface_baselines_v2.py` | `--verify`; Blender previews are derivatives | [Surface contract](../../docs/asset-pipeline/SURFACE_BASELINES_V2.md) |
| Browse or reuse library assets | `asset_library.py` for listings; `vendor_assets.py` for curated offline assets | Provenance and hashes; local listing/group checks | [Library contract](../../docs/asset-pipeline/BLENDER_CORE.md#browsing-asset-libraries-read-only) |
| Work interactively in Blender | `live_bridge/`; preserve the same source authority | Bridge tests plus the source's ordinary compile/export/native checks | [Bridge protocol and usage](live_bridge/README.md) |

The [generated tool-role index](SCRIPTS.md) classifies every top-level Python
and JavaScript file. Start with its supported entry points; studies and recorded
source surgery remain available for their original evidence. Add a role in
`SCRIPTS.json` when adding a tool, then run `script_index.py --write`.

Agents can query measured pieces without loading Blender or reading the whole
library: `python tools/blender/furnishings_catalogue.py --find "water"` prints
the matching builders, dimensions, signature and placement notes. `--build`
uses pinned Blender to regenerate all images and measurements; `--check`
checks coverage, input fingerprints and image integrity without rendering.

## Rules that keep authoring reliable

- Never regenerate an adopted `.blend`. Open and edit the document. Read
  `environment-sources.json` before a write; `save_source_blend` refuses an
  overwrite by default. Item sources are authoritative after creation.
- Studies, numbered revisions and dated reports are evidence. They are not
  production templates. The neutral exterior example teaches structure and
  must never be adopted as a shipping source.
- Never overwrite shipping products to preview an idea. Stage it, capture it,
  inspect it, then promote the reviewed result in the task's authorized scope.
- Never recapture a golden or rewrite a corpus/depth baseline just to clear a
  failure. Diagnose the difference and retain the owner approval boundary.
- Preserve character scale, thresholds, depth gaps, intermittent occlusion,
  near-band coverage and source lighting. The lane briefs define the camera
  contract. A structurally valid asset still needs visual review.

## Cheap checks and native review

```text
python -m unittest discover -s tools/blender/tests
python -m unittest discover -s tools/asset-production/tests
python tools/asset-production/check_item_models.py
python tools/blender/environment_sources.py --check
```

Host discovery runs every pure test. With no `BLENDER_EXECUTABLE`, integrations
report explicit skips. A configured missing/wrong Blender fails; it never
becomes a skip. For required integrations set `BLENDER_TESTS_REQUIRED=1`, as
the pinned Blender CI job does. Skips are missing coverage, not visual proof.

Capture prepares its own probe in a fresh canonical stage and restores borrowed
files even on failure. Engine errors return a trace instead of an interactive
error window. Use a new output directory for every evidence run:

```text
node tools/ci/stage-project-gates.js --output out/environment-review-stage
python tools/blender/capture_environment.py --game-root out/environment-review-stage --output out/environment-review-frames --map-id 28 --positions 1 3 6
```

This captures classic, 4:3, wide and a device surface. Choose lane positions
from the target map, including entrances and occlusion transitions. Review
the captured images; successful capture only proves that the runtime drew them.
