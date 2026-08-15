# Asset production adapters

This directory is the first production use of the unified asset vocabulary. It
does **not** replace `tools/asset-gen`, the shared Blender core, the V2 surface
baselines, or the future full asset-record schema. It gives one coherent asset
set stable identities and connects those identities to the specialized tools
that already work.

## First Stratum set

`assets/authoring/first_stratum/asset-set.json` currently describes:

- four depth-conditioned wall/floor/ceiling surface products;
- a treasure chest with matching `closed` and `open` exports;
- a static ritual dais;
- a static offering pedestal.

Every entry uses contract representation, role, authoring space, placement
frame, semantic materials, states and intended product paths.

## Generate a surface

Inspect the exact existing `gen.py` invocation without spending credits:

```text
python tools/asset-production/generate_surface.py \
  first_stratum_floor_broken_flagstones --dry-run
```

Run it normally by removing `--dry-run`. The adapter invokes the existing
`wallPiece` or `texturePiece` pipeline, supplies the V2 `depth_guide.png`, and
then adds a `productionRecord` to the resulting `asset_gen_run` manifest. That
record hashes both the guide and metric height products and preserves the
intended albedo destination. The original run manifest lifecycle remains intact.

Provider/model/sampling overrides remain available, for example:

```text
python tools/asset-production/generate_surface.py \
  first_stratum_wall_ritual_pilasters \
  --provider sdapi --variants 6 --seed 1200 --lora JoStyle:0.65
```

## Build staged world props

Preview the Blender command:

```text
python tools/asset-production/build_world_prop.py \
  first_stratum_treasure_chest --dry-run
```

Build all declared states:

```text
python tools/asset-production/build_world_prop.py \
  first_stratum_treasure_chest
```

Set `BLENDER_BIN` when Blender is not on `PATH`. Builds go to
`out/asset-production/world-props/` by default. The Blender-side builder refuses
to write beneath `assets/`; promotion remains an explicit reviewed action.

Each state receives:

- deterministic OBJ/MTL export through `second_rite_asset_core.py`;
- an inspection `.blend`;
- contract metadata and semantic material bindings;
- bounds and socket data;
- SHA-256 output provenance in one `build.json` report.

The chest states are separate static models generated from one recipe and one
floor pivot. Runtime event-page switching is intentionally not part of this
commit.

## Validate

```text
python -m unittest discover \
  -s tools/asset-production/tests \
  -p "test_*.py" -v
```

## Item model corpus gate

The per-asset validity rubric used by the census scores each model in
isolation, so a renamed box passes every check. Measured against the library
shipped in August 2026: 207 items reference 208 OBJs, but there are only 112
distinct shapes, 27 "armours" share one mesh, and 155 models carry no UVs at
all — which also blocks any texture-projection work, since there is nothing to
paint onto.

`check_item_models.py` adds the checks that only exist at corpus scale:

| Check | Catches |
|---|---|
| `shared_file` | two items pointing at one OBJ |
| `duplicate_geometry` | the same shape renamed, moved, rescaled or reordered |
| `indistinct_silhouette` | two shapes the player cannot tell apart at display size |
| `no_uvs` | a model the texturing track cannot use |

Run it:

```text
python tools/asset-production/check_item_models.py            # gate
python tools/asset-production/check_item_models.py --report   # full listing
```

Geometry is normalized (centroid, scale, vertex order) before hashing, so a
copy cannot launder itself past the gate by being moved or resized.
Silhouettes are rasterized from the mesh across three canonical axes at the
resolution the item is actually displayed at — no GPU required, so this runs
anywhere.

### The baseline

The existing library is known-bad and stays in place as placeholders, so its
212 violations are recorded in `item-model-baseline.json`. The gate therefore
fails on **new** violations only, and the baseline shrinks as replacement
cohorts land. **The list may only shrink**: when a baselined violation stops
reproducing, the gate fails and asks for a rewrite, because leaving a stale
entry would let a future duplicate re-enter under an already-accepted key.

Rewriting the baseline is an owner-signed action, exactly as recapturing a
golden is — it is the one way to make this gate green without improving a
model.

```text
python tools/asset-production/check_item_models.py --write-baseline
```

Tests, including a negative control per check, are in
`tests/test_item_model_corpus.py`.
