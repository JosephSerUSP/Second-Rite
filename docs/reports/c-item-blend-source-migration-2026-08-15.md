# First production C item Blender-source migration — 2026-08-15

## Scope

This migration moves four salvaged Batch C / spatial-gesture item models from runtime-product-only status to real per-item Blender source authority:

- Barbed Spear
- Blackroot
- Cerberus Fang
- Water Scepter

The starting runtime models are the canonical files landed by #582. The destination contract is the production `.blend -> OBJ/MTL -> runtime validation` pipeline landed by #583.

This is deliberately **not** a baked-OBJ import wrapped in a `.blend`. The Blender documents preserve editable spatial construction: separate Curve objects for semantic parts, per-point path coordinates, radius/taper, tilt, material bindings, and an ordinary item export root. Once materialized and reviewed, the `.blend` files become the source authority; the one-shot migration bootstrap was deleted.

## Source documents

| Item | Source size | Authoring shape |
|---|---:|---|
| Barbed Spear | 90,097 bytes | shaft + head + four barbs + binding curves |
| Blackroot | 88,718 bytes | trunk + five branch curves + sap curve |
| Cerberus Fang | 88,502 bytes | hooked fang + three root curves + gold scar |
| Water Scepter | 91,133 bytes | shaft + paired waves + pearl swell + gold curl |

The source files live under `assets/authoring/items/` and carry the normal production root metadata including `sr_source_authority = "blend"`.

## Migration standard

A technically successful compile was not considered sufficient. Every attempt was compared against the current canonical runtime models through the real four-angle item viewer (`engine/item_model_sheet.lua` / `presentation.item_model_view`). Two technically valid migrations were rejected before the final pass.

### Rejected pass 1 — coordinate-frame drift

The first compiled models were runtime-valid but visibly rotated into the wrong frame: the spear lay sideways, the fang became a horizontal tusk, Blackroot sprawled laterally, and the scepter staff no longer occupied the canonical vertical presentation.

Cause: the old C recipes authored coordinates directly in the OBJ interchange frame (+Y up). Production Blender source is +Z up, while the shared exporter maps Blender coordinates into OBJ. The preserved C coordinates therefore needed the legacy OBJ -> Blender source mapping before first save.

The migration was corrected at the source boundary. The final `.blend` files contain ordinary Blender-space geometry; there is no permanent legacy-coordinate adapter in the production pipeline.

### Rejected pass 2 — material-pass drift

After the axis correction, geometry was visually close but the item presentation still regressed. In particular, Cerberus Fang's ritual-gold scar became dull and Water Scepter lost part of the crystal/gold sparkle.

Cause: the canonical C MTL authored sphere-mapped runtime sheen:

```text
crystal     -> assets/models/matcaps/ruby.png
ritual_gold -> assets/models/matcaps/gold.png
```

Blender's stock OBJ/MTL exporter preserves ordinary material fields but cannot express Second Rite's bounded runtime overlay-pass vocabulary.

The fix is generic production infrastructure rather than a C-specific post-process:

- Blender materials may carry `sr_runtime_passes_json`;
- `tools/blender/item_mtl_runtime.py` validates the runtime vocabulary and two-pass shader bound;
- `tools/blender/compile_item_blend.py` finalizes those source-authored passes into emitted MTL;
- CI tests invalid UV sources, blend operations, pass counts, missing material sections, and successful injection.

Runtime-pass binding is intentionally per authored Blender material, **not globally implied by semantic material id**. Different uses of `crystal`, for example, may legitimately have different or no overlay stacks.

## Geometry comparison

The production Blender Curve representation is slightly less compact at the OBJ face/vertex level than the hand-written sweep output, while remaining in the same low-poly range.

