# Item grammar study — findings

The intended question was whether the C spatial-sweep grammar or unrestricted Blender-native modeling produced stronger versions of the same three items. The first controlled run produced a more fundamental answer: **the two producer paths do not yet share an equally enforced resolved-mesh contract.**

## Result 1 — Cerberus Fang is a valid direct comparison

Both Cerberus Fang exports load through the authoritative item viewer.

C spends its representation on the continuous hooked/tapered body plus three root branches. The Blender-native version adds local narrative topology: segmented construction, root tissue, repair staples and backward barbs. Blender uses 179 vs 126 vertices, 290 vs 146 authored faces, and 35 vs 22 object-specific recipe LOC. Its three-axis silhouette IoU against C is 0.312, so the two authors made materially different gross-form choices.

The useful boundary is not “Blender can curve and C cannot.” C expresses the main spatial body naturally. Blender earns its heavier representation when the art direction depends on arbitrary local damage, repairs, attachments, booleans, or other topology that is not conveniently described as a changing cross-section along a path.

## Result 2 — Mimic Tongue and Phoenix Pinion expose a validation gap

The pinned Blender-native Mimic Tongue and Phoenix Pinion OBJ files pass the study's offline parsing/UV/silhouette analysis, but the real runtime rejects each with `mesh contains a degenerate face` and displays fallback geometry. The C versions load normally.

This is not an aesthetic loss for Blender; it is a producer/runtime contract failure. Those two Blender cells in the committed contact sheets are therefore evidence of fallback behavior, not evidence about the authored models' visual quality.

`engine/geometry/model.lua` deliberately calculates a face normal for every triangle and rejects exact zero-area triangles. `lathe.write_obj` already mirrors this requirement before writing A/B/C-style products. The Blender/shared-export route needs an equivalent post-export validity check.

## Result 3 — representation cost still tells us something

Across the three authored OBJ files, before considering runtime validity:

- C: 519 vertices, 587 authored faces, 116 object-recipe LOC.
- Blender-native: 979 vertices, 1,742 authored faces, 161 object-recipe LOC.
- Blender/C ratio: 1.89x vertices, 2.97x authored faces, 1.39x object-recipe LOC.

That extra geometry is not automatically waste: the Blender recipes deliberately use independently controlled local pieces and detail. But the study supports keeping C as a compact first-class language for continuous spatial form rather than treating Blender as the default way to get curvature.

## Architectural implication

Do **not** merge A, B, C and Blender into one giant authoring API. Their different biases are useful. Converge them lower down instead:

`authoring dialect -> resolved geometry/finalization contract -> presentation/export`

The shared contract should eventually include at least valid non-degenerate triangles, UV/material binding, normals, coordinate conventions, provenance, and any future junction/union resolution. A/B/C can remain comprehensible Studio-facing dialects; Blender can remain the unrestricted escape hatch.

## Next controlled pass

First add runtime-parity degeneracy validation to the Blender/shared-export route, repair/re-export only the two invalid pinned recipes without changing their intended designs, and rerun the exact same neutral/as-authored four-angle comparison. Only then should Mimic Tongue and Phoenix Pinion be included in the artistic C-vs-Blender judgment.
