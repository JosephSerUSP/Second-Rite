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

## Pass 2 — features to add

- Field menu (button: Menu/B) with Status, Item, Equip, PE pages.
- Inventory with a slot limit and item descriptions; use Medicine in the field.
- Equipment: weapon slot (Handgun M84F, Baton) and an armor slot (Day 1
  starts with a basic vest), with stats shown and changed in the menu.
- Battle: a "Change" command for weapons instead of a hidden Item entry.

## Pass 3 — fine-tuning

Check every screen against `ART/Menu.png` and the guide screenshot once the
reference drive is online; tune colour, borders, fonts, spacing.
