# Editable item-model sources

This directory is the production home for **authoritative per-item Blender source documents**.

A source file is named after the item model it compiles:

```text
assets/authoring/items/cerberus_fang.blend
        ↓ read-only compile
assets/models/items/cerberus_fang.obj
assets/models/items/cerberus_fang.mtl
```

The `.blend` is the authored source. OBJ/MTL are runtime products.

## Source contract

Each production source contains exactly one export root with:

```text
item_export = true
item_export_name = "cerberus_fang"
sr_source_authority = "blend"
```

`item_export_name` must match the `.blend` filename stem. The root also carries the ordinary shared asset metadata required by `second_rite_asset_core.validate_asset_metadata()`.

Everything beneath that root is free to remain useful Blender authoring structure. A source may contain:

- sparse profile meshes with `SCREW`;
- planar source plates with `SOLIDIFY`;
- Boolean cutters and negative space;
- editable Curve splines, taper and tilt;
- `ARRAY` + `CURVE` compositions;
- Geometry Nodes and instances;
- hidden guides, construction objects and manually authored exceptions;
- arbitrary mesh editing where a procedural construction is not useful.

The runtime does not inherit those authoring abstractions. Compilation evaluates a temporary duplicate and writes resolved geometry only.

## Source authority is one-way

Once a `.blend` has been created and committed, **do not regenerate or overwrite it from an external recipe during ordinary compilation**.

A script or agent may scaffold a new source document. After that first save, the `.blend` becomes the authority so that human Blender edits and agent edits operate on the same document rather than competing with a generator.

The production compiler therefore:

1. hashes the source;
2. opens it in Blender;
3. evaluates the existing authoring graph on a temporary duplicate;
4. exports OBJ/MTL;
5. validates the OBJ against the runtime face contract;
6. hashes the `.blend` again and requires byte-for-byte identity.

Blender `.blend1`, `.blend2`, etc. files are workstation safety backups, not repository source assets.

## Compile

With Blender on `PATH`:

```text
python tools/blender/compile_item_blends.py
```

Or point at a specific executable/source:

```text
python tools/blender/compile_item_blends.py \
  --blender /path/to/blender \
  --source assets/authoring/items/cerberus_fang.blend
```

CI uses `--check`, which compiles into a temporary directory and requires the result to match the checked-in runtime product without dirtying the repository:

```text
python tools/blender/compile_item_blends.py --blender /path/to/blender --check
```

## A / B / C after the experiments

The recent item-model experiments remain useful as **authoring vocabularies**, not mutually exclusive production backends:

- **A — semantic sculpture:** profile/revolve and meaningful volume assembly;
- **B — polygonal fabrication:** outlines, holes, plates and thickness;
- **C — spatial gesture:** curves, taper, roll, loft and body-following paths.

A single `.blend` can mix all three plus direct modeling and Geometry Nodes. The shared contract belongs below those choices: read-only evaluation, runtime-valid resolved geometry, and export.

## Migration status

Existing canonical OBJ models are allowed to predate this source convention. Do not manufacture anonymous baked `.blend` wrappers merely to claim migration.

Move a model here when its useful construction intent has actually been represented as an editable Blender document and its compiled output has been reviewed against the current canonical runtime model.
