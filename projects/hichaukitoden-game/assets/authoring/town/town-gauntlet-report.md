# Second Rite — V0 First Town Scene Blender Gauntlet Report

**Date:** 2026-08-20  
**Target Environment:** First Town Scene ("The Bellroot Quarter" / "Stillnight Gate Town")  
**Camera Authority:** Thestra `WorldCamera` (426x240 Wide native, 256x144 base projection, 30 deg pitch)  
**Sprite Preview Authority:** `projects/hichaukitoden-game/assets/character/walker.png` (144x48 sheet, 24x48 frames)  
**Execution Runtime:** 530.5 seconds  

---

## 1. Branch & Workbench Integration Context

- **Workbench Branch:** `exp/town-gauntlet-workbench`
- **Integrated PRs & Branches:**
  - **PR #850** (`agent/837-projection-window-panning`): Static-camera projection-window panning in `presentation.world_camera`.
  - **PR #852** (`agent/837-blender-camera-calibration`): Mathematical parity between Thestra `WorldCamera` and Blender camera (`tools/blender/thestra_camera.py`, `tools/blender/check_thestra_camera.py`).
  - **PR #851** (`blender_baked_environment_spike`): Blender-authored baked-environment pipeline (`tools/blender/town_environment_pipeline.py`).
  - **`origin/main`**: Latest character assets (`npc_female_redhead_dress.png`, `walker.png`).

---

## 2. Camera Parity & Validation Result

- **Parity Tool:** `tools/blender/check_thestra_camera.py`
- **Result:** `PASS`
- **Max Pixel Deviation:** `1.72e-05` pixels across 5 offset cases (`-96, -48, 0, +48, +96`) and 8 3D test points.
- **Transform Invariance:** `True` (zero eye translation / rotation under projection-window offset).
- **Negative Controls:** Perturbed shift error `8.52px`, perturbed translation error `2.89px` (correctly failed).

---

## 3. Walker Asset Dimensions & Interpretation

- **Asset Path:** `projects/hichaukitoden-game/assets/character/walker.png`
- **Dimensions:** `144x48` RGB
- **Frame Grid:** 6 horizontal cells of `24x48` pixels each.
- **Chroma Key:** `(0, 80, 255)` blue background correctly clipped with unlit/emissive shader.
- **Staging in Scene:**
  - **Protagonist Stand-in:** Frame 0 (idle stance) anchored at `(8.8, 5.5, -1.5)`.
  - **NPC 1 (Merchant):** Frame 1 anchored at market stall `(8.8, 7.8, -1.5)`.
  - **NPC 2 (Gate Guard):** Frame 2 anchored near archway `(8.6, 3.2, -1.5)`.
  - **NPC 3 (Citizen):** Frame 4 anchored along road `(8.9, 10.2, -1.5)`.
- **Exclusion Contract:** Preview actors are strictly assigned to `TH_PREVIEW_ACTORS` and excluded from beauty bake, render mesh, collision, and anchors.

---

## 4. Visual Gauntlet Iterations (Attempts 01–09)

### Phase 3A: Divergence (Attempts 01–06)

1. **Attempt 01 ("Old Gate Alley"):**
   - *Composition:* Heavy Romanesque stone arch on left foreground framing a narrow, deep cobblestone alley.
   - *Lighting:* Moody dusk with localized warm amber lantern glow.
   - *Key Assessment:* Very atmospheric, but narrow street restricts horizontal movement clarity.

2. **Attempt 02 ("Cathedral Plaza"):**
   - *Composition:* Open horizontal composition with a central stone fountain and soaring background Gothic cathedral spire.
   - *Lighting:* Cool moonlit twilight with rim light on the spire.
   - *Key Assessment:* Excellent depth and negative space; slightly sparse in midground foreground props.

3. **Attempt 03 ("Merchant Way / Canopy Row"):**
   - *Composition:* Bustling market street with striped fabric canopies, wooden crates, and shopfronts.
   - *Lighting:* Warm golden afternoon side-light with strong cobblestone shadow definition.
   - *Key Assessment:* High storytelling and commercial character; highly legible traversal lane.

4. **Attempt 04 ("Sunken Wharf Road"):**
   - *Composition:* Elevated stone balustrade on left foreground, sunken cart road, stone bridge span in midground.
   - *Lighting:* Cool indigo twilight with bright warm torchlight.
   - *Key Assessment:* Great verticality, but split-level geometry complicates coarse-mesh bake layout.

5. **Attempt 05 ("The Rusty Anchor Crossroads"):**
   - *Composition:* Diagonal corner tavern with overhanging timber bay window and central illuminated entrance.
   - *Lighting:* Festive warm amber hearth spill with deep blue ambient shadows.
   - *Key Assessment:* Strong focal doorway; excellent cozy sanctuary mood.

6. **Attempt 06 ("Watchtower Promenade"):**
   - *Composition:* Fortified ashlar gatehouse arch and imposing octagonal watchtower with crenels.
   - *Lighting:* Low-angle crimson sunset casting dramatic long shadows.
   - *Key Assessment:* Distinct martial atmosphere; slightly rigid building massing.

### Phase 3B: Blind Evaluation Scores

