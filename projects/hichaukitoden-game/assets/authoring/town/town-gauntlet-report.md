# Second Gate town gauntlet report

Date: 2026-08-20  
Workbench: `exp/town-gauntlet-workbench-20260820`  
Source: `origin/main` plus local, no-remote-write merges of the open camera and bake spikes.

## Outcome

The selected V0 town slice is attempt 08, **Lantern Threshold**. It is authored as a real Blender scene at [town-pilot.blend](./town-pilot.blend), previewed at the native 426x240 projection frame, and exported as the runtime package in [exports/environments/town_lantern_threshold](../../../../../exports/environments/town_lantern_threshold/).

Attempt 04, Twin Gables, received the highest blind external score. Attempt 08 was chosen after the scored pass because it preserves the warm readability of attempt 01 while improving the middle lane, doorway breathing room, and NPC beat separation needed for a horizontally traversable town slice. Attempts 07-09 were convergence candidates and were compared by the owner, not presented to the external evaluators as blind scores.

## Camera and asset validation

- The runtime calibration record is [thestra-town-camera.json](./thestra-town-camera.json).
- The record is emitted by the actual `presentation.world_camera_calibration.resolve()` path for the first-person session, not hand-entered Blender values.
- Required Blender parity gate passed with `maxPixelError=1.720587442832766e-05`, `wrongShiftError=8.519995490710272`, `wrongTranslationError=2.8900254567460877`, five offset cases, and eight samples per case.
- The preview uses the resolved eye and pitch, a 426x240 target frame, and a 256x144 composition frame. Projection-window proof renders are in [town-final-projection-window-strip.png](./town-final-projection-window-strip.png).
- The real [walker.png](../../character/walker.png) was validated as a 144x48 sheet containing six 24x48 frames. Frames 0, 2, 4, and 5 are used for the protagonist and NPC previews. They are excluded from the baked environment package.

## Gauntlet

The nine deterministic compositions are in the [render directory](./renders/), and the labeled overview is [town-gauntlet-contact-sheet.png](./town-gauntlet-contact-sheet.png).

| ID | Composition | Purpose / result |
| --- | --- | --- |
| 01 | Lantern Row | Warm lantern rhythm and centered doorway; dense but readable. |
| 02 | Quiet Shrine | Cool negative-space return lane; darker and quieter. |
| 03 | Market Turn | Broad market/awning story beat; weaker depth and focal clarity. |
| 04 | Twin Gables | Tall silhouettes and strongest external score; doorway competes with massing. |
| 05 | Canal Edge | Cool canal depth; water competes with protagonist contrast. |
| 06 | Gatehouse | Strong foreground portal and termination tower; right lane narrows. |
| 07 | Shrine Return | Refined 02: doorway nearer optical center and separated NPC beats. |
| 08 | Lantern Threshold | Refined 01: open middle lane and more doorway breathing room; selected. |
| 09 | Market Reprise | Refined 03: quieter center, but still less clear than 08. |

Blind external totals for 01-06 are the mean of OpenAI `gpt-4.1-mini` and OpenRouter `openai/gpt-4o-mini`, using the same ten visual criteria:

| Attempt | OpenAI | OpenRouter | Mean |
| --- | ---: | ---: | ---: |
| 01 | 6.3 | 6.0 | 6.15 |
| 02 | 5.8 | 5.0 | 5.40 |
| 03 | 5.4 | 5.0 | 5.20 |
| 04 | 6.7 | 7.0 | 6.85 |
| 05 | 5.6 | 5.0 | 5.30 |
| 06 | 6.3 | 6.0 | 6.15 |

The raw evaluator record is [town-blind-evaluation.json](./town-blind-evaluation.json), and the contact-sheet labels are driven by [town-score-summary.json](./town-score-summary.json).

## Bake/export census

The V0 package is produced by `tools/blender/town_environment_pipeline.py` from the canonical source blend. The package contains:

- 236 render triangles, 158 vertices, one material group.
- 512x512 baked atlas: 162,049 bytes.
- `environment.obj`: 13,955 bytes; `environment.mtl`: 134 bytes; `collision.obj`: 663 bytes.
- Manifest-reported package size: 176,801 bytes.
- Anchors: `spawn_player`, `focal_doorway`, `street_midpoint`, `foreground_occluder`, and `town_exit`.
- Source blend size: 1,840,064 bytes.

The exported mesh is [environment.obj](../../../../../exports/environments/town_lantern_threshold/environment.obj), the baked atlas is [environment.png](../../../../../exports/environments/town_lantern_threshold/environment.png), and the proof render is [town-baked-runtime-look.png](./town-baked-runtime-look.png). The proof hides source mesh and preview actors, renders only `TH_RENDER` with the exported atlas material, and keeps the authored lighting mood for visual comparison.

## Contract and compromises

The scene retains the V0 collection contract: `TH_SOURCE`, `TH_RENDER`, `TH_COLLISION`, `TH_ANCHORS`, `TH_PREVIEW_ACTORS`, `TH_PREVIEW_ONLY`, and `TH_CAMERA_PREVIEW`. Preview actors, guides, anchors, and camera collections are excluded from the bake. The source geometry is richer than the coarse render proxy; the package is intentionally a V0 proxy, not a production town asset.

Blender 4.1.1 was used. The authored ground datum is z=-2.0 because the validated runtime camera aims through the scene at the resolved pitch; this is recorded in the package bounds and anchors. No production movement, gameplay, save, golden recapture, or engine integration was added in this pass.

## Handoff

The next owner review is the source-versus-baked comparison. If the V0 composition is accepted, the next bounded slice is to connect the package to runtime traversal and test one short town route using the exported anchors. If it is not accepted, refine one composition family at a time; do not silently recapture goldens or merge the open camera/bake spike PRs without owner review.

Open remote work remains unmerged: PRs #850, #851, and #852; related issues #837, #838, and #695 remain open. This workbench made no PR merge, push, or golden-reference change.
