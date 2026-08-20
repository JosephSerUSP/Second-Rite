# Next Second Gate Town — calibrated-camera material gauntlet

## Camera authority

`python tools/blender/check_next_town_camera.py` passed on 2026-08-20.

| property | value |
| --- | --- |
| pitch | 0 degrees |
| horizontal FOV | 28.0724869 degrees |
| Blender-equivalent lens | 43.2676 mm |
| fixed eye | `(0.9, 5.5, 0.0)` |
| projection windows | `-96`, `0`, `+96` pixels |

The Blender acceptance check proves the eye transform and lens do not change at
those offsets. Blender is downstream of the Thestra calibration JSON.

## Material micro-gauntlet

The native-resolution court is `town-material-gauntlet-contact-sheet.png`.
It tests the same lighting and level camera with three source strategies:

1. **A — procedural:** Blender Noise Texture, ColorRamp and Bump are used for
   plaster, wood, tile and metal breakup.
2. **B — public library:** Poly Haven `cobblestone_01`, CC0; its locally kept
   1K diffuse, roughness and displacement maps drive the town paving.
3. **C — generated:** OpenAI-generated warm-limestone PBR source sheet;
   cropped albedo, roughness and height maps are used in Blender. The height
   map drives Blender Bump only; no generated normal map is trusted.

Full provenance, source URLs, license and local files are in
`material-provenance.json`.

## Nine level-camera studies

`town-next-gauntlet-contact-sheet.png` is the current 3×3 native-render work
sheet. Attempts 01–06 are divergence studies; 07–09 respond to the evaluation
evidence. They all contain the actual `walker.png` 24×48 frames for a
protagonist and two stand-ins, a door anchor, coarse runtime geometry, a
foreground occluder, and source lighting.

Raw independent evaluator data is preserved in `next-evaluation-divergence.json`,
`next-evaluation-convergence.json`, and `next-evaluation-all.json`. The best
convergence average was **08 (54.0/100)**. GPT-4o preferred its readability and
pre-rendered direction (69/100); Gemini identified the decisive shortcomings:
generic/abstract architecture, weak depth separation, and insufficient
narrative staging (39/100). The current visual winner is therefore **08 v2**
as a direction, not a completed production scene.

## Native game-mockup correction

The original Blender preview billboard made the 24×48 Walker frame far too
large for the 426×240 target. The current review path is therefore
`town_gauntlet_level.py --no-actors` followed by
`composite_town_mockup.py`: Blender renders only the environment at native
resolution, while the real walker cells are composited nearest-neighbour at
1:1 pixels. Their feet are projected from the calibrated world anchors, not
hand-placed. `town-next-divergence-01-06-game-mockups.png` is the current
six-way proof. The human-metric revision scales the set around that fixed
sprite, without changing the camera.

The historic #856 evidence was restored after this work; this next-gauntlet
record is additive and must not be read as a rewrite of the first gauntlet.

`next-evaluation-native-divergence.json` is the authoritative ranking for the
new presentation path: Old Gate (01) scored 57.5, Wharf (04) 54.5, Market (03)
48.0, Plaza (02) 47.0, Fortress (06) 45.0, and Tavern (05) 37.5. Any final
convergence decision must start from Old Gate / Wharf evidence rather than the
earlier billboard-scale ordering.

## Bake/export proof (current 09 baseline)

`town-next-level-winner.blend` preserves the required collections. The exported
runtime package is `exports/environments/town_next_level/`.

| metric | value |
| --- | --- |
| TH_RENDER triangles | 48 |
| TH_RENDER vertices | 32 |
| runtime materials | 1 |
| beauty atlas | 512×512 PNG |
| atlas bytes | 127,493 |
| full package bytes | 131,637 |
| source blend bytes | 210,419 |

`town-next-projection-window-strip.png` demonstrates panning. The output
package keeps collision and anchors separate; preview actors are excluded from
the atlas and OBJ.

## Known weaknesses / next exact step

The work is a real calibrated material-and-bake proof, but **not yet the final
visual gauntlet requested by the owner**. Independent evaluation correctly
finds that the studied facades remain too abstract and that the NPCs currently
read as technical stand-ins rather than staged people. The next pass should
expand the 08-v2 apothecary approach into three genuinely different, named
street compositions (apothecary arcade, fortified gate/wharf, and tavern
crossroads), then rerun both evaluators before a final bake is selected. Do not
alter the calibrated camera to solve these art-direction failures.

## Latest native-resolution WIP

`wip-old-gate-arch-v2-game-mockup.png` is the current fast EEVEE review frame.
It supersedes the earlier `wip-old-gate-refined-game-mockup.png` as a gateway
study: the full torus-like surround and horizontal courses made that frame read
as a barricade at 1:1 Walker scale. The replacement uses a recessed doorway,
side jambs, and individually placed upper voussoirs. It was rendered at
426x240 with the camera contract unchanged and Walker cells composited from
their camera-projected anchors. It is a WIP, not a selected final scene.

The parallel wharf rework (`wip-wharf-v3-game-mockup.png`) introduced a
side-canal, quay, bridge, pilings, crane, and moored boat while retaining the
same camera and 1:1 actor composition. At this frontal framing it still
collapses too much into the generic facade vocabulary, so it is retained as a
negative WIP rather than advanced as a convergence candidate.

## Gateway WIP export proof

`town-next-old-gate-arch-v2.blend` was exported separately to
`exports/environments/town_next_old_gate_arch_v2/` using the established
environment pipeline. The deliberately low-cost WIP bake completed with a
128x128 beauty atlas and one Cycles sample: 48 runtime triangles, 32 runtime
vertices, a 13,374-byte PNG atlas, collision OBJ, and the player, two NPC, and
door anchors in `environment.json`. This verifies the source artifact is
exportable; it does not turn the current art-direction WIP into a final scene.

## Requirement audit (2026-08-20)

| brief requirement | current evidence | status |
| --- | --- | --- |
| calibrated side-view camera and panning invariance | `check_next_town_camera.py` prints both acceptance markers; current WIPs use its generated calibration | verified |
| required collections / actor exclusion | `town_gauntlet_level.py`, `town-next-old-gate-arch-v2.blend`, and its export package | verified for the gateway WIP |
| actual 24x48 Walker frames at native scale | `composite_town_mockup.py` and the WIP anchor JSON | verified for WIPs |
| procedural, CC0 public, and generated material sources | material court, `material-provenance.json`, and source files | verified as experiments |
| material micro-gauntlet contact sheet | `town-material-gauntlet-contact-sheet.png` | present, but visually weak |
| nine rich, genuinely divergent full scenes | nine early attempts exist, but the native-scale audit exposes insufficient divergence | not satisfied |
| two independent blind evaluations | raw evaluation JSON files | present; billboard-scale scores are not composition authority |
| 07-09 convergence responding to evidence | convergence artifacts | partial; no accepted final selection |
| selected winner / final bake / strip / comparison | only the gateway WIP export exists | not satisfied |
| final report and tomorrow handoff | report plus provenance | partial |

This audit prevents the existing artifacts from being presented as a completed
gauntlet. The next production pass must replace—not merely recolour—the
native-scale street vocabulary before choosing a winner.

`wip-old-gate-materials-v4-game-mockup.png` is the current material-mapping
correction WIP. It wires the generated limestone albedo, height, and roughness
maps into Blender's box-projected material graph while retaining the
procedural variation and the CC0 cobblestone ground. The first projection used
the narrow objects' generated coordinates directly and created vertical
streaking; that rejected `v3` is preserved as diagnostic evidence. `v4` uses
box projection and the texture's block relief remains readable at 426x240.
