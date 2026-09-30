# EEVEE pilot on the Padaria: plate and atlas together (2026-09-30)

Owner decision (2026-09-30): pilot one room, plate and atlas both on EEVEE, judged from contact
sheets against the Cycles versions. No shipped file changes; the decision is the owner's, from the
pictures. Driver: `tools/blender/study_eevee_pilot.py`. Blender 5.2.2.

## What was run

- **Plates**, through `stage_room_model.py` at the production settings (256 x 240 plate,
  supersampled 3x and box-averaged): Cycles; EEVEE as `--engine eevee` renders today (AO
  raytracing); EEVEE with a baked light probe volume (`capture_world`, 2 cells per metre).
- **Exposure**, solved rather than guessed: film exposure in EV, stepped until the EEVEE plate's mean
  linear luminance over the lit rows is within 3% of the Cycles plate's. It converged in three
  steps at **+0.617 EV**. (Scaling the lamps does not work: doubling `--lamp-scale` moved the mean
  by 5%, because these rooms are lit mostly by world fill and window emission; a film exposure
  keeps the balance the recipe struck.) `--exposure` is a new stager flag, default 0.
- **The 3D room**, from an EEVEE projected atlas (`study_eevee_atlas.py`, packed layout) baked with
  the same probe volume and exposure, next to the shipped Cycles atlas (packed since #1278), drawn
  unlit and nearest-sampled at native size with no film filter, from cameras the bake did not use.

Sheets: `eevee-pilot-padaria-2026-09-30/pilot_sheet.png` (the comparison), `plates_sheet.png` and
`rooms_sheet.png` (with difference strips and numbers), `pilot.json`.

## Findings

| plate | world-fill share | mean abs diff vs Cycles plate, lit pixels | lit pixels >8/255 |
|---|---:|---:|---:|
| Cycles (reference) | **17.5%** | 0 | 0 |
| EEVEE as it renders today | 86.6% | 12.0 | 53.1% |
| EEVEE + probe volume, exposure matched | **23.8%** | 10.9 | 49.1% |

1. **The leak is fixed.** The probe volume brings the world-fill share from 86.6% to 23.8%, against
   Cycles' 17.5%. Nothing else tried in this work (raytracing, Fast GI, the backface option) moved it.
2. **The room is darker without an exposure, and one number restores it.** +0.617 EV matches the
   Cycles plate's mean; the balance between lamps and fill is untouched.
3. **In pixel terms the gain is modest.** The lit-pixel difference from the Cycles plate falls from
   12.0 to 10.9. The sheet is the honest reading: the EEVEE probe plate has the Cycles plate's mood
   (darker corners, less flat plaster, a contained oven glow) where today's EEVEE plate is flatter
   and brighter. What still differs is fine bounce and contact shading, which a probe volume
   approximates rather than reproduces.
4. **The atlas follows the plate.** The EEVEE projected atlas reproduces its own beauty target to
   3.1 of 255 (lit pixels), against 8.8 for the shipped Cycles atlas against its own Cycles target.
   The two atlases differ from each other by 13.1, of which most is the engine gap.
5. **Time:** an EEVEE plate is about 10 s and the atlas about 9 s, against a Cycles plate of about
   20 s and a Cycles atlas of 5 minutes. The probe volume bake adds a few seconds per room.

## What it costs and what it leaves

- A per-room lighting step: the probe volume resolution, and an exposure that has to be solved
  again for each room (a script does it; a person still has to look at the result).
- The look is not Cycles'. It is close, and consistent between plate and atlas, which the current
  Cycles-plate-with-Cycles-atlas arrangement is by construction and an EEVEE-plate-with-Cycles-atlas
  arrangement would not be.
- The EEVEE atlas fills only what the lane cameras saw (about 20-28% of the island texels), and its
  coverage assumption is a fixed-pitch side view along the lane.
- Not tried: the smith, the exterior plates, and a probe volume per room tuned by hand.

## Not decided

Whether to move the interior plates and atlases to EEVEE. This pilot is the evidence for that
decision; no shipped plate, package or golden was touched.

Agent-Signature:
  platform: Claude Code (desktop)
  model: Sonnet 5.5
  role: research
  task: "owner decision: EEVEE pilot on the Padaria"
  base: 68ea4220
