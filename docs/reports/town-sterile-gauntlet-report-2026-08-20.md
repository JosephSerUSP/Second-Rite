# Second Gate Town Visual Gauntlet Report — Sterile Art Base

**Date:** 2026-08-20  
**Host Environment:** Blender 5.1.2 / EEVEE Next  
**Target Native Resolution:** 426 x 240  
**Base Projection:** 256 x 144  
**Camera:** 43.27 mm Blender-equivalent, Horizontal FOV 28.07 deg (fovHalfX = 0.25), Level Pitch 0.0 deg, Horizon Native Y ~ 110.

---

## 1. Executive Summary & Acceptance Gate

This visual gauntlet executed the complete sterile pipeline from an empty art base:
1. **Firewall & Authority:** Clean-room isolation maintained. Zero historical town visual files, .blend scenes, old OBJ models, or legacy materials were inspected or consumed.
2. **Generic Tooling Parity:** Used tools/blender/thestra_camera.py and thestra_camera.create_actor_preview(...) to guarantee mathematical calibration, feet anchoring, nearest-neighbor filtering, unlit emissive presentation, and upright Walker orientation.
3. **Acceptance Gate 1:** Verified 1 protagonist and 2 NPC stand-ins on a calibrated baseline at exact 426x240. Walker height projected to 48.00 px at the action plane.

---

## 2. Research Structure: Three Independent Lineages (A / B / C)

Three fundamentally different architectural concepts were built from bpy.ops.wm.read_factory_settings(use_empty=True):
- **Lineage A (The Bastion Gate & Guildhouse):** Fortified stone gateway, deep barrel-vaulted passage, enterable merchant dwelling with timber-framed jetty overhang, stone stairs, and elevated watch terrace.
- **Lineage B (The Sunken Canal & Quayside Alley):** Lowered canal water basin, mooring posts, dockside derrick crane, heavy warehouse cargo arch, and quayside tavern with porch.
- **Lineage C (The Monastic Cloister & Scriptorium Arcade):** Rhythmic Gothic arcade gallery, vaulted Chapterhouse portal with carved tympanum, high clerestory wall, and distant abbey spire.

---

## 3. Iterative Refinement & Selection (A1 -> A2 -> A3)

- **Lineage Selection:** Lineage A demonstrated the strongest human scale, dramatic depth reveals (through the arched bastion passage), and natural walking route.
- **Stage 2 Refinement (A2):** Added beveled stone plinths, floor demarcations, timber corbels, oriel window bays, leaded glass shop windows, door reveals, and masonry chimneys.
- **Stage 3 Master (A3):** Implemented full procedural PBR materials (Stone Ashlar, Weathered Timber, Terracotta Tiles, Warm Plaster, Leaded Glass, Cobblestones, Interior Cavity Darkness) with world-scale mapping and normal bump micro-relief.

---

## 4. Projection-Window Invariance Proof

Rendered Lineage A3 at 3 projection-window offsets with invariant camera eye (0, -18.67, 2.37), 0.0 deg pitch, and 43.27 mm lens:
- **Left Window (-96 px offset):** projection_window_left_neg96.png
- **Center Window (0 px baseline):** final_winner_A3_center.png
- **Right Window (+96 px offset):** projection_window_right_pos96.png

---

## 5. Source vs Runtime Geometry & Packaging

The environment was packaged into tools/sterile_town/output/environment_package/ following the runtime contract (no flat background planes; coarse real 3D geometry + beauty atlas):
- **TH_SOURCE Complexity:** 325 polygons / rich relief
- **TH_RENDER Complexity:** 36 polygons / coarse real 3D occluder geometry
- **Triangle Reduction Ratio:** **9.03x**
- **Runtime Material Count:** 1 (Single cohesive Beauty Atlas)
- **Atlas Dimensions:** 426 x 240 (128 KB PNG)
- **Runtime Geometry Mesh:** environment_render.obj (3.6 KB)
- **Spatial Anchors & Collision:** environment.json containing spawn_player, doorway, npc_1, npc_2, walk_start, walk_end, and continuous collision bounds.

---

## 6. Pre-Existing Repository Visual Asset Audit

`
======================================================================
ASSET INPUT AUDIT
======================================================================
The ONLY pre-existing repository visual asset read during this task was:

projects/hichaukitoden-game/assets/character/walker.png

Total pre-existing visual files read: 1
Pre-existing town visual assets read: ZERO
======================================================================
`
