# Vertex Shading Layers

> Design intent for #482. Current implementation truth remains `docs/ENGINE-STATE.md`; reviewed runtime contract belongs in `docs/SPEC.md`.

Vertex shading is environmental **colour character**, not illumination. It gives map geometry low-frequency regional tint variation without inventing lamps merely to make one room warmer, greener, dustier, or more violet than another.

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

`colorNoise` is smooth deterministic value noise over map-space vertices. `scale` is the size of the colour drift in map cells; it is not image/pixel noise. `strength = 0` is neutral. Each layer mixes its generated colour from white by `strength`, then multiple layers multiply together from a white baseline.

The seed is explicit authored identity rather than dungeon-generation RNG. Re-colouring a stratum must not perturb its topology, encounters, fixtures, or other generated facts.

## Procedural maps

This representation deliberately does not store a painted vertex grid. A procedural Map can carry the same layers as a fixed Map; whichever topology resolves for the expedition samples the stable field in map space. That makes vertex shading particularly suitable for Second Gate's generated dungeon floors.

## Studio

Vertex shading is a Map/environment property rather than a brush mode. Studio should expose layer controls in Map authoring and evaluate the same deterministic function in the browser. The live source-colour baseline becomes:

```text
resolved material colour × vertex shading
```

Light authoring then modulates that baseline, so moving or editing a lamp never erases the environmental tint.

## Deferred ideas

The list-shaped contract leaves room for additional generators only when they earn their authoring cost: directional gradients, radial/region tint, semantic-zone tint, height/orientation response, etc. Manual vertex painting is deliberately deferred after the #467 lighting audit; it is not required for this model.
