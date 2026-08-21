# Second Gate human-made low-poly town gauntlet

## Result

Direction A, **Cinderbridge Market**, is the selected environment.  Its market
front, chapel, water-edge bridge, lamp, storage clutter and oversized barrel
give the 426x240 side view a stronger sense of place, human scale and visual
incident than direction B / Pinewatch Court.  B remains in the evidence folder
as a genuinely independent comparison, not as a lineage of A.

The scene was built from empty Blender state for each direction.  The winner
uses the calibrated side camera and shared Walker presentation from the landed
Blender authoring pipeline.  It contains the required `TH_SOURCE`, `TH_RENDER`,
`TH_COLLISION`, `TH_ANCHORS`, `TH_PREVIEW_ACTORS`, `TH_PREVIEW_ONLY` and
`TH_CAMERA_PREVIEW` collections.

## Evidence

- `evidence/a/a_early_426.png` and `evidence/b/b_early_426.png` — early clay
  compositions.
- `evidence/a/a_developed_426.png` and `evidence/b/b_developed_426.png` —
  developed native comparisons.
- `evidence/sourced_asset_contact_sheet.png` — selected sourced candidates.
- `evidence/winner/winner_source_426.png` — rich source render.
- `evidence/winner/winner_th_render_baked_426.png` — coarse TH_RENDER with
  source-derived baked atlas.
- `evidence/winner/source_vs_runtime_426.png` — baked runtime with Walker.
- `evidence/winner/winner_camera_left_96_426.png` and
  `evidence/winner/winner_camera_right_96_426.png` — authored window extremes.
- `evidence/winner/winner.blend` — final authoring scene with the corrected
  baked runtime imported into TH_RENDER; `winner_source_authoring.blend`
  preserves the pre-bake source authoring state.

## Accounting

- 21 unique sourced model candidates were actually imported and auditioned:
  16 KayKit and 5 Poly Haven.
- 11 sourced candidates survive in the selected winner: 8 KayKit and 3 Poly
  Haven.  The remaining visible structure is minimal glue geometry for ground,
  path, wall overscan, awning, steps, lights and collision.
- Source render mesh: 59,293 polygons before the coarse runtime collapse.
- Exported runtime: 6,216 triangles / 12,595 vertices.
- Atlas: 1024x1024, 6,060 packed per-face islands, 0.590 packed fraction,
  view-weighted over `-96 / 0 / +96` projection-window samples.
- Atlas PNG: 745,579 bytes, explicitly sRGB-encoded from the scene-linear bake.
- Exported runtime package: 1,984,876 bytes including environment, atlas,
  material library and collision.

## Assessment

KayKit was the most useful source for coherent architecture: market, tavern,
chapel, gate and bridge share a readable low-poly vocabulary.  Poly Haven was
most useful as a controlled contrast for hero-scale street props and helped
the set feel dressed rather than like an untouched pack.

The kitbash approach materially improved the fresh composition pass over the
same scene's initial glue-only massing: the town gained a landmark, inhabited
frontage, recognizable doorway/continuation cues and a stronger foreground.
This sterile run intentionally does not inspect or score previous town
attempts, so it makes no historical claim about outperforming earlier
procedural branches.

The weakest remaining area is the coarse runtime bake: it preserves silhouette,
scale, window rhythm and traversal space, but loses some source-specific prop
detail and produces broad blocky floor shadow transitions.  It is suitable as
an environment-design prototype, not production-final topology or material
quality.

## Traversal preparation

Anchors include `spawn_player`, `walk_start`, `walk_end`, `doorway`,
`npc_merchant` and `npc_watch`.  `TH_COLLISION` contains a bounded walk lane.
Gameplay traversal was not implemented.
