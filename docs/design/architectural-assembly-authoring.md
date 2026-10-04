# Architectural assemblies for environment authoring

Describe a place as connected building volumes before dressing its facade. A
volume needs a footprint, floor, enclosed walls, a coherent roof and declared
apertures. Adjacent rooms need matching internal passages. Foundations reach the
terrain; room floors do not redefine the map's traversal profile. Keep semantic
ownership in Blender's hierarchy so a room, roof or opening can be inspected and
edited as an assembly.

Treat windows as construction: a masonry aperture, reveal, sill and head, rebated
timber frame, individual panes, hardware and shutter leaves. Width and height
morph a stock construction. Hinges own leaf pose; 0 degrees closes a shutter and
180 degrees folds it against the wall. Use deliberate partial opening angles
where they improve shape and readability. Inspect front, oblique, side and rear
views before composing the window into a scene. A detail hidden from one view may
become the entire visible face from another.

Maintain two representations with different purposes. The editable source can
contain rounded profiles, louvres, mouldings, tile barrels and fine masonry.
Runtime surfaces retain the aperture depth, meaningful silhouette and parallax.
Fine relief can project onto simpler targets. A target must be absent from the
beauty source when it would conceal the construction being baked—for example,
an opaque shutter backing hides louvres viewed from behind. Surface simplification
must be evaluated from the authored view envelope, not one flattering screenshot.

Measure source construction, runtime triangles, useful atlas allocation and render
cost separately. Source complexity is a render/build expense; it is not a runtime
triangle budget. An optimization succeeds only when the native Classic and Wide
views preserve the intended construction with the actual actor and menu present.
Detailed source renders alone do not prove that the atlas carries those details.

Use the owning map's resolved camera and ground profile. Camera pitch, placement,
room floor datum and lighting belong to their authored contracts. Bake through the
environment package boundary; geometry experiments do not justify scene-specific
navigation or a second elevation authority. Adopted source files remain editable
authority, and regenerable scaffolds remain explicitly identified as such.

For tools and current measured evidence, see the courtyard candidate README and
its dated reports. This document describes authoring intent, not delivery status.
