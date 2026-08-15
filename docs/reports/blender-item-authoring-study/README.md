# Editable Blender item-authoring study

This experiment tests a different source-of-truth assumption from the earlier A/B/C item cohorts.

The question is not merely whether a procedural recipe can produce a good runtime OBJ. It is whether the authored item can remain a useful, understandable Blender document that a human can open, inspect, and art-direct without destroying the construction history.

## Source / product split

The study treats each generated `.blend` as legitimate editable source material and the OBJ/MTL pair as a compiled runtime product:

```text
editable .blend
  curves / sparse profiles / cutters / source plates / modifier stacks
        ↓ temporary evaluated duplicate
runtime OBJ + MTL
        ↓ runtime-parity geometry validation
LÖVE item geometry contract
```

The runtime does not need Blender. Blender does not get permission to emit geometry the runtime cannot load.

## Five specimens

- **study_screw_reliquary** — A-like sparse profile meshes with live Screw and Bevel modifiers.
- **study_fabricated_mask** — B-like planar shell with live Solidify, Bevel, and Boolean lens cutters.
- **study_curve_fang** — C-like spatial gesture kept as editable Curve objects with per-point radius/taper.
- **study_segmented_spine** — one fabricated vertebra repeated, tapered, and deformed along a curve with a modifier stack.
- **study_phoenix_pinion** — hybrid A+B+C proof: revolved clasp, curved rachis, and fabricated vane sources repeated/tapered along an editable guide curve.

These are intentionally non-canonical study assets. They do not replace item database paths or the current game models.

## What must remain editable

The `.blend` files are rejected if their saved structure has collapsed into anonymous baked meshes. The hosted check re-opens every saved file and verifies the expected live operations/objects are still present.

In particular the study is looking for understandable handles such as:

- sparse profile meshes driving `SCREW`;
- planar source meshes driving `SOLIDIFY`;
- explicit Boolean cutter objects;
- editable `CURVE` splines;
- `ARRAY` + `CURVE` composition;
- taper/deformation before final export.

Every source file also embeds an `AUTHORING_README` Text block and marks its export root with `sr_source_authority = blend`.

## Runtime boundary

`tools/blender/validate_item_obj_runtime.py` validates every generated OBJ after Blender export. It deliberately mirrors the runtime's hard non-degenerate-triangle rule rather than assuming that a successful Blender export is sufficient.

This is a direct response to the controlled C-vs-Blender study, where Blender-native Mimic Tongue and Phoenix Pinion products were writable but rejected by `engine/geometry/model.lua` as containing degenerate faces.

## Generated paths

Hosted materialization writes:

```text
assets/authoring/items/studies/blender_editable/*.blend
assets/models/items/studies/blender_editable/*.obj
assets/models/items/studies/blender_editable/*.mtl
docs/reports/blender-item-authoring-study/previews/*.png
docs/reports/blender-item-authoring-study/generated-manifest.json
```

The generated manifest records each source object's type and modifier stack, making binary `.blend` changes at least partially inspectable in ordinary PR review.

## Decision this study should inform

If these files are pleasant to edit, A/B/C should be treated less as mutually exclusive generators and more as construction vocabularies that produce/operate on Blender-native authoring structures. Blender then becomes the composition environment while Thestra owns the evaluated geometry/export contract below it.

If the files are unpleasant, opaque, fragile, or difficult to regenerate without destroying hand edits, the repository should retain a stronger external procedural authority and treat `.blend` files as derivatives instead.
