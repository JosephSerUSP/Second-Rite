# Tileset format experiment — resource ontology / reuse

Status: **experimental branch evidence for #558; not canonical design.**

Baseline: `main@fcdc4ea8fadd9fd38dc1f6e35c9b024d1a862a40`.

## Question

What should a Thestra `tileset` mean now that runtime presentation already mixes atlas-backed surfaces, weighted semantic variants, image-authored geometry, OBJ fixtures, sparse Map overrides, generated features, lighting, and environment presentation?

This lane tests whether the current record is usefully one resource or whether it conflates source packing, reusable surfaces, environment composition, fixture vocabulary, and procedural placement policy.

## Current facts to preserve

- A Map currently selects one base tileset id and may provide one sparse `tilesetOverride`.
- `engine/tileset_resolver.lua` deep-merges ordinary objects and merges the semantic pools `features`, `doors`, `fixturePrefabs`, plus `base.walls`, `base.floors`, `base.ceilings`, and `base.skies` by stable `id`.
- Weighted wall/floor/ceiling/door variants are semantic records. Their identity must not regress to "whatever occupies atlas cell N".
- A variant or feature may already escape the atlas by using `geometry` or `model`.
- Maps already have sparse material/feature seams in addition to their default tileset. Mixed presentation therefore does not require replacing the logical Map ontology.
- Tilesets are stored as independent registry records under authored storage; physical file-per-record storage is not itself the ontology.

## Suspected conflation

The current Tileset record owns all of the following at once:

1. a source atlas (`texture`, tile dimensions, atlas coordinates);
2. base role pools (walls/floors/ceilings/skies);
3. door variants;
4. reusable features;
5. fixture-prefab predicates and probabilities;
6. material geometry controls (`heightMap*`);
7. emission (`glowMap`, strength);
8. sky/environment defaults;
9. deterministic visual-variation vocabulary.

A record can therefore be a style preset, an image packing manifest, a surface library and a procedural decoration rulebook simultaneously.

## Candidate A — Surface Library + Environment Palette

Introduce a reusable surface/material resource whose authored representation is independent of the environment palette that consumes it.

Conceptual example only:

```json
{
  "id": "wet_stone",
  "albedo": "assets/surfaces/wet_stone/albedo.png",
  "height": "assets/surfaces/wet_stone/height.png",
  "emission": "assets/surfaces/wet_stone/emission.png"
}
```

An environment palette then assigns/reuses those resources:

```json
{
  "id": "flooded_catacomb",
  "walls": [
    { "surface": "old_stone", "weight": 70 },
    { "surface": "wet_stone", "weight": 30 }
  ],
  "floors": [
    { "surface": "flagstone", "weight": 80 },
    { "surface": "shallow_water", "weight": 20 }
  ]
}
```

Questions:

- Is `Surface` the right granularity for both atlas-backed and standalone-image sources?
- Do fixtures reference surfaces, representations, or a separate visual asset vocabulary?
- Which current tileset-level settings actually belong to a palette rather than a surface?
- Can one surface be reused in several palettes without duplicating placement policy?

## Candidate B — Composable/importing Tilesets

Keep the current primary resource but allow one Tileset to import smaller libraries/tilesets.

This preserves the current vocabulary but introduces precedence questions immediately:

- duplicate variant ids;
- weight combination versus replacement;
- fixture-prefab ownership;
- remove semantics;
- sky/environment precedence;
- height/glow settings that currently apply to an entire atlas;
- whether imports form a readable dependency graph or inheritance maze.

A useful failure result for this branch would be evidence that explicit imports are more complex than extracting reusable surfaces.

## Candidate C — default palette + local Map/zone presentation

Preserve one simple default palette per Map, while allowing semantically bounded areas to draw from another reusable family.

This should pressure-test the existing sparse seams (`materials`, generated features, zones, `tilesetOverride`) before inventing a `tilesets: []` merge contract.

The key question is locality: can a cathedral nave and a flooded crypt look materially different while ordinary cells remain terse and deterministic?

## Migration cases to test

1. `dungeon_default`: simple atlas + height map + features.
2. `stillnight_bellroot_vigil`: weighted atlas variants + height + glow + model/geometry features.
3. `showcase_thestra`: atlas floors/ceilings plus a geometry-backed base wall and geometry/OBJ fixtures.
4. One sparse Project tileset with minimal/default content.

For each, record whether migration duplicates data, creates new resource ids, or changes deterministic variant selection.

## First hypothesis

The most promising separation is currently:

```text
Map -> one default Environment Palette
                |
                +-> weighted reusable Surface references
                +-> fixture/decor vocabulary
                +-> environment defaults

Surface -> authored visual/material representation
```

But this is deliberately **not a decision**. In particular, fixture placement predicates may prove to belong neither to Surface nor Palette; the nasty-room gauntlet must expose that.

## Next spike

Create data-only candidate manifests for the three migration cases above, without changing the production loader. Compare:

- duplicate authored bytes/paths;
- number of new concepts and ids;
- how a local mixed-family Map is expressed;
- whether the current sparse-delta semantics remain understandable;
- whether atlas-backed sources remain first-class compatibility rather than becoming the ontology.
