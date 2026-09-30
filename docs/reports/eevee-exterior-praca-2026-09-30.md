# The Praça exterior under EEVEE (2026-09-30)

The last environment with a Blender source, and the one the interior pilots did not cover. It is lit and baked
differently from a room: the exporter's `flat_bake` profile (Cycles, one sample, no bounces) under a world fill
and a sun, with no authored lamps. Blender 5.2.2, `tools/blender/study_eevee_exterior.py`. Nothing shipped
changes, the source document is never saved, and as with the interiors the goal is the tooling, not a tuned
Praça.

## What was measured

The study rebuilds the joined render mesh exactly as `export_exterior_environment.py` does, stages the same
lighting (the document's own overcast sun at 3.0, the exporter's `TH_SUN` at 2.5, a 0.35 world fill), and bakes
two atlases on the **same mesh and UVs**: the Cycles one through the exporter's own pipeline, and an EEVEE one by
camera projection. The Cycles atlas it produces matches the shipped `praca/environment.png` (43.5% of texels
written, mean 48.6, 68% of pixels identical, the rest 1-sample noise), so it is a fair stand-in for what ships.
Views are from lane positions the EEVEE bake did not use, unlit and nearest-sampled at native size.

| | Cycles (today) | EEVEE projection |
|---|---|---|
| bake time, 2048 atlas | **1,003 s** | **29 s** |
| facade brightness vs the EEVEE beauty (mean linear, 5 lane positions) | 0.64-0.68 of it | 0.97-0.99 of it |
| ground | **black** | filled, coarse |
| foliage | near black | green, as in the beauty |
| texels the bake reaches | 43.5% of the atlas | 18.9% of island texels seen, 34.6% after dilation |

The EEVEE atlas reproduces its own beauty on the facades to within 3% at every lane position. Against the Cycles
atlas the facades sit at a steady ratio of about two thirds (0.64-0.68 in all five), which is a constant exposure
offset of about -0.6 EV, not a per-position difference. Deeper shadow contrast in the Cycles bake is the other
visible difference; the EEVEE world fill is unoccluded, the same leak the interiors needed a probe volume for. I
did not try a probe volume here: the ground is one 200 m quad (below), so the volume's bounds would be 200 x 200 m.

## The ground was already black (filed as #1287)

The comparison exposed a defect in the shipped package that is independent of EEVEE. After the exporter's
sealed-face cull, the Praça's whole ground is **one face, 200 x 200 m, facing down** (normal z = -1.0). The Cycles
selected-to-active bake casts its rays along the target's normal, so it hits nothing and leaves the atlas at its
opaque-black initial fill. The shipped package, photographed from lane y = 12, is black from the facades down
(`shipped_package_lane_12.png`). Blender draws both sides of a face, which is why every Blender-side view still
shows a ground. Details, a repro and options are in the issue; it is an owner-signed regeneration, so it is a
finding first.

It also explains the exporter's own note that the ground "measured 0.00 texels per screen pixel": the 3% of the
atlas it gets (83,643 texels) is about 2 texels per m² over a 200 m quad. The EEVEE ground is filled but
visibly coarse for that reason (`sheet_lane_1.35.png`: the cobbles become blocks). Coarse, not wrong: that is
the allocation, and spending the atlas where the cameras look (`atlas_allocation.allocate_by_view`, #877) is
the fix, not more bake.

## What it means for moving the exterior to EEVEE

- **It works, and it is better where it matters.** The EEVEE atlas has ground and green foliage where today's
  has black, in 29 seconds against 17 minutes, and reproduces its own lighting to within 3% on the buildings.
- **It needs a gain to sit beside today's look**, about -0.6 EV on the facades, by the same kind of solve the
  interiors used. Whether today's look or the brighter EEVEE one is the intended Praça is the owner's call; the
  Cycles one is darker partly because it is also missing ground and foliage light.
- **The atlas layout is the real limit now, not the engine.** The exterior still uses `smart_project` and a fixed
  3% ground share. The packed and view-allocated layouts from the interior work are what would give the ground
  and the facades the texel density they lack (79% of screen pixels get under one texel today).
- **Not covered:** the exterior flow's UV allocation and the ground cull, the foliage in Cycles (why it bakes
  near black is undiagnosed), and a probe volume for the exterior.

## Tools

`tools/blender/eevee_projection.py` is the projection bake lifted out of `study_eevee_atlas.py` so the exterior
study and, next, the exporter share one implementation: `project_atlas` takes the lighting, the cameras and two
hooks that decide what the beauty frame and the UV frame see (an exterior's joined mesh has no real materials,
so its beauty frame is of the source meshes). `study_eevee_atlas.py` now uses it; re-running the Padaria pilot
reproduces the earlier atlas numbers exactly (coverage, texel density, and 3.10 atlas-against-target).
`study_eevee_exterior.py` drives `study_eevee_exterior_blender.py` and writes two sheets.

Agent-Signature:
  platform: Claude Code (desktop)
  model: Sonnet 5.5
  role: research
  task: "check the Praça exterior under EEVEE before the exporter backend work"
