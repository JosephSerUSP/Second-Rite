# Consumable model rework — 2026-10-05

Six legacy consumables from the 149–158 batch were re-authored from scratch as **authoritative per-item Blender sources**, not edited from the old shared bottle/profile generator:

- **Potion** — squat smoked-glass apothecary bottle with wax closure and cloth neck binding.
- **Hi-Potion** — deliberately four-sided medicinal phial with a live ritual-gold harness/rib assembly.
- **X-Potion** — six-sided crystalline biconic reliquary with gold equator and neck hardware.
- **Mega-Potion** — flattened field-canteen/grenade vessel with live handles, harness rings, stopper and cloth seal.
- **Healing Water** — clear pilgrim-gourd flask with waist/neck binding, wood stopper and curved carry cord.
- **Ether** — narrow ampoule/retort with gold calibration rings and crystalline needle cap.

## Source authority

The production authority is now:

`projects/hichaukitoden-game/assets/authoring/items/<item>.blend`

Each source contains exactly one `item_export` root with `sr_source_authority = "blend"`. Vessel bodies, collars and stoppers are sparse editable profile meshes with live **Screw** modifiers; ribs, handles, seals and cords use Blender **Curves** where spatial gesture is the useful editing handle. The first saves were created under the repository-pinned Blender 5.2.2 and then adopted as source documents. The one-shot bootstrap that created those first saves is removed after adoption; future edits operate on the `.blend` files themselves.

The runtime OBJ/MTL files are compiler products from `tools/blender/compile_item_blends.py`. No item database path or ID changed.

## UV and material treatment

Every revolved source profile declares an authored UV layer and lets the live Screw modifier generate stretched cylindrical UVs (`use_stretch_u` / `use_stretch_v`). The compiled outputs have UV indices on every face line. Materials use the existing semantic material registry through `second_rite_asset_core`; no new material IDs were introduced.

The compiled runtime OBJ/MTL pairs are mirrored byte-for-byte into the editor fixture so Studio and the game Project inspect the same products.

## Silhouette result

The re-authored six are measured using the same 64-pixel, three-view silhouette IoU method used by `item_model_corpus.py`. The worst pair is **X-Potion vs Healing Water at 0.8167 IoU**, below the **0.85** strict limit for new work. The two relationships that initially sat too near the bar were deliberately widened: Potion vs Hi-Potion is **0.7597**, and X-Potion vs Mega-Potion is **0.6802**.

## Verification

Before adoption, pinned-Blender CI successfully created all six first-save `.blend` documents and compiled every source through the production compiler. The adoption lane then installs those compiler products, removes only these six legacy/no-UV baseline exemptions, runs `compile_item_blends.py --check`, and runs the full item-model corpus gate before committing the source documents.
