# Batch A relics → editable Blender source migration

**Date:** 2026-08-15  
**Accepted materialization run:** GitHub Actions `31910912055`  
**Review artifact:** `9253630728` / `a-item-source-migration-review`

## Question

Batch A originally tested a semantic-sculpture vocabulary: meaningful revolved volumes and named parts rather than one large anonymous polygon mesh. Once editable `.blend` documents became the production source-authority model, the useful question changed:

> Can the semantic/revolve intent live directly inside ordinary Blender source documents, or does production still need an external A geometry backend?

The migrated relics are:

- Forbidden Lamp
- Town Portal
- Crossing Writ
- Smoke Bell
- Mourning Ribbon
- First Scale
- Bell Salt
- Sealed Reliquary

## Result

**All eight Batch-A relics now have viable editable Blender source authority. A separate production semantic-sculpture geometry backend is not required.**

The central native construction is extremely small:

```text
editable 2D generating profile (Curve points)
        ↓
live SCREW / revolve modifier
        ↓
ordinary object transforms / named semantic assembly
        ↓
read-only evaluated runtime OBJ + MTL
```

A source does not have to use Screw everywhere. Named child objects, partial bands and linked repeated parts remain ordinary Blender construction. The important property is that the artist sees and edits the meaningful source handles rather than a baked output mesh.

## Visual target

The migration rendered two pre-migration boards through the real LÖVE item viewer:

1. the branch's current canonical runtime products;
2. the preserved `agent/relic-showcase` / PR #569 Batch-A products.

Those two boards were **byte-identical**:

```text
SHA-256
10a5b794fc7d5d5484681d54c14e0ca0cd9ec450ac033561a5466a5941e0c763
```

So, as with Batch B, the historical experiment's visuals had already become the canonical target somewhere in the integration history. This PR is principally a source-authority migration rather than a deliberate wholesale redesign.

The accepted Blender-source viewer board has SHA-256:

```text
abfac56759a61197c33b5d7420072fee0a94e67ec389fd11234d88ef77b0288a
```

It preserves the target closely. A few construction differences read positively in the real inventory presentation:

- Bell Salt's bowl reads more clearly as a genuinely hollow ritual font;
- Mourning Ribbon has slightly fuller material volume;
- Sealed Reliquary's base/arch assembly reads somewhat more materially substantial;
- First Scale remains deliberately graphic and flattened rather than becoming a generic thick 3D object.

No relic was rejected on visual grounds.

## What each source preserves

### Forbidden Lamp

The lamp body, roof, base, crown, seal and flame remain separate named semantic pieces. The body and other round volumes expose their generating profiles directly; cage rods share a linked source profile so changing the rod construction propagates to the cage.

### Town Portal

The three broken astrolabe rings are live partial revolutions with independent transforms. The open seams are therefore source-level construction rather than merely gaps in a baked mesh. Core, grip, pommel and repeated studs remain independently editable.

### Crossing Writ

Sheet, rollers, seal, cord sleeve and tail remain separate parts. The migration caught one useful modeling distinction here: a partial wrap should be a thin closed sleeve profile, not a partial revolution that touches the axis.

### Smoke Bell

The bell is the strongest pure-A proof. One closed editable profile describes the outer wall, rim and inner wall; revolving it produces a genuinely hollow bell. The clapper, lip, crown and soot band remain independent semantic objects.

### Mourning Ribbon

The bow loops are editable partial band profiles, while tails, knot and medallion remain separate. Flattening and asymmetry are ordinary Blender transforms rather than hard-coded generator parameters.

### First Scale

The scale remains a layered semantic assembly: main crystal scale, gold inset, iron inset, ridge and scars. The teardrop-derived profiles are flattened through ordinary object scale, which keeps source profile and thickness/depth art direction separate.

### Bell Salt

The font uses one closed hollow vessel profile. Its mineral shards share linked generating data but retain independent placement, rotation and scale handles; the salt bed and broken halo remain separate.

### Sealed Reliquary

The miniature shrine is intentionally an assembly rather than a one-piece mesh: base, foot, linked pillars, shrine core, arch, seal, chain, cross and finial remain named and directly editable.

## The partial-wrap failure

The first A materialization successfully wrote all eight `.blend` documents and compiled Forbidden Lamp and Town Portal, but Crossing Writ failed strict runtime validation with a zero-area triangle.

The cause was not Screw itself. The generic migration helper had represented the cord wrap as a *partial* sweep whose profile touched the revolve axis. On a full 360° revolution Blender can merge coincident pole vertices; on a partial revolution those repeated pole positions remain separate and produce degenerate triangles.

The accepted correction represents wraps as what they semantically are: a thin closed sleeve profile swept through only the desired angle.

This is a durable A rule:

> **Partial revolutions should not touch the revolve axis unless their pole topology is explicitly resolved.**

For hoops, wraps and open bands, use a closed off-axis section. For complete solids, axis-terminating profiles are fine because the full revolution can merge the pole.

## UV result

Unlike Batch B, A did **not** require a special source UV migration strategy.

The accepted Blender Curve + Screw sources export UV-bearing evaluated surfaces through the ordinary OBJ path and pass the existing corpus checks. `use_stretch_u` / `use_stretch_v` remain enabled on the authored Screw modifiers so Blender's generated revolve UVs follow the profile/sweep dimensions.

This is preferable for these procedural surfaces: their UV parameterization follows the actual revolve construction and remains source-native rather than being patched after export.

## Validation

Accepted run `31910912055` proved all of the following in one lane:

- canonical and preserved Batch-A reference boards rendered and were byte-identical;
- all eight authoritative `.blend` sources materialized successfully;
- all eight compiled runtime products passed strict runtime OBJ validation;
- the full item corpus remained green after the migration;
- the production `compile_item_blends.py --check` passed across **all 24 current Blender-authority item sources**;
- the eight new source `.blend` hashes remained byte-identical during read-only compilation;
- the post-migration board rendered successfully through the real item viewer.

The accepted source documents are intentionally higher-level than their runtime products. Resolved vertex/triangle count is not treated as an authoring-goal metric here; runtime decimation/optimization can be evaluated separately without compromising source authority.

## Architectural conclusion

Batch A survives primarily as a **semantic construction vocabulary inside Blender**:

- A lathe/profile → editable Curve generating section + live Screw;
- A hollow vessel → one closed wall profile + live Screw;
- A disc/dome/teardrop/rod → small readable generating profile;
- A band/hoop → off-axis closed section with full or partial Screw;
- A repeated semantic part → linked source data where shared editing is useful;
- A compound relic → named child-object assembly.

The result is much easier to inspect than the old external builder because the meaningful construction is visible in the same document an artist edits.

With A, B and C all translated successfully, the production architecture is now coherent:

```text
A: semantic profiles / revolved volumes
B: planar fabrication / symmetry / thickness
C: spatial paths / cross-sections / roll / taper
             ↓
        ordinary Blender authoring
             ↓
        committed .blend authority
             ↓
     read-only evaluated duplicate
             ↓
 deterministic runtime-valid geometry
```

There is no need to invent a universal Thestra modeling language before authoring real content. Blender already supplies the dependency graph; Thestra owns the resolved runtime contract below it.
