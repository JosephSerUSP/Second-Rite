# What Blender 5.2.2 changes in our outputs, and whether EEVEE can replace Cycles (2026-09-30)

Follows `blender-tooling-audit-2026-09-28.md`, whose 5.2 facts were second-hand.
This report measures instead. Everything below was run under **Blender 5.2.2 LTS**
(build `d13f752e3b9c`) against `origin/main` at `7b7ff85a`, and nothing here writes
an asset: renders and bakes go to `out/`, and the `.blend` sources are opened and
never saved.

Instruments (committed, rerunnable):

- `tools/blender/study_engine_parity.py`: the shop plates under six EEVEE
  configurations, judged against the Cycles plate.
- `tools/blender/study_atlas_drift.py`: the two shop atlases re-baked and compared
  with what is committed.

## Findings

1. **The Cycles bake fix moves our atlases very little, and does not sharpen them.**
   Re-baking the Padaria and the smith under 5.2.2 differs from the committed
   atlases by a mean 0.85 and 0.62 of 255, with 1.7% and 0.6% of pixels more than
   8/255 away. Sharpness (Laplacian variance, new over shipped) is 0.96 and 0.99:
   not crisper. Vertex and UV positions are identical (max difference 0.0), and
   vertex, UV and face counts are unchanged. The audit expected "every rebaked
   atlas shifts"; on these two it is below what the eye sees on the sheet.
2. **The bake is deterministic, so that difference is real.** Two 5.2.2 bakes of the
   smith are byte-identical. The committed OBJ header reads `# Blender 5.1.2`, so
   the shipped atlases were baked by 5.1.2, which the repository did not record.
3. **EEVEE in 5.2.2 does not reproduce the Cycles plates.** No configuration comes
   near it (table below). The best exposure-fitted result still leaves a mean of
   4.7 to 6.3 of 255 and 24% to 32% of pixels more than 8/255 away.
4. **The world-fill leak is real and a baked light probe volume fixes it,** at the
   cost of a much darker room that would need re-exposing. Fast GI, the new
   backface option and full-resolution raytracing do not.
5. **EEVEE cannot bake.** The atlas that the 3D packages use comes from a Cycles
   selected-to-active bake (`town_environment_pipeline.py`). Moving *plates* to
   EEVEE is possible; moving the *atlas* is not, and it would decouple the two
   presentations of a room, which the design doc says agree "by construction".
6. **The plate and atlas paths are both deterministic** under 5.2.2 (a Cycles plate
   and an EEVEE plate are each byte-identical across two runs), so any pixel
   difference after a change is a real change.

## Plates: Cycles against EEVEE

Setup: the documented interior command (`--ambient 0.13 --lamp-scale 0.3
--accent-scale 0.4 --window-emission-scale 1.0 --no-walker`), each room twice
(fill on and off). `fill%` is the world fill's share of the median luminance over
the rows the room occupies: lower means less light leaking in. `fit` columns fit
one linear-light gain to each plate first, so uniform darkness is not counted:
what remains is structure (bounce, occlusion, colour). Cycles is the reference and
scores 0 against itself.

**Padaria**

