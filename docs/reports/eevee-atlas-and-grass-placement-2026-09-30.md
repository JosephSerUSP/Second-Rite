# EEVEE atlases, the atlas layout, EEVEE previews, and the Praça grass placement (2026-09-30)

Follows `blender-52-measurement-2026-09-30.md`. Four pieces of work, one report. All of it ran
under Blender 5.2.2 LTS; nothing here writes or regenerates a shipped asset, and the `.blend`
sources are opened and never saved. Evidence is in `eevee-atlas-and-grass-placement-2026-09-30/`.

## 1. A correction to the last report

The last report recommended "Atlas rebake: no action", on the strength of the Cycles 5.2 bake fix
moving the shop atlases by under 1/255. That was true and beside the point. Both shop atlases were
laid out with `smart_project(island_margin=0.02)`, which the shops report had already measured as
"roughly 23% of the atlas carries texels" and which `export_room_environment.py` still used. I
built the atlas study on that layout without saying so; the owner caught it. The layout, not the
Blender version, is where the atlas is wasting resolution (section 4).

## 2. Placement study for #1270 (owner decision)

`study_ground_cover_placement.py` puts the `SR_GroundCover` modifier on a scratch terrain guide
over the adopted `st_maria_praca_modelled.blend` (never saved) under five candidate density
fields, and photographs each through the plate camera at 906 x 240 with EEVEE. Every candidate
follows the same rules: density only inside the plate frame including the menu rows; never under a
building or on the walkable lane; and a hard budget of 375 tufts (1,500 triangles) met by scaling
the density until the realised count fits, not by truncating in index order. The sheets are
`placement_sheet.png` (native size, the rows the menu covers dimmed) and `placement_zoom.png`
(the right-hand lane at 2x).

| candidate | tufts | above the menu | under the menu |
|---|---:|---:|---:|
| A: building bases | 375 | 375 | 0 |
| B: tree rings | 375 | 0 | 375 |
| C: lane edges | 375 | 268 | 107 |
| D: worn-paving patches | 375 | 132 | 243 |
| E: bases + trees + lane edges | 375 | 256 | 119 |

What the frame actually holds: the ground the player can see above the menu line is a strip about
25 rows tall (roughly rows 118-144, between the building bases and the menu), and the ground
below it, 96 rows, is under the menu. So the choice of layout is mostly a choice about how much
of the cover the menu hides. A and C put it where it stays visible; B and D put it in the menu
band; E splits the difference. A tuft is 0.34 m, about 9 px at this camera, so at 375 tufts the
cover is subtle at 1x whichever layout is chosen.

Placement is not decided. Nothing is adopted into the source `.blend`.

## 3. Cycles out of previews

`ground_cover_pilot.py` now renders with EEVEE. The two `tools/asset-gen` exploration scripts
still render with Cycles, deliberately: nothing references them, they write models into a
cwd-relative `assets/models/dungeon` as well as previews, and a naive engine swap changes the
picture a lot (`preview_engine_diff.png`):

| preview | mean abs diff (of 255) | pixels >8/255 |
|---|---:|---:|
| chest exploration | 10.63 | 30.2% |
| props exploration | 12.14 | 17.6% |
| ground-cover pilot | 12.49 | 31.9% |

Those scenes are lit by suns and a world colour only; under EEVEE the props go near-black. Making
them EEVEE previews means re-lighting them, which is not worth doing for unreferenced one-shot
scripts. They should be frozen or deleted, not converted; that is a separate call.

## 4. The atlas layout

Measured on the joined room mesh by rendering a UV frame from five held-out lane cameras and
taking, per pixel, how far (u, v) moves in texels for one screen pixel: 1.0 is one texel per
pixel. `islandCoverage` is the share of the atlas the UV islands occupy.

| room | layout | atlas | islands cover | median texels/pixel | pixels under 1 texel |
|---|---|---:|---:|---:|---:|
| Padaria | loose (as shipped) | 1024 | **10.9%** | **0.61** | **75.5%** |
| Padaria | packed | 1024 | 73.2% | 1.53 | 1.0% |
| Padaria | view | 1024 | 75.3% | 3.23 | 1.0% |
| Padaria | view | 512 | 57.0% | 1.47 | 4.5% |
| smith | loose (as shipped) | 1024 | **15.4%** | **0.75** | **66.1%** |
| smith | packed | 1024 | 80.1% | 1.73 | 0.5% |
| smith | view | 1024 | 83.2% | 3.38 | 0.6% |