| Item | Canonical C | Blender-source compile | Vertex change | Face-line change | Triangle change |
|---|---:|---:|---:|---:|---:|
| Cerberus Fang | 126v / 146f / 232t | 152v / 168f / 224t | +20.6% | +15.1% | -3.4% |
| Water Scepter | 174v / 196f / 328t | 208v / 252f / 336t | +19.5% | +28.6% | +2.4% |
| Blackroot | 161v / 189f / 294t | 192v / 204f / 272t | +19.3% | +7.9% | -7.5% |
| Barbed Spear | 147v / 170f / 266t | 200v / 216f / 288t | +36.1% | +27.1% | +8.3% |
| **Total** | **608v / 701f / 1120t** | **752v / 840f / 1120t** | **+23.7%** | **+19.8%** | **0%** |

The exact equality in aggregate triangle count is incidental, not a target, but it is useful evidence that editable native Curves did not create a meaningful runtime geometry explosion for this cohort.

Barbed Spear is the clearest remaining representational compromise: the old sweep recipe used intentionally flattened/an-isotropic cross-sections for its head and barbs, while this first native Curve source uses round bevel sections and preserves the original aspect intent as source metadata. At the inventory viewer's scale the visual difference is restrained, but this is strong evidence that the second C cohort should gain editable custom/profile cross-sections rather than forcing every gesture through a round tube.

## Final validation

The accepted materialization run was GitHub Actions run `31906274404`.

Observed results:

```text
runtime material-pass tests: 4 passed
ITEM MODELS OK
  items with models: 207
  duplicate_geometry: 11
  no_uvs: 124
  shared_file: 1

Cerberus Fang: RUNTIME OBJ OK, 152 vertices / 168 faces / 224 triangles
Water Scepter: RUNTIME OBJ OK, 208 vertices / 252 faces / 336 triangles
Blackroot:      RUNTIME OBJ OK, 192 vertices / 204 faces / 272 triangles
Barbed Spear:   RUNTIME OBJ OK, 200 vertices / 216 faces / 288 triangles

ITEM BLEND COMPILE OK: 4 source(s)
ITEM SHEET OK: 4 models, 1152x216 (before)
ITEM SHEET OK: 4 models, 1152x216 (after)
```

A second `--check` compile reproduced the committed products and the SHA-256 digest of every `.blend` remained unchanged before/after compilation.

The accepted A/B viewer artifact is `c-item-source-migration-review` from run `31906274404` (artifact id `9252436887`). It deliberately uses current `main` runtime models as the before side, not whatever products happened to exist on the migration branch from an earlier rejected attempt.

## Visual conclusion

The accepted after sheet preserves the canonical orientation, major silhouettes, and gold/crystal runtime passes. Blackroot is especially close; Cerberus Fang retains its hooked body/root structure and gold scar; Water Scepter retains its paired-wave gesture and material sparkle; Barbed Spear keeps the overall weapon read despite the simpler round cross-section.

A whole-sheet pixel difference was also computed as a rough drift diagnostic, not an artistic score. Mean absolute RGB difference was about 0.42 channel levels on a 0–255 scale. The remaining differences are localized geometry/normal/material precision differences rather than a wholesale presentation change.

## What this establishes

The migration strengthened the production contract in three ways:

1. **Visual review is part of source migration.** Compile-green/runtime-valid is a floor, not an approval signal.
2. **Coordinate conventions belong at explicit boundaries.** Legacy interchange coordinates are converted once when creating source, not carried as hidden permanent source semantics.
3. **Material presentation belongs to source authority too.** Editable geometry is insufficient if migration silently drops runtime sheen, grime, glow, or other authored pass information.

## Next C cohort

The remaining C items are intentionally deferred:

- Hermes' Boots
- Mimic Tongue
- Molten Manacle
- Phoenix Pinion

They exercise the next authoring requirement: custom/anisotropic cross-sections, broader ribbon/loft behavior, closed-loop profile control, and hybrid Curve/mesh constructions. The first cohort says native Curves are already an excellent source grammar for centerline-driven forms; the next step is to make cross-section intent equally editable rather than approximating it away.
