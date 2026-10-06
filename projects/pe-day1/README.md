# Parasite Eve — Day 1 (fan recreation vertical slice)

Recreation of Parasite Eve's chapter 1, **Day 1: Resonance**, from the
Carnegie Hall arrival through the sewer alligator and the exit. Plan and owner
decisions: epic #1422, milestone *PE Day 1 vertical slice* (#1423–#1429).

All geometry, textures and text here are original approximations authored for
this Project. Reference media (screenshots, footage, guide scans) is used only
for private comparison and never ships here. The private pack lives under the
ignored `out/parasite-eve-day1-reference-pack`.

## Status

**M1 (#1424):** `basement_rat` runs on the real-time battle scheduler
(`engine/realtime_battle.lua`), a second scheduler over production Battle:
every hit, cost, heal, reward and outcome is resolved by `Battle:executeTurn`.
The scene owns only input, menus and presentation and reads domain facts from
`rt.*`. Design and owner decisions:
`docs/design/runtime/semantics/realtime-battle-merge-ledger.md`. Tests:
`tests/test_realtime_battle.lua`, `tests/test_pe_day1_scene.lua`.

PE is Aya's own declared battler resource (`system.battlerResources.pe`);
ammunition is inventory spent through the skill's `itemCost`.

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
only rat HP 20, EXP 2 and Ammo +6 come from Day 1 guides. The original
formulas are not yet verified. After victory, Enter acknowledges the rewards
(already granted by the victory phase) and Enter again replays.

## Sources of authority

- `assets/authoring/environments/backstage_rat.blend` is the editable source
  (copied byte-identical from `b009_encounter.blend`). Export with
  `tools/build_backstage_models.py --export-only`; never regenerate it.
  `assets/models/backstage/provenance.json` records the hashes.
- Visual walkthrough evidence: `reports/basement-rat/index.html` (this Project). The original lab encounter keeps its own:
  `projects/labs/scene-benchmarks/reports/b009-3d/index.html`.
