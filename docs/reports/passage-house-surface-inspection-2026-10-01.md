# Courtyard source and exported surface inspection — 2026-10-01

The owner's observation is confirmed: the current package has real visual defects. Native screenshots and the seven critical portal bindings were insufficient to certify the scene. This inspection changes neither the source nor package.

## Independent visual evidence

Candidate `review/surface-inspection/` contains twenty views: full-source Workbench clay, full-source Cycles beauty under the authored lights, exported Workbench clay, and exported atlas emission, from five independent cameras. The cameras cover the rear houses, two window angles, an oblique court view and the covered portal. Atlas emission adds no inspection lighting; existing baked shading remains visible. Source beauty uses AgX, atlas inspection uses Standard; these are structural/large-patch comparisons, not a photometric pixel-equivalence test.

The source has connected roofs, complete background facades and lit plaster inside the passage. The package has an incomplete background envelope, some large black surfaces, black window/head/reveal strips and a black passage recess. Source roof tile detail is reduced as intended; whole missing roof membership and exposed interior patches are different defects.

## Traced findings

The per-object centre filter (`in_square`, span 12 and margin 6) excludes 49 runtime candidate objects. It excludes the East street roof, rear wall, floor, return and several facade/window parts while admitting other parts of that same building. West street and Service wing are also admitted as fragments. This breaks architectural envelopes and can expose otherwise hidden, legitimately dark interior/back faces. Repair admission at a coherent assembly/volume boundary; increasing lighting or samples cannot restore excluded geometry.

Culling is a distinct operation. Retained West/Rear roofs survive with 9 of 10 faces; all inspected admitted background wall front faces survive. The East street roof is excluded before culling. This is not evidence of a general recurrence of the earlier inverted-roof-normal defect.

Centroid source rays find hits on the investigated window/background surfaces; a nonmissing hit does not establish correct correspondence. For example, Court casement 1 right reveal rays hit the fountain ceramic panel and decorative diamonds; shutter target rays also hit sleeping-wing walls and sills. Some head/reveal corner rays hit adjacent joinery. Some cross-hits may represent expected occlusion or intentionally baked mouldings, so the report records named hits rather than labeling all of them bugs. The source inspection also shows how close the fountain panel is to the window reveal. The family needs face-specific expectations and explicit treatment of louvre gaps, not just a broad window-prefix success check.

Many sampled black texels lie on undersides/interior faces. Their darkness is not automatically a missing bake. The exterior must avoid exposing those faces through a fragmented envelope. Other dark strips differ from the full-source view and require targeted face/ray/bake controls before accepting them as authored shading. The active/render UV layer is UVMap; all material indices reset to zero when the single atlas material is installed. Those two suspected state errors were ruled out in this source.

A real Cycles isolated front-face control with the other simplified receivers visible versus hidden changed mean linear RGB from approximately (0.1215,0.0905,0.0903) to (0.1385,0.1014,0.0997). Receiver occlusion affects illumination, but this control did not reproduce total blackness. It does not justify a blanket shadow-visibility workaround or establish one root cause for every patch.

## Reproduction and limits

Run `tools/blender/inspect_environment_surfaces.py --source <blend> --package <package> --out <directory>` through the normal network-denying Blender wrapper. OBJ import uses Blender's default coordinate conversion, and the tool checks imported bounds against environment.json before rendering. It verifies the source hash remains unchanged.

`tools/blender/study_environment_receivers.py` takes the same arguments, with optional --span/--margin. It reconstructs the current legacy-layout receiver mesh and records before/after culling counts, named centroid ray hits and dark atlas samples. These geometric probes are not Cycles texel-shading proof or exhaustive visibility coverage. Atlas lookup requires matching source/layout/export settings. The full package emission views inspect the actual committed OBJ/PNG directly.

The current registered source hash remains b1b989a3093e67dbefb8188a3b7b17c17d8445d4e4625fc96a0488c2947c6ec5. No shipping data, source geometry, package or goldens were changed. Both diagnostic commands ran successfully with source-hash guards; imported bounds matched the manifest. Broad gameplay gates were not rerun for this read-only inspection. #1301 now records these concrete failures and repair acceptance. Current visual/PLAYED acceptance remains outstanding, and further decorative refinement should wait for coherent assembly admission and wider correspondence checks.
