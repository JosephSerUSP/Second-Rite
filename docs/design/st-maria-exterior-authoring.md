# St. Maria — authoring a modelled exterior

Status: vocabulary landed, no screen built from it yet. This describes what was
**measured**, not what was designed: every number below was read out of the
engine's own calibration through `thestra_camera.project_world_point`, not
derived on paper.

The interior counterpart is [`st-maria-interior-authoring.md`](st-maria-interior-authoring.md).
The vocabulary is `tools/blender/recipes/exterior.py`.

> **There is no worked example, on purpose.** One screen (Market Row) was built
> to derive these numbers and was not good enough to stand as a template, so it
> was not landed. PRs #941 and #942 converged on one identical room because the
> interior brief hands over a worked `build()` that *is* a bakery; repeating
> that mistake outdoors would be worse, because a street has more free
> variables to lose. Compose from the vocabulary.

## The camera is the interior camera

A modelled exterior reuses `tools/blender/fixtures/town_sideview_camera.json`
unchanged. Character pixel scale is fixed across the whole game, so the solved
distance is the same indoors and out.

**The `distance: 21.1175` in the exterior maps is not a camera.** It belongs to
the 2D plate presentation (`preRendered.mode = "layered_2d"`), which never uses
the 3D camera at all: it draws the player as a fixed 24x48 sprite at screenY 136
and pans an 1100px painting at its own `pixelsPerRuntimeY` of 34.6. A modelled
screen that inherits 21.1175 renders the walker at 42.4 px and the player
visibly shrinks on stepping outdoors.

| | plate exterior | modelled exterior | modelled interior |
|---|---|---|---|
| distance | (2D, no camera) | **18.6667** | 18.6667 |
| walker height | 24x48 declared | 48.00 px | 48.00 px |
| px per world unit | 34.6 | 27.4286 | 27.4286 |

### Pitch

Maps 28 and 29 (the 3D interiors) run a compensated **-17.5 degree** pitch, and
a modelled exterior should match them — at pitch 0 every box face is parallel or
perpendicular to the view plane, so a box can only ever present as a rectangle
and the massing reads as blocks.

Principal-point compensation (shift `viewportCenterY` by the amount the anchor's
feet moved) pins the feet **exactly**, measured drift 2e-5 px. It cannot hold
the character's HEIGHT, and the anisotropic `projectionScale` the interiors ship
only claws back about half:

| treatment | walker | feet drift |
|---|---|---|
| pitch 0 | 48.00 px | 2e-5 |
| -17.5, uncompensated | 55.34 px | 2e-5 |
| -17.5 + `projectionScale {0.94079629, 0.9116197588}` | **52.07 px** | 2e-5 |

So the canon is not "48 px". It is **whatever treatment the 3D interiors use**,
because what matters is that the character is the same size on both sides of a
door. `tools/blender/study_town_pitch.py` reports the residual rather than
masking it; keep it that way.

## Measured constants

Ground authored at Z = 0 like an interior floor; the lane's own `groundZ`
places it at runtime.

- The ground plane crosses the frame bottom (native row 240) at **X = -12.0153**.
  An exterior slab must reach it. The Praca scaffold's slab starts at X = 5.1,
  which is why that ground stops short of the status window.
- Height needed to reach the top of the menu band (row 144): **0.03 m at X=-4,
  0.64 m at X=-8, 1.09 m at X=-11.**
- Visible half-width: **4.67 m at the action plane, 2.67 m at X=-8, 1.92 m at
  X=-11.**
- The walker occupies rows **80 (head) to 128 (feet)**.

Those last two run in opposite directions, and that opposition is the single
most useful fact here: the frame narrows toward the lens while the height needed
to cover the menu falls. The very front of a scene can be low and still do its
job, and it *must* be, because almost nothing fits there.

## The near stack is three ranks

"Foreground" collapses two independent axes — where a thing sits in the parallax
stack, and whether it occludes the player. Separate them.

    NEAR         occludes the foreground layer, parallaxes fastest, and by
                 default does NOT touch the player
    FOREGROUND   the pass-behind layer, which DOES occlude the player -- that
                 occlusion event is the reason it exists
    PROP         street furniture at or behind the action plane, built inside
                 `Exterior.props()` so it is excluded from the near-rank
                 measurements

**A known-size object cannot stand in the near rank.** At X = -10 an object
renders 2.15x magnified. That is correct perspective, but a crate has a known
real-world size, so at 2x the eye reads it as *wrong* rather than as *near*.
Foliage, masonry, cloth and a roof edge have no canonical size, so the same
magnification reads as proximity. Human-scale goods belong at the action plane.

