# Second Rite Tiny 3D Character Authoring Pipeline: Gauntlet Findings & Architecture Report (24×24 Target)

## 1. Executive Summary

This study pressure-tested Second Rite's real Blender character-authoring pipeline by developing and iterating three distinct chibi 3D character prototypes constrained to an honest final raster resolution of **24×24 pixels**:

1. **Approach A: Volumetric / Sculptural (The Knight / Ironward)**
2. **Approach B: Graphic / Faceted (The Rogue / Shadow Blade)**
3. **Approach C: Rendered-Sprite / Compressed Depth (The Mage / Chronomancer)**

The investigation proved that **spending surprisingly sophisticated 3D modeling, lighting, and animation effort on a hilariously tiny raster produces characters with extraordinary depth, presence, and motion that surpass hand-drawn 24×24 pixel art in lighting consistency and turnarounds.**

All source documents are preserved as authoritative, editable Blender documents under [`assets/authoring/characters/`](file:///d:/Antigravity/Hichaukitoden/assets/authoring/characters/):
- [`knight_volumetric.blend`](file:///d:/Antigravity/Hichaukitoden/assets/authoring/characters/knight_volumetric.blend)
- [`rogue_faceted.blend`](file:///d:/Antigravity/Hichaukitoden/assets/authoring/characters/rogue_faceted.blend)
- [`mage_planar.blend`](file:///d:/Antigravity/Hichaukitoden/assets/authoring/characters/mage_planar.blend)

---

## 2. Eliminating the White Outline Artifact & Perfecting Edge Color

### What Caused the White Outline?
1. **Un-padded Alpha Downsampling:** When an image rendered on transparent film is downsampled, transparent border pixels containing white/ambient background light leak into the edge pixels.
2. **Blender Film Pixel Filter Blur:** Blender's default Film Pixel Filter (`filter_size = 1.5` Gaussian) spreads background world light across 1.5 pixels of geometry boundary.

### The Complete Three-Pronged Solution

```
[Blender 48×48: Box Filter 0.5 + Black World (0,0,0)]
                          │
                          ▼
             [Color Padding / Dilation]
      (Extends true surface RGB outward into margin)
                          │
                          ▼
            [Smooth RGB Downsample (24×24)] ◄─── (Smooth internal AA & specular)
                          │
                          ▼
         [Binary Alpha Threshold (α ≥ 110)] ◄─── (100% solid, crisp contour)
```

1. **Blender Film & World Configuration:**
   - Set `scene.render.filter_size = 0.5` with `scene.render.pixel_filter_type = 'BOX'`. This eliminates film-level Gaussian blur at the rendering source.
   - Set `scene.world` background node to pure black `(0.0, 0.0, 0.0, 1.0)` with strength `0.0`. Rays escaping geometry boundary never encounter white or ambient environment wash.
2. **True Surface Color Padding (Voronoi Margin Dilation):**
   - For all pixels outside the solid alpha mask ($a \le 64$), their RGB values are populated by extending the nearest solid pixel's genuine surface color (steel, gold, fabric, porcelain).
   - When downscaled to 24×24, the filter kernel samples **100% genuine character colors right up to the edge**.
3. **Strict Binary Alpha Threshold:**
   - Outer contour is strictly binary (0 or 255) — **zero semi-transparent halo pixels**.

---

## 3. Edge Treatment Strategies Evaluated

| Edge Treatment Method | Description | Read on Dark Slate | Read on UI Parchment | Read on Pitch Black | Best Use Case |
|---|---|---|---|---|---|
| **Method A: True Surface Color (Clean Edge)** | Border pixels carry the exact color of the armor/fabric dilated outward. 0% white, 0% dark halo. | **Flawless.** Seamless integration with dungeon floor. | **Flawless.** Crisp, vibrant, zero white fringe. | **Flawless.** Natural, clean character silhouette. | **Recommended Default** for modern 2.5D and high-fidelity retro RPGs. |
| **Method B: 1-Pixel Dark Outline** | 1-pixel dark charcoal contour `#14161c` drawn around the 24×24 solid boundary. | Excellent retro contrast. | High contrast, comic/16-bit style. | Blends slightly into black background. | Great for high-contrast anime/retro GBA styling. |
| **Method C: Alpha Clamp (Steep Curve)** | Smoothstep curve on alpha ($0.25 \dots 0.85$). | Good, but retains tiny subpixel edge. | Slight edge softening. | Good. | Best for smooth UI porting. |

---

## 4. Visual Test Sheets & Verification

- **Edge Treatment on Pitch Black (8× Zoom):** [`edge_treatment_on_pitch_black_8x.png`](file:///d:/Antigravity/Hichaukitoden/experiments/tiny-character-pipeline/renders/contact_sheets/edge_treatment_on_pitch_black_8x.png)
- **Edge Treatment on Dungeon Slate (8× Zoom):** [`edge_treatment_on_dungeon_slate_8x.png`](file:///d:/Antigravity/Hichaukitoden/experiments/tiny-character-pipeline/renders/contact_sheets/edge_treatment_on_dungeon_slate_8x.png)
- **Edge Treatment on UI Parchment (8× Zoom):** [`edge_treatment_on_ui_parchment_8x.png`](file:///d:/Antigravity/Hichaukitoden/experiments/tiny-character-pipeline/renders/contact_sheets/edge_treatment_on_ui_parchment_8x.png)
- **Edge Treatment on Checkered Pattern (8× Zoom):** [`edge_treatment_on_checkered_bg_8x.png`](file:///d:/Antigravity/Hichaukitoden/experiments/tiny-character-pipeline/renders/contact_sheets/edge_treatment_on_checkered_bg_8x.png)
- **8-Direction Compass Turnaround Sheet (8× Zoom):** [`directional_comparison_8x.png`](file:///d:/Antigravity/Hichaukitoden/experiments/tiny-character-pipeline/renders/contact_sheets/directional_comparison_8x.png)
- **Walk Cycle Contact Sheet (8× Zoom):** [`walk_cycle_contact_sheet_8x.png`](file:///d:/Antigravity/Hichaukitoden/experiments/tiny-character-pipeline/renders/contact_sheets/walk_cycle_contact_sheet_8x.png)

### Animated Walk GIFs (24×24 & 8×)
- **Knight Walk:** [`knight_volumetric_walk_24x24.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/tiny-character-pipeline/renders/animations/knight_volumetric_walk_24x24.gif) | [`knight_volumetric_walk_8x.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/tiny-character-pipeline/renders/animations/knight_volumetric_walk_8x.gif)
- **Rogue Walk:** [`rogue_faceted_walk_24x24.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/tiny-character-pipeline/renders/animations/rogue_faceted_walk_24x24.gif) | [`rogue_faceted_walk_8x.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/tiny-character-pipeline/renders/animations/rogue_faceted_walk_8x.gif)
- **Mage Walk:** [`mage_planar_walk_24x24.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/tiny-character-pipeline/renders/animations/mage_planar_walk_24x24.gif) | [`mage_planar_walk_8x.gif`](file:///d:/Antigravity/Hichaukitoden/experiments/tiny-character-pipeline/renders/animations/mage_planar_walk_8x.gif)

---

## 5. Realtime 3D vs Baked Spritesheets Trade-off

| Dimension | Realtime 3D Evaluation | Prerendered Spritesheet Evaluation |
|---|---|---|
| **Visual Quality at 24×24** | Good, but limited by retro shader lack of specular highlights and overlay pass limits. | **Exceptional.** Full EEVEE/Cycles lighting, custom rim lights, rich material roughness, and subpixel supersampling are preserved. |
| **Directional Flexibility** | Infinite continuous rotation angles. | Discrete 4 or 8 baked directions. (For Second Rite's grid-based dungeon crawling, 4 or 8 directions is exact and authentic to 1996 classics). |
| **Animation Production Cost** | Rigging must strictly conform to bone constraints; detached parts need skeletal parenting. | Very fast: can use detached hierarchies, shape keys, procedural modifiers, and camera cheats freely without runtime overhead. |
| **Runtime Performance** | Multi-draw GPU calls for mesh instances; depth buffer overhead in 3D viewport. | 1 texture bind per spritesheet atlas; ultra-fast quad draw in LÖVE. |
| **Verdict** | Best for large interactive world props and boss battlers. | **Decisively superior for 24×24 chibi player and NPC party characters.** |
