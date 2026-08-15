# Phoenix Pinion organic-hybrid authoring pressure test

**Date:** 2026-08-15  
**Accepted V2 materialization run:** GitHub Actions `31911503667`  
**Accepted review artifact:** `9253788203` / `phoenix-organic-hybrid-v2-review`

## Question

After migrating the original A, B and C item-model experiments into authoritative editable `.blend` documents, the remaining question was not whether Thestra needed a fourth geometry grammar. It was whether Blender's own dependency graph could combine the three useful authoring ideas without producing the procedural sameness seen in repeated feather/spine experiments.

Phoenix Pinion was chosen because it is a clear stress case: a coherent continuous C-style gesture wants repeated B-style vanes, but uniform repetition makes a feather read like a ladder. It also benefits from small semantic A-style hardware/ornament at its base.

The experiment therefore asked:

> Can a production `.blend` use Geometry Nodes narrowly as a repetition/variation layer while keeping the meaningful guide, source element and hero exceptions directly editable?

## V1 architecture

The first hybrid source replaced Phoenix's eight manually authored sparse C vanes with:

- **C:** two separate asymmetrical 3D guide Curves following the rachis;
- **B:** one explicit low-poly fabricated vane source mesh per side;
- **Geometry Nodes:** guide resampling, deliberate member omission, per-point instancing, deterministic scale envelope and local roll variation;
- **manual B exceptions:** three independently authored hero vanes outside the node graph;
- **A:** a small profile-driven gold calamus collar built with Screw.

The continuous feather body, gold spine and ember tip remained ordinary existing source objects.

The Geometry Nodes graph resolves instances before export. The runtime sees only ordinary OBJ/MTL geometry; no Geometry Nodes concept was added to the runtime.

## V1 technical result: accepted

V1 established the architecture successfully:

- the source `.blend` saved with the Geometry Nodes graphs intact;
- the strict runtime OBJ validator accepted the evaluated result;
- the entire item-model corpus remained green;
- `compile_item_blends.py --check` reproduced all 24 authoritative source products;
- source `.blend` hashes remained byte-identical during read-only compilation.

So the authoring graph was technically viable.

## V1 visual result: rejected

Real-viewer inspection rejected V1 as the final art result.

The generated vanes were structurally varied, but too many lived inside the existing broad continuous feather body. At actual inventory scale they read primarily as extra internal ribbing rather than as authored variation in the feather silhouette.

This was a useful failure: a sophisticated procedural graph is not valuable merely because it exists. If the variation does not survive into the presentation silhouette, it has not bought enough authorship to justify its complexity.

## V2: let the vanes own contour

V2 retained the same graph and source objects but changed the art direction rather than inventing more nodes:

- narrowed the continuous C body to 84% lateral scale;
- offset the left and right guide Curves slightly away from the centerline;
- reduced generated point/member counts;
- lengthened and swept the two B-authored source vanes;
- increased local fan/roll variation;
- slightly strengthened the two long manual hero vanes while keeping a short broken member understated.

This is deliberately a **fewer, clearer members** solution rather than an attempt to add more procedural detail.

The V2 real-viewer board reads more asymmetrically than V1. The vanes participate in the contour in the oblique views instead of disappearing into the continuous body, while the item remains recognizably the accepted Phoenix Pinion design.

The improvement is useful but not as transformational as the earlier Hermes' Boots Blender migration. That distinction is worth keeping: Geometry Nodes earned a place in the toolbox, not a mandate to rebuild every C item around it.

## Runtime cost

Accepted V2 product:

```text
576 vertices
656 face records
844 triangles
```

The preceding profile-based Phoenix product used:

```text
648 vertices
624 face records
792 triangles
```

V2 therefore does not create a vertex-count explosion; it actually resolves to fewer vertices while using slightly more faces/triangles to represent the explicit varied vane structure. No runtime decimation or optimization was introduced in this experiment.

## Authoring contract learned

Geometry Nodes is useful here only because the human/agent-facing source remains obvious:

```text
C guide curves
      +
B source vane meshes
      +
small deterministic variation graph
      +
manual hero exceptions
      +
A semantic collar
      ↓
resolved runtime geometry
```

The node graph is **derived construction**, not the sole source of artistic intent.

Durable rule:

> Use Geometry Nodes when authored structure needs repeated placement/variation, but keep the controlling guide geometry, source element and important exceptions as obvious editable objects in the `.blend`.

A graph that hides the important shape decisions inside opaque node constants is worse for this pipeline than a handful of explicit Blender objects.

## What Geometry Nodes has earned

This experiment does **not** create a new D vocabulary and does not make Geometry Nodes mandatory for C.

It earns one narrower escalation path:

- ordinary Curve profile is the baseline for C;
- manual authored repeated pieces are fine when repetition is sparse;
- Geometry Nodes becomes useful when many repeated pieces should follow an authored gesture with bounded variation and deliberate gaps;
- hero exceptions remain manual when they matter to silhouette or storytelling.

Likely good future uses include:

- feathers, spines and ribs;
- roots/branches with repeated thorns or leaves;
- chains/ornamental repeats that need controlled irregularity;
- architectural trims with damaged/missing members;
- hair/cloth accessory clusters where a guide gesture matters more than a grid.

It is not justified for a plain fang, rod, vessel, plate, mask or other asset whose useful source graph is already simpler without it.

## Validation

Accepted V2 run `31911503667` proved:

- V1 baseline rendered through the real LÖVE item viewer;
- V2 source edit saved successfully;
- Phoenix V2 passed strict runtime validation at `576v / 656f / 844t`;
- the item corpus remained green (`duplicate_geometry: 11`, `no_uvs: 124`, `shared_file: 1`);
- all 24 authoritative `.blend` products reproduced through `compile_item_blends.py --check`;
- source hashes remained unchanged during read-only compilation;
- V2 rendered successfully through the real item viewer.

## Architectural conclusion

The item-model authoring stack is now broad enough without inventing additional project-specific geometry languages:

```text
A  semantic profile/revolve
B  planar fabrication/symmetry/thickness
C  spatial guide/profile/taper/roll
GN optional repeated-detail variation
manual exceptions wherever art direction wins
              ↓
      authoritative editable .blend
              ↓
       read-only evaluated duplicate
              ↓
      deterministic runtime geometry
```

This keeps Thestra focused on a strong authoring/runtime boundary rather than competing with Blender as a modeling environment.
