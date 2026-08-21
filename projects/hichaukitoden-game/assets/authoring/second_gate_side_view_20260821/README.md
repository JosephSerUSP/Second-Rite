# Second Gate side-view town visual gauntlet — 2026-08-21

This package is the focused follow-up gauntlet on top of PR #881's Blender
authoring pipeline. It contains two environments built from empty Blender
scenes, two image-assisted facade directions, a selected winner, and a runtime
handoff package. The review authority for every image is native 426x240.

## Directions

- **Ashglass Aqueduct Quarter** — pale riverstone, water channels, teal civic
  ornament, balconies and a recessed route doorway.
- **Ember Bell Foundry Lane** — soot-dark basalt, copper roofwork, furnace
  windows, a real bell frame, awnings, chains and warm workshop light.

The foundry direction wins on sense of place, silhouette rhythm, foreground
occlusion, Walker integration and desire to explore. It is refined into
`winner/` and is the only direction carried through the runtime collapse.

## Evidence map

- `renders/initial/` — both clay blockouts.
- `renders/refined/` — both refined native environments.
- `generated/` — the two whole-facade image-generation treatments and their
  derived grayscale height inputs.
- `projection/*/control/` — calibrated depth/normal/control packets.
- `projection/*/result/` — geometry-conditioned generated, baked and inspection
  results for both facade directions.
- `evidence/` — contact sheets for direction comparison, projection comparison,
  camera-envelope continuity and source/runtime comparison.
- `winner/final_views/` — the selected foundry scene at the normal authored
  camera envelope: center, projection-window left/right, eye-up and pitch-up.
- `winner/comparisons/` — matched rich `TH_SOURCE` and baked `TH_RENDER`
  frames.
- `winner/package/` — `environment.obj`, `environment.mtl`, `environment.png`,
  `collision.obj` and `environment.json`.
- `winner/winner_source_and_baked.blend` — final inspection blend retaining the
  collection contract and both rich source and coarse runtime layers.

## Handoff facts

- Source: **1,826 triangles / 85 mesh objects**.
- Runtime: **180 triangles / 120 vertices / one joined mesh**.
- Atlas: **512x512**, view-weighted bounded-camera allocation, 90 UV islands,
  0.243 packed fraction.
- Camera envelope: five authored samples in `camera_envelope.json`.
- Required collections: `TH_SOURCE`, `TH_RENDER`, `TH_COLLISION`, `TH_ANCHORS`,
  `TH_PREVIEW_ACTORS`, `TH_PREVIEW_ONLY`, `TH_CAMERA_PREVIEW`.
- Anchors: `spawn_player`, `walk_start`, `walk_end`, `doorway`, two NPC
  anchors, and `foreground_occlusion`.
- Gameplay traversal is intentionally not implemented.

## Authoring judgment

Image generation helped most with the coherent facade language: window/trim
families, gutters, banners, repaired masonry, furnace windows, copper details
and lived-in surface variation. Blender retained massing, real doorway void,
bell frame, awnings, route, foreground depth and continuation geometry.

The bell frame, doorway, awnings, foreground pillars/beam, pipes, chains,
balcony/trim supports and the large roofline were promoted or authored as
geometry because they affect silhouette, occlusion or traversal. Small masonry,
paint, soot, window grouping and ornament remain image-assisted surface.

The runtime result is intentionally honest: it preserves the coarse route,
doorway void, depth and occlusion but is visibly flatter and darker than
`TH_SOURCE`. The weakest remaining area is runtime atlas richness/lighting,
not the selected source composition. A later runtime material pass should
improve that transfer without changing the camera, anchors or collision.
