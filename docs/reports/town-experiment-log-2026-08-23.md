# Second Gate town experiments — maintainer research log

**Audience: owner and orchestration agents only.**

This log deliberately names attempts, branches, winners and dead ends. That
makes it the exact input that
[`town-gauntlet-agent-boundary.md`](../design/town-gauntlet-agent-boundary.md)
forbids handing to a fresh town art agent. Do not cite, summarise, or quote it
into an art task. Art agents get
[`town-authoring-known-good.md`](../design/town-authoring-known-good.md) and
nothing else.

It exists because the durable *facts* were distilled into that sterile contract
while the *history* — what was tried, what killed each direction, which
questions are still open — stayed spread across roughly two dozen branches and
PR bodies. Answering "did we already try X?" required reading all of them. This
log answers it in one place.

Companion documents:

- [`town-gauntlet-absorption-2026-08-20.md`](town-gauntlet-absorption-2026-08-20.md)
  — the anonymised closure boundary for the 08-20 family.
- Issue #838 — the design charter (sidescroller, not platformer).

Covers 2026-08-19 through 2026-08-23.

## What actually landed on `main`

Only the non-visual camera/pipeline lane. No town art, no environment package,
and **no traversal code** are on `main`.

| PR | What landed |
|---|---|
| #848 | Principal-point ownership moved onto resolved `WorldCamera` |
| #850 | Static-camera projection-window panning prototype |
| #851 | Blender baked-environment pipeline spike |
| #852 | `WorldCamera` to Blender calibration (`tools/blender/thestra_camera.py`) |

Also on `main`: `tools/blender/town_environment_pipeline.py`,
`tools/blender/tests/test_town_environment_pipeline.py`,
`tools/blender/fixtures/town_slice_synthetic.blend`,
`exports/environments/town_slice_spike/`.

Verified absent from `main` as of 2026-08-23: any side-view or bounded-lane
runtime code. A grep over `shared/`, `runtime/`, `studio/editor/src` and
`projects/hichaukitoden-game/data` returns nothing for `sidescroll`,
`sideView`, `bounded.lane` or `laneProvider`.

## Phase 1 — first gauntlet and the camera correction (08-20)

| PR | Branch | State | Outcome |
|---|---|---|---|
| #856 | `exp/town-gauntlet-workbench` | closed | V0 gauntlet: 9 attempts, contact sheet, projection strip, baked `town_pilot` package |
| #859 | `prep/town-gauntlet-camera-authority` | closed | Camera correction — the durable output of this phase |
| #860 | `codex/next-second-gate-town` | closed | Calibrated workbench; first three-way material-source comparison |
| #863 | `exp/town-material-gauntlet` | closed | Materials/bake pass; found a mathematically unreachable camera assertion |
| #865 | `next_town_material_gauntlet` | closed | Submitted with an unfilled PR template; no recoverable findings |

**The load-bearing event of this phase is #859.** #856 had silently promoted
#852's 30 degree *parity test fixture* into art direction — a number that
existed to verify a calibration round-trip, not to frame a town. The 08-20
perspective study caught it and #859 replaced it with an owner-selected
baseline: 0 degree pitch, `fovHalfX = 0.25` (28.0724869 degrees horizontal
FOV), ~43.27 mm Blender-equivalent, study framing distance 6.9 world units.
That baseline survives unchanged into every later run and is now in the sterile
contract.

This is the clearest instance of a failure mode worth remembering: **a test
fixture leaked into art authority because both were "the camera number."**

#863 found the related tooling defect — `check_next_town_camera.py` compared a
single-precision `camera.data.lens` against a double-precision derivation with
a `1e-8` absolute tolerance. At ~43 mm, float32 resolution is ~3.8e-6, so the
check could never pass; the 8.06e-07 delta was pure storage rounding. Tolerance
now scales with float32 resolution.

## Phase 2 — the playable proof (08-20)

