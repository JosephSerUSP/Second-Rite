# Making the Padaria and the smith walkable

Branch: `claude/st-maria-shops-walkable`, cut from `exp/838-town-2d-flat` with
`main` merged in. 27.08.2026.

The two authored interiors from
[`st-maria-shop-interiors-2026-08-26.md`](st-maria-shop-interiors-2026-08-26.md)
were dioramas: rendered, reviewed, shipped as pictures. This makes them places
the player walks into, twice over — once as a pre-rendered plate, once as baked
3D geometry — so the two presentations can be compared on the same rooms.

## The thing that nearly went wrong

The first instinct was to build a way to walk into a room. That was wrong, and
the maintainer caught it: both a pre-rendered 2D and a full 3D side-view town
had already been built.

`exp/838-town-2d-flat` (last commit 24.08) is a traversable ten-screen St.
Maria — maps 16–26, NPC sprites, two-way interiors — verified with
`lovec <stage> town-walk` and 103/103 on `tests/test_bounded_lane.lua`. Under
it sits real runtime engineering: `runtime/engine/bounded_lane.lua`,
`environment_package.lua`, a `town_sideview` WorldCamera profile, and a
`layered_2d` prerender compositor, transplanted free of visual ancestry in
f3016180.

Nothing here is new infrastructure. Every mechanism below already existed; the
work was fitting the rooms to it and finding where the two coordinate
conventions disagree.

**The lesson worth keeping is cheap to state and was expensive to nearly miss:
before building a mechanism, search the branch corpus, not just `main`.** The
seam was never merged, so `main` gave no sign of it.

## One package, two renderers

`environment_package.lua` and `viewport_3d.lua` already support both
presentations in a single contract. `drawWorldSpace` checks for a `preRendered`
block and, finding one, composites plates; finding none, it falls through and
submits `renderMesh` as placed 3D geometry.

That made "try both" a matter of writing two packages per room rather than two
code paths.

| | Pre-rendered | Baked 3D |
|---|---|---|
| Package | `alicias_padaria/`, `lauras_smith/` | `alicias_padaria_3d/`, `lauras_smith_3d/` |
| Map | 27, 20 | 28, 29 |
| Carries | 256×240 plate + empty foreground | `environment.obj` + 1024² baked atlas |
| `preRendered` | present, `cameraMode: "static"` | absent |

Both rooms are reached from Market Row; the 3D twins hang off their own doors
so the pair can be walked back to back.

## Nothing about the rooms was re-authored

The plates come from the shipped `.blend` through the existing
`stage_room_model.py`, and the 3D packages open the *same* `.blend` and sort
what is already in it into the `TH_*` contract collections. If the recipe
changes both outputs change together; if it does not, neither drifts.

Two decisions preserved the reviewed art rather than "improving" it:

- **The rooms were not widened.** `base_half_width_at` carries a documented
  rule: a self-contained interior is sized to the Classic 256 width "because a
  room wider than the default view promises the player a screen edge they can
  walk to". Making the rooms walkable flips the premise that rule is
  conditioned on — the promised edge is now reachable — so widening would have
  been defensible. It was still declined, because the composition that was
  reviewed is the composition at 8.27 m. The room is exactly as wide as the
  frame, so the plate holds still and the actor walks across it: `cameraMode:
  "static"`, which is the shape the 24.08 interiors had already settled on.
- **The black top band stays.** Rows 0–15 of each plate are empty. That is
  in-vocabulary — the `Interior.foreground` docstring records that this grammar
  "has a black backdrop" rather than a proscenium — and it is the look that was
  reviewed. Filling it means raising the ceiling from 3.7 m to 4.39 m, which is
  an art decision, not a consequence of making the room walkable.

Measurement corrected one thing an eyeball reading got wrong. The rooms look
like they float in void; they do not. Every row from 16 to 146 is lit edge to
edge across all 256 columns. The only voids are that top band and rows 147–239,
which sit below the character floor limit — and the shipped town plates have
exactly the same black bottom band, because the translucent dock covers it.

## The plate projection is derived, not authored

Every number in the pre-rendered packages falls out of
`tools/blender/fixtures/town_sideview_camera.json`:

| Quantity | Value | Where it comes from |
|---|---|---|
| Room half-width | 4.13333 m | `fovHalfX × front_depth`, front edge on row 136 |
| `pixelsPerRuntimeY` | 27.42857 | `128 / (fovHalfX × 18.6667)` |
| `screenY` | 128.0 | where the floor projects **at the action plane** |
| Lane span | 7.7667 m | inner wall face to inner wall face |

