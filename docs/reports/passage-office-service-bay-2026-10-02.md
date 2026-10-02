# Registry: supported counter and a connected divider

The owner found revision 8 functional but too rectangular after removal of the detached masonry frame, and noticed a floating countertop. Inspection confirmed a source geometry error: the counter carcass ended at 0.8096 m while the slab underside began at 0.92 m, leaving a 0.1104 m gap.

Revision 9 raises the existing carcass's upper vertices to the existing slab underside, preserving the joined object, materials and UVs. The shared `furnishings.counter` builder now extends its carcass to the underside of its slab. A regression test checks supported tops and overhanging footprints at three authored heights.

A wall-connected L-shaped timber service screen restores a distinct service bay. Front uprights meet the counter ends, a narrow open transom runs above the serving opening, and a low painted side return with open timber rails meets the rear wall. It is joinery associated with the counter and perimeter, rather than the earlier detached masonry portal. Daylight, window construction, wall art, foreground plant, native camera and event anchors are retained. The new screen uses shared `furnishings.service_screen` geometry.

`out/registry-workflow/r9/service-bay.html` compares revision 8 and 9 in native Classic, Wide and nominal device views, with closeups and clay views of the supported counter and connected screen. The full `review.html` includes four surfaces at five lane positions with and without UI, plus source views using native camera records. The Classic and device centre frames were visually inspected; the divider restores a visible counter silhouette while preserving the rear records and window. This is a candidate judgment, not owner acceptance.

G1 passed for the revision 9 stage. The counter-support regression, two capture-preservation tests and source-authority check passed. Export and inspections preserved the source hash. Full staged units were not repeated for this source-art iteration, and no golden images were recaptured.

The packed source is `projects/hichaukitoden-game/assets/authoring/candidates/passage_office/passage_office_r9.blend`. `define_registry_bay.py` performs the bounded edit on an existing source and refuses overwrite. Revision 8 and all previous documents remain available. Shipping maps and environment bindings are unchanged; visual acceptance and played interaction remain open.