## Occluders: tall or continuous, never both

The house rule for anything crossing the character:

    pole        tall, narrow          fine
    skirt       wide, low             fine
    board       tall AND wide         REJECTED
    incidental  covers neither much   fine

Foliage hiding the characters' feet across a good part of the screen is fine. A
pole is fine. A board that swallows the whole character is not — the player
loses track of where they are.

`Exterior.occludes_player()` classifies by shape and `boards()` returns the
violations; **`boards()` must be empty.** Occluding the player is legitimate and
sometimes the point, but it has to be a choice rather than a side effect of a
height picked to cover the menu.

## Vegetation is alpha cards

A bush is not modelled leaf by leaf. It is a handful of quads, each carrying a
cutout texture of a whole leaf **cluster** with its twigs. The mesh gives the
silhouette and the parallax; the texture gives every leaf. Real leaf geometry
was tried first: 8,751 objects for one hedge, and it still read as boulders
wearing spikes.

Cards come from `tools/materials/make_foliage_cards.py`, which uses the image
route's `background: transparent` for a REAL alpha channel — keying a colour
backdrop leaves a fringe on every leaf edge, and at 256x240 the fringe is most
of the leaf. ambientCG cannot supply these: it is a library of tiling ground
surfaces, and its `Atlas` type is single leaves rather than clusters.

**Card content decides what a placement can be.** A vertical broadleaf sprig
scattered over a dome produces clumps of tall grass no matter how it is placed;
three passes of re-scattering could not fix it. A hedge needs a card that is
itself a hedge section — domed top, ragged edge, wider than tall — laid
overlapping along the lane. Generate the card the composition needs instead of
re-placing the wrong one.

Two silent Blender traps, both of which render foliage black or flat:

1. **A custom split normal is stored in LOCAL space**, before the object
   rotation. Transferring a normal is what makes cards light as the volume they
   stand in for rather than as separate slabs, so author it in the space it is
   stored in.
2. **Card facing decides whether that normal survives.** The quad's own normal
   is local **-Y**, so a `+pi/2` yaw turns it to `+X`, away from the lens.
   Cycles flips the shading normal on a backface, turning a skyward normal into
   a downward one and rendering the whole run black. Face the quad at the
   camera.

## Light

Interiors take every hard shadow from a source the room contains, because a
raking key makes a room read as a diorama. Outdoors the sky IS the source:
`Exterior.sky_rig()` is a large soft dome plus one weak sun for direction. Still
no harsh key, and the albedo doctrine still holds — textures carry their own
ambient occlusion and no baked direct light.

Watch for near-rank pieces shadowing each other. A stone parapet and a run of
planting occupying the same depths and lane spans shaded each other to near
black, and that looked exactly like a lighting bug.

## Always render with a character in frame

Not a nicety. `Exterior.foreground_scale()` reports each near piece as a
fraction of the frame width at its own depth, and a pass tuned against it to a
"safe" 0.447 turned out to have handcarts taller than a person and crates the
size of boulders — obvious in the first frame that had a walker in it. **A frame
fraction cannot tell you whether a cart dwarfs a human.**

Stage the walker at the camera's own lane position plus an NPC from the screen's
real cast, via `thestra_camera.create_actor_preview` at `world_height=1.75`,
frame 24x48. Guard the camera basis determinant first or the actor silently
flips (issue #935).

## Open questions

1. **No sky yet.** The engine already has the whole `skyPanorama` path
   (`viewport_3d.lua`), horizon-anchored and vertically clamped, gated on
   `ceilingStyle == "sky"` — which map 18 already declares. But it scrolls off
   camera YAW, and a `bounded_lane` camera is yaw-0 and pans via
   `projectionWindowOffsetX`, so the sky would sit frozen while the street
   slides past it. Driving sky offset from the projection window is engine work
   nobody has done.
2. **The exporter is interior-only.** `export_room_environment.py` hardcodes
   `LANE_CENTRE = 3.8833`, a room-box collision, `INTERIOR_FILL` lighting and a
   spawn/exit/one-NPC anchor set. An exterior needs its own lane centre, a
   lane-strip collision, the sky rig, and arbitrary anchors.
3. **Alpha cards through the bake is untested.** The pipeline joins TH_SOURCE
   into one mesh with a smart UV unwrap and bakes to an opaque atlas. Whether
   cutout foliage survives that as anything but opaque rectangles is unknown.