| configuration | fill% | median | mean abs diff | px >8/255 | gain | fitted mean | fitted >8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| cycles (reference) | 10.1 | 42.4 | 0.00 | 0.0% | 1.00 | 0.00 | 0.0% |
| eevee, no raytracing | 79.7 | 45.4 | 6.62 | 28.7% | 1.15 | 6.70 | 31.2% |
| eevee, AO raytracing (today's `--engine eevee`) | 76.4 | 39.3 | 6.83 | 30.2% | 1.26 | 6.27 | 30.1% |
| eevee, backface hit off | 76.4 | 39.3 | 6.83 | 30.2% | 1.26 | 6.27 | 30.1% |
| eevee, Fast GI global illumination | 73.7 | 40.6 | 6.55 | 29.4% | 1.24 | 6.12 | 28.8% |
| eevee, full-resolution GI | 73.6 | 40.5 | 6.53 | 29.3% | 1.24 | 6.11 | 28.8% |
| eevee + probe volume, 2 cells/m | 14.6 | 26.1 | 8.88 | 35.7% | 1.45 | 6.85 | 30.0% |
| eevee + probe volume, 4 cells/m | 13.7 | 24.4 | 9.63 | 38.7% | 1.46 | 7.11 | 32.2% |
| eevee + probe volume, no raytracing | 16.5 | 29.4 | 7.58 | 31.4% | 1.37 | 6.30 | 27.2% |

**Smith**

| configuration | fill% | median | mean abs diff | px >8/255 | gain | fitted mean | fitted >8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| cycles (reference) | 40.5 | 20.8 | 0.00 | 0.0% | 1.00 | 0.00 | 0.0% |
| eevee, no raytracing | 100.0 | 31.3 | 6.05 | 29.5% | 0.91 | 5.83 | 29.9% |
| eevee, AO raytracing | 100.0 | 25.3 | 4.70 | 22.2% | 1.01 | 4.72 | 24.5% |
| eevee, backface hit off | 100.0 | 25.3 | 4.70 | 22.2% | 1.01 | 4.72 | 24.5% |
| eevee, Fast GI global illumination | 100.0 | 26.1 | 4.78 | 23.0% | 1.00 | 4.77 | 24.2% |
| eevee, full-resolution GI | 100.0 | 26.1 | 4.77 | 23.0% | 1.00 | 4.77 | 24.2% |
| eevee + probe volume, 2 cells/m | 81.1 | 8.3 | 6.86 | 32.7% | 1.37 | 5.97 | 30.1% |
| eevee + probe volume, 4 cells/m | 83.2 | 7.2 | 7.47 | 35.7% | 1.40 | 6.39 | 32.5% |
| eevee + probe volume, no raytracing | 78.9 | 10.1 | 6.12 | 28.2% | 1.31 | 5.43 | 26.6% |

Contact sheets (each configuration beside the Cycles plate, with a 4x difference
strip): `blender-52-measurement/alicias_padaria_contact.png` and
`lauras_smith_contact.png`. Raw numbers: `plate-engine-results.json`.

Reading it:

- The fill share is not the doc's 3.4% for Cycles. That figure was measured before
  `--lamp-scale 0.3` dimmed the lamps, which raises the fill's share of a dimmer
  room. Read the column relatively: Cycles 10%, EEVEE 74% to 80% (Padaria).
- Every EEVEE variant except the probe volume leaves the fill at 74% or worse. So
  the design doc's reason for Cycles still stands under 5.2.2: raytracing, Fast GI
  and the backface option do not stop the fill lighting a sealed box.
- The probe volume with `capture_world` brings the Padaria to 14.6%, within reach of
  Cycles' 10%. The smith stays at 81%: its median is 8, so a small absolute
  difference is a large share.
- The forge and the oven show as the largest, most colourful differences in every
  EEVEE row: Cycles bounces their light onto nearby walls and EEVEE does not.
- Probe-volume plates come out much darker (gain 1.31 to 1.46) and the smith
  changes mood, not just level, so it is a re-lighting job, not a switch.
- The best-fitted EEVEE result (smith, AO raytracing, 4.7) is still four to five
  levels of 255 away on average. This project judges plates by eye at 256 px, so
  the contact sheets decide; the numbers say only that no configuration is a
  drop-in replacement.

## Atlases: 5.2.2 against the committed bake

| package | bake time | mean abs diff | p95 | px >8/255 | sharpness ratio | vertices / UVs / faces |
|---|---:|---:|---:|---:|---:|---|
| `alicias_padaria_3d` | 229 s | 0.85 | 5.0 | 1.7% | 0.962 | 1934 / 4986 / 3208, unchanged |
| `lauras_smith_3d` | 171 s | 0.62 | 4.0 | 0.6% | 0.989 | 1186 / 3450 / 1816, unchanged |

The OBJ text differs in two places that are not geometry: the header comment, and
the object's group line (`g lauras_smith_TH_RENDER_Mesh` became
`..._floor_mesh.001`), consistent with the 5.2 note that evaluated meshes get
distinct names. The runtime parser (`runtime/presentation/obj_model.lua`) handles only
`v`, `vt`, `vn`, `mtllib`, `usemtl` and `f`, so neither difference reaches the game.

**Not measured:** the Praça atlas (a 2048 px Cycles bake; the arguments the shipped
package was baked with are not recorded, so a comparison would be against a guess),
and exterior plates. Both belong with #1270, which needs the full bake anyway.

## Where Cycles is used

| use | can EEVEE replace it? |
|---|---|
| Atlas bake (`town_environment_pipeline.py`) | **No.** EEVEE has no bake. |
| Interior plates (`stage_room_model.py`, default) | Not as a drop-in; see above. Possible with re-lighting and an owner decision. |
| Asset-gen exploration scripts (`build_chest_exploration.py`, `build_props_exploration.py`) | Likely yes; previews only. Not measured. |
| Ground-cover pilot preview (`recipes/ground_cover_pilot.py`) | Likely yes; a study render. Not measured. |

So "no Cycles at all" is reachable for previews and studies, but the atlas bake
keeps one Cycles dependency. If that is unwelcome the alternative is a different
way of producing the atlas (for example rendering an unwrapped view with EEVEE),
which would be a new pipeline, not a setting.

## Cleanup done with this measurement

The pin removed the reason for three copies of "which EEVEE is this?":
`stage_room_model._eevee_engine`, `study_house_grammar.eevee_engine` and the probing
in `towngen/spike_massing.py` are gone; all three name `BLENDER_EEVEE`, the only id
in 5.2.2. The `hasattr(eevee, "use_raytracing")` guard went with them, and two
asset-gen docstrings that named Blender 5.1 now point at the pin.

