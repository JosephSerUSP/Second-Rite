# Item model fabrication: items 149–158

This batch replaces the ordinary item-view fallback for ten contiguous consumables with deterministic, low-poly OBJ models. The assets are deliberately compact and share the repository's semantic material vocabulary rather than embedding one-off presentation colors.

## Scope

| ID | Item | Model | Read at item-view scale |
|---:|---|---|---|
| 149 | Potion | `assets/models/items/potion.obj` | modest round smoked-glass bottle, wax closure |
| 150 | Hi-Potion | `assets/models/items/hi_potion.obj` | taller bottle, ritual-gold closure and body band |
| 151 | X-Potion | `assets/models/items/x_potion.obj` | six-sided crystal body with a sharper medicinal silhouette |
| 152 | Mega-Potion | `assets/models/items/mega_potion.obj` | broad heavy bottle, gold hardware and hanging cloth tag |
| 153 | Healing Water | `assets/models/items/healing_water.obj` | soft-bellied clear flask with a narrow waxed neck |
| 154 | Soma | `assets/models/items/soma.obj` | large ten-sided ritual flask with an emphasized central volume |
| 155 | Elixir | `assets/models/items/elixir.obj` | faceted crystal vessel with gold banding and cloth tag |
| 156 | Ether | `assets/models/items/ether.obj` | narrow, tall smoked-glass vial |
| 157 | Hi-Ether | `assets/models/items/hi_ether.obj` | broader crystal ether bottle with ritual banding |
| 158 | Dry Ether | `assets/models/items/dry_ether.obj` | squat hexagonal bottle, dark stopper and dry cloth tag |

All ten are assigned explicitly in `data/items.json`. No item points directly at `placeholder_question.obj`; the fallback remains available for records that still omit `model`.

## Design approach

The batch is a small prop language rather than ten unrelated miniatures. Potion tiers increase in physical ceremony as their effect and cost rise: the base bottle is plain, Hi-Potion becomes taller and banded, X-Potion turns crystalline and angular, and Mega-Potion becomes visibly oversized and tagged. The percentage-healing line then changes vessel language instead of merely scaling those shapes: Healing Water is soft and clear, Soma is broad and ritualized, and Elixir is a compact faceted reliquary-like bottle.

Ether uses a second progression. Ether begins as a narrow smoked-glass vial, Hi-Ether gains crystal volume and a gold band, and Dry Ether compresses into a squat hexagonal vessel with a dark stopper and cloth marker. This keeps HP and MP restoratives recognizable as related inventory objects without making them palette swaps.

## Deterministic tooling

`tools/asset-production/build_item_models_149_158.py` is the canonical fabrication script for the batch. It:

- reads RGB values from `tools/asset-language/materials.json` instead of owning a parallel palette;
- emits one shared `item_batch_149_158.mtl` and ten OBJ files;
- uses only `smoked_glass`, `crystal`, `wax`, `ritual_gold`, `dark_wood`, and `aged_cloth`;
- triangulates every face at construction time;
- rejects degenerate triangles, invalid face indices, undeclared materials, missing `mtllib` targets, off-center bounds, and zero-size meshes;
- assigns the ten canonical model paths in `data/items.json` and refuses to overwrite an existing different assignment.

A regeneration pass produced byte-for-byte identical Git blobs to every OBJ and the MTL already committed on the PR.

## Mesh audit

| ID | Vertices | Triangles | Bounds (min → max) | Materials |
|---:|---:|---:|---|---|
| 149 | 60 | 112 | `(-0.460,-0.855,-0.460) → (0.460,0.855,0.460)` | smoked_glass, wax |
| 150 | 68 | 124 | `(-0.440,-1.060,-0.440) → (0.440,1.060,0.440)` | ritual_gold, smoked_glass |
| 151 | 54 | 96 | `(-0.500,-0.890,-0.462) → (0.500,0.890,0.462)` | crystal, ritual_gold, wax |
| 152 | 76 | 136 | `(-0.620,-1.130,-0.620) → (0.620,1.130,0.620)` | aged_cloth, ritual_gold, smoked_glass |
| 153 | 60 | 112 | `(-0.520,-0.900,-0.520) → (0.520,0.900,0.520)` | crystal, wax |
| 154 | 82 | 152 | `(-0.580,-1.000,-0.558) → (0.580,1.000,0.558)` | crystal, ritual_gold |
| 155 | 62 | 108 | `(-0.540,-1.020,-0.468) → (0.540,1.020,0.468)` | aged_cloth, crystal, ritual_gold |
| 156 | 60 | 112 | `(-0.300,-1.070,-0.300) → (0.300,1.070,0.300)` | smoked_glass, wax |
| 157 | 68 | 124 | `(-0.480,-1.010,-0.480) → (0.480,1.010,0.480)` | crystal, ritual_gold, wax |
| 158 | 54 | 96 | `(-0.460,-0.910,-0.398) → (0.460,0.910,0.398)` | aged_cloth, dark_wood, smoked_glass |

Static validation passed for all ten assets: non-empty geometry, triangular indexed faces, indices in range, no degenerate triangles, declared semantic materials, resolvable shared MTL, centered bounds, and non-zero extent on every axis.

## Visual review

The ten neutral silhouettes were rendered together in a contact-sheet inspection. The review focused on whether tier changes survive thumbnail/item-view scale rather than on fine surface detail. The final set preserves clearly different width/height ratios, shoulder transitions, faceting, closures, bands, and tags; no two entries are simply the same bottle under a different filename.

The contact sheet is a review artifact, not a runtime dependency, so it is not committed with the game assets.

## Runtime validation

The repository's existing item-model viewer resolves an authored `model` path and falls back only when the field is absent or invalid. These ten records now provide explicit paths, and every OBJ's referenced MTL is present in the same directory.

GitHub Actions `verify` is the authoritative repository gate for the PR. Local LÖVE/Blender execution is not available in this connector-only environment, so this report does not claim a local G1/G5 or Blender run.
