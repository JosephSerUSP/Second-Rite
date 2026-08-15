# Tileset format experiment — material imagery / animation / normalization

Status: **experimental branch evidence for #558; not canonical design.**

Baseline: `main@fcdc4ea8fadd9fd38dc1f6e35c9b024d1a862a40`.

## Question

How should a Thestra surface/material be authored so that it remains readable to artists and multimodal agents, while the runtime remains free to atlas, pack, cache, and compile aggressively?

## Current facts

- Current world tilesets can declare one albedo atlas, an optional height map, and an optional glow map.
- The height map is CPU-consumed to build static geometry; it is not merely another fragment-shader sampler.
- Current world glow is a scalar mask sampled from the glow texture and used to restore albedo toward full brightness through lighting/fog.
- Image-authored geometry already treats visual source images as understandable fields rather than opaque GPU payloads.
- `main@fcdc4ea8` just generalized item-material sheen into ordered overlay passes with explicit `uvSource`, blend op, strength, and image path. Current blend vocabulary is `add`, `subtract`, `multiply`, `screen`, `mix`; current UV sources are `uv` and `sphere`.
- The item implementation has an explicit fixed runtime pass-slot bound. That is a renderer constraint, not a reason to impose a fixed four-channel authored-image ontology.

## Principle under test — author loose; compile tight

Authored assets should use semantically legible source images:

```text
wet_stone/
  surface.json
  albedo.png
  height.png
  emission.png
```

Optional semantic layers appear only when they have authored meaning:

```text
  moss-mask.png
  wetness.png
  coverage.png
```

The runtime may normalize those sources into whatever representation is cheapest:

```text
standalone images -> generated atlas / array / cached canvases
height.png        -> compiled static mesh
several masks     -> packed runtime auxiliary texture when useful
```

Source channel packing is therefore **not** the default contract. Runtime channel packing remains allowed.

## Why not authored RGBA data packing by default

1. Four channels are an arbitrary ceiling; the current item-material overlay work already demonstrates an open-ended authored layer vocabulary.
2. A grayscale `height.png` is immediately inspectable in ordinary image tools and by machine vision; a red channel hidden inside a composite "data" texture is not.
3. Different semantic maps may animate independently.
4. Height is not consumed by the same runtime stage as emission/material overlays.
5. Semantic naming makes provenance, visual diffing, generated-asset review, and debugging substantially clearer.

This does **not** forbid intentionally multi-channel images where the image itself has one coherent visual meaning. It rejects spare-channel packing as the default source ontology.

## Animation contract to prove

Ordinary animation must not imply animated geometry.

Required cases:

### A. animated albedo, static height

```json
{
  "albedo": {
    "frames": ["water_0.png", "water_1.png", "water_2.png"],
    "fps": 6
  },
  "height": "height.png"
}
```

### B. static albedo, animated emission

```json
{
  "albedo": "monitor.png",
  "emission": {
    "frames": ["off.png", "dim.png", "bright.png", "dim.png"],
    "fps": 10
  }
}
```

### C. synchronized animation when desired

The format needs a way to express that two properties share one frame clock without duplicating static properties.

### D. independent animation when desired

Emission flicker should not force albedo frames merely because both belong to one Surface.

### E. animated height is explicitly out of the ordinary material contract

Current height data drives CPU mesh compilation and decimation. Animated height would require repeated geometry compilation or a different displacement path. Treat it as an independently justified geometry feature.

## Relationship to ordered material overlay passes

The new item-material pass vocabulary suggests a useful separation:

- **source image**: semantically named, independently inspectable image;
- **material layer**: references an image, declares blend, strength and UV source;
- **runtime pass slot**: fixed renderer capacity used after validation/normalization.

A future surface format should test whether the same *conceptual* layer vocabulary can serve world materials without forcing world and item renderers to share one implementation prematurely.

Conceptual example only:

```json
{
  "id": "wet_stone",
  "albedo": "albedo.png",
  "height": "height.png",
  "layers": [
    {
      "image": "moss-mask.png",
      "material": "moss",
      "blend": "multiply",
      "uvSource": "uv"
    },
    {
      "image": "wetness.png",
      "material": "water_sheen",
      "blend": "add",
      "uvSource": "sphere"
    }
  ],
  "emission": "emission.png"
}
```

Do not ratify this schema until the nasty-room fixture proves which distinctions are actually useful.

## Alpha / coverage question

Current image-authored geometry sometimes uses height alpha as geometric influence or coverage. Test two source contracts:

1. height grayscale + alpha coverage in one file;
2. plain grayscale `height.png` + optional `coverage.png`.

Evaluation should include:

- artist readability;
- registration safety;
- image-tool convenience;
- machine-vision legibility;
- storage duplication;
- whether coverage is common enough to justify a permanent companion map.

## Runtime normalization questions

Measure rather than assume:

- can independently authored images be packed/cached without changing source paths?
- can static masks be packed separately from animated masks?
- can height disappear from GPU material state after mesh compilation?
- how much texture switching does standalone authoring actually produce after normalization?
- can Renderable Bundle provenance still point back to semantic source images after packing/composition?
- can hot reload invalidate one Surface rather than a whole atlas/environment palette?

## First hypothesis

A likely useful hierarchy is:

```text
Surface
  albedo source
  optional height source
  optional emission source
  optional ordered material layers
  per-property animation metadata
        |
        v
engine normalization
  compile geometry
  compose/cache/pack runtime textures
  bind bounded renderer pass slots
```

The important claim to test is not the exact schema. It is that **semantic source imagery should remain independent of renderer packing and shader slot layout.**

## Next spike

Build a neutral material fixture with:

- one standalone surface using separate albedo/height/emission;
- one animated-albedo/static-height surface;
- one static-albedo/animated-emission surface;
- one surface using at least two ordered visual layers inspired by the new material-pass vocabulary;
- a captured normalization report showing which source images became meshes/textures/runtime passes;
- Renderable Bundle provenance back to the authored sources.
