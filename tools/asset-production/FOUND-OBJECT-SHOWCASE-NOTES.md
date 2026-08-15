# Found-object showcase: Batch B experiment notes

This cohort is a deliberate contrast to the six-item relic showcase in PR #571.
The goal is not to decide that one pipeline is globally better. It is to expose
what kinds of visual thinking each authoring approach makes cheap, and what it
silently encourages an agent to repeat.

## What Batch A made unusually easy

The pure-Python `lathe.py` + `parts.py` vocabulary is excellent at composition.
A model can be described as a readable hierarchy of bands, domes, rods, wraps,
scatters and transformed profiles. That gave the author a lot of time to think
about silhouette, material hierarchy and symbolic identity rather than mesh
plumbing. Deterministic UVs and normals also came almost for free.

That was the best part of the approach: iteration stayed semantic. "Give the
reliquary another broken halo" is nearly the same instruction in prose and in
code.

## What became difficult in Batch A

The vocabulary has a strong gravitational field. Rings, halos, radial ribs,
lathed bodies and evenly repeated satellites are cheap, so they become tempting
answers to unrelated design problems. The six relics remained distinct, but a
family resemblance emerged that was partly Second Gate art direction and partly
the affordances of the tool.

The second limitation is local deformation. A bent cage member, a torn organic
edge, a bored-through hole, a fork that curls out of plane, or a slab with one
missing chunk is much less natural to express with surfaces of revolution and a
small parts vocabulary than with a general mesh modeler.

## Batch B hypothesis

Batch B uses Blender-native procedural modeling through the shared asset core:

- custom polygon extrusions;
- explicit polyline tubes converted to mesh;
- off-axis primitives;
- a real boolean void;
- linear rather than radial repetition;
- intentional missing/broken members;
- Smart UV projection after arbitrary mesh construction.

The cohort is deliberately physical rather than heraldic:

- **Cerberus Fang**: curved harvested tooth, root tissue, repair staples, barbs;
- **Mimic Tongue**: broad flesh, mismatched fork, torn underside, papillae;
- **Forbidden Lamp**: crooked open cage whose negative space is the main form;
- **Pile Bunker**: compact industrial mechanism, rails, side chamber, crank;
- **Celestial Fossil**: irregular slab, actual through-hole, raised fossil spiral;
- **Phoenix Pinion**: arcing quill, uneven linear vanes, missing and charred areas.

No material overlay passes are authored in this batch. That is intentional: the
comparison should reveal what the geometry itself is doing rather than letting
Batch B borrow Batch A's strongest surface trick.

## Questions for the eventual A/B review

1. Which batch produces more memorable silhouettes at the actual item-view size?
2. Which batch feels more like one coherent game without collapsing into one
   repeated construction grammar?
3. Which source is easier for a human to read and art-direct?
4. Which source is easier for an agent to vary without accidental sameness?
5. How much authoring time is being spent on object design versus mesh plumbing?
6. Do Blender-native deformation and negative space justify the heavier compiler
   dependency and less automatic UV topology?
7. Should the long-term item language be one system, or a layered system where
   semantic parts cover common forms and Blender-native recipes are the escape
   hatch for objects that need deformation, holes or asymmetry?

The expected useful outcome is probably not a winner. It is a boundary: a clearer
sense of which visual problem belongs to which level of the authoring stack.
