# Second Gate: Pale Crossing

> **Format**: Complete, compressed, playable alternative campaign interpretation for *Second Gate* / *Second Rite*.  
> **Status**: Verified Playable (`VALIDATE OK`, automated smoke tested, all 8 authored maps rendered).  
> **Target Playtime**: 45–75 minutes.  
> **Branch**: `exp/full-campaign-pale-crossing`  
> **Project Root**: `projects/labs/pale-crossing`

---

## 1. How to Play

### Quick Launch (Repository Root)
- **Windows (Double-click / Command Prompt)**:
  ```cmd
  PLAY_CAMPAIGN.bat
  ```
- **PowerShell**:
  ```powershell
  .\PLAY_CAMPAIGN.ps1
  ```

### CLI / Studio Launch
- **Launch via Project CLI**:
  ```bash
  node tools/editor/project-cli.js play projects/labs/pale-crossing
  ```
- **Open in Editor / Studio**:
  ```bash
  npm start -- --project projects/labs/pale-crossing
  ```

---

## 2. Narrative Premise & Systems

*Second Gate: Pale Crossing* explores an alternative machine-authored campaign arc built directly on the engine's core pillars: **first-person dungeon crawling**, **the Summoner's step-based MP economy**, and **attachment under pressure**.

### The Protagonist & Saban
You play an outsider Summoner arriving at the frontier village of St. Maria with your bonded companion: **Saban**, a young, stubborn pink-feathered Moa (Level 3, Cooking discipline). Saban is not merely combat muscle; he is your emotional anchor in the dark. While heavy summoned beasts drain your spirit with every stride, Saban's modest upkeep (MPD 2) keeps your expedition horizon alive.

### The Traversal Economy: MP as Horizon
In the Bellroot Labyrinth, **MP is not just a combat mana pool—it is your physical stamina and traversal horizon**. Every pace taken through the labyrinth exerts **MP Drain (MPD)** proportional to your active summon contracts:
- **Saban (Moa)**: MPD 2. Efficient, steady, reliable.
- **Cerberus (Hellhound)**: MPD 6. Brutal physical offense (ATK 28, Fire Claw), but drains your mana rapidly, drastically shortening how far you can delve before you are forced to retreat.
- **Daphne (Wood Nymph / Undine)**: MPD 4. Potent water recovery and healing.

If your MP hits zero in the deep dark, darkness claims you. Knowing when to turn back to St. Maria before crossing the point of no return is the heart of the campaign.

### The Strata
1. **Act I: The Bellroot Descent (Floors 1 & 2)** — Medieval stone crypts, damp earth, Ines's chalk warnings, the Salt Table, and the first contract trials.
2. **Act II: The Subterranean Rupture — Estação Sé (Floors 3 & 4)** — An impossible subterranean breach into a contemporary São Paulo Metro station. Fluorescent lights flicker over white subway tiles, bilingual Portuguese signage, locked stainless steel turnstiles (*catracas*), ticket booths, PA announcements, and ghost trains across abandoned rails.
3. **Revisit: The Vigil of the Bells** — Returning to St. Maria as twilight sets in and the three bells of the valley sound.
4. **Act III: The Rusted Choir & The Pale Crossing (Floors 5 & 6)** — Cathedral spires intersecting suspended subway tracks. The surreal *Borrowed Room*, the Three-Bell resonance puzzle, the Ashen Guardian Red Dragon, and the ultimate choice at the threshold of the Gate.
5. **Epilogue: The Morning After (Floor 7 / Map 8)** — Complete authored narrative closure.

---

## 3. Complete Campaign Walkthrough

### Act I: St. Maria & Entry Vault
1. **Room 3 (Passage House)**: Begin your morning in St. Maria. Inspect Saban's feed bowl and prepare your gear.
2. **Town Interactions**:
   - **Registrar Celina (x: 11, y: 6)**: Register your summoner seal to receive the **Crossing Writ (Item 198)**.
   - **Alicia's Bakery (x: 15, y: 9)**: Receive freshly baked bread and an errand to carry lunch to Laura.
   - **Laura's Forge (x: 3, y: 5)**: Deliver lunch (+25G) and purchase iron equipment.
   - **Gate Guard (x: 8, y: 2)**: Present your Crossing Writ to open the descent gate.
3. **Floor 1: Entry Vault (Map 2)**:
   - **Ines's Mark (x: 7, y: 5)**: Inspect the blue chalk sigil (*"SENI"*) warning against low MP.
   - **Cerberus Chamber (x: 2, y: 1)**: Optional high-risk trial. Defeat Cerberus to form a contract (powerful attack, high MPD drain).
   - **Treasure Chest (x: 12, y: 1)**: Collect HP Tonic x2, Sigil Ink x1.
   - **Stairs Down (x: 7, y: 1)**: Descend to Floor 2.

### Act I (Cont.): Bellroot Chasm
4. **Floor 2: Bellroot Chasm (Map 3)**:
   - **The Salt Table (x: 3, y: 3)**: Harvest **Bell Salt x2 (Item 206)** to replenish summon skill charges.
   - **Daphne's Spring (x: 13, y: 3)**: Contract the water spirit Daphne (healer).
   - **Recovery Font (x: 8, y: 7)**: Restore full party HP.
   - **The Rupture Hatch (x: 8, y: 1)**: Inspect the heavy industrial yellow bulkhead door. Turn the pneumatic release wheel to breach the barrier into Estação Sé.

