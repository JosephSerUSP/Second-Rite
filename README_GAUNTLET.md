# Second Rite — Design Gauntlet: Unidentified Equipment & Curse Risk

To play the gauntlet immediately, run either of the following from the repository root:

```cmd
.\PLAY_GAUNTLET.cmd
```
or
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File PLAY_GAUNTLET.ps1
```

---

## 1. Core Design Question

> **"Is experimenting with unidentified equipment fun when the player may equip it without identifying it, infer some effects from stat previews, while traits remain unknown and CURSE creates real risk?"**

This gauntlet tests whether equipping unknown loot before appraisal creates engaging, high-stakes tactical gameplay, or whether it degenerates into frustrating guesswork.

---

## 2. Playable Candidate Slices

Each candidate is an authored, standalone Thestra Project that runs through the standard engine/project lifecycle (`tools/editor/project-play.js`) without modifying canonical Second Gate data.

### Candidate A — The High-Roller's Ruin
- **Location**: `projects/experiments/gauntlet-unidentified-gear/candidate-a`
- **Dungeon**: *Crypt of the Cursed Vanguard*
- **Party**: Saban (Moa Runner) & Puck (Pixie Cleric)
- **Mechanic Profile**:
  - **Extreme Stat Previews**: Equipping `Blood-Stained ????` gives an immediate **+32 ATK** (-6 DEF) preview boost.
  - **Severe Hidden Curses**: Equipping the Blood-Drinker drains **10% max HP** every single combat round (`HRG -0.10`). `Obsidian ?????` provides **+26 DEF / +14 MDF** but incurs **+60% Fire vulnerability** against the Hellfire breath of boss *Cerberus*.
  - **Appraisal Economy**: Town Appraiser charges **150 Gold** per item. With 150G starting gold, you can appraise at most one relic before venturing into the crypt.
- **Boss Encounter**: *Tomb Sentinel Cerberus* (Hellfire breath + double crunch).

### Candidate B — The Alchemical Spire
- **Location**: `projects/experiments/gauntlet-unidentified-gear/candidate-b`
- **Dungeon**: *Spire Testing Corridors*
- **Party**: Aqua (Undine Mystic) & Slate (Clay Golem)
- **Mechanic Profile**:
  - **Subtle Stat Fingerprints**: `Vibrant Ring ????` displays **+8 ASP, +2 ATK** preview, subtly hinting at extreme speed. When equipped, it grants `ACTION_PLUS` (+1 additional action every battle turn!).
  - **Tactical Vulnerabilities**: `Glacial Shard ????` (+14 MAT, -3 ASP) infuses attacks with Ice and 35% Freeze rate. `Volatile Conduit ????` provides **+22 MAT** but makes the wearer **70% more vulnerable** to Lightning/Dark against boss *Arch-Automaton Proteus*.
  - **Appraisal Economy**: A one-time *Divination Altar* inside the dungeon allows 1 free item identification mid-run.
- **Boss Encounter**: *Arch-Automaton Proteus* (Heavy slam + Arcane Overload beam).

### Candidate C — The Purifier's Crucible
- **Location**: `projects/experiments/gauntlet-unidentified-gear/candidate-c`
- **Dungeon**: *Sunken Catacomb*
- **Party**: Seraph (Cathedral Angel) & Fizz (Imp Scout)
- **Mechanic Profile**:
  - **Direct Curse-to-Relic Transfiguration**: Corrupted demon relics (`Tarnished Blade ????`, `Corrupted Mail ????`, `Demon's Clasp ????`) provide immediate brute stats (+20 ATK, +24 DEF) but bleed the bearer (-8% HP/round) or heavily penalize speed (-10 ASP).
  - **Purification Quest**: Carrying the corrupted items through the dungeon to the *Sacred Purification Font* cleanses them into consecrated relics (`Radiant Sunblade` with +5% HP regeneration, `Paladin's Cuirass` with Poison Immunity, `Saint's Reliquary` with Death Ward).
  - **Appraisal Economy**: No town appraiser; purification is earned entirely through dungeon navigation.
- **Boss Encounter**: *Corrupted Seraph Diablos* (Demonic rend + Abyssal Dark wave).

---

## 3. Gauntlet Controls & Flow

1. Run `.\PLAY_GAUNTLET.cmd`.
2. Select **[1]**, **[2]**, or **[3]** to launch and play each candidate slice.
3. In each candidate:
   - Talk to NPCs in camp.
   - Enter the dungeon stairs.
   - Loot chest sarcophagi/reliquaries.
   - Open menu (`X` or `Esc`) -> **Equip** -> test out unidentified gear vs appraised/purified gear.
   - Fight dungeon encounters and challenge the floor boss.
4. Select **[R]** to rate the candidates across inference, risk balance, and overall fun. Ratings are persisted to:
   `artifacts/gauntlet/owner_ratings.json`
5. Select **[C]** (or `npm run gauntlet:reveal`) to reveal the pre-play external critic jury evaluations (`artifacts/gauntlet/critic_evaluations.json`) and compare your verdicts side-by-side!

---

## 4. Architecture & Integrity Notes

- **Zero Parallel Engine**: All candidates run via standard `tools/editor/project-play.js` and `data/authored_storage.lua` RTP 1.0 inheritance.
- **No Second Gate Contamination**: Canonical Second Gate files remain untouched; all experimental slices reside under `projects/experiments/gauntlet-unidentified-gear/`.
- **Validation**: All candidates pass full engine validation (`VALIDATE OK`). Run `npm run gauntlet:validate` to re-verify at any time.
