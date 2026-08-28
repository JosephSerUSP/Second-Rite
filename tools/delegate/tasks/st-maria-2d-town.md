# Author the St. Maria side-view town data

You are authoring **Project data only** for an experimental 2D side-view town.
The runtime that consumes it is already written and already passes `VALIDATE OK`
on this branch. Do not modify anything under `runtime/`, `shared/`, `tools/` or
`tests/`. If you believe the runtime is wrong, say so in your report and stop —
do not edit it.

Read `docs/design/town-authoring-known-good.md` for the presentation facts, and
`AGENTS.md` for document authority. Read `docs/EXTERNAL-AGENT-BRIEF.md` before
reporting anything.

## What already exists on this branch

- `runtime/engine/bounded_lane.lua` — continuous 1D traversal with authored
  bounds and doorway proximity. No jumping, no gravity.
- `runtime/engine/environment_package.lua` — reads a package manifest. The
  `preRendered` block with `"mode": "layered_2d"` is what this town uses.
- `runtime/presentation/viewport_3d.lua` — the compositor. With
  `"cameraMode": "static"` it holds the plate still and walks the actor across
  it; that is the mode this town uses.
- `projects/hichaukitoden-game/assets/environments/st_maria_town/plates/*_bg.png`
  — nine finished 426x240 background plates, already generated. **Do not create,
  regenerate, edit or replace any PNG.** They are the art; you are the wiring.

Read `runtime/engine/environment_package.lua` and the `drawTownPrerender`
function in `runtime/presentation/viewport_3d.lua` before writing any JSON. The
manifest fields are validated at load and a wrong field is a hard error, not a
warning.

## The screen graph

Nine screens. Exteriors form one street, west to east; interiors hang off it.

| Screen | Map id | Plate | Reached from |
|---|---|---|---|
| Gate of Thestra | 16 | `gate_bg.png` | west end of Praca |
| The Praca | 17 | `praca_bg.png` | Gate (west), Market (east) |
| Market Row | 18 | `market_bg.png` | Praca (west), Quay (east) |
| The Quay | 19 | `quay_bg.png` | Market (west) |
| Weaponsmith | 20 | `weaponsmith_bg.png` | door on Market Row |
| The Pub | 21 | `pub_bg.png` | door on The Quay |
| Chapel | 22 | `chapel_bg.png` | door on The Quay |
| Laura's House | 23 | `house_laura_bg.png` | door on The Praca |
| Alicia's Room | 24 | `house_alicia_bg.png` | door on The Praca |

The Gate of Thestra also holds the entrance to the Labyrinth: its gate event
must `LOAD_MAP` to map `2`, which is the existing first dungeon floor.

## The numeric convention — use these exact values

Every screen uses the same calibration. Do not invent per-screen variants.