The loose layout is worse than the 23% the shops report quoted, and it puts two thirds to three
quarters of the visible surface below one texel per pixel, which is the "sharper plate, blurrier
3D room" result in that report. Packing alone fixes it. The view allocation
(`tools/blender/atlas_allocation.py`, the first implementation of #877) goes further: it
measures how many pixels each face covers from nine lane positions (face ids rendered as a float
frame, no antialiasing), scales each island to that demand blended with world-uniform density
(`view_bias`, default 0.85), never below a floor (4% of the mean visible density), and packs. At
512 it gives the Padaria what `packed` gives at 1024, from a quarter of the texels.

Cycles agrees. Re-baking the Padaria with the tight layouts brings the Cycles atlas closer to its
own Cycles beauty target: mean abs difference over the lit pixels 8.9 (loose) to 6.6 (packed) and
6.3 (view), of 255.

`layouts_sheet.png` shows the four atlases and the same 5x crop from each.

What changed in the code: `export_room_environment.py` gains `--atlas-layout {loose,packed,view}`
with **`packed` as the default** (`loose` stays only to reproduce a shipped package, and
`study_atlas_drift.py` passes it). Shipped packages are untouched; rebaking one for resolution is
an owner-signed step, and this reverses the earlier "no action" for the two shop packages.

## 5. Atlas baking on EEVEE

EEVEE cannot bake (`bpy.ops.object.bake` refuses: "Current render engine does not support
baking"), so `study_eevee_atlas.py` bakes by projection, on the same mesh and UVs as the Cycles
atlas. For each of nine camera positions along the lane it renders the joined room mesh twice
with EEVEE: a beauty frame in linear light with the room's own lamps and materials, and a UV
frame under an emission override painting each pixel with its own (u, v) in 32-bit float. Every
beauty pixel is splatted into the atlas at the texel its UV names; a texel seen more than once is
averaged in linear light and the result is encoded to sRGB, as the Cycles bake's PNG is. The atlas
is then drawn back on the mesh as an unlit, nearest-sampled emission texture (the way the runtime
draws it) from five camera positions the bake did not use, including both ends of the lane, and
compared with the beauty target.

| | Cycles bake | EEVEE projection |
|---|---:|---:|
| time, Padaria (1024, loose layout) | 229 s | 8-11 s |
| time, Padaria (1024, packed / view) | 296 s / 340 s | about 11 s |
| atlas vs its own beauty target, loose layout, lit-pixel mean of 255 | 8.9 | 2.1 |
| same, packed / view | 6.6 / 6.3 | 1.7 / 1.7 |

Reading it:

- The EEVEE atlas reproduces the EEVEE look to about 2/255 on lit pixels, from cameras it never
  baked, including the lane ends. The Cycles bake is further from the Cycles look (6-9) because a
  selected-to-active bake of a fixed view is not the same computation as rendering that view.
- The EEVEE atlas is not closer to the Cycles look than the plates are: EEVEE beauty against
  Cycles beauty is already about 9-11 apart, and the EEVEE atlas against the Cycles beauty is the
  same. The atlas step adds nothing on top of the engine difference measured for the plates.
  This is the coherence point: a Cycles-baked room next to an EEVEE plate is off by that engine
  gap; an EEVEE atlas next to an EEVEE plate is not.
- It only fills what the bake cameras saw, about 20-30% of the island texels before dilution
  (50% under the view layout, which shrinks unseen islands). The rest stay black. Held-out cameras
  show no holes, but a camera outside the bake range would; the game's camera is fixed in pitch
  and distance and constrained to the lane, and that is the assumption.
- View-dependent effects (specular, reflection) are baked in for the camera that saw them.
  These rooms are matte and keyless, so it is small here.
- The world-fill leak in EEVEE (see the last report) is unchanged: an EEVEE atlas inherits the
  flatter EEVEE lighting. The light probe volume fixes that for plates and would for atlases.

### A bug in my first draft, kept as a lesson

`sort_into_contract_collections` moves every object, lights included, into `TH_SOURCE`, and my
first version hid that collection from render to avoid double geometry. That hid the lamps, so the
first "EEVEE beauty" was lit by the world fill alone (no oven glow) and the first comparison
showed the Cycles atlas "brighter than the Cycles render". The images showed it; the numbers did
not. The script now hides only the source meshes and refuses a source with no lights.

## 6. Not done

- Not measured: the Praça atlas, exterior plates, and the game runtime's own 3D view of any of
  this (everything is judged through Blender renders of the mesh).
- Not adopted: the EEVEE projection bake is a study script, not a pipeline backend. The exporter
  still bakes with Cycles; only its default layout changed.
- Not decided: the grass placement (#1270), whether to rebake the shop packages on a tight layout,
  and whether plates and atlases move to EEVEE together.

Agent-Signature:
  platform: Claude Code (desktop)
  model: Sonnet 5.5
  role: research
  task: "EEVEE atlas, atlas layout, #1270 placement study, Cycles out of previews"
  base: b678ad5b