| PR | Branch | State | Outcome |
|---|---|---|---|
| #862 | `codex/second-gate-town-playable-v2` | closed | **Bounded-lane traversal proof — the only playability evidence in the whole family** |

This is the most consequential closed PR in the set, and the one most likely to
be re-derived by accident. It demonstrated:

- continuous left/right world position with authored min/max bounds;
- projection-window tracking clamped to -96..96 px with the camera eye fixed;
- no jump, no gravity, no platformer grammar;
- **no new Map ontology** — no `sideScrollerMap`, no Map v2;
- ordinary Project/Event authority still owning dialogue, flags and transfers;
- two ordinary maps (16 Old Gate Street exterior, 17 Apothecary interior) with a
  working doorway between them.

Measured camera authority: solved distance 21.1175, horizon Y=110, a
1.75-world-unit actor measuring 47.9979 px at the action plane.

The conclusion recorded in the sterile contract — *"the useful behavioral seam
is a bounded continuous lane/provider, not a new universal Map ontology"* — is
this PR's. Its map data and naming are explicitly **not** production authority.

## Phase 3 — clean-room and the continuity gate (08-20 to 08-21)

| PR | Branch | State | Selected direction |
|---|---|---|---|
| #864 | `codex/cleanroom-town-gauntlet` | closed | Attempt 04, "Needle Forum" (6 divergence + 3 convergence) |
| #867 | `codex/cleanroom-town-gauntlet-findings-20260820` | closed | Lineage B (3 factory-reset lineages) |
| #868 | `sterile_town_gauntlet_init` | closed | Sterile exploration, Blender 5.1 |
| #875 | `codex/second-gate-town-gauntlet-20260820` | closed | C3 — bell tower, gate passage, diagonal canopy, foreground bridge roof |
| #876 | `exp/town-cleanroom-gauntlet` | closed | Nine scenes from geometric zero |

Findings that became rules:

- **Breadth loses to depth.** A broad nine-scene batch produced shallower
  geometry than a small number of independent lineages each given serious
  refinement passes. The clean-room reset belongs *between* independent
  directions, not between every revision.
- **The continuity gate came from #875.** Its first clay ground read as a
  clipped platform — a walkable strip in front of a backdrop rather than a view
  inside a place. The rejection produced the whole "full-environment framing"
  section: authored world-space overscan beyond the tracking envelope, no
  visible set edges at -96/0/+96, a real foreground layer at meaningful depth,
  floor as part of the composition.
- **#867's review note:** the buildings read too close to the Walker. The fix is
  a farther-back authored action plane, *not* a wider lens.
- **#876 measured the atlas waste** that became issue #877: of 182 triangles,
  only 45 were ever visible across the measured projection-window views; 69.5%
  of allocated texels went to faces never visible in that envelope; visible-face
  density ranged 0.57 to 56.5 texels per native screen pixel; true 1:1 visible
  demand was about 264x264 against a 1024x1024 atlas. Its `atlaspack.py` was
  **not** absorbed — it backface-culled per sampled view and could destructively
  delete faces, which is too absolute for the engine.
- **#876's asset-firewall audit** established that "pre-existing" must be defined
  by git tracking at the base commit, not by file location, because the task
  writes into the repo during promotion and a location test flags every promoted
  file as a breach.

Three generic defects surfaced here and belong to tooling, not art:

1. a reflected camera/billboard basis (determinant -1) cannot survive quaternion
   conversion — a quaternion represents rotation, not reflection, and the result
   was inverted actors;
2. a selected-to-active bake receiver does not automatically own a usable
   non-overlapping atlas UV layout;
3. a scene-linear Combined bake written as raw bytes into a PNG later sampled as
   sRGB renders dramatically too dark.

Also established: **4-sample Cycles with denoising is sufficient** for authoring
decisions through clay, presentation and bake comparison. Expensive sample
counts should not be the exploratory default.

## Phase 4 — generic tooling lane (08-21, mostly open)