`screenY` is worth naming because an earlier note in this work had it wrong.
136 is the floor's *front edge*, nearest the camera. 128 is where the floor
projects at the action plane — the depth at which a 1.75 m Walker measures 48
native pixels — and it is the actor's foot line. It is the number the
calibration solves for, and it is 128 exactly.

`--no-walker` was added to `stage_room_model.py`: it hides the actor from the
render *after* `measure_actor` and the floor-limit check, so a plate carries no
actor pixels (the known-good rule) while staying calibrated to the actor that
gets composited onto it. Both plates measured 47.99999713 px.

## Two coordinate traps, both silent

### The engine's screen-right is the mirror of Blender's

`resolveTownSideview` builds `right = (-dirY, dirX)`, which at yaw 0 is **+Y**.
For forward +X and up +Z, `forward × up` is **−Y**. That is the determinant −1
basis of issue #935: the town camera's basis is a reflection.

Exported unchanged, the 3D room would render as its own mirror image — the
Padaria's oven on the right instead of the left — and nothing in the 3D path
would catch it, because a reflection preserves both point projection and
transform invariance.

The export therefore reflects the mesh and reverses face winding. This is not
a cost: it makes the 3D package land on *the same lane coordinates as the
plate*, so a door at lane Y 7.03 is the same door in both presentations, and
the anchors are identical.

### The lane axis is not where a Z-up reading puts it

`obj_model.objToWorld` is `x, -z, y`: the runtime expects Blender's default
**Y-up, forward −Z** OBJ preset. So in the exported file the *second*
component is height and the *third* is the lane.

The first implementation mirrored the second component and turned the room
upside down. Composing the two conversions gives the correct transform:

```
obj_z = -blender_y          =>  world_y = -obj_z = blender_y
want world_y = C - blender_y  =>  obj_z' = -obj_z - C
```

This was caught before it shipped by measuring the exported OBJ's axis ranges
rather than reasoning about them. The height axis un-mirrors to exactly
`[-0.35, 4.0]` — floor thickness to ceiling — which identifies it beyond
argument, and the lane axis is the symmetric one at span 9.287.

**Neither trap is visible in a passing gate.** Both produce a room that loads,
projects and renders; one is mirrored and one is upside down.

## Wiring findings

- Map 20 "Weaponsmith" is Laura's: its shop is id 8, `"Laura's Counter"`. The
  screen was already hers and only had a generated plate, so the authored
  smithy takes it over rather than adding a screen.
- The Padaria is new. Shop 7 is `"Alicia's Shelf"`, which it opens.
- **Map 26 was already the Backstreet.** Claiming id 26 for the Padaria
  silently overwrote it and broke maps 23 and 25, which reach the town only
  through it. `git status` showed `M` rather than `??`, which is what caught
  it; the Padaria moved to 27.
- `data/maps/index.json` is an explicit manifest. A map file that exists but is
  not listed is not staged, and therefore not validated and not walked —
  `VALIDATE OK` on an unregistered map means nothing was checked. This produced
  a false pass that had to be withdrawn.

## Verification

| Check | Result |
|---|---|
| `lovec <stage> validate` | `VALIDATE OK` |
| `lovec <stage> town-walk` | `TOWN WALK REACHED EVERY SCREEN` |
| `tools/golden/capture-town-proof.py` | `THESTRA_TOWN_PROOF OK frames=36` |
| Plate actor scale | 47.99999713 px (target 48) |

The proof harness enumerates every map declaring `provider: "bounded_lane"`
rather than naming ids, so both new screens are photographed without touching
it.

## Open

- The Market Row plate does not draw the Padaria's door. The doorway exists in
  data and works; the painted street has no opening at lane Y 22. The plate is
  regenerable, so this is art, not wiring.
- `TH_RENDER` is the whole room joined and unwrapped, not a hand-authored
  coarse mesh. It is a valid render mesh — it carries the real depth and
  silhouette — and it is honestly derived, but the intended collapse is
  coarser. `--decimate` exists and defaults to 1.0, because collapsing boxes
  blindly tears shared edges.
- The counter and the anvil sit behind the action plane, so the player walks in
  front of them. A `foregrounds` layer carrying the counter would let the
  player and Alicia stand *behind* it, which is what a shop counter is for.
  The slot exists and currently holds an empty plate.
