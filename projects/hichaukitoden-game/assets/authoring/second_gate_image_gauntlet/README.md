# Second Gate image-assisted town gauntlet

This package tests two spatially distinct native-426x240 town directions from
empty Blender scenes, using the calibrated camera, mixed Walker presentation,
facade projection, and view-weighted atlas path established by PR #881.

## Directions and selection

- **A — civic waterworks:** an open bathhouse/causeway precinct. The generated
  plate supplied coherent copper plumbing, public mural bands, repaired mineral
  plaster, grouped arches, and water-stained masonry.
- **B — stacked reliquary market:** a compressed hill market around a shrine
  tower, with high walk, foreground posts, indigo awnings, votive cabinets,
  brick/timber repairs, drainpipes, and warm inhabited windows. B was selected
  because its vertical layering, warm/cool hierarchy, foreground compression,
  and route reveal produce the stronger sense of place and desire to explore.

The generated images remain surface-authoring inputs. Door slabs/recesses,
window blocks and trim, roofs/canopies, high-walk/cornice, foreground occluders,
continuous walk band, and collision volume are real geometry. Fine brick,
cracks, soot, paint, carved masks, symbols, pipes, and votive ornament remain
surface detail. No gameplay traversal is implemented.

## Runtime collapse

- TH_SOURCE: **10,228 triangles** (including the subdivided source-only masonry
  field and source detail).
- TH_RENDER: **424 triangles**, 290 vertices.
- Beauty atlas: **1024x1024 PNG**, 960,957 bytes.
- Allocation: #881 `bounded-camera`, three explicit projection-window samples
  (-96/0/+96 px), view bias 0.65, peak mix 0.35, minimum density 0.08. The
  allocator measured 217 faces: 27 nominally visible, 4 envelope-visible, 4
  offscreen-reachable, 69 occluded, 80 near-visible, and 33 strongly back-facing.
  Density multipliers ranged from 0.402 to 115.785; visible authored faces
  therefore received dramatically more atlas budget without culling rear faces.

Anchors in the selected Blender source define `spawn_player`, `walk_start`,
`walk_end`, `doorway`, `npc_market_keeper`, and
`npc_reliquary_warden`. The package also carries collision/walk bounds and real
foreground occlusion.

## Provenance

- Whole-facade plates: OpenAI built-in image generation, project-generated,
  prompts recorded by `direction_*/projection/projection.json`; no credentials
  are stored.
- Cobblestone diffuse/displacement: Poly Haven
  `cobblestone_pavement`, CC0.
- Stone, plaster, timber, roof, iron, windows, and lighting: procedural Blender
  materials in `tools/blender/build_second_gate_town.py`, project-generated.
- Walker: repository preview asset; preview-only and excluded from baking.

## Evidence map

- `directions_comparison.png`: both clays and both refined 426x240 directions.
- `generated/`: the two whole-facade treatments.
- `direction_*/control/`: beauty, depth, normals, and calibrated packet.
- `direction_*/projection/`: source blockout, generated projection, per-building
  ordinary-UV bakes, refined result, manifest, and inspection blend.
- `winner_evidence/runtime_tracking_actors_strip.png`: selected winner across
  the authored envelope with native nearest-filtered Walker previews.
- `winner_evidence/source_vs_runtime_center.png`: rich TH_SOURCE versus baked
  TH_RENDER at the center view.
- `exports/environments/second_gate_reliquary_market/environment.png`: final
  beauty atlas; the adjacent JSON records per-face allocation and bake metrics.

## Weakest remaining area

The surface-authoring hypothesis succeeds most strongly on projected facades,
but the current coarse collapse loses too much mid-building brightness and
small-window separation—especially around the central crossing—and the wide
foreground beam is heavier than ideal. This is ready for a gameplay-integration
spike, but a production art pass should improve that source/runtime tonal match
before owner acceptance as final town art.