Left alone on purpose: the live bridge's undo workarounds
(`live_bridge/server.py`, "Blender 5.1 can restore transform RNA..."). Whether 5.2.2
still needs them can only be tested by the owner undoing in a live session.

## Online asset libraries

Investigated read-only; nothing was downloaded beyond the listing files.

**What exists in the installed 5.2.2.** Remote libraries are a static-file protocol
(`_asset-library-meta.json`, `_v1/asset-index.json`, paginated
`_v1/assets-NNNNN.json`, SHA-256 hashes on every file). The client is Python and
ships in the install under `scripts/modules/_bpy_internal/assets/remote_library/`,
with a CLI (`blender -c asset_listing download <url>` and `... generate <dir>`) and
`asset_downloader.download_asset_file(...)`. The package is underscore-private:
Blender's own notes say only that parts are intended to become public.

**What Online Essentials contains** (listing read from
`https://cdn.extensions.blender.org/asset-libraries/essentials/`): 113 assets,
about 422 MB in 57 files, **all `CC0 - Public Domain`, each with `author`,
`license`, `description` and a minimum Blender version** (105 need 5.2, 8 need 5.3).

| type | count | examples |
|---|---:|---|
| materials | 37 | bricks (cobblestone, natural, regular), tiles (terracotta, checkered, alternating), wooden boards (strip, herringbone, basketweave), metal (rusted, galvanized, brushed), fabric, concrete, leather |
| worlds (HDRI) | 12 | courtyard, forest street, interior, night, sunrise, sunset |
| compositor node groups | 8 (listed twice) | dithering, depth atmosphere, rim 2D, paint filter, normal/position mask |
| collections and objects | 25 | human base meshes, heads, hands, skeleton |
| brushes | 23 | sculpt and paint brushes |

**What that could mean for agents.**

- *Provenance for free.* The listing carries licence and author per asset, in a
  machine-readable form, and the downloader verifies a hash. That is a stronger
  provenance record than most sources give, and it fits the inventory rule.
- *No Blender needed to search.* The listing is JSON over HTTP, so an agent can
  filter by type, licence and catalogue with ordinary Python and fetch one asset by
  hash.
- *A way to publish our own.* `asset_listing generate` turns a directory of `.blend`
  files into a library that any static host can serve. `SR_GroundCover` and the
  material library are candidates; a local (non-remote) asset library would do the
  same for agents working inside the repository, with no network.
- *Relevant content:* the procedural brick, tile and wood materials, the courtyard
  and interior HDRIs (as lighting references for plates), and the dithering and
  depth-atmosphere compositor groups (a pixel-art post step).
- *Not relevant:* the human base meshes and skeleton (characters are sprites).

**Constraints to settle before anyone adopts anything.**

- Assets must be single-file: no links to other `.blend` files and no external
  media. Multi-file assets are not supported yet.
- Online use needs Blender's *Allow Internet Access* preference, and CI and a build
  must not depend on a remote host: anything adopted has to be **vendored into the
  repository with its listing metadata**, the same way the CC0 texture sets were.
- A downloaded `.blend` can carry scripts. Open assets with `--disable-autoexec`,
  and prefer appending a named datablock over opening the file.
- The material library rule ("sourced CC0, `.blend` freezes its node graph") means
  a procedural Blender material is a different kind of source from the image sets
  now in use; whether procedural materials suit the pixel-art bake is untested.
- The Python entry points are private and can move between 5.2.x releases; talking
  to the HTTP listing directly is the stable route.

I have **not** adopted any asset, added a network dependency, or changed the
material library.

## Recommendations

1. **Atlas rebake: no action.** The drift is sub-visual on the two measured
   packages and buys no sharpness. Do not rebake for the aliasing fix. Whether to
   record the Blender that baked each shipped package is worth doing in the
   package `provenance` (the OBJ header was the only record).
2. **Plates stay on Cycles for now.** Moving them to EEVEE is a lighting project
   (probe volume plus re-exposure, per room), not a setting, and it splits the plate
   from the atlas. If the owner wants to pursue it, start with the Padaria, where the
   probe volume already reaches the Cycles fill share, and judge the contact sheets
   before any exposure work.
3. **Retire Cycles from previews and studies** (asset-gen exploration scripts, the
   ground-cover pilot render) with a visual diff each; they are the cheap part of
   "less Cycles".
4. **Asset libraries:** the first concrete step is a read-only listing browser for
   agents (search by type and licence, print provenance), plus a decision on whether
   to publish our own library. No vendoring until a scene needs something.

Agent-Signature:
  platform: Claude Code (desktop)
  model: Sonnet 5.5
  role: research
  task: "Blender 5.2 measurement; cleanup of EEVEE enum probing"
  base: 7b7ff85a