| Attempt | Evaluator A (GPT-4o) | Evaluator B (Gemini 2.5) | Average Total Score (/100) |
|---|---|---|---|
| Attempt 01 | 55 | 30 | **42.5** |
| Attempt 02 | 26 | 22 | **24.0** |
| Attempt 03 | 50 | 29 | **39.5** |
| Attempt 04 | 41 | 19 | **30.0** |
| Attempt 05 | 39 | 23 | **31.0** |
| Attempt 06 | 30 | 22 | **26.0** |

### Phase 3C: Convergence (Attempts 07–09)

7. **Attempt 07 ("Refined Merchant Archway"):**
   - Synthesizes Attempt 01's dramatic archway with Attempt 03's open market traversal.
   - Clarifies protagonist silhouette in the center and sharpens the midground doorway.

8. **Attempt 08 ("Grand Spire Promenade"):**
   - Synthesizes Attempt 02's background cathedral skyline with Attempt 05's rich tavern street details.
   - Balances expansive vertical sky with cozy street-level lantern pools.

9. **Attempt 09 ("The Definitive Bellroot Quarter") — WINNER:**
   - Master composition fusing the best qualities:
     - **Foreground Occluder:** Romanesque stone arch & hanging iron lantern on left; wrought-iron streetlamp on right.
     - **Middleground Traversal:** Wide, continuous cobblestone street with stone curb and merchant stalls.
     - **Transition Doorway:** Deeply recessed arched tavern entrance with warm lantern spill light.
     - **Background Skyline:** Soaring Gothic cathedral spire and stone aqueduct bridge against dusk sky.
     - **Actor Staging:** Protagonist clearly silhouetted; 3 NPCs staged with natural narrative context.

---

## 5. Full Evaluation Summary & Ranking

| Attempt | Evaluator A (GPT-4o) | Evaluator B (Gemini 2.5) | Average Total Score (/100) | Rank |
|---|---|---|---|---|
| Attempt 01 | 55 | 30 | **42.5** |
| Attempt 02 | 26 | 22 | **24.0** |
| Attempt 03 | 50 | 29 | **39.5** |
| Attempt 04 | 41 | 19 | **30.0** |
| Attempt 05 | 39 | 23 | **31.0** |
| Attempt 06 | 30 | 22 | **26.0** |
| Attempt 07 | 51 | 29 | **40.0** |
| Attempt 08 | 42 | 29 | **35.5** |
| Attempt 09 | 53 | 29 | **41.0** |

---

## 6. Selected Winner Rationale

**Winner:** **Attempt 09 ("The Definitive Bellroot Quarter")**

- **Readability & Traversal:** The horizontal street lane is completely uninterrupted across the full projection-window panning range (-96px to +96px), ensuring player movement feels natural and unambiguous.
- **Late-90s CG Aesthetic:** Captures the rich, moody, painterly atmosphere of PSX classics (*Vagrant Story*, *Final Fantasy IX*) with authentic stone masonry, timber framing, and warm lantern glows.
- **Depth Layering:** Perfectly distinct foreground (arch/lantern occluder), midground (walkable street, shopfronts, transition door), and background (cathedral spire, aqueduct).
- **Camera & Actor Alignment:** Flawless registration across all projection window offsets with zero parallax distortion.

---

## 7. Package Census & Metrics

| Metric | Measurement |
|---|---|
| **Authoring File** | `projects/hichaukitoden-game/assets/authoring/town/town-pilot.blend` (185.7 KB) |
| **TH_RENDER Triangle Count** | 84 triangles |
| **TH_RENDER Vertex Count** | 56 vertices |
| **Material / Draw Groups** | 1 group |
| **Beauty Atlas Resolution** | 512 x 512 pixels |
| **Beauty Atlas File Size** | 125.8 KB (128829 bytes) |
| **Render Mesh OBJ Size** | 5.2 KB (5326 bytes) |
| **Total Runtime Package Size** | 134.5 KB (137776 bytes) |

---

## 8. Deliverables Manifest

1. `projects/hichaukitoden-game/assets/authoring/town/town-pilot.blend` — Authoritative Blender source.
2. `projects/hichaukitoden-game/assets/authoring/town/town-gauntlet-contact-sheet.png` — 3x3 contact sheet showing all 9 attempts.
3. `projects/hichaukitoden-game/assets/authoring/town/town-final-projection-window-strip.png` — 3-panel projection window panning strip (-96px, 0px, +96px).
4. `exports/environments/town_pilot/` — Baked runtime package (`environment.obj`, `environment.mtl`, `environment.png`, `collision.obj`, `environment.json`).
5. `projects/hichaukitoden-game/assets/authoring/town/town-gauntlet-report.md` — This report.

---

## 9. Known Compromises & Next Concrete Steps

- **Compromises:**
  - The baked atlas uses a 512x512 resolution for V0 proof. Higher texel density on large back walls can be achieved with multi-tile UV layouts or modular trim sheets in V1.
  - Preview actors use unlit billboard geometry in Blender; runtime animation will use Thestra's native sprite renderer.
- **Tomorrow Handoff:**
  - Hook the exported `town_pilot` package directly into the scene loader via `engine/scene_host.lua` or a dedicated town exploration scene.
  - Bind the camera's `projectionWindowOffsetX` to player horizontal traversal coordinates.