### Act II: Estação Sé (São Paulo Metro Stratum)
5. **Floor 3: Estação Sé — Concourse (Map 4)**:
   - Notice the buzzing fluorescent tubes, white ceramic tiles, and the smell of ozone.
   - **Ticket Booth / Guichê (x: 3, y: 3)**: Search the service tray to acquire the **Metro Transit Pass (Item 208)**.
   - **PA Speaker (x: 13, y: 3)**: Listen to the automated transit chime and announcement (*"Atenção passageiros..."*).
   - **Turnstiles / Catracas (x: 8, y: 7)**: Scan your transit pass to unlock the passage to the lower level.
   - **Platform Stairs (x: 8, y: 1)**: Descend to Platform 2.
6. **Floor 4: Estação Sé — Platform 2 & Ghost Tracks (Map 5)**:
   - **Abandoned Train (x: 3, y: 9)**: Step inside the silver commuter car to recover the **Lost Commuter's Bag (Item 209)** containing Ambrosia and Golden Egg.
   - **Sub-Boss: Guardian Talos (x: 9, y: 7)**: Engage the concrete-and-rebar guardian blocking the rail tunnel. Defeat Talos to clear the path (+75G).
   - **Astral Breach (x: 9, y: 1)**: Step across the sheared rail edge into the starry chasm.

### Revisit & Act III: The Rusted Choir & Pale Crossing
7. **Floor 5: The Rusted Choir (Map 6)**:
   - **The Borrowed Room (x: 3, y: 13)**: Encounter the uncanny replica of Room 3. Saban's loyalty bolsters your spirit (+50 Max HP).
   - **Three-Bell Resonance Puzzle**:
     - Strike the **Bell of Salt (x: 3, y: 3)** (West).
     - Strike the **Bell of Iron (x: 13, y: 3)** (East).
     - Strike the **Bell of Dusk (x: 8, y: 7)** (Center) to harmonize all three tones and rumble open the Ashen Gate.
   - **Stratum Boss: Red Dragon (x: 8, y: 4)**: Defeat the ancient guardian of ash and ember to claim the **First Scale (Item 205)**.
   - **Pale Archway (x: 8, y: 1)**: Step into the threshold.
8. **Floor 6: The Pale Crossing (Map 7)**:
   - **Thestra Seam Pedestal (x: 7, y: 7)**: Approach the center altar under the cosmic sky. Make your final choice:
     - **[Choice A: Return with Saban — Seal the Pale Gate]**
     - **[Choice B: Cross the Boundary — Awaken the Second Rite]**
9. **Floor 7: Epilogue (Map 8)**:
   - **Epilogue Chronicle (x: 6, y: 5)**: Read the comprehensive closing narrative for your chosen path, detailing the village, companions, and the morning after.

---

## 4. Known Rough Edges & Engine Observations

1. **First-Person Viewport Rendering**:
   - Custom floor textures use the engine's built-in raycaster presentation surfaces (`dungeon_default`, `dungeon_ffxii_depth_explore`, `stillnight_bellroot_vigil`).
   - Turnstiles and subway fixtures are represented through evocative billboard sprites and interactive wall events.
2. **Combat Balance**:
   - Starting with Saban provides steady single-target and kitchen utility. Contracting Cerberus turns combat into swift victories at the cost of intense MP drain during movement; Daphne balances survivability against exploration time.
3. **No Softlocks**:
   - All doors, stairs, and milestone flags have explicit return paths and fail-safe transitions verified by G1 validation and automated smoke tests.

---

## 5. Owner Campaign Journal

*Please fill out your scores and thoughts after completing a playthrough:*

### Rubric (1–5 Scale)

| Criterion | Score (1–5) | Owner Notes |
| :--- | :---: | :--- |
| **Tone & Coherence** | `[ ] / 5` | *(Did the low-fantasy frontier feel grounded and consistent?)* |
| **Tension & Traversal Economy** | `[ ] / 5` | *(Did MP step-drain create meaningful expedition risk/reward?)* |
| **Anachronism & Metro Stratum** | `[ ] / 5` | *(Did Estação Sé feel uncanny and atmospheric rather than gimmicky?)* |
| **Pacing & Climax** | `[ ] / 5` | *(Did the Borrowed Room and 3-Bell puzzle lead naturally to the ending?)* |
| **Emotional Anchor (Saban)** | `[ ] / 5` | *(Did Saban feel like an indispensable bonded companion?)* |

### Short Questions

1. **Which moment stood out most during your expedition?**
   > *[Your answer here]*

2. **Did you recruit Cerberus, Daphne, or rely primarily on Saban? How did that affect your MP management?**
   > *[Your answer here]*

3. **Which ending choice did you make at the Pale Crossing, and why?**
   > *[Your answer here]*

### Final Question
- **If this interpretation was expanded into a 20-hour full game, what is the single most important element you would preserve or expand?**
   > *[Your answer here]*

---

## 6. External AI Critics

External AI design critiques from **Luna (OpenAI GPT-4o-mini)**, **OpenRouter Critic A (Gemma 4 31B)**, and **OpenRouter Critic B (Nemotron 3.5)** have been compiled into:
👉 [`projects/labs/pale-crossing/CRITIQUE.md`](./CRITIQUE.md)

*(Critics are preserved in their dedicated document so the owner can play with fresh eyes before reading outside evaluations).*
