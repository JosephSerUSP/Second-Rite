# PE Day 1 menu mechanics (#1427)

The owner's verdict on UI pass 3: the menu is still fundamentally different
from the original, and it needs mechanics underneath it to work. This file
specifies those mechanics. `Menu.png` in the private pack is an HD fan
remake (owner-confirmed), so it is not evidence of the original layout. The
evidence is the decompilation (github.com/khasinski/parasite-eve-decomp),
read for facts only; nothing from it is copied here.

## What the original does (from the decompilation)

- **Seven stat tracks** (`Aya_StatDerivation`, `Inv_RecalcSlotStats`):
  0 Max HP, 1 Offense, 2 Defense, 3 PE / AT gauge, 4 Status recovery,
  5 a battle stat (Active Time), 6 Item capacity. Each track stores a
  growth value; a per-track 99-level growth table turns it into a level
  plus a sub-level 0–48 (`Stat_QueryLevelAndSubLevel`), and a shared
  per-level table gives the stat (`Aya_LookupLevelStats`).
- **Max HP** = (points + 20) × tableHP / 20. Other tracks read their row at
  (track level + bonus points allocated to that track).
- **Item capacity is a stat**: the capacity column sets Aya's inventory
  slot count (`Inv_SetAyaSlotCount`). Weapons and armor occupy slots
  (`Inv_EquipmentCapacityFlow`, `Inv_ArmorCapacity`).
- **Level-up after battle** (`Battle_StepLevelUp` → `Aya_SetTotalExp`):
  EXP plus a PE bonus are awarded together, then every track is recomputed.
- **PE abilities unlock by level** (`Aya_UnlockParasiteSpell`).
- **Weapons and armor are inventory items with their own parameters**
  (`Inv_BuildWeaponList`, `Inv_BuildArmorList`, `BattleCmd_LoadWeaponModifiers`).
- **Status panel** (`Menu_DrawStatusPanel`): name at the top, then level and
  stats, then the equipped weapon and armor rows 16 px apart. The menu has a
  help line for the focused entry and a play-time clock (`Menu_ContextHelpFlow`).

The growth tables themselves are disc data, not in the decompilation; ours
are original numbers with the same structure.

## What we build

1. **Level and EXP.** Fights award EXP and Bonus Points; level-ups raise the
   tracks. Shown as Level and Next Level.
2. **Bonus Points** spent from the menu into Offense, Defense, PE, Active
   Time or Item Capacity.
3. **Derived stats** feeding the existing battle: Offense → damage, Defense,
   Active Time → AT fill rate, PE → max PE.
4. **Inventory capacity**: a slot count from the capacity track; pickups
   that do not fit are refused with a message.
5. **Weapons and armor as inventory items** with parameters (attack, range,
   rounds, capacity; defense) shown on their pages.
6. **The menu itself** rebuilt on the original's structure: status panel,
   then Item / PE / Weapon / Armor pages with the help line and clock.
