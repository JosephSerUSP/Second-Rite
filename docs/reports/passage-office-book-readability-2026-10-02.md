# Registry book and material readability

Revision 6 responds to the owner's observation that the records did not read as books and the room remained materially uniform. It directly edits the packed revision 5 source into a new document, preserving prior candidates and shipping content.

The previous shelf contents were anonymous stacks of pale rectangular parcels. They are now separately editable upright volumes with recessed page blocks, projecting cover boards, continuous spines, raised binding bands and pale spine labels. Three binding colours, varying heights and deliberate gaps distinguish the groups. The shared furnishing vocabulary now exposes `bound_volume`; this geometry is reusable outside the Registry.

The writing ledger has a wider open spread, raised gutter and sloping page blocks instead of two flat paper slabs. The cover and spine have a darker oxblood finish. These are shape and silhouette changes; there is no claim that fine written entries are legible in gameplay.

## Materials and scale

Local authored finish variants separate pale limewashed masonry, a muted green painted counter, walnut shelving, warm bench wood, cream rag paper and burgundy/green/ochre bindings. Flat finishes quiet the repeated coarse texture noise. They retain semantic registry bindings; the base material library and upstream textures were not recoloured. Variant sRGB palette values are converted to shader linear values explicitly. The room's existing practical lighting, shell and camera remain unchanged.

Closeups and native game frames were both inspected. At the Classic camera the selected upright volume projects to approximately 3.0 x 10.7 pixels; its label and bands remain small. The current open ledger projects to 16.9 x 2.7 pixels. These are bounding-box projections including potentially occluded geometry, not visible pixel counts. Consequently the room relies on grouped upright spines, height rhythm, colour breaks and pale labels rather than manuscript detail for its read at game scale. The shelf carcass closeup intentionally excludes the separately editable books; populated storage is assessed in the complete native frame.

The counter now separates from the masonry more clearly, and the records lose their identical parcel silhouettes. Rear storage remains relatively dark in native lighting. Visual acceptance and physical-phone testing remain open.

## Evidence

`out/registry-workflow/r6/readability.html` pairs revision 5 and 6 native frames at original size and nearest-neighbour enlargement, then shows beauty/clay inspections of six objects. `review.html` contains four-surface native/source/UI comparisons at five lane positions. `parts-r6/parts.json` contains shape dimensions and projected bounds.

The packed source is `projects/hichaukitoden-game/assets/authoring/candidates/passage_office/passage_office_r6.blend`. Reproduce it with `refine_registry_materials.py --source <revision5> --output <newRevision>`, followed by `registry_workflow.py --source <newRevision> --output <newRun> --exit-y 1.0833 --npc-y 4.5833 --npc-x 1.15`.

G1 passed for the revision 6 stage. The two capture-preservation tests and the Blender dependency-relocation test passed; the latter required setting the pinned `BLENDER_EXECUTABLE` in the invocation. Export and inspections verified the source hash remained unchanged. No goldens were recaptured and no production map binding was changed. Full staged units passed in the previous revision; this iteration changes source art and shared furnishing geometry only and does not claim a new full-suite run.
