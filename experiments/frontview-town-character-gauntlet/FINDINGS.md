# Second Gate 128×128 Front-View World-Event Character Sprite Gauntlet: Findings & Production Report

**Target:** 128×128 Front-View Billboard Character Sprites  
**Characters:** Registrar Celina, Sister Agnes, The Gambler (3 Concepts Evaluated)  
**Authoring Authority:** Editable Blender 5.1 sources in [`assets/authoring/characters/`](file:///d:/Antigravity/Hichaukitoden/assets/authoring/characters/)  
**Status:** Completed 8-Round Visual Gauntlet, Production-Ready Assets Generated  

---

## 1. Executive Summary: The Front-View Camera Grammar

This study establishes the production visual language for **128×128 front-view world-event character sprites** in Second Gate.

While the prior 24×24 overhead experiment solved miniature top-down chibis for dungeon exploration, front-view town encounters operate under a fundamentally different camera grammar:
- The player encounters town NPCs through Second Gate's **first-person / front-view world camera**, where characters are presented as vertical 3D billboards facing the camera.
- Rather than viewing top-of-head, shoulders, and footprints from a 32° elevation, the player looks directly into the character's face, posture, and hands at eye/chest level.
- **Proportion Target:** Stylized adults (~5.25–5.75 heads tall, ~108–116 px height within a 128×128 canvas).
- **Core Acting Principle:** Prioritize **face inclination → shoulder line → hands → torso lean → hips/stance → characteristic prop or garment**. Characters must appear actively occupied in their lives *before* dialogue begins.

---

## 2. Character Visual Architecture & Acting Critiques

### A. Registrar Celina (Passage Office Registrar)
- **Authoring Source:** [`assets/authoring/characters/registrar_celina.blend`](file:///d:/Antigravity/Hichaukitoden/assets/authoring/characters/registrar_celina.blend)
- **Proportions:** ~5.6 heads tall (112 px occupied height, 33 px width).
- **Design Intent:** Severe, watchful, formal Portuguese-colonial tailored coat, high ivory collar with bronze brooch, high swept hair bun with dark pins, narrow ledger held tightly in the crook of the left arm against ribs.
- **Body Language:** Asymmetrical stance with weight settled on the rear right foot and left shoulder slightly advanced; chin tilted slightly downward (-7°) to produce an assessing, inspecting gaze.
- **Poses Authored:**
  1. `idle`: Vertical composure, ledger tucked firmly against chest, right hand resting near waist.
  2. `request_seal` (*Signature Acting Pose*): Right arm extended forward/center with palm open upward toward the player ("Your Summoner's seal. Not your name."), ledger held tightly, chin lowered.
  3. `dry_warning`: Right forefinger subtly raised, chin lifted in dry bureaucratic observation.
- **Cliches Avoided:** No anime glasses/secretary tropes, no oversized quill pens, no theatrical villain posture. Reads as a woman whose severe bureaucracy exists because people routinely disappear into the Labyrinth.

### B. Sister Agnes (Chapel Caretaker)
- **Authoring Source:** [`assets/authoring/characters/sister_agnes.blend`](file:///d:/Antigravity/Hichaukitoden/assets/authoring/characters/sister_agnes.blend)
- **Proportions:** ~5.3 heads tall (109 px occupied height, 34 px width).
- **Design Intent:** Grounded, earthy chapel caretaker; unpretentious dark habit with natural linen cowl drape, working canvas apron with subtle stone dust marks, coarse hemp belt cord with hanging prayer beads.
- **Key Bodily Motif:** Right sleeve rolled up to the forearm revealing bare working skin; right hand carrying a masonry trowel/chisel used to repair the chapel steps.
- **Body Language:** Relaxed forward inclination (+6° to +10°), calm lower shoulders, grounded wide skirt mass, patience better suited to embroidery.
- **Poses Authored:**
  1. `idle_working` (*Signature Acting Pose*): Slight forward crouch, right sleeve rolled up, masonry trowel held low near knee height, looking up warmly toward the player.
  2. `brush_dust`: Right hand reaching across to brush stone dust from her left forearm, head inclined down-forward in an unhurried, grounded gesture.
  3. `quiet_welcome`: Both hands open low and grounded in hospitalitarian welcome without theatrical preaching.
- **Cliches Avoided:** No halos, no immaculate untouched nun robes, no magical priestess tropes, no Catholic-stock-photo clasped hands. Looks capable of saying: *"If you need quiet, the chapel is open. If you need certainty, try somewhere else."*

### C. The Gambler (Number Collector — Rusty Tankard)
- **Authoring Sources:**
  - Concept 1: [`the_gambler_c1_local.blend`](file:///d:/Antigravity/Hichaukitoden/assets/authoring/characters/the_gambler_c1_local.blend)
  - Concept 2 (*Champion*): [`the_gambler_c2_wiry.blend`](file:///d:/Antigravity/Hichaukitoden/assets/authoring/characters/the_gambler_c2_wiry.blend) → Canonical [`the_gambler.blend`](file:///d:/Antigravity/Hichaukitoden/assets/authoring/characters/the_gambler.blend)
  - Concept 3: [`the_gambler_c3_sleight.blend`](file:///d:/Antigravity/Hichaukitoden/assets/authoring/characters/the_gambler_c3_sleight.blend)
- **Canon vs. Inference:**
  - *Canon:* Encountered in The Rusty Tankard, shuffles cards in dim corner, "collector of numbers", offers 10G high/low guessing game.
  - *Inference (Visual):* Physical silhouette and attire were completely undefined. We authored and compared three distinct conceptual directions:
- **Concept Evaluation:**
  1. *Concept 1 (Local Regular / Deceptive Plain):* Weathered brown coat with cards concealed in cuff. *Verdict:* Too generic; silhouette looked like an ordinary villager until magnified.
  2. *Concept 2 (Wiry Number Obsessive / "The Counter") — **SELECTED CHAMPION**:* Forward-hunched posture (~5.2 heads, 107 px height), narrow shoulders, sharp angular profile, long spindly arms with spread counting fingers, multiple-pocket waistcoat, brass counting tokens and dice held between fingertips. *Verdict:* Communicates his obsessive relationship with numbers instantly through silhouette and hand posture.
  3. *Concept 3 (Sleight-of-Hand Deceiver):* Asymmetric contrapposto, open burgundy vest, cocked elbow, fanned cards. *Verdict:* Looked slightly too flamboyant/Vegas-adjacent.
- **Champion Poses Authored:**
  1. `idle`: Forward calculating hunch, brass tokens held between splayed counting fingers.
  2. `offer_game` (*Signature Acting Pose*): Leaning forward offering a brass token/card between outstretched fingertips.
  3. `win_or_reveal`: Wry head tilt displaying a rolled die on an upturned palm, other hand tucked in waistcoat pocket.
- **Cliches Avoided:** No top hats, no card-suit patterned garments, no roulette wheels, no floating magical numbers.

---

## 3. Gauntlet Rounds Summary & Evidence

| Round | Focus | Deliverable / Contact Sheet | Key Outcome |
|---|---|---|---|
| **Round 0** | Codebase & Integration Audit | [`audit/round0_audit.md`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/audit/round0_audit.md) | Identified that Celina and Agnes shared generic `NPC06` and `NPC11` sprites; proved Gambler is in Pub Event 8 dialogue tree. |
| **Round 1** | Baseline Bodies | [`contact_sheets/round_01_baseline_bodies.png`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/contact_sheets/round_01_baseline_bodies.png) | Established distinct heights (107–112 px) and proportions (5.2–5.6 heads) across all 5 models. |
| **Round 2** | Silhouette & Value Masses | [`contact_sheets/round_02_silhouette_proportions.png`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/contact_sheets/round_02_silhouette_proportions.png) | Solid black silhouette inspection proved Gambler C2 ("The Counter") had the strongest character silhouette. |
| **Round 3** | Front-View Acting | [`contact_sheets/round_03_frontview_acting.png`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/contact_sheets/round_03_frontview_acting.png) | Authored 9 expressive key poses with bold arm negative spaces and foreshortened hands. |
| **Round 4** | Distance Torture Test | [`contact_sheets/round_04_distance_torture_test.png`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/contact_sheets/round_04_distance_torture_test.png) | Tested 128 / 96 / 64 / 48 / 32 px scales across 5 backgrounds; thickened props to ensure survival at 48 px. |
| **Round 5** | Character Specificity | [`contact_sheets/round_05_character_specificity.png`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/contact_sheets/round_05_character_specificity.png) | Verified that facial planes, collar contrast, stone dust wear, and hand tokens read crisply without visual clutter. |
| **Round 6** | Motion / Gesture Proof | [`contact_sheets/round_06_motion_gesture_proof.png`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/contact_sheets/round_06_motion_gesture_proof.png) | Exported 15 animated GIFs across native, gameplay (64/48), and 4x/8x inspection scales. |
| **Round 7** | Runtime & Alpha Polish | [`contact_sheets/round_07_runtime_alpha_polish.png`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/contact_sheets/round_07_runtime_alpha_polish.png) | Proved 256→128 supersampling with Voronoi RGB margin dilation and steep alpha curve achieves 0% white fringe. |
| **Round 8** | Final Master Review | [`contact_sheets/round_08_final_comparative_review.png`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/contact_sheets/round_08_final_comparative_review.png) | Side-by-side comparison with old placeholders, final production assets exported. |
| **In-Engine** | Live 3D Viewport Frames | [`contact_sheets/in_engine_runtime_views.png`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/contact_sheets/in_engine_runtime_views.png) | Real LÖVE2D raycaster captures in St. Maria at 1, 2, and 4 tile encounter distances. |

---

## 4. Multi-Scale Reduction & Distance Torture Results

Sprites were evaluated at:
- **128×128 (Direct Encounter, 1 Tile):** Full facial structure, cravat/brooch, stone dust marks on apron, individual fingers, and ledger texture are crisp.
- **96×96 (~1.5 Tiles):** Proportions and secondary garment masses remain 100% intact.
- **64×64 (~2.5 Tiles):** Head tilt, hand extension (`request_seal`), trowel prop, and counting fingers remain immediately readable.
- **48×48 (~4 Tiles):** Signature value masses (dark coat vs ivory collar for Celina; dark habit vs pale cowl/apron for Agnes; wiry olive vest vs pale shirt for Gambler) keep character identity distinct across the square.
- **32×32 (~6 Tiles):** Outer silhouette contour remains instantly identifiable (vertical rectangular poise for Celina; wide triangular grounded base for Agnes; angular forward hunch for Gambler).

---

## 5. Alpha & Edge Pipeline Architecture

To guarantee that sprites render seamlessly against any world lighting, fog, or background without halo artifacts:
1. **Source Film:** Rendered in Blender with `film_transparent = True`, pure black world `(0,0,0,1)` with 0 emission, and Box filter `0.5` to eliminate film-level Gaussian blur.
2. **Voronoi RGB Margin Dilation:** Genuine surface colors (navy wool, ivory linen, leather, skin) are dilated outward into 0-alpha border pixels. When downsampled, filter kernels sample 100% true character colors right up to the boundary.
3. **Alpha Treatment:** Tested binary thresholding vs steep smoothstep curve (`clamped((alpha - 0.2) / 0.6)`). The steep curve preserves subtle subpixel anti-aliasing on diagonal silhouettes while eliminating faint fuzzy edges, reading flawlessly on `#000000` pitch black, dungeon slate, and masonry.

---

## 6. Animated Gesture Proof (GIFs)

Animated acting cycles with clear anticipation, action apex, hold, and return were produced and verified at multiple resolutions:

| Character | Action | Native 128 | Reduced 64 | Reduced 48 | Enlarged 8x |
|---|---|---|---|---|---|
| **Celina** | Seal Request | [`celina_request_seal_128x128.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/animations/celina_request_seal_128x128.gif) | [`celina_request_seal_64x64.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/animations/celina_request_seal_64x64.gif) | [`celina_request_seal_48x48.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/animations/celina_request_seal_48x48.gif) | [`celina_request_seal_enlarged_8x.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/animations/celina_request_seal_enlarged_8x.gif) |
| **Agnes** | Brushing Dust | [`agnes_brush_dust_128x128.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/animations/agnes_brush_dust_128x128.gif) | [`agnes_brush_dust_64x64.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/animations/agnes_brush_dust_64x64.gif) | [`agnes_brush_dust_48x48.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/animations/agnes_brush_dust_48x48.gif) | [`agnes_brush_dust_enlarged_8x.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/animations/agnes_brush_dust_enlarged_8x.gif) |
| **Gambler** | Offering Token | [`gambler_offer_game_128x128.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/animations/gambler_offer_game_128x128.gif) | [`gambler_offer_game_64x64.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/animations/gambler_offer_game_64x64.gif) | [`gambler_offer_game_48x48.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/animations/gambler_offer_game_48x48.gif) | [`gambler_offer_game_enlarged_8x.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/frontview-town-character-gauntlet/renders/animations/gambler_offer_game_enlarged_8x.gif) |

---

## 7. Production Integration Status

1. **Production Assets Deployed:**
   - `assets/sprites/event_registrar_celina.png` (128×128 RGBA PNG)
   - `assets/sprites/event_sister_agnes.png` (128×128 RGBA PNG)
   - `assets/sprites/event_the_gambler.png` (128×128 RGBA PNG)
2. **St. Maria Event References (`data/maps/1.json`):**
   - **Registrar Celina (Event 13):** Safely migrated from shared generic placeholder `NPC06.png` to dedicated `event_registrar_celina.png`.
   - **Sister Agnes (Event 12):** Safely migrated from shared generic placeholder `NPC11.png` to dedicated `event_sister_agnes.png`.
3. **The Gambler Integration Gap:**
   - The Gambler is currently implemented exclusively inside the dialogue/choice tree of Event 8 (`Pub Owner` at x=14, y=13).
   - In accordance with project instructions, **no unsanctioned world map event was invented**.
   - `event_the_gambler.png` is ready in `assets/sprites/` and documented for future map authoring or visual dialogue expansion.
4. **Engine Invariants & Verification:**
   - `lovec . validate` passes with `VALIDATE OK`.
   - In-engine first-person viewport capture verified via `lovec . preview-map 1 <x> <y> N`.
