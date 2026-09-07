# Town 3D spatial proof

This report records the first asymmetric proof slice for modelled St. Maria
town scenes. It is a synthetic fixture, not an adopted source blend and not a
production map change.

## Reproduction

```text
blender -b --factory-startup --python tools/blender/town_spatial_proof.py -- --fixture tools/blender/fixtures/town_spatial_proof.json --output out/town-spatial-proof
python -m unittest tools/blender/tests/test_town_spatial_proof.py
```

The Blender run produced `out/town-spatial-proof/direct.png`,
`out/town-spatial-proof/reflected.png`, and
`out/town-spatial-proof/town-spatial-proof.json`. The report contains the
projected landmarks, ray-cast hit object, triangle normal, and every check
result; both rendered variants passed all checks.

The staged runtime assertion also passed:

```text
THESTRA_TOWN_SPATIAL_RUNTIME OK {"directSourceYScreenDeltaSign":"positive","map":28,"pitch":-0.30543261909900765,"reflectedSourceYScreenDeltaSign":"negative","rightY":1,"transformContract":"engine_y = laneOriginY - blender_y"}
```

## Finding

The live `town_sideview` resolver uses `rightY=+1` and the viewport's canonical
horizontal projection term consumes that basis. The Blender authoring
calibration used by the existing staging helpers uses `rightY=-1`.

The current exporters therefore disagree at the source-to-engine boundary:

- `export_room_environment.py` applies `engine_y = 3.8833 - blender_y` and
  reverses triangle winding.
- `export_exterior_environment.py` leaves `engine_y = blender_y` and does not
  reverse winding.

The synthetic render proves the visible consequence: under the Blender
authoring view, direct source `+Y` moves left and the reflected candidate moves
right; occlusion, facing, elevation, and front-facing winding remain valid in
both candidates. The runtime assertion then proves the live town projection
has the opposite screen-order sign, so the adapter—not the camera math—must
own the reconciliation.

## Required adapter contract

Use one explicit source-space adapter for adopted blends:

```text
engine_y = laneOriginY - blender_y
reverse face winding after reflection
```

`laneOriginY` and the source coordinate space must be authored per scene or
package. Do not guess a mirror centre and do not silently move existing map
anchors. This slice intentionally does not modify either exporter until an
adopted interior/exterior pair supplies the required rendered evidence.
