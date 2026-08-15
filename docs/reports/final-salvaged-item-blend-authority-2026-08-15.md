# Final salvaged-item Blender authority — 2026-08-15

## Result

The item-model salvage begun by #582 is now complete at the source-authority layer.

All **32 item models salvaged by #582** have authoritative per-item Blender documents under `assets/authoring/items/`. The final two are:

- `pile_bunker.blend`
- `celestial_fossil.blend`

The checked-in OBJ/MTL files remain runtime products. The `.blend` documents are the editable source authority and ordinary compilation is read-only.

## Final two source structures

### Pile Bunker

Pile Bunker remains a semantic industrial assembly rather than a baked anonymous mesh. Its source keeps separately editable housing, back plate, exposed driver spike, twin rails, driver collar, side pressure chamber, grip, crank and gold bolts. Small decorative bevel results are materialized where useful for deterministic export; the meaningful assembly remains directly editable.

Accepted runtime product:

```text
304 vertices
548 face records
548 triangles
```

### Celestial Fossil

Celestial Fossil keeps its irregular stone slab, raised fossil spiral, two mineral-vein curves and embedded nodule as separate authored objects. The bored-through void is genuine geometry. Its Boolean result is materialized for deterministic export while the hidden cutter remains in the `.blend` as an authoring guide rather than disappearing from the source history.

Accepted runtime product:

```text
372 vertices
512 face records
620 triangles
```

## Graduation review

The final materialization/review lane was GitHub Actions run **31914672676**. Review artifact **9254603213**, `salvaged-32-blender-authority-graduation`, contains the real LÖVE item-viewer boards before and after the last two source migrations.

The viewer rendered all 32 selected models at four established review angles:

```text
ITEM SHEET OK: 32 models, 1152x1188
```

Before-board SHA-256:

```text
979bd8ae55ff5fb0489215cbdb76d8f25bf5880f132608eddca746978b5cdf4c
```

After-board SHA-256:

```text
98a68f5b4fc9fa1cd10c1b6794f750e707549303ee8fd2e6e60325d3fbb39b31
```

Visual review accepted the migration. Celestial Fossil is effectively indistinguishable at inventory scale. Pile Bunker differs only in tiny topology/edge-highlight details. A whole-board pixel comparison found a mean absolute RGB-channel delta of roughly `0.027 / 255`, with about `0.13%` of RGB channel samples differing at all. That metric is only a localization check, not an artistic score; the real-viewer inspection is the acceptance authority.

## Corpus and runtime validation

The final run reported:

```text
items with models: 207
  duplicate_geometry: 11
  no_uvs: 124
  shared_file: 1
ITEM MODELS OK

RUNTIME OBJ OK assets/models/items/pile_bunker.obj:
  vertices=304 faces=548 triangles=548

RUNTIME OBJ OK assets/models/items/celestial_fossil.obj:
  vertices=372 faces=512 triangles=620

ITEM BLEND COMPILE OK: 32 source(s)
```

The production `compile_item_blends.py --check` path reopened and recompiled **all 32 authoritative item `.blend` sources**. The two new source hashes were unchanged before/after compilation and no numbered Blender backup files were created.

No runtime decimation or geometry optimization is introduced here. Resolved-product optimization remains a separate concern below the source-authority layer.

## Source ownership and cleanup

The one-shot bootstrap and write-capable materialization workflow used to create the first saved documents are deleted before the production PR is opened. There is no retained recipe that can silently regenerate or overwrite these two `.blend` files.

This completes the promise made by #582: first preserve the strongest recent art as canonical runtime products, then migrate the useful construction intent into ordinary human/agent-editable Blender source documents without canonizing the experimental A/B/C/found-object generators.

## Architectural conclusion

The item-model investigation is complete enough to stop treating A/B/C as production systems.

They are authoring techniques inside Blender:

```text
A — semantic profiles / revolved volumes
B — planar fabrication / symmetry / thickness
C — spatial paths / profiles / taper / roll
optional Geometry Nodes — controlled repeated detail
                 ↓
         authoritative .blend
                 ↓ read-only evaluation
         resolved runtime geometry
```

Future item work should be normal content creation. New abstractions should be added only when a concrete item earns them, not because the modeling investigation remains open.
