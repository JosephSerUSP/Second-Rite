# Editable Blender item-authoring study

This experiment tests a different source-of-truth assumption from the earlier A/B/C item cohorts.

The question is not merely whether a procedural recipe can produce a good runtime OBJ. It is whether the authored item can remain a useful, understandable Blender document that a human can open, inspect, and art-direct without destroying the construction history.

## Result

The experiment supports a **per-item `.blend` source-authority model**.

The important boundary is now:

```text
human / agent creates or edits item.blend
  sparse profiles / curves / cutters / source plates / modifier stacks
        ↓
committed .blend is source authority
        ↓ read-only compile
temporary evaluated duplicate
        ↓
runtime OBJ + MTL
        ↓
runtime-parity geometry validation
        ↓
LÖVE item geometry contract
```

Blender is the authoring/composition environment. Thestra still owns the resolved runtime geometry contract. The runtime does not need Blender, and a successful Blender export does not get permission to violate the runtime's mesh rules.

`tools/blender/build_editable_item_study.py` remains useful as a **bootstrap/scaffolding recipe** for creating these first source documents. Ordinary compilation does not run it and must not overwrite the committed `.blend` files.

## Why source regeneration was rejected

An intermediate hosted pass regenerated the five `.blend` files from an unchanged recipe. Blender produced five binary-only Git changes even though the intended authoring structure was unchanged.

That is enough to reject regenerate-on-CI as the normal source model. If a human opens a `.blend` and improves it, an external recipe must not be allowed to silently replace that work; even an unchanged recipe also creates review-noisy binary churn when the document is saved again.

The final compile lane instead hashes every committed `.blend` before opening it, evaluates/exports the existing document, hashes it again, and fails if any source byte changed. That proof is green for all five specimens.

Blender `.blend1` workstation backups are explicitly excluded from the source tree. They are safety copies, not asset semantics.

## Five specimens

These are intentionally non-canonical study assets. They do not replace item database paths or current game models.

- **study_screw_reliquary** — A-like sparse profile meshes with live `SCREW` and `BEVEL` modifiers.
- **study_fabricated_mask** — B-like planar shell with live `SOLIDIFY`, `BEVEL`, and explicit Boolean lens cutters.
- **study_curve_fang** — C-like spatial gesture kept entirely as two editable `CURVE` objects with per-point radius/taper; it deliberately has no mesh source.
- **study_segmented_spine** — one fabricated vertebra repeated, tapered, and deformed along a C guide with `ARRAY` + `SIMPLE_DEFORM` + `CURVE`, plus a visible curve cord.
- **study_phoenix_pinion** — A+B+C hybrid: Screw-authored clasp, curved rachis/guide, two fabricated vane sources repeated/tapered along the guide, and a fabricated ember tip.

The hybrid Phoenix source reopens as six named authored objects: four meshes + two curves. Its live modifier vocabulary is `ARRAY`, `BEVEL`, `CURVE`, `SCREW`, `SIMPLE_DEFORM`, and `SOLIDIFY`.

## Saved-source proof

The compiler does not trust binary files merely because Blender can open them. Every committed source is reopened in a fresh Blender process and checked for its intended authoring structure.

Validated reopen summaries:

```text
study_curve_fang       objects=2 meshes=0 curves=2 modifiers=[]
study_fabricated_mask  objects=4 meshes=4 curves=0 modifiers=[BEVEL, BOOLEAN, SOLIDIFY]
study_phoenix_pinion   objects=6 meshes=4 curves=2 modifiers=[ARRAY, BEVEL, CURVE, SCREW, SIMPLE_DEFORM, SOLIDIFY]
study_screw_reliquary  objects=2 meshes=2 curves=0 modifiers=[BEVEL, SCREW]
study_segmented_spine  objects=3 meshes=1 curves=2 modifiers=[ARRAY, BEVEL, CURVE, SIMPLE_DEFORM, SOLIDIFY]
```

The first strict checker usefully exposed a bad architectural assumption: it required every source to contain a mesh and therefore rejected the healthy curve-only Fang. The invariant is now authoring-neutral: retain editable mesh **or curve** source geometry plus the item-specific expected structures.

Every source also embeds an `AUTHORING_README` Text block and marks its export root with `sr_source_authority = blend` and `sr_study_only = true`.

## Runtime boundary proof

`tools/blender/compile_editable_item_blend.py` opens an existing source document and delegates evaluated export to `second_rite_asset_core.export_asset_root()`. The shared core duplicates the hierarchy for export and applies modifiers only to the evaluated product.