| PR | Branch | State | Owns |
|---|---|---|---|
| #873 | `tools/871-blender-render-profiles` | open | Named render profiles, expensive-render guard, Second Gate presentation facts, facade projection |
| #874 | `exp/872-ai-surface-projection` | closed | Geometry-conditioned AI surface projection spike |
| #879 | `tools/877-view-weighted-atlas` | open | Continuous world/view density blend over a camera envelope |
| #881 | `codex/finish-blender-authoring` | open | **The pipeline every later gauntlet stacks on** |

#874 is the conceptual pivot the later art runs depend on: image generation used
as *semantic facade authorship* rather than as a commodity texture generator.
The loop is: real Blender mass plus calibrated camera, then one cheap control
render plus a multilayer depth/normal/object-index EXR, then an external
provider, then a view-aligned facade treatment projected through the same camera
onto real mesh UVs, then baked to ordinary UV space. Provider-agnostic by
construction.

#879 replaced binary visibility with `density = lerp(world_density,
view_density, view_bias)` over a `ViewSample` envelope (projection-window X/Y,
eye offset, yaw, pitch, weight, movement cost), keeping culling separate from
texel weighting.

**#881 is the current bottleneck.** It was rebuilt directly on `main` after
#848/#850/#852 landed, and #882/#883/#884 all stack on it. It is still open, so
those three are stacked on an unlanded base.

## Phase 5 — parallel art gauntlets (08-21, all open, none merged)

Three sourcing strategies were run in parallel against the same brief.

**Image-assisted** (generation projected onto authored mass):

| PR | Direction selected | Runtime cost |
|---|---|---|
| #882 | Cinder-Quay Apothecary & Embalmers' Terrace | — |
| #883 | Stacked reliquary market | 10,228 to 424 tris, 1024² atlas |
| #884 | Ember Bell Foundry | 512² view-weighted atlas, 5-sample envelope |

#883 recorded the sharpest division of labour: generation helped most with
*coherent architectural systems* (reliquary cabinets, repaired brick/plaster,
awnings, drainpipes, votive ornament, inhabited window groupings), while
depth-critical roofs, canopies, door recesses, cornices and foreground occluders
had to stay geometry. #884's honest weakness: runtime atlas richness and
lighting.

**Blender-authored from empty scenes:**

| PR | Direction selected | Runtime cost |
|---|---|---|
| #878 | Bell Foundry Gate (Ashwater) | 5,069 to 621 tris, 512² atlas, OptiX bake |
| #880 | Lantern Cleft | 10,496 to 460 tris, 22.8x reduction |

**Human-made CC0 kitbash** (no AI assets at all):

| PR | Direction selected | Sources |
|---|---|---|
| #885 | Phase 1 sourcing only — stopped for review | 16 KayKit candidates, 13 shortlisted; Poly Haven HDRI + cobblestone |
| #886 | Market landing (Direction A) | KayKit Medieval Hexagon Pack, CC0 |
| #887 | Cinderbridge Market (Direction A) | KayKit + five Poly Haven CC0 models |

All five completed art PRs converge on the same triangle budget — **~420 to 620
runtime triangles from 5k to 10k source** — which is strong independent evidence
that the collapse ratio is real and not an artefact of one authoring style. None
was selected. #885 is explicitly waiting on owner review of its shortlist before
Phase 2.

## Phase 6 — the Meshy prerender experiment (08-21, open)

| PR | Branch | State |
|---|---|---|
| #890 | `codex/second-gate-town-experimental-20260821` | open |

The most complete end-to-end result in the family, and the one that most
directly matches the current production intent. It turned a supplied Meshy
old-stone-village scene into a playable Second Gate exterior with the church as
the Labyrinth entrance.

What it proved:

- a Blender annotation scene as the human-editable source of truth, with a
  required object contract (`CAMERA_PLAYER_VIEW`, `Meshy_Village_Source`,
  `SPAWN_PLAYER`, `WALKABLE_MAIN`, `WALKER_SPRITE`);
- interpolated live actor movement with a presentation position separate from
  the resolved traversal coordinate, so the walker no longer snaps tile to tile;
- events, doorways and anchors staying in ordinary map data (map 16 to map 2
  through the church; map 17 apothecary side door), with a `town_bell_rung` flag
  changing later text;
- `VALIDATE OK`, `THESTRA_TOWN_PROOF OK frames=7`, `ALL UNIT TESTS OK` against a
  staged project.

Two compositing bugs found by inspecting proof frames rather than trusting
generated files — both worth remembering because both produced plausible-looking
output:

- Blender's `Image.pixels` depth rows are **bottom-up**. Reading them top-down
  inverted the foreground mask, putting sky in the foreground and removing the
  objects that should occlude the player.
- The camera-shift correction initially had the wrong sign, so fixed landmarks
  travelled *with* the player.

A three-reviewer blind pass (three independent lenses, no shared output) found
the collision OBJ using the wrong world-to-OBJ conversion (fixed to
`(world X, world Z, -world Y)`), a test that never exercised the shipped package
(fixed), and an ignored `--projection-samples` flag (removed).

### The unresolved architectural conflict

**#890 chose the presentation the sterile contract forbids, and it worked.**

The known-good doc is explicit: *"Do not replace the environment with a
camera-space beauty plane or one flat prerendered background. The runtime
geometry must retain the depth/silhouette/occlusion structure needed by the
scene."* #890 did precisely that — 41 camera-centred slices from runtime Y -2.0
to 13.0 at 0.375 spacing, each producing `scene`/`background`/`foreground`
layers with the foreground mask derived from the depth render, live actors
composited between them.

It did so for a concrete reason: the Meshy package is ~830k triangles and 112 MB
for the render OBJ, too expensive to draw live and too hard to make match the
intended 2D presentation. **The decimation step that every Phase 5 gauntlet
performed — 5k to 10k source down to ~420 to 620 runtime triangles — was
skipped, and full prerendering was adopted in its place.** The dense fallback
needs Git LFS and records `targetFaces: 60000` against a measured 830,226
triangles, a discrepancy #890 left visible rather than fixing.

Known costs of the flat-layer route: a ~17 MB PNG cache for 41 slices; a
central-slice-plus-underlay compositor that can still expose a seam if a scene
change moves the camera outside baked coverage; and no true runtime lighting or
depth interaction for anything that moves independently of the bake.

The stated production goal — low-poly unlit geometry carrying a high-quality
baked texture under a fixed camera — is the **sterile contract's** position, not
#890's. #890 is best read as evidence that the *content and interaction* work,
obtained by taking a shortcut around the geometry collapse. Reconciling the two
means running Meshy output through the decimation the Phase 5 gauntlets already
demonstrated, rather than choosing between the two presentations.

## Open questions this log does not answer

1. **The firewall has no exit condition.** The clean-room protocol forbids
   reusing any prior town mesh, layout or material, and mandates empty-scene
   restarts between directions. That is correct for research and structurally
   prevents convergence. Nothing declares the research phase over and the
   production lane open.
2. **Where Meshy output enters the `TH_*` contract.** It is neither `TH_SOURCE`
   (assumed to be authored Blender material) nor `TH_RENDER` (needs a valid
   non-overlapping receiver atlas UV set). The most likely answer is
   `TH_SOURCE`, leaving the collapse unchanged downstream — but the documented
   receiver-UV trap is exactly where generated meshes will fail, and it has not
   been proven on even one asset.
3. **Twelve open PRs have no disposition:** #873, #878, #879, #880, #881, #882,
   #883, #884, #885, #886, #887, #890. #881 blocks three of them.
4. **Which sourcing strategy wins.** Image-assisted, Blender-authored and CC0
   kitbash were run in parallel and never compared against each other.
