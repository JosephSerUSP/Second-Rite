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
- editable Curve bevel/profile objects;
- `ARRAY` + `CURVE` compositions;
- Geometry Nodes and instances;
- hidden guides, construction objects and manually authored exceptions;
- arbitrary mesh editing where a procedural construction is not useful.

The runtime does not inherit those authoring abstractions. Compilation evaluates a temporary duplicate and writes resolved geometry only.

## Runtime material passes

Blender's OBJ exporter can represent ordinary material colour/texture data but does not know Second Rite's retro overlay vocabulary. A Blender material may therefore carry `sr_runtime_passes_json` as source metadata.

The value is a JSON list of at most two entries:

```json
[
  {
    "uvSource": "sphere",
    "blend": "add",
    "strength": 1.0,
    "texture": "assets/models/matcaps/gold.png"
  }
]
```

The compiler validates this against the same bounded vocabulary used by `presentation/retro_mesh_shader.lua` / `presentation/obj_model.lua` and writes deterministic `pass` statements into the runtime MTL.

Supported UV sources are `uv` and `sphere`. Supported blends are `add`, `subtract`, `multiply`, `screen`, and `mix`. The two-pass shader maximum is also enforced at compile time.

This metadata is **per Blender material, not globally implied by the semantic material id**. For example, Batch C intentionally gives `crystal` a ruby sphere sheen while another crystal use may remain flat or use a different pass stack.

## Source authority is one-way

Once a `.blend` has been created and committed, **do not regenerate or overwrite it from an external recipe during ordinary compilation**.

A script or agent may scaffold a new source document. After that first save, the `.blend` becomes the authority so that human Blender edits and agent edits operate on the same document rather than competing with a generator.

The production compiler therefore:

1. hashes the source;
2. opens it in Blender;
3. evaluates the existing authoring graph on a temporary duplicate;
4. exports OBJ/MTL and finalizes source-authored runtime material passes;
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

A single `.blend` can mix all three plus direct modeling and Geometry Nodes. The shared contract belongs below those choices: read-only evaluation, runtime-valid resolved geometry, material-pass finalization, and export.

### C profiles in Blender

For a large part of C, Blender's own Curve model is sufficient and deliberately preferred over an immediate Geometry Nodes abstraction:

```text
editable 3D path Curve
        +
editable 2D bevel/profile Curve
        +
per-point radius  → taper
per-point tilt    → roll
        ↓
resolved swept surface
```

Profile objects are source-only construction geometry. Keep them parented beneath the item export root, set `hide_render = true`, and use them as the visible path Curve's `bevel_object`. The shared exporter keeps hidden construction objects out of the runtime product while Blender still evaluates them as dependencies of the visible Curve.

This supports round, elliptical, flattened polygonal and rectangular/ribbon sections while leaving both the centerline and section visibly editable in Blender. Cyclic source splines are also valid for cuffs, rings and chain links.

A native Curve bevel object supplies **one profile per path**. It does not independently vary the profile's X:Y aspect at every path point. The migrated C sources preserve inherited per-point aspect/thickness data as source metadata where useful, but Geometry Nodes is an escalation path only when an item genuinely needs that extra degree of freedom. Do not promote per-point anisotropy into mandatory pipeline complexity merely because the old experimental sweep grammar could express it.

When translating old Batch-C roll values, note that its transported sweep frame and Blender's native minimum-twist bevel frame used perpendicular zero-roll bases. That historical migration required one +90° tilt calibration. New Blender-native authoring should simply treat Blender's displayed profile frame as authority rather than preserving that legacy offset as a permanent runtime convention.

## Migration status

Existing canonical OBJ models are allowed to predate this source convention. Do not manufacture anonymous baked `.blend` wrappers merely to claim migration.

Move a model here when its useful construction intent has actually been represented as an editable Blender document and its compiled output has been reviewed against the current canonical runtime model.

The first production C migration establishes editable curve authority for:

- `barbed_spear.blend`
- `blackroot.blend`
- `cerberus_fang.blend`
- `water_scepter.blend`

These retain separate semantic curve parts, per-point radius/tilt and material bindings rather than importing a baked OBJ as the source.

The second C migration adds explicit editable profile-object authority for:

- `hermes_boots.blend`
- `mimic_tongue.blend`
- `molten_manacle.blend`
- `phoenix_pinion.blend`

Together, all eight Batch-C production items now have real Blender source authority. The second cohort was visually reviewed against the canonical LÖVE item viewer before acceptance; the static-profile limitation remains documented rather than silently replaced by Geometry Nodes.
