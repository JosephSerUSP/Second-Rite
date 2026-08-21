# Second Gate human-asset town gauntlet

Fresh visual gauntlet for the Second Gate side-view town brief, authored on 2026-08-21.
This is an experimental visual package; it does not claim gameplay traversal or replace
the existing Walker/runtime environment.

## Selection

Two independent empty-scene lineages were authored at the native 426x240 target:

- Direction A: market landing, civic spire, bridge, usable gate, foreground tree and
  awning, warm street-level props, distant hill and mountain.
- Direction B: ridge alley, church/tower massing, homes, bridge, gate, destroyed
  building, hills, trees and props.

Direction A is the selected winner because it reads most clearly as a lived-in town
landing while preserving a strong landmark, a usable doorway, a readable walk lane,
foreground framing, and deep continuation at both camera-window extremes.

## Asset provenance

All modeled scene assets are human-made, publicly sourced low-poly assets. No AI-generated
assets, scraping, paid assets, or API-generated imagery were used.

| Creator | Public source | License | Use in scene |
| --- | --- | --- | --- |
| Kay Lousberg | [KayKit Medieval Hexagon Pack](https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0) | CC0-1.0 | Architecture, walls, bridge/gate, hill/mountain, tree, flag and market props |
| Kay Lousberg | [KayKit City Builder Bits](https://github.com/KayKit-Game-Assets/KayKit-City-Builder-Bits-1.0) | CC0-1.0 | Bench and box clutter |
| Sergej Majboroda; Jarod Guest (sky edits) | [Poly Haven industrial sunset pure sky](https://polyhaven.com/a/industrial_sunset_puresky) | CC0 | Outdoor HDRI skybox and world lighting |

The HDRI is packed into the winner `.blend`. The selected KayKit model records and
local roles are listed in `provenance.json`.

## Blender contract

The winner source file contains the required collections:

`TH_SOURCE`, `TH_RENDER`, `TH_COLLISION`, `TH_ANCHORS`, `TH_PREVIEW_ACTORS`,
`TH_PREVIEW_ONLY`, and `TH_CAMERA_PREVIEW`.

The camera record is the Thestra calibration contract: perspective, pitch 0, 426x240,
fovHalfX 0.249328, fixed eye `(0, -31, 4.5)`, forward `+Y`, and a ±96-pixel projection
window envelope with small high/low eye samples. The three preview Walkers use the
existing `projects/hichaukitoden-game/assets/character/walker.png` sprite.

## Runtime package

The source-derived bake uses the calibrated camera envelope and view-weighted atlas
allocation. It contains 5,446 render triangles, 11,836 vertices, one material group,
and a 1024x1024 sRGB atlas. Collision remains a simple authored blockout and anchors
are explicit in `runtime-package/environment.json`:

`spawn_player`, `walk_start`, `walk_end`, `doorway`, `npc_anchor_01`, `npc_anchor_02`,
and `foreground_occluder`.

The runtime evidence is rendered from the exported OBJ/MTL/PNG package, not from the
authoring scene. A few dark triangular bake artifacts remain visible in the runtime
comparison; they are recorded as the current weakest presentation detail for a future
owner-directed refinement.

## Evidence

- `evidence/contact-sheet.png` — early A/B, developed A/B, selected source and runtime.
- `evidence/source-vs-runtime.png` — direct source/runtime comparison.
- `evidence/winner-extremes-sheet.png` — source at center, -96 and +96 window offsets,
  plus runtime.
- `evidence/early_A.png`, `evidence/developed_A.png`, `evidence/early_B.png`,
  `evidence/developed_B.png` — candidate progression.
- `evidence/camera_calibration.json` and `winner/camera-envelope.json` — camera records.

## Verification

Focused checks run against the authoring scripts and the existing camera/atlas/render
helpers. The full gameplay golden gates are not claimed because this change adds an
experimental visual asset package and does not alter gameplay data or battle behavior.
