# Six relics: generator-to-Blender content migration

Date: 2026-08-15

## Scope

This pass moved six established Second Gate relic models from generator-authored construction to individual editable Blender source authority:

- Black Hinge
- Chrysalis Sigil
- Qilin Bell
- Vial of Second Breath
- Meteorite Plate
- Philosopher's Stone

The items, IDs and gameplay data were not changed. This is an art/source-authority pass.

The starting design reference was the six-item relic showcase preserved on PR #571 / `agent/relic-showcase-items`. That branch still described `tools/asset-production/build_relic_showcase.py` as the source of truth.

## Baseline finding

The current canonical six-item LÖVE viewer board and the restored PR #571 board were byte-identical:

```text
39015ae369eb38b4bfd37f52dce823969a8091784d354a765fe58136635a1162
```

So #571's designs had already become the runtime visual target. This work did not need to revive an unshipped redesign; it needed to replace generator authority with useful editable Blender documents and improve the art where the new representation made that worthwhile.

## First Blender pass

The first source materialization produced all six `.blend` files successfully and compiled through the strict runtime boundary. The resulting board was:

```text
5b3705705fcb96db44dee3f9dfe914f98ddcd5c21225fd262e1b695bd73cd693
```

Technical acceptance was intentionally not treated as art acceptance.

Viewer review accepted three items immediately:

- **Meteorite Plate** — major readability improvement. The plate mass, gold rim, crater ring and crystal core became a legible layered object rather than a dark flattened splat.
- **Philosopher's Stone** — cleaner, more readable core/orbit/pedestal hierarchy. Its three orbit rings are independent editable Curve objects.
- **Qilin Bell** — preserved the established identity while gaining a genuinely hollow editable outside→rim→inside bell wall, plus editable hanging loop and horn Curves.

Viewer review rejected or questioned three:

- **Black Hinge** — gold halo arcs dominated too strongly and weakened the paired iron gate-leaf / hinge read.
- **Chrysalis Sigil** — convincing front-on but too paper-thin from the side.
- **Vial of Second Breath** — the six round tapered breath Curves read like porcupine spines rather than dry feather/exhalation gestures.

## The important source-authority proof

After the first `.blend` documents were committed, the migration bootstrap was **not** used to improve them.

The art corrections opened the existing committed Blender files, edited named artist-facing objects, saved those same documents, and recompiled read-only:

```text
committed .blend
    ↓ open
inspect real-viewer failure
    ↓
edit named source objects
    ↓ save same .blend
read-only compile
    ↓
runtime validation + viewer review
```

This is the first production batch in which the Blender-authority architecture was exercised as an actual art iteration loop rather than only a migration mechanism.

## V2 direct-source corrections

The second viewer board was:

```text
9d6ba16d6875e069e07cbedf2100ccc152a9c6745a50735d7a3e265c32184a22
```

### Black Hinge

The saved source's two iron leaves were made narrower/deeper/heavier in presentation, the halo arcs were reduced and thinned, and the crystal heart was given more presence.

Result: the item again reads first as paired occult gate hardware around a central ceremonial pin, with the gold arcs acting as framing rather than the dominant silhouette.

### Chrysalis Sigil

The saved cocoon was deepened, the three ritual ribs staggered in depth, and the four wing-petals gained thickness and small opposing depth rotations.

Result: the sigil remains graphic front-on but has a much more credible layered ceremonial-object read from oblique and side views.

### Vial of Second Breath

The six existing paths were reshaped into asymmetric upper/middle/lower fans. This improved rhythm but did not fully solve the material read: round tube cross-sections still looked too much like spines.

Vial therefore remained under art review after V2.

## V3 Vial correction

V3 kept the six authored paths and changed the representation that had actually failed: cross-section.

One shared hidden editable `C_BreathFeather_PROFILE` was added. The six visible paths now use that flattened ribbon/feather profile as their Curve bevel object, with four explicit path points, point-radius taper and authored roll.

The accepted final six-item board is:

```text
87abc2b6a1306727294d6a9b7b14f793f2f7929c5112c807c97d583469d3ef03
```

The change is deliberately modest at inventory scale, but the side elements now expose broad faces and papery taper instead of reading as six round needles. This is a better fit for the intended dry breath-feather / exhalation motif.

## Final source constructions

### Black Hinge

- two separately editable iron leaf bodies;
- central ceremonial pin and three gold collars;
- two secondary gold halo Curves;
- individual rivets;
- crystal heart.

### Chrysalis Sigil

- live revolved crystal cocoon;
- independent outer halo and ritual-rib Curves;
- four separately editable verdigris wing-petals;
- top loop and front gem;
- authored depth layering rather than a flat generated sigil.

### Qilin Bell

- one genuinely hollow Screw wall profile containing outer and inner bell surfaces;
- bronze rim Curve;
- hanging loop Curve;
- tapered horn Curves;
- separate cap, clapper and studs.

### Vial of Second Breath

- live smoked-glass revolve body;
- gold foot/neck Curves;
- crystal stopper;
- six independent 3D breath-feather paths;
- one shared editable flattened profile object;
- broken halo and breath bead.

### Meteorite Plate

- separate iron mass and bronze side lobes;
- gold rim Curve;
- limestone crater ring Curve;
- crystal meteor heart;
- gold crest Curve;
- six individually placed splinters.

### Philosopher's Stone

- crystal stone body;
- three independently transformed orbit Curves;
- crown, pedestal and base;
- three crystal satellites.

## Final runtime geometry

The accepted products validate as:

| Item | Vertices | Face records | Triangles |
|---|---:|---:|---:|
| Black Hinge | 694 | 1,176 | 1,264 |
| Chrysalis Sigil | 774 | 1,188 | 1,404 |
| Meteorite Plate | 768 | 1,284 | 1,456 |
| Philosopher's Stone | 850 | 1,360 | 1,636 |
| Qilin Bell | 848 | 1,400 | 1,560 |
| Vial of Second Breath | 1,024 | 1,372 | 1,660 |
| **Total** | **4,958** | **7,780** | **8,980** |

No decimation or runtime geometry optimization is introduced here. Source representation and resolved-product optimization remain separate concerns.

## Validation

Accepted V3 review run: `31912672878`  
Artifact: `9254105156` (`vial-second-breath-v3-review`)

The final Vial product reported:

```text
RUNTIME OBJ OK vial_of_second_breath.obj:
vertices=1024 faces=1372 triangles=1660
```

The complete item-model corpus remained green:

```text
items with models: 207
  duplicate_geometry: 11
  no_uvs: 124
  shared_file: 1
ITEM MODELS OK
```

And the full Blender-authority corpus now reproduces through the production compiler:

```text
ITEM BLEND COMPILE OK: 30 source(s)
```

Source hashes were identical before and after the read-only compile check.

## Conclusion

This batch is the practical payoff of the earlier A/B/C investigation.

The important result is no longer that Blender *can* encode semantic profiles, fabricated pieces, curves or flattened sweep profiles. It is that those structures survived a normal art process:

1. materialize a source once;
2. inspect it in the real game viewer;
3. reject technically valid art where necessary;
4. directly edit the authoritative Blender documents;
5. recompile through an unchanged strict runtime contract;
6. repeat until the object reads correctly.

The production architecture should therefore continue to treat individual `.blend` documents as normal item art sources, not as outputs of a project-specific generator language.
