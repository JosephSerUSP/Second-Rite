# PE Day 1 UI study (#1427)

Three-pass plan, as requested by the owner on 2026-10-07:

1. **Study + base changes** (this document; first pass landed with it).
2. **Feature updates** — the systems the UI needs to show: a field menu,
   inventory, equipment (weapon *and* armor), status.
3. **UI fine-tuning** — once those features exist, finish their screens.

## Evidence and its limits

- The owner's private reference pack (never committed; see the
  reference-only rule) was copied in part to `out/pe-original-reference/`.
  Of its GUI folder only the 30 weapon-ability icons were copied (acid, burst,
  counter, quickdraw, rof, tranq, …). The pack's `ART/Menu.png` and
  `ART/guide_screenshot.jpg` would be the primary layout references, but the
  `G:` drive was offline during this pass. **Layout claims marked
  _unverified_ below come from memory of the original and must be checked
  against those images before pass 3.**
- Our own UI was captured state by state from the engine (battle idle,
  command menu, targeting, PE menu, item menu, field message).

- **The decompilation** (github.com/khasinski/parasite-eve-decomp, source
  only, work in progress) has the original's battle HUD and menu code by
  name: `Battle_DrawHPBar`, `Battle_DrawStatusPanel`, and a `menu/`
  subsystem (`Menu_DrawStatusPanel`, `Menu_DrawEquipSelectionList`,
  `Menu_DrawItemDetailPanel`, `Menu_TextboxDraw`, `Menu_ContextHelpFlow`,
  …). It is Square Enix's code: read it for facts and numbers, never copy
  it into this repo. Facts taken from it so far:
  - AT gauge: 56 px wide on a dark green track (#1D3E32) with a grey frame
    (#303030), filled by a cyan gradient (#004682 → #9FFFF9). A green
    (#008236 → #4AFF3B) and a pink-red (#FF3D81 → #831301) gradient are also
    defined there.
  - Numbers are 6×10 digit sprites; floating damage/recovery numbers are 8×8
    digits that rise for 30 frames while fading (white damage, green
    recovery, plus yellow and magenta styles).
  - The menu shows a help line for the focused entry (item description,
    ability or option hint) and a play-time clock.

## What the original does

| Area | Original | Status |
|---|---|---|
| Field | No HUD at all while exploring; the room is the screen. | _unverified_, high confidence |
| Battle | Real-time: an AT gauge fills; when full, the command menu opens and the action is taken; the weapon's range is a dome around Aya. | matches our battle model |
| Battle commands | Attack, PE (Parasite Energy), Item, Escape; plus changing the equipped weapon mid-battle. | _unverified_ |
| Battle status | Aya's HP and PE as numbers with the AT gauge. | _unverified_ layout |
| Weapons | Each weapon has attack, range, bullet capacity and rate of fire, plus special abilities (the 30 icons). The Baton is a melee weapon with unlimited use. | icons verified; stats _unverified_ |
| Armor | A separate armor slot with defense and its own abilities. | _unverified_ |
| Field menu | Opens on a button: Aya's HP/PE/level, then Item, Equip, PE, and Config pages; the item list has limited slots. | _unverified_ |
| Messages | Text in a box at the bottom of the screen, sized to the text. | _unverified_, high confidence |

## What ours does (captured 2026-10-07)

- HUD: AT gauge on top; HP shown only as a number with no bar; PE has a
  label but no value; HP and PE labels crowd the same corner.
- Weapon name floats unboxed in the top-right corner, with an `[X]` hint.
- Messages: a one-line message fills a panel covering most of the screen.
- The room name is printed permanently at the bottom-left while exploring.
- No field menu: no status, inventory or equipment screens. Weapon swap is
  a hidden X shortcut or an Item-menu entry in battle; there is no armor.
- Battle menus are text with a `>` cursor, each a different width.

## Base changes (pass 1)

- **Battle status panel**: three aligned rows — AT, HP, PE — each with its
  label, a gauge and (HP/PE) a value, on the 8px text grid; the equipped
  weapon and its ammunition sit in a fourth row of the same panel.
- **Field is clean**: no permanent room name or weapon line while
  exploring, as in the original.
- **Messages**: a bottom message box sized to its text.
- **Battle menus**: one column under the status panel, same width,
  with a title row.

## Pass 2 — features (landed)

- Field menu on B: Item and Equip pages, Aya's status alongside, a help
  line at the bottom; B backs out page by page.
- Items: Medicine usable in the field; rounds listed. (Slot limit: pass 3.)
- Equipment: the weapon (M84F / Baton) and a real engine Armor slot. Aya
  starts in a Police Vest (DEF +2); a Kevlar Vest (DEF +6) is in the prop
  store. Armor stats apply through the production stat path.
- Battle: a Change command swaps weapons; Item holds items only.
- Engine: `session.items.<id>` and `<battler>.equip.<slot>` formula views;
  the Actor Change snapshot no longer counts equipment as development.

## Pass 3 — fine-tuning (first round landed)

From the decompilation:
- Gauges: AT is the original's cyan on its dark green track (#1D3E32),
  brightening when full; HP and PE use the HUD's green and pink-red
  gradients (which gauge each belongs to is inferred, not verified).
- Menu help panel carries the play-time clock at its right edge
  (`Menu_ContextHelpFlow`); play time is a persistent game variable
  advanced by every room's fixed tick.
- Status panel groups name and stats, then the equipped weapon and armor
  rows (`Menu_DrawStatusPanel`).
- PE page in the field menu: Heal 1 restores 30 HP for 30 PE.

Still open: exact pixel positions and the original's fonts/frames (needs
the decomp's draw primitives decoded further and `ART/Menu.png`); the
inventory slot limit; gradients instead of flat gauge fills (the gauge
widget draws one colour).
