# Gate backdrop textures — do not edit

`gate_room.png` and `gate_room_heightmap.png` exist for **G5 only**. They are a
frozen copy of `dungeon_001.png` / `dungeon_001_heightmap.png` as of
28.08.2026, and are deliberately duplicated rather than referenced.

Together with `data/tilesets/_gate_room.json` and `data/maps/30.json` they are
the frozen backdrop behind every `backdrop: "map"` scene the screenshot harness
photographs.

## Why this exists

85 of G5's 144 frames are a menu, a window or a cursor composited over the
world. They exist to guard windowskin compositing, layout, fonts and cursors.
They need *something* behind them — a semitransparent skin over a void tests a
composite that never occurs — but they do not care *what*.

They used to photograph St. Maria (map 1), the most actively authored art
surface in the repository. Two consequences:

- A town commit reddened two thirds of the gate, so a real UI regression had to
  be found inside that noise. #951 landed exactly that way: 69 frames red, on
  the reasoning that G5 is not a required check.
- Worse, the *standpoint* was derived. `positionAtClearCorridor` scans the grid
  for the nearest clear three-cell corridor, so a town layout edit teleported
  the camera to a different quarter of the town.

## Why it is a duplicate, and frozen

Same reasoning as `assets/effects/_gate/`. Pointing the gate at a shipping
tileset would leave it coupled to the material library instead of the town —
better, but still a surface someone has a reason to retouch. A gate that gets
recaptured reflexively is worse than no gate.

Map 30 carries an **authored spawn**, so the harness standpoint is declared
rather than derived and cannot drift under a layout edit.

## What still gates the world

The world view is not gated here, and must not be. That is:

- the `map` scene's eight frames, which stay on the real town
- `battle`'s nine, which stay on the first generated dungeon map
- the 32 curated frames in `tools/golden/screens-wide/`

Town churn reddens those, legibly, instead of ninety-three.

## Rules

- **Never edit these files, `_gate_room.json`, or map 30.** Changing them
  defeats the purpose.
- Map 30 is a fixture, not content. It is unreachable from play by design: no
  events, no encounters, nothing warps to it.
- If the Group B frames go red, that is a **UI or renderer regression** until
  proven otherwise. Do not recapture to clear it.
- Re-baselining the fixture is owner-signed, like any other recapture.
