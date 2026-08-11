# Item-model completion audit

Date: 2026-08-11

## Inventory result

The authoritative `data/items.json` contains 207 items: 66 consumables, 124
equipment items, and 17 quest items. Before this pass, 82 items had model
assignments and 125 reached the question-mark fallback. After the pass, all
207 items resolve to an OBJ model; the only intentional sharing is the existing
`wind_charm.obj` representation for Wind Charm, Light Amulet, and Alert Charm.
There are 205 unique OBJ paths.

The machine-readable per-item inventory is
`tools/asset-production/complete-item-models.json`. It records every new item,
OBJ path, vertex/triangle count, and semantic materials.

## Acceptance specifications

All families use the runtime contract of Y-up OBJ coordinates, centered pivot,
relative `assets/models/items/` paths, a local MTL, no textures required, and
low-poly silhouettes that remain readable in the 80x80 item-view panel.

| Family | Identity and primary idea | Distinguishing read | Rejection conditions |
|---|---|---|---|
| Weapons | handheld implement with an unmistakable blade, shaft, hook, or head | blade profile, handle, guard, or specialized head | reads as a generic rod or loses its point of use |
| Armor and robes | wearable torso/garment mass | shoulder width, hem, cloth-vs-metal material, emblem | collapses to a flat token or cannot be read as wearable |
| Accessories | compact wearable/relic object | ring opening, bell body, feather/scale profile, lens pair, strap, or badge face | only decorative noise separates it from its family |
| Bottles and drinks | contained liquid or draught | bottle height/shoulder, neck, cap, or faceted glass | silhouette is indistinguishable from a coin or blank box |
| Food and incense | prepared serving or ritual consumable | dish/block mass, flame/wick, or culinary form | cannot be distinguished at gameplay scale |
| Quest props | document, reliquary, scale, or key object | closure, relief, lid, seal, or suspended emblem | reads as the generic fallback placeholder |

## Approach experiments and decisions

1. Historical Blender/AI-generated assets were treated as technical precedent
   only. Their valid OBJ/MTL conventions were retained, but their silhouettes
   were not used as an art-quality threshold.
2. Deterministic primitive composition was selected for the missing batch after
   comparing it with the existing generated library. It gives reproducible
   pivots, material assignment, family consistency, and intentional revision.
3. The first completion candidate used a generic branch for too many accessory
   names. One refinement pass split weapons into spear, sickle, club/fang,
   cleaver, bunker, and sword branches; accessories into rings, bells, lenses,
   feathers/scales, straps/garments, shields, and badge/relic branches; and
   consumables into food, incense/lamp, bomb, bottle, and clock/bell/nut forms.
4. The existing `bottle_family__angular.obj` emitted a runtime degenerate-face
   warning during the first real screenshot pass. It was replaced with a clean
   deterministic angular bottle export while preserving its item path and
   registry assignment.

## Classification

- Items 1-52: retain their established visual identities; items 7-9 are
  intentionally shared. `bottle_family__angular.obj` was revised for runtime
  validity.
- Items 53-72: retain the deterministic low-poly family batches already
  integrated into the database; their authored material vocabulary remains the
  technical and visual baseline for the new work.
- Items 73-207: dedicated deterministic models, generated from the family
  acceptance specifications above. No item is intentionally omitted.
- `placeholder_question.obj`: retain only as the fail-loud runtime fallback;
  it is not assigned to production content.

## Evidence and validation

- `lovec . validate`: `VALIDATE OK`.
- `lovec . savetest`: `SAVETEST OK`.
- Item-model unit coverage: 473 assignment checks and 34 viewer checks pass.
- The real `lovec . screenshots` path captured the item scene and the full
  screenshot suite after the completion pass. The earlier angular-bottle load
  warning disappeared after the revision.
- Existing full-suite limitation: `test_map_geometry_export` cannot create
  its map texture export directory in this environment. The item-model suites
  themselves pass; no golden assets were regenerated.

## Remaining review note

The runtime screenshots confirm loading, scale path, materials, and gameplay
presentation, but this repository does not currently expose a dedicated
four-angle OBJ contact-sheet command for all 207 item records. A human art
pass should still review the generated family sheets from front, three-quarter,
side, rear three-quarter, and top views before treating the procedural batch as
final art-direction gold. The geometry and evidence are intentionally kept
reproducible so that review can replace individual models without changing the
item contract.
