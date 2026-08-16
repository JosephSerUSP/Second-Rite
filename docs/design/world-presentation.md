# World presentation units and camera framing

A Thestra world Scene may describe presentation facts without changing Map
structure or gameplay semantics:

```json
{
  "draw": "world",
  "world": "map",
  "worldPresentation": {
    "pixelsPerTile": 24,
    "camera": {
      "profile": "rpg_perspective",
      "pitchDegrees": 40,
      "fovDegrees": 26,
      "tilesAcross": 18
    }
  }
}
```

All fields are optional. A Scene that omits `worldPresentation` preserves the
existing renderer defaults.

## `pixelsPerTile` means authored/design pixels

`pixelsPerTile` establishes a unit relationship between raster art and the
world grid:

> **1 world tile = `pixelsPerTile` authored/design pixels.**

At `pixelsPerTile: 24`:

- a 24×24 authored image is 1×1 tile at native authored scale;
- 48×24 is 2×1 tiles;
- 12×12 is 0.5×0.5 tiles;
- 24×48 is 1×2 tiles.

This is deliberately **not** a physical-screen-pixel promise. Window size,
render-surface scaling, camera zoom, orthographic framing, perspective depth and
integer output scaling may all change how many monitor pixels a tile occupies.
The authored density remains the same.

Likewise, visual bounds do not define collision. A 24×32 character can still
have a 1×1 logical footprint; hair, weapons, wings and shadows may extend beyond
that cell.

`presentation.world_presentation` owns pure conversion helpers so importers,
Event sprite presentation, editor rulers and preview tools can share one unit
contract instead of each inventing scale constants.

## Camera framing is separate

Camera fields answer a different question: how much of the world is visible and
through what lens. `pixelsPerTile` alone never moves or zooms the camera.

Perspective `tilesAcross` is measured at the optical target. Combined with an
authored FOV, it derives camera distance while preserving target framing. A
future tool may explicitly request that target screen scale match authored pixel
density, but that must be an authored framing choice rather than an accidental
side effect of changing asset density.

## Ownership and precedence

The world Scene owns the durable presentation default because the same Map
structure can legitimately be presented through different cameras/art-density
contexts. Temporary runtime/session camera overrides remain higher precedence
for cinematics, debugging and evidence capture. None of these presentation facts
mutate Map topology, movement, collision or save data.
