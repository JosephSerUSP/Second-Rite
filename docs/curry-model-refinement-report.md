# Curry model refinement report

## Scope

This change updates only the curry item model and its companion material file.
No other asset was intentionally edited for this PR.

## Baseline review

The original OBJ was rendered from six fixed camera angles before editing. The
visible weaknesses were:

1. The lower form read as a featureless rectangular block rather than a serving vessel.
2. The top food form appeared as a thin, floating faceted cap.
3. The silhouette was nearly square from the front and side.
4. There was no visible rim, lip, handle, utensil, garnish, or curry-specific cue.
5. The underside shadow made the top piece look detached from the base.

## Structural alternatives

Three different silhouettes were built and rendered from the same six angles:

- A rounded ceramic bowl with a curry mound.
- A handled cooking pot with a raised loop handle.
- A shallow platter with an asymmetric curry mound.

The rounded bowl was selected because it had the clearest serving-vessel profile,
the strongest food readability, and the most balanced silhouette across the
angle set.

## Refinement cycles

### Cycle 1

Render inspection found that the first bowl version still read like a smooth
lidded disk. Geometry was revised to add a recessed interior, separate curry
pieces, dark gravy, and three garnish leaves. The next six-angle render showed
an unambiguous bowl of food.

### Cycle 2

Render inspection found that the first spoon was too long and floated outside
the bowl. The spoon was shortened, lowered, and placed against the rim. The
next six-angle render showed the spoon as an integrated serving detail.

### Export cleanup

Inspection of the exported OBJ found that the presentation ground plane had
been included accidentally. The export was rebuilt with the ground, camera,
and lights removed. A fresh six-angle render of the actual exported OBJ
confirmed that its bounds contain only the curry model.

### Material correction

The first exported MTL contained named material groups but assigned every group
the same white diffuse color. The material file was corrected so the groups now
render distinctly: brown ceramic, orange curry, dark gravy, green garnish, and
gold-toned spoon. The corrected OBJ/MTL pair was rendered again from all six
angles.

## Final deliverables

- `assets/models/items/curry.obj`
- `assets/models/items/curry.mtl`

The final model is a rounded curry bowl with a recessed gravy base, three
distinct curry pieces, garnish leaves, and an integrated spoon. The progression
contact sheet was preserved locally during review at
`tools/asset-gen/out/curry_refinement/curry_progression_contact_sheet.png`.

## Verification

- Baseline: six renders completed before geometry changes.
- Alternatives: three structural redesigns rendered from identical angles.
- Refinement: each geometry revision was preceded and followed by rendering and visual inspection.
- Final export: six-angle render completed after removing presentation-only geometry.
- Materials: final six-angle render confirms non-white material separation.