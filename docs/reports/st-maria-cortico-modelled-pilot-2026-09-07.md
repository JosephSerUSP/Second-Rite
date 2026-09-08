# St. Maria Cortico modelled pilot — 2026-09-07

## Result

The Cortico pilot keeps the canonical map camera at `-17.5` degrees. The
visible composition correction is authored geometry: the near parapets were
lowered in the adopted source blend, while their lane spans and gameplay
anchors were not moved. The floor is now an independent source-authored grid,
not a giant atlas UV island. Flat doorway markers use the shared orientation
contract and no longer pitch upward toward the sky.

The source authority is:

`projects/hichaukitoden-game/assets/authoring/environments/st_maria_cortico.blend`

The absolute workspace file is
`C:/Users/josep/.codex/worktrees/6d7d/Hichaukitoden/projects/hichaukitoden-game/assets/authoring/environments/st_maria_cortico.blend`.
It was edited directly after adoption; the recipe is not used to regenerate
over it.

## Resolved contract

The runtime package is
`projects/hichaukitoden-game/assets/environments/st_maria_town/cortico_modelled/`
and map 26 is `projects/hichaukitoden-game/data/maps/26.json`. Its camera keeps
the authored `pitchDegrees=-17.5`, target Z `2.2604`, eye-height offset
`-1.4583333333`, projection scale `{x=0.94079629,y=0.9116197588}`, vertical
window offset `-107.16301268`, and west/east tracking of `-300/+300`.

The floor source object is `CORTICO_floor_grid`. It exports 1 m world-unit
spacing, a 2 m texture period, 1,548 vertices, and 1,470 faces, with authored
vertex heights retained and a 0.006 m clearance above the beauty mesh. The
package has a separate `floor.obj`, `floor.mtl`, and `floor.png`; its
manifest records the source object, counts, source texture, and SHA-256 hashes.
The runtime loader rejects a floor mesh with missing or malformed provenance.
The former `CORTICO_ground` remains in the blend as an authoring reference but
is no longer marked for beauty-atlas export, so the runtime floor is not
duplicated inside the facade UV allocation.

The floor diagnosis was not “the camera pitch is wrong.” The earlier runtime
floor was one giant quad (four vertices, two faces) covering roughly 17 by 20
world units. Its atlas-style UV treatment was then asked to represent a
glancing, large surface, producing shearing/stripes and a visually uniform
floor. A separate, explicitly spaced grid makes the interpolation and texture
repeat visible at the authored resolution while leaving gameplay elevation
flat in this pilot.

The adopted source also now carries the Cortiço composition pass: visible
household thresholds and patched subdivision piers along the grand-house
gallery, irregular lean-to masses, the shared wash basin, interrupted edge
masonry/drains, planters, the workers' stair and the padaria back-service
canopy. The laundry is intentionally one image-authored quad,
`CORTICO_AUTHORED_LAUNDRY_QUAD`, with the poles, wire and folded cloth in one
generated alpha texture. It is exported as one world-space placed model rather
than baked into the opaque atlas, so transparent pixels discard cleanly and do
not create a rectangular slab.

The follow-up composition pass also adds explicit depth-ranked source geometry:
small limestone near fragments at runtime-visible `x=-8.2..-6.8` around the
actual map-26 west/centre/east camera lanes, plus separated background
household rooflines, terraces, doors, and vegetation at both ends of the
street. The near fragments are intentionally discontinuous and keep the
central actor corridor open; they are not a replacement for the separate
floor mesh or for the pitch-reactive background cards.

The west/east readability issue had a separate cause: the source parapet body
was 0.82 m high plus its coping, about 0.94 m total at this camera. The adopted
blend now uses a 0.58 m body with the coping at a 0.70 m total top. The wall
spans and anchors are unchanged. This leaves the player's upper body visible at
the west and east bounds in both review surfaces; the parapets still occlude
the lower legs.

Doorway arrows are authored with explicit `direction` values (`left`,
`right`, or `away`). The shared `presentation.transition_marker` contract
maps the chevron shaft to lane Y for side exits and world X for depth exits.
The shared OBJ is now a ground-hugging chevron, so the doorway cue reads as a
floor direction instead of a vertical spear while retaining the true `+X`
depth meaning. Under the canonical pitched camera the far-door direction still
projects toward screen-up, but the cue is visibly a floor triangle and its
world Z remains flat. The previous town compositor added a 22-degree depth/Z tilt;
that path is gone, and the focused negative test rejects an upward-pointing
flat-depth marker.

## Runtime semantics

`town-walk` starts at the system spawn, follows the authored bounded-lane
doorway graph breadth-first, moves with production `lane.update` toward anchors,
pushes to the appropriate bound for edge doors, calls production
`lane.eventFor`, executes the authored `LOAD_MAP` commands, and logs each
arrival. It proves transfer reachability and door paths. It does not press the
NPC interaction button. The Scholar and Euler are therefore checked separately
at their real Cortico anchors by compiling their authored command lists through
`interpreter.runInteractive` and walking them with the production
`director.GraphWalker`; both reach dialogue nodes. The visible proof frames
also show the actors' upper bodies and continuous ground.

The generated town graph currently reports 35 doorway edges/arrival anchors.
The only town-walk unreachable map remains map 28, the pre-existing interior
case outside this Cortico package; it is not treated as a Cortico transfer
failure.

## Verification and evidence

The source-side floor exporter test passes its positive and negative cases:
`tools/blender/tests/test_cortico_floor_export.py`. Runtime package tests cover
OBJ parsing, manifest counts, all three floor-file hashes, missing provenance,
and malformed hashes. The focused marker test is
`tests/test_transition_marker.lua`.

The current proof captures are:

- Wide: `out/st-maria-cortico/wide-proof-final2/26-west.png`,
  `26-centre.png`, and `26-east.png`.
- Classic: `out/st-maria-cortico/classic-proof-final2/26-west.png`,
  `26-centre.png`, and `26-east.png`.

Those six frames show the corrected west/centre/east composition: the player
upper body is visible above the lowered parapets, the floor is continuous and
no longer sheary, the laundry quad has visible alpha-cut poles/wire/cloth, and
the NPC/architecture placements remain readable. The final Classic and Wide
proof runs each completed 45 frames.

The distant scenery candidate is now installed as four reusable
`backgroundLayers` world-space OBJ/MTL cards: west, centre, east, and the
alpha-bearing `laundry_quad`. They are derived from the adopted source at the
canonical `-17.5` degree camera, then consumed by the normal depth-tested
placed-model queue. They are not camera-space overlays, and their candidate
floor bridges were intentionally omitted so the authoritative `floor.obj`
remains the sole floor surface. The package records mesh/material/texture
hashes and the `cameraSpace=false`, `reactsToPitch=true` provenance contract;
the laundry texture retains RGBA alpha through export.

The live staged verification uses the canonical exporter boundary and the full
LÖVE runtime. Native coverage remains limited where the local Effekseer shim is
unavailable: the unit lane reports that seven `test_map_transfer` world-effect
assertions were not exercised. That is an environment limitation, not a claim
that those assertions passed natively. The post-export G5 check was not green:
classic matched 131/144 frames and wide matched 24/34; the differing frames
were battle/title (plus the developer-menu frames in Classic), not the map
frames. No golden references were recaptured.

## Remaining scope

The grid carries visual per-vertex heights, but the bounded-lane pilot still
walks a flat authored `groundZ`; there is no full terrain-elevation traversal
contract yet. The background card also remains non-interactive: it supplies
depth/parallax scenery, not collision or traversal. No global sky or default
background behavior was changed.
