# Controlled item-grammar comparison

The permanent study artifacts live under `docs/reports/item-grammar-study/`.

`compare_item_grammars.py` compares already-authored products from two pinned checkouts; it does not regenerate either modeling approach. This is intentional: the study is about the products and authoring surfaces that actually existed at the recorded refs, including producer/runtime incompatibilities.

Use `item-grammar-study.json` as the authority for refs, item identities, source recipe functions, and presentation angles. For a metrics-only reproduction, write into a temporary directory so the curated findings report is not overwritten:

```text
python tools/asset-production/compare_item_grammars.py \
  --blender-root <checkout-at-the-pinned-blender-ref> \
  --out-dir tmp/item-grammar-study-repro
```

For authoritative visual review, use the real LÖVE item viewer. The first controlled run is preserved in the report directory, including `runtime-compatibility.txt`; it found that the pinned Blender-native Mimic Tongue and Phoenix Pinion contain degenerate faces rejected by the runtime, so their committed Blender contact-sheet cells are fallback geometry. Do not interpret those two cells as artistic comparisons until repaired exports are rerun under the same controls.
