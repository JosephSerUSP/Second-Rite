# PE Day 1 menu mechanics (#1427)

The owner's verdict on UI pass 3: the menu is still fundamentally different
from the original, and it needs mechanics underneath it to work. This file
specifies those mechanics.

## Evidence

- **Primary:** the PlayStation manual (pp. 10–13) and in-game captures in
  the owner's private reference pack
  (`out/parasite-eve-day1-reference-pack/`: `menu-*.jpg`,
  `longplay-14m00s-inventory.png`, `battle-mutated-rat.png`).
- **Corroborating:** the decompilation (github.com/khasinski/parasite-eve-decomp),
  read for facts only; nothing from it is copied here.
- `Menu.png` in the older pack is an HD fan remake (owner-confirmed) and is
  not evidence.

## The original's menu

- **Opens on Triangle** over the live field, dimmed; Circle closes/cancels.
- **Frame:** a title bar across the top shows the help text for the focused
  entry (or the focused item's name), with the play-time clock at its right.
  A vertical icon column on the left selects the page: Item, PE, Weapon,
  Armor, SYS, SORT (Tune-up and BP appear when available). Aya's HP
  ("45/45 HP") with a green PE bar sits at the bottom right.
- **Status screen** (the default view): portrait and name; Level; Next Level
  (EXP to go, 3 at level 1); Equipment: weapon with its loaded rounds, then
  armor. Right column: Bonus Point; Offense, Defense, PEnergy, Status
  Recover; Active Time, Item Capacity (all start at 1). Labels sit on
  slanted blue tabs.
- **Item page:** two columns of slots, each an icon, name and count; equipped
  items highlighted blue; unusable items gray; "Total 6/10" capacity. Every
  carried thing takes a slot: weapons, armor, each Medicine, the Ammo Crate
  (whose count is its rounds). Commands: Use, Discard, Move, Reload. Day 1
  start: M84F, Club, N Vest, Ammo Crate (42), Medicine ×2 → 6/10.
- **PE page:** abilities usable at Aya's level (Heal 1 at the start); gray if
  PE is short.
- **Weapon page:** the equipped weapon's Attack, Range, Bullets with base and
  plus columns, effect slots below; carried weapons listed on the right;
  choose one to equip.
- **Armor page:** Defense, PEnergy, Critical with base/plus, effect slots;
  carried armor on the right.
- **Bonus Points:** awarded after each battle, fewer the more Aya was hit.
  100 BP buy one level of Active Time or Item Capacity, or +1 to an
  equipment parameter.
- **Stats:** Offense/Defense are Aya's attack/defense skill; PEnergy sets the
  PE bar's recovery and how fast PE use drains it; Status Recover shortens
  abnormal states; Active Time sets the AT fill rate; Item Capacity the slot
  count (10 at the start).
- **Battle HUD** (top left): a long cyan AT bar, HP as large digits with no
  bar, a green PE bar; AT/HP/PE labels to the right.

## Implementation plan

1. **Engine (owner-approved):** permanent per-battler parameter bonuses
   (`paramPlus`) accept any parameter a unit declares, not only the five
   growth stats; formulas read final values of any parameter. Aya declares
   `offense`, `defense`, `penergy`, `srecover`, `act` and `cap`.
2. **Progression:** an EXP curve (3 to reach level 2), EXP and BP per fight,
   BP reduced per hit taken; level-ups raise the tracks.
3. **Inventory:** slot capacity from Item Capacity; weapons, armor, each
   Medicine and the Ammo Crate take slots; full pickups are refused.
4. **Weapons and armor** as items with Attack/Range/Bullets and
   Defense/PEnergy/Critical; equip from their pages.
5. **The menu** rebuilt on this frame and these pages.
6. **Battle HUD** to the original's layout.

Not in Day 1 scope: Tune-up (appears later in the game), SYS window colour
and position settings, SORT orders beyond one.