- Plate size and `imageSize`: `[426, 240]`
- `"cameraMode": "static"`, `"mode": "layered_2d"`
- Lane: `minY: 0.0`, `maxY: 10.0`. Lane centre is `5.0`.
- `slicePositions`: `[5.0]` — exactly one slice, at the lane centre.
- `lane.runtimeCenterY`: `5.0`
- `playerProjection`:
  - `centerX`: `213`
  - `screenY`: `206` (the actor's feet, in native pixels)
  - `width`: `24`, `height`: `48`
  - `pixelsPerRuntimeY`: `34.6`

That mapping puts lane `y=0` at native x≈40 and `y=10` at native x≈386, so the
walker crosses the plate without touching either edge.

Interiors are smaller rooms: use `minY: 1.5`, `maxY: 8.5` and keep every other
number identical. Do not change `pixelsPerRuntimeY` — narrowing the bounds is
what makes a room feel smaller.

## Files to write, per screen

**1. The environment package**, at
`projects/hichaukitoden-game/assets/environments/st_maria_town/<screen>/environment.json`.

`environment_package.load` requires `renderMesh`, `materialLibrary`,
`textureAtlas` and `collisionMesh` to be present as strings even though a
pre-rendered screen draws none of them. A single shared stub for all nine lives
at `assets/environments/st_maria_town/stub/`; create it once (a one-quad OBJ, a
one-material MTL, and reference the screen's own plate as the atlas) and point
every manifest at it with a relative path. Do not create nine copies.

`contractVersion` is `1`. `bounds` is a six-number array. `anchors` is an
object; every screen needs at least `spawn_player`, plus one anchor per doorway.

`foregrounds` and `scenes` are required arrays of the same length as
`backgrounds`. This town has no separate occluder layer yet, so point `scenes`
at the same plate and `foregrounds` at a fully transparent 426x240 PNG. **One**
transparent PNG, shared, at `assets/environments/st_maria_town/stub/empty.png` —
create it with Pillow, it is not art.

**2. The map**, at `projects/hichaukitoden-game/data/maps/<id>.json`.

Copy the shape of an existing town map exactly. The `traversal` block is:

```json
"traversal": {
  "provider": "bounded_lane",
  "environmentPackage": "assets/environments/st_maria_town/<screen>/environment.json",
  "spawnAnchor": "spawn_player",
  "lane": { "minY": 0.0, "maxY": 10.0, "depthX": 7.8, "groundZ": -1.5, "speed": 0.75 },
  "blockedRanges": [],
  "camera": { ... },
  "doorways": [ { "anchor": "<id>", "eventInstanceId": "<id>", "radius": 1.2 } ]
}
```

For the `camera` block use `"profile": "town_sideview"`, `yawDegrees` 0,
`pitchDegrees` 0, `fovDegrees` 28.072486935852957, `nearPlane` 0.05, `farPlane`
128, `projectionScale` 1/1, and `tracking` with `minOffsetX: 0` and
`maxOffsetX: 0` — the plate is static, so the projection window must not move.
Keep `interpolationSpeed` 12.0, `movementInterpolationSpeed` 14.0,
`animationFps` 8.0.

Each map also needs the ordinary fields every map has: `id`, `title`, `intro`,
`depth` 0, `safe` true, `category` "town", `generation` "Fixed",
`layout: ["."]`, `spawn`, `music`, `tileset`, `ceilingStyle`.

Register every new map in `projects/hichaukitoden-game/data/maps/index.json`.

## Movement and transitions — the interaction grammar

Left/right walks. There is **no** new trigger type and **no** new Map schema.

- A **door** is an ordinary event placed at a lane position, with
  `"trigger": "bump"`, whose commands `LOAD_MAP` to the target screen. The
  player reaches it by walking into it. Pressing up is not required and must not
  be implemented.
- A **screen edge transition** is the same thing at the end of the lane: an
  event at `y` just inside `minY` or `maxY` that transfers to the neighbouring
  screen.
- Every transfer must land the player at a sensible position on the destination:
  entering the Praca from the Gate puts you at the Praca's **west** end, not its
  centre. Use the destination map's spawn or an explicit target position — do
  not invent a new "spawn point" object type.
- Interiors must return you to the door you came in by.

Doorway positions must match where a door is actually painted on that plate.
**Open each plate and look at it** before choosing a lane position; a door
anchored where there is no painted door is the main way this task fails. Report
the pixel x of each door you targeted and the lane y you derived from it, using
`y = (pixel_x - 213) / 34.6 + 5.0`.

## NPCs and dialogue — migrate, do not invent

The existing 3D grid town is `projects/hichaukitoden-game/data/maps/1.json`. It
holds fifteen events with real authored dialogue: Gate Guard, Labyrinth Gate,
Weapon Shop, Yukio, Laura, Sign, Pub Owner, Auctioneer, Temple, Registrar,
Euler, Scholar, and two more.

**Carry that authored dialogue across verbatim.** Do not paraphrase it, do not
"improve" it, and do not write new characters. Distribute the existing NPCs onto
the screens where they belong:

- Gate: Gate Guard, Labyrinth Gate
- Praca: Registrar, the NPC11 event, Laura's door, Alicia's door
- Market: Auctioneer, Euler, Scholar, Yukio, Weapon Shop door
- Quay: Pub Owner door, Temple/Chapel door, Sign
- Interiors: the shopkeeper/owner of that interior

An NPC event on a pre-rendered screen needs `worldPosition` as
`[depthX, laneY, groundZ]`, plus `sprite`, `frameWidth` 24, `frameHeight` 48,
`frameIndex`, and `worldHeight` 1.75. Keep the original `sprite` paths from map
1. Keep `instanceId` values unique and stable.

Shops, the auction and any `commonEvents` calls must keep working — carry the
original `commands` arrays across unchanged, including their `CALL_COMMON_EVENT`
and shop commands.

## Demote the 3D grid town

`projects/hichaukitoden-game/data/system.json` has `spawn.mapId: 1`. Point it at
map `16` so a new game starts at the Gate of Thestra.

Map `1` must remain loadable but stop being part of the ordinary game. Add an
entry to the Developer Room — map `8` — that `LOAD_MAP`s to map 1, so it stays
reachable for testing. Do not delete map 1 and do not edit its contents.

Check whether anything else routes to map 1 (the Town Portal item, the opening
common event, any `LOAD_MAP` with map 1) and repoint those at map 16. Report
every such site you found and what you did, including ones you found and decided
to leave.

## Setting — hold this tone

St. Maria is a **dreary yet cozy colonial Portuguese village**: sea fog,
whitewashed lime plaster, azulejo tiles, terracotta roofs, wet stone, warm
lantern light in small windows. Poor, damp, old, and genuinely warm inside.
Where you must write connective text — an `intro` line, a screen-edge sign — hold
that register and keep it short. Never write text that contradicts the existing
authored dialogue.

## Verification you may and may not run

You **may** run:

- `node tools/ci/stage-project-gates.js --output out/luna-stage`
- `python -c` JSON round-trip checks over every file you wrote

You **may not** run the golden gates, and you must not report a gate result you
did not observe. This worktree has no GPU and no Effekseer DLL; `lovec` will not
work here. If you cannot verify something, say that plainly — an honest "not
verified" is worth more than a confident guess and is what I am checking for.

## Report

State, in this order:

1. Every file you created or modified, one line each.
2. The door pixel-x → lane-y derivation for every doorway, per screen.
3. The full screen-transition graph as you actually wired it, so I can check it
   is bidirectional and has no dead ends.
4. Which map-1 events you migrated, and which you deliberately did not, and why.
5. Every site that referenced map 1, and its disposition.
6. What you could not verify.

Do not report success for anything you did not observe. A list of "files I wrote
and did not test" is a fine and expected part of this report.
