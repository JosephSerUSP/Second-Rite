# Can the other interiors move to EEVEE too? (2026-09-30)

Follows `eevee-pilot-padaria-2026-09-30.md`. The owner's reading of the Padaria pilot: the EEVEE
projected atlas is consistent with the Cycles renders and is the favoured look; today's EEVEE plate is
the odd one out (colder, no colour bounce). That is enough to move the Padaria, but not to say the
approach is safe for every environment, so the same pilot was run on the other Blender interiors.
Blender 5.2.2, `tools/blender/study_eevee_pilot.py`, no shipped file touched.

Which environments there are: the interiors with a source `.blend` are the Padaria and the smith (shipped
as 3D packages), and Passage House room 3 and the corridor (authored, not yet packaged). The Praça
is the one exterior source and goes through the exterior pipeline (a flat, sun-lit bake), which this
comparison does not cover. The other plates (chapel, port, market and so on) have no `.blend` at all and
nothing to migrate.

## Results

| room | world-fill share: Cycles / EEVEE today / EEVEE + probe | plate diff vs Cycles (lit mean of 255), today -> probe | EEVEE atlas vs its own EEVEE target | verdict |
|---|---|---|---|---|
| Padaria (pilot) | 17.5% / 86.6% / 23.8% | 12.0 -> 10.9 | 3.1 | works |
| Smith | 48.7% / 100% / 77.7% | 8.0 -> 9.6 | 2.2 | works visually; the metrics disagree with the eye |
| Passage House room 3 | 21.1% / 98.1% / 24.5% | 9.0 -> 10.2 | 2.5 | works, with a colour blotch (below) |
| Passage House corridor | 89.2% / 100% / 98.5% | 14.6 -> 12.0 | 1.8 | **needs tuning** (below) |

The numbers do not rank the rooms the way the pictures do. World-fill share stops meaning anything
where the room is lit mostly by fill anyway (the corridor: Cycles itself is at 89%) or by one hard
source (the smith's forge), and the plate difference against Cycles sits at 9-12 in every room whichever
way EEVEE is set up: it is mostly the engine gap, not the probe volume. The sheets are the evidence:
`smith_sheet.png`, `passage_house_room3_sheet.png`, `passage_house_corridor_sheet.png`.

## What the pictures show

- **Smith:** the EEVEE probe plate has the forge's warm glow spilling onto the wall and floor that today's
  EEVEE plate lacks and the Cycles plate has. It is darker overall, and the metric that says today's
  plate is closer is not measuring bounce. The 3D view from the EEVEE atlas is consistent with the
  Cycles beauty.
- **Room 3:** mood and layout match well. A pink blotch appears on and around the terracotta pot in the
  EEVEE probe plate and atlas: the window's sunlit floor patch bouncing warm light onto a red object, over-
  strong at half-metre probe cells. Cycles shows it much more softly.
- **Corridor, at the defaults (2 cells per metre):** thin bright bars along the ceiling, light leaking through
  the ceiling shell into the beam recesses, in the plate and in the atlas. Denser probes and a lower light
  threshold (`--probe-cells 4 --eevee-option light_threshold=0.0002`) remove the bars (`corridor_tuning_sheet.png`).
  **Not fixed by that:** the wall lantern's soft glow. *Correction, `eevee-emissive-lights-2026-09-30.md`:* I
  first put this down to EEVEE not casting emission. It is the lantern's own housing shadowing its light in
  EEVEE (the flame's emission is under a watt), fixed by releasing the housing's shadow. The doorway's warm
  spill is also weaker.

## What it means

- **Safe with per-room tuning, not with one setting.** Two of four rooms are fine as they stand, one needs
  a blotch looked at (probe density), and the corridor needs denser probes and a fix for its lanterns
  (they shadow their own light in EEVEE; see the correction above). None of that was needed in the Padaria, which is the risk of
  deciding from one room.
- **The atlas is not the risk.** In every room the EEVEE projected atlas matches its own EEVEE target to
  1.8-3.1 of 255. What varies from room to room is the EEVEE *lighting*, not the bake.
- **Exposure is solved per room** (+0.52 to +0.63 EV here), by a script.
- Not covered: the Praça exterior, the material specular finding (still an owner decision), and a hand-
  tuned probe volume per room.

## Tools

`study_eevee_pilot.py` now takes `--span`, `--atlas-size`, `--probe-cells` and `--eevee-option`;
`study_eevee_atlas.py` takes `--eevee-option`, `--cycles-target` (Cycles reference frames without an
atlas) and derives the lane centre from `--span`; `lane_camera` takes a `centre`.

Agent-Signature:
  platform: Claude Code (desktop)
  model: Sonnet 5.5
  role: research
  task: "check the other environments for the EEVEE move"
