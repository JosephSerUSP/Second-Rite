# Vertex Shading Layers

> Design intent for #482. Current implementation truth remains `docs/ENGINE-STATE.md`; reviewed runtime contract belongs in `docs/SPEC.md`.

Vertex shading is environmental **colour character**, not illumination. It gives map geometry regional tint variation without inventing lamps merely to make one room warmer, greener, dustier, or more violet than another.

The composition model is:

```text
material / source colour
    × vertex shading
    × static illumination
    × runtime presentation (orientation shading, player light, fog, ...)
    + emission
```

## Authored form

A Map may carry an ordered `vertexShadingLayers` list. The first supported layer is `colorNoise`:

```json
"vertexShadingLayers": [
  {
    "type": "colorNoise",
    "colorA": [0.88, 0.94, 0.90],
    "colorB": [0.96, 0.88, 0.93],
    "strength": 0.12,
    "scale": 5,
    "seed": 1729
  }
]
```

`colorNoise` is deterministic **multi-octave 2D fractal value noise** over map-space vertices. Four value-noise octaves are rotated and offset relative to the authored grid, doubled in spatial frequency, and reduced in amplitude at each octave. The result combines broad regional drift with smaller structure without making the interpolation lattice read as horizontal/vertical bands.

`scale` controls the broad spatial size of the colour field in map cells; it is not image/pixel noise. `strength = 0` is neutral. Each layer mixes its generated colour from white by `strength`, then multiple layers multiply together from a white baseline.

The richer fractal field deliberately replaces the original single-octave `colorNoise` semantics. Second Rite is pre-release and owns its authored data, so there is one current implementation rather than a legacy noise mode or compatibility shim. The authored shape itself does not change: existing Scale/Strength/Seed controls now drive the richer field.

The seed is explicit authored identity rather than dungeon-generation RNG. Re-colouring a stratum must not perturb its topology, encounters, fixtures, or other generated facts.

## Procedural maps

This representation deliberately does not store a painted vertex grid. A procedural Map can carry the same layers as a fixed Map; whichever topology resolves for the expedition samples the stable field in map space. That makes vertex shading particularly suitable for Second Gate's generated dungeon floors.

## Studio

Vertex shading is a Map/environment property rather than a brush mode. Studio evaluates the exact same fractal function in the browser, including the same literal octave transforms and seed offsets used by Lua. The live source-colour baseline becomes:

```text
resolved material colour × vertex shading
```

Light authoring then modulates that baseline, so moving or editing a lamp never erases the environmental tint. Scale, Strength, colour endpoints, and Seed remain frame-local authoring controls; changing them does not require LÖVE or an explicit bake before visible feedback.

## Deferred ideas

The list-shaped contract leaves room for additional generators only when they earn their authoring cost: directional gradients, radial/region tint, semantic-zone tint, height/orientation response, etc. Manual vertex painting is deliberately deferred after the #467 lighting audit; it is not required for this model.

Extra technical knobs such as octave count, lacunarity, persistence, domain rotation, or warp should not be exposed merely because the implementation has them. If artist testing later demonstrates a meaningful need for a `Detail` or `Roughness` control, add it as an intentional authored property with paired validation rather than leaking every noise constant into the UI.
