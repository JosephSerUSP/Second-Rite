# Parasite Eve — Day 1 (fan recreation vertical slice)

Recreation of Parasite Eve's chapter 1, **Day 1: Resonance**, from the
Carnegie Hall arrival through the sewer alligator and the exit. Plan and owner
decisions: epic #1422, milestone *PE Day 1 vertical slice* (#1423–#1429).

All geometry, textures and text here are original approximations authored for
this Project. Reference media (screenshots, footage, guide scans) is used only
for private comparison and never ships here. The private pack lives under the
ignored `out/parasite-eve-day1-reference-pack`.

## Status

**M0 (#1423):** this Project exists and carries a port of the B009 lab encounter
(`projects/labs/scene-benchmarks`, PR #1413) as `basement_rat`. Until M1
replaces the scene-local combat, `tests/test_b009_spatial.lua` runs the same
assertions against both copies. It also fails if the two scene files differ in
anything but id, display name and model directory.

The real-time AT battle mode (M1, #1424) is being built beside production
Battle. The owner made this conditional: it must be designed to merge into
production Battle later.

## Walkthrough

1. Title → **Begin** enters the Carnegie Hall basement corridor.
2. Arrow keys move Aya freely; the rat winds up and then bites toward the
   position it locked, or sprays three fire-tail projectiles. Step aside to evade.
3. When the AT gauge fills, **Enter** aims (blue ground and green air range,
   red cursor), and Enter again fires a bullet. **X** opens the command menu
   (Attack / PE Heal 1 / Item Medicine / Escape); the fight pauses while it is open.
4. Reduce the rat's 20 HP to win, then confirm to collect Ammo +6. Confirm
   again to replay; **Escape** returns to the title.

Combat values and timings are prototype approximations carried over from B009;
the original formulas are not yet verified.

## Sources of authority

- `assets/authoring/environments/backstage_rat.blend` is the editable source
  (copied byte-identical from `b009_encounter.blend`). Export with
  `tools/build_backstage_models.py --export-only`; never regenerate it.
  `assets/models/backstage/provenance.json` records the hashes.
- Visual walkthrough evidence currently lives with the lab encounter:
  `projects/labs/scene-benchmarks/reports/b009-3d/index.html`.