`tools/blender/validate_item_obj_runtime.py` then validates the resulting OBJ. It deliberately mirrors the runtime's hard non-degenerate-triangle rule rather than assuming that a successful Blender export is sufficient. This responds directly to the earlier controlled C-vs-Blender study, where Blender-native Mimic Tongue and Phoenix Pinion products were writable but rejected by `engine/geometry/model.lua` as containing degenerate faces.

All five current products pass:

```text
study_curve_fang       72 vertices / 84 faces / 112 triangles
study_fabricated_mask  124 / 248 / 248
study_phoenix_pinion   724 / 1296 / 1316
study_screw_reliquary  416 / 774 / 774
study_segmented_spine  420 / 768 / 784
```

The final hosted compile also proves the before/after SHA-256 hashes of all five `.blend` sources are identical.

## Review lane

Visual review is intentionally separate from compilation.

An early version rendered four Eevee views per item inside the build and spent minutes in hosted software rendering. Saving/exporting the five authoring graphs themselves took only seconds, so expensive review should not sit on the authoring critical path.

`tools/blender/render_editable_item_blend.py` now opens the **same committed `.blend` source**, renders four inexpensive Workbench views, and never saves the document. The review workflow also checks source hashes before and after rendering.

The visual pass supports the construction architecture while preserving useful art-direction failures:

- **Curve Fang** is a clean proof that C can be a curve-only editable source.
- **Fabricated Mask** preserves real Boolean eye holes and demonstrates how naturally B maps to Blender.
- **Segmented Spine** proves B-along-C composition, but its uniform repetition still reads mechanically.
- **Phoenix Pinion** proves A+B+C composition. A first review caught a wrongly rotated clasp floating out of plane; correcting one live source transform repaired it without changing the composition model. The vane array remains intentionally useful evidence that procedural repetition does not automatically produce organicity.
- **Screw Reliquary** is a straightforward proof that A-like profile/revolve authoring remains compact and understandable as a Blender stack.

The next hybrid experiment should therefore pressure-test **Geometry Nodes / instance variation**, especially per-point scale, tilt, spacing, missing members, and authored exceptions along a C path. The lesson is not that hybrid composition failed; it is that `ARRAY + CURVE` is an intentionally simple repetition grammar.

## Responsiveness and footprint

The first five source documents are individually small, roughly **89–94 KB each**. That makes one `.blend` per authored item substantially more plausible than one monolithic binary item library.

Once Blender is available, opening/evaluating/exporting these small sources is fast. The slow operation in this study was hosted beauty-style rendering, which is now outside the compiler lane.

The generated JSON manifest mirrors object names, types, curve/mesh counts, and live modifier stacks so ordinary PR review has text evidence about a binary source without pretending `.blend` itself is meaningfully diffable.

## Paths

Authoring source:

```text
assets/authoring/items/studies/blender_editable/*.blend
```

Compiled runtime products:

```text
assets/models/items/studies/blender_editable/*.obj
assets/models/items/studies/blender_editable/*.mtl
```

Text inspection product:

```text
docs/reports/blender-item-authoring-study/generated-manifest.json
```

Core study tools:

```text
tools/blender/build_editable_item_study.py       # bootstrap/source creation only
tools/blender/check_editable_item_blend.py       # reopen/source-structure gate
tools/blender/compile_editable_item_blend.py     # read-only source -> runtime product
tools/blender/validate_item_obj_runtime.py       # runtime-parity geometry gate
tools/blender/render_editable_item_blend.py      # read-only Workbench review
```

## Architectural implication

A/B/C now look more useful as **construction vocabularies inside an editable Blender document** than as mutually exclusive production generators:

- A: profile / revolve / semantic volumes;
- B: outline / thickness / Boolean fabrication;
- C: curves / taper / spatial gesture;
- hybrid composition: parenting, modifiers, instances, and eventually Geometry Nodes.

The durable contract belongs below them:

```text
editable Blender authoring graph
        ↓
read-only evaluation / finalization
        ↓
runtime-valid resolved geometry
        ↓
OBJ today / another runtime format later
```

This argues against merging the earlier A/B/C experiments wholesale merely to canonize their external Python builders. Their shape ideas and recipes remain valuable evidence and migration material, but a production item-authoring architecture should preserve the editable `.blend` as source and compile **from it**, not regenerate it.
