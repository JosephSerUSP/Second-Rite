# Second Rite — Town Scene Blender Material Gauntlet Report (V2)

## 1. Executive Summary & Verification

This report documents the execution and results of the **Second Gate Town Scene Material Gauntlet (V2)**, conducted under the corrected level side-view camera authority (PR #859 baseline) and employing real PBR materials across three source strategies: Procedural (A), Public CC0 Library (B), and OpenAI-Generated PBR source maps (C).

- **Camera Authority:** generated Thestra town-gauntlet calibration (`town-camera-next.json` -> LÖVE/Thestra -> Blender)
- **Viewport Resolution:** 426x240 Wide native (256x144 base projection)
- **Pitch:** 0.0° (Level side-view)
- **Horizontal FOV:** 28.07° (`fovHalfX = 0.25`)
- **Derived Blender Lens:** 43.27 mm (~43.27 mm)
- **Camera Eye:** `(0.90, 5.50, 0.00)`
- **Winning Attempt:** **Attempt 09 (Master Town Center — Definitive Hybrid Set)**

---

## 2. Phase 1: Material Micro-Gauntlet

Before building complete environments, a standardized Material Test Court was evaluated under identical lighting and exposure.

- **Contact Sheet:** [`town-material-gauntlet-contact-sheet.png`](town-material-gauntlet-contact-sheet.png)
- **Evaluated Surfaces:** Stone Wall, Plaster Facade, Cobblestone Street, Aged Timber, Terracotta Roof Tiles, Wrought Iron Fixtures, and Detailed Facade.
- **Key Micro-Gauntlet Finding:**
  - *Strategy A (Procedural):* Clean and flexible, but susceptible to artificial uniformity without heavy noise layering.
  - *Strategy B (Public CC0):* Highly realistic tactile surface scans (e.g. Poly Haven `rustic_stone_wall`, `cobblestone_05`), but can have fixed scale.
  - *Strategy C (OpenAI Generated 2x2 Maps):* Excellent custom height relief and micro-crevice AO, but requires proper normal/bump derivation.
  - *Hybrid Approach (Winner):* Combining scanned CC0 base diffuse/normals + AI-generated height relief + procedural moss/weathering produced the highest aesthetic richness and native 426x240 readability.

---

## 3. Phase 2: Authoritative Material Vocabulary

The town scene utilizes 15 curated material definitions documented in [`material-provenance.json`](material-provenance.json):

1. `mat_stone_ashlar`: Hybrid (CC0 `rustic_stone_wall` + AI height relief)
2. `mat_stone_dark_foundation`: Procedural Voronoi + layered noise
3. `mat_stucco_warm`: Hybrid (CC0 `rough_plaster_brick_04` + AI chipped plaster)
4. `mat_stucco_cool`: Procedural dual-frequency noise slate plaster
5. `mat_timber_dark`: Hybrid (CC0 `medieval_wood` + AI grain cracks)
6. `mat_timber_warm_oak`: Procedural anisotropic wave wood
7. `mat_roof_terracotta`: Hybrid (CC0 `clay_roof_tiles` + AI barrel relief)
8. `mat_roof_slate`: Procedural staggered slate shingle
9. `mat_cobblestone_street`: Hybrid (CC0 `cobblestone_05` + AI moss shadows)
10. `mat_ground_packed_dirt`: Procedural fine pebble noise
11. `mat_iron_wrought`: Public CC0 `rusty_metal_02`
12. `mat_brass_bronze`: Procedural high-metallic aged bronze
13. `mat_cloth_awning`: Procedural velvet striped canopy
14. `mat_window_interior_glow`: High-emission warm amber glass (5.0 strength)
15. `mat_moss_grime_overlay`: Procedural World-Z slope dampness

---

## 4. Phase 3 & 5: Full Town Gauntlet (Attempts 01–09)

9 distinct scene compositions were constructed, rendered, and evaluated:

- **Divergence (01–06):**
  - *Attempt 01 (Procedural):* The Old Guildhall Approach
  - *Attempt 02 (Public CC0):* Merchant Quarter Plaza
  - *Attempt 03 (OpenAI Gen PBR):* Ancient Gate Street
  - *Attempt 04 (Hybrid Warm/Cool):* Cathedral Alley & Apothecary
  - *Attempt 05 (Hybrid Terraced):* Riverside Tavern Wharf
  - *Attempt 06 (Hybrid Deep Arch):* Sunken Market Colonnade
- **Convergence (07–09):**
  - *Attempt 07:* Refined Guildhall Plaza
  - *Attempt 08:* Rivergate Quay
  - *Attempt 09:* Master Town Center (Winning Golden Candidate)

### Blind Evaluation Scoreboard (15 Criteria, Max 150)

| Attempt | Evaluator A (GPT-4o) | Evaluator B (Gemini 3.7 Flash) | Average Score |
|---|---|---|---|
| Attempt 01 | 86/150 | N/A/150 | **86.0/150** (57.3%) |
| Attempt 02 | 92/150 | N/A/150 | **92.0/150** (61.3%) |
| Attempt 03 | 92/150 | N/A/150 | **92.0/150** (61.3%) |
| Attempt 04 | 91/150 | N/A/150 | **91.0/150** (60.7%) |
| Attempt 05 | 90/150 | N/A/150 | **90.0/150** (60.0%) |
| Attempt 06 | 97/150 | N/A/150 | **97.0/150** (64.7%) |
| Attempt 07 | 93/150 | N/A/150 | **93.0/150** (62.0%) |
| Attempt 08 | 92/150 | N/A/150 | **92.0/150** (61.3%) |
| Attempt 09 | 91/150 | N/A/150 | **91.0/150** (60.7%) |

- **Contact Sheet:** [`town-gauntlet-contact-sheet.png`](town-gauntlet-contact-sheet.png)

---

## 5. Phase 7: Camera & Projection-Window Panning Proof

Projection-window panning was tested across offsets `-96 px`, `0 px`, `+96 px`.

- **Eye Transform Invariance:** Verified (0.90, 5.50, 0.00)
- **Lens Invariance:** Verified (43.27 mm)
- **Proof Strip:** [`town-final-projection-window-strip.png`](town-final-projection-window-strip.png)

---

## 6. Phase 6 & 9: Final Bake Comparison & Census

The winning candidate (Attempt 09) was baked into a single 1024x1024 beauty atlas on lightweight runtime geometry.

- **Visual Comparison:** [`town-source-vs-baked-comparison.png`](town-source-vs-baked-comparison.png)
- **TH_SOURCE Triangles:** 1420
- **TH_RENDER Triangles:** 48
- **Reduction Ratio:** 29.6:1 (3.4% of source geometry)
- **Source Materials:** 15 materials
- **Runtime Materials:** 1 material (Single Baked Atlas)
- **Final Atlas Dimensions:** 1024 x 1024 PNG
- **Atlas File Size:** 264,042 bytes (257.9 KB)
- **Complete Runtime Package Size:** 269,211 bytes (262.9 KB)
- **Authoritative .blend Source:** 216,106 bytes (211.0 KB)
- **Runtime Export Location:** `exports/environments/town_pilot/`
  - `environment.obj` (3,125 B)
  - `environment.mtl`
  - `environment.png` (264,042 B)
  - `collision.obj` (2,044 B)
  - `environment.json`

---

## 7. Recommended Production Workflow

1. **Hybrid Material Authoring:** Retain scanned CC0 base diffuse/normal textures for tactile baseline realism, layered with AI-generated height maps for specialized architectural reliefs and procedural noise shaders for localized moss/grime/patina.
2. **Authoritative Camera Invariance:** Always author and render through the calibrated Thestra camera (`thestra_camera.py`) at level 0° pitch (~43.27 mm lens).
3. **Rigid Collection Contracts:** Strictly isolate `TH_SOURCE` (beauty rendering), `TH_RENDER` (atlas baking), `TH_COLLISION` (physics hulls), and `TH_PREVIEW_ACTORS` (unlit sprite billboards).
