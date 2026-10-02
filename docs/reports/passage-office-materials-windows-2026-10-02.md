# Registry: tactile materials, daylight and window coherence

Revision 7 edits the preserved revision 6 candidate directly into a new packed document. It responds to the owner's rejection of weak materials, requests for side daylight and coherent inside/outside windows, and preference for a few deliberate wall and foreground objects.

## Composition and materials

The screen-left wall now has a real 2.45 x 1.60 opening, segmented masonry above/below/beside it, and a motivated area light inside the aperture. Side daylight crosses the waiting side of the room. No sun or unrelated key light was added, and the camera, walk lane, registrar and exit anchors were retained.

The earlier flat limewash and green paint were replaced by authored procedural finishes. Limewash has low-frequency pigment/patina variation and fine relief; green paint has tonal variation and sparse exposed timber patches; timber has directional grain, while the plant pot uses rough unglazed clay. Palette values are converted from sRGB to linear shader values. These retain material semantics and bake through the existing room pipeline. The base library and upstream textures were preserved.

Additions are limited to three groups: a framed harbour painting above the waiting bench, three pinned notices beside the service opening, and one small foreground table carrying a potted plant. The plant is lit by the side window and remains away from the action lane and the threshold. This adds a near silhouette and an asymmetrical lit group, without a continuous foreground barrier. The notices carry visual ink rules, not invented dialogue or gameplay instructions.

## Window construction

Both rear and side windows use one shared `opening_families.two_sided_window` assembly. A declared outward wall normal determines every component's placement. External panelled shutters swing outward; interior glazed timber casements swing inward behind a fixed exterior iron grille. The paired leaves rotate around their jamb hinges, and reveal dimensions match the source wall apertures.

The same physical source assemblies were inspected from inside, outside and across the hinge, in material and clay views. A Blender geometry probe verifies shutter centres lie outside the reveal, casements lie indoors, and the grille stays in its fixed plane for both orthogonal wall orientations. The five existing opening-family tests still pass.

This establishes a coherent candidate construction, not a claim of shipping exterior parity. The retained Registry exterior massing in `recipes/st_maria_praca.py` has no corresponding detailed authored window layout, and no exterior source or production map was changed. These outside assembly views provide a concrete construction reference for that eventual facade authoring. Full facade placement and owner acceptance remain open.

## Review and verification

The before/after native comparison, seven individual objects, and inside/outside window inspections are collected in `out/registry-workflow/r7/materials-windows.html`. The native workflow captures Classic, 4:3, Wide and nominal 21:9 at five lane positions, with and without UI, and compares the room source using the native camera records. The nominal device is desktop simulation at 2100x900, not a physical-phone measurement.

G1 passed for the revision 7 stage. The actual Blender two-sided window probe, five existing opening-family tests and two capture-preservation tests passed. Source authority and vendor synchronization checks passed. Export and all inspections verified that the source bytes remained unchanged. No goldens were recaptured. Full staged runtime units were not repeated for this art-only iteration; the previously reported revision 5 run remains the most recent full-suite evidence.

The retained packed source is `projects/hichaukitoden-game/assets/authoring/candidates/passage_office/passage_office_r7.blend`. `enrich_registry_source.py` edits revision 6 into a new document and refuses overwrite. `surface_finishes.py` supplies the reusable procedural finish implementation. Source review and closeups use different lighting for their different purposes; material closeup detail is not alone evidence of in-game readability. Rear storage and counter remain deliberately darker than the window side and still require owner visual judgment.

The harbour painting was generated with the built-in image-generation tool, saved under the candidate's `art/harbour_painting.png`, and embedded in the source. Its exact prompt and provenance are retained in `art/harbour_painting.provenance.json`. It is a decorative candidate painting, not geographic authority for the town.
