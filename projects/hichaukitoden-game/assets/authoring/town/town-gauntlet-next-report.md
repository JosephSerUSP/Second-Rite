# Second Gate - next town visual gauntlet (report)

Branch `exp/town-material-gauntlet`, stacked on PR #859 (`prep/town-gauntlet-camera-authority`). No PR was merged. PR #856's first-gauntlet evidence was not modified.

### A note on #856's files

The brief mandates the output names `town-gauntlet-contact-sheet.png` and `town-final-projection-window-strip.png`, which are also #856's deliverable names. On this branch those two paths therefore now carry the NEXT gauntlet's output. #856's own branch (`exp/town-gauntlet-workbench`, f69999fb) is untouched, so its historical evidence remains intact where it lives, and the first gauntlet's nine frames are still present here under `attempts/` - the new frames live in `attempts_next/`.

## 1. Camera validation

`python tools/blender/check_next_town_camera.py` **passes**.

```
THESTRA_TOWN_CAMERA_CALIBRATION OK eye=(0.900000,5.500000,0.000000) pitch=0.000000 fovHalfX=0.250000000
THESTRA_TOWN_CAMERA_BLENDER OK lens=43.2676mm pitch=0 offsets=-96,0,+96 transformInvariant=true
```

It did **not** pass as found. `tools/blender/tests/town_camera_blender.py` compared Blender's single-precision `camera.data.lens` against a double-precision derivation with a 1e-8 absolute tolerance. At ~43 mm the float32 resolution is ~3.8e-6, so the check was mathematically unreachable; `float32(expected) == float32(lens)` exactly and the 8.06e-07 delta was pure storage rounding. The tolerance now scales with float32 resolution.

That assertion is a near-tautology by construction - `thestra_camera` sets `camera.lens = SENSOR_WIDTH_MM * ax * 0.5` from the same record fields the expectation re-derives - so it can only ever detect rounding. The guards that actually protect art direction were negative-controlled and both correctly reject bad input:

| negative control | result |
|---|---|
| pitch = -30 deg (the exact #856 mistake) | rejected: "town camera must be level" |
| fovHalfX = 0.55 (wide parity-style) | rejected: lens 19.667 mm outside the 40-45 mm family |
| real calibration | accepted: 43.2676 mm |

### Calibrated values used throughout

| quantity | value |
|---|---|
| pitch | 0 deg (level side view) |
| horizontal FOV | 28.0724869 deg (`fovHalfX` = 0.25) |
| Blender lens | **43.2676 mm** |
| eye | (0.9, 5.5, 0.0), fixed |
| forward / screen-right / up | +X / +Y / +Z |
| target | 426x240 (base viewport 256x144) |
| horizon | y = 70 px (29% from top) |

**A framing consequence worth recording.** `fovHalfX`/`fovHalfY` are tangents, so the visible frame at distance *d* is `(2*0.25*d) x (2*0.140625*d)`. At the study's 6.9-unit framing distance a 1.7 m person fills **88% of the frame height** - that distance was chosen to compare lenses, not to stage a town. The action plane therefore sits at x = 19.0 (d = 18.1), where the frame is ~15.1 x 8.5 units and the protagonist renders at exactly **24x48 px**, one native walker cell at 1:1. The eye, lens and pitch were never touched.

## 2. Material micro-gauntlet (Phase 1)

`town-material-gauntlet-contact-sheet.png` - 16 samples across 6 surface families on identical geometry, camera, lighting and exposure, each rendered at both 512 px study scale and the real 426x240 town scale.

Procedural was initially handicapped by a bug rather than by the strategy: the palette was authored in sRGB numbers and assigned straight to Blender colour sockets, which are **linear**, so every procedural sample rendered roughly twice as bright and desaturated. After fixing that and four specific defects (an inverted joint mask washing every cobble pale green, a rust ramp turning iron into tan cloud, roof rows carrying all the relief so tiles read flat, and a dense distance-to-edge voronoi crazing plaster into a regular ceramic net), procedural improved substantially but still does not match a curated CC0 scan or a generated albedo on hero field surfaces: it lacks high-frequency micro-detail and keeps a soft, low-contrast read.

### Strategy C: the brief's 2x2 sheet format does not work, and why

The brief's default was one 1024x1024 sheet carrying albedo / height / roughness / AO in four quadrants. Measured on real output from two models, the quadrants are **not pixel-registered**:

| model | structural alignment vs albedo | tonal correlation | albedo vertical ramp |
|---|---|---|---|
| gpt-image-1-mini | r = 0.06 - 0.38 | up to +0.83 | +32.0 |
| gpt-image-2 | r = 0.16 - 0.42 | up to +0.74 | +4.9 |

A usable set needs ~0.9+. Both models returned four tonal variants of one lit render; the "height" quadrant shaded flat dentil faces with a 66-level top-to-bottom gradient, which is shading, not elevation.

Strategy C was therefore restructured to generate **one flat albedo** - the one thing the models do well - and derive the rest numerically, so registration is exact by construction and the brief's preferred chain (`generated height -> Blender bump/normal -> optional displacement`) is preserved. Normals are never generated.

| height map | low-frequency shading energy | detail std |
|---|---|---|
| generated quadrant (same subject) | 21.02 | 39.10 |
| derived from the same lit albedo | 6.25 | 54.38 |
| derived from a flat gpt-image-2 albedo | **1.50 - 3.17** | 41.0 - 53.1 |

Derivation quality is bounded by albedo flatness, which is why gpt-image-2 (ramp +4.9) is used rather than gpt-image-1-mini (ramp +32.0).

### Source resolution

Source maps are stored at **512 px** and attempts render at 96 samples. Only the final baked atlas is kept high (2048). Source textures exist purely to feed the bake, and at a 426x240 target nothing downstream can resolve more; the original 2K download also pushed the scene past 4 GB of VRAM into CPU fallback, which made one bake run over 30 minutes. Downsampling took the material set from **116.8 MiB to 6.4 MiB** with no visible difference in the renders.

## 3. Material palette and provenance

22 materials: **7 procedural**, **10 CC0 public-library**, **5 OpenAI-generated**.

Machine-readable manifest: `material-provenance.json`.

Poly Haven assets are **CC0-1.0**, verified at <https://polyhaven.com/license> on 2026-08-20: commercial use and redistribution permitted, attribution not required. Every downloaded file is recorded with its source URL and sha256. No API key is stored anywhere in the repository.

| role | id | strategy | licence |
|---|---|---|---|
| warm_old_limestone | `polyhaven:medieval_blocks_02` | CC0 library | CC0-1.0 |
| darker_structural_stone | `polyhaven:castle_brick_02_white` | CC0 library | CC0-1.0 |
| painted_stained_plaster | `polyhaven:plastered_stone_wall` | CC0 library | CC0-1.0 |
| worn_timber | `polyhaven:weathered_peeling_timber` | CC0 library | CC0-1.0 |
| dark_timber | `polyhaven:dark_wooden_planks` | CC0 library | CC0-1.0 |
| roof_ceramic | `polyhaven:clay_roof_tiles_02` | CC0 library | CC0-1.0 |
| cobblestone | `polyhaven:cobblestone_floor_02` | CC0 library | CC0-1.0 |
| packed_dirt | `polyhaven:dirt_floor` | CC0 library | CC0-1.0 |
| oxidized_iron | `polyhaven:rust_coarse_01` | CC0 library | CC0-1.0 |
| painted_shopfront_wood | `polyhaven:rough_pine_door` | CC0 library | CC0-1.0 |
| gen_facade_ornament | `openai:gen_facade_ornament` | generated albedo + derived maps | owner-generated |
| gen_facade_ornament_img2 | `openai:gen_facade_ornament_img2` | generated albedo + derived maps | owner-generated |
| gen_plaster_patch | `openai:gen_plaster_patch` | generated albedo + derived maps | owner-generated |
| gen_roof_tile | `openai:gen_roof_tile` | generated albedo + derived maps | owner-generated |
| gen_shop_timber | `openai:gen_shop_timber` | generated albedo + derived maps | owner-generated |

## 4. Attempts 01-09

`town-gauntlet-contact-sheet.png` (3x3, native 426x240 renders, aspect preserved).

| # | title | material bias | TH_SOURCE tris | TH_RENDER tris | reduction | blind score |
|---|---|---|---|---|---|---|
| 01 | Narrow stone lane, hard morning rake | B | 197,232 | 444 | 444:1 | **5.10** |
| 02 | Wide plaster square, flat overcast | A | 540 | 372 | 1:1 | **4.07** |
| 03 | Carved facade terrace, late afternoon | C | 197,388 | 528 | 374:1 | **4.70** |
| 04 | Timber upper storeys, deep arch | hybrid | 197,388 | 540 | 366:1 | **5.67** |
| 05 | Shopfront row, cool blue hour | hybrid | 229,976 | 456 | 504:1 | **4.37** |
| 06 | Stepped hill street, strong foreground post | hybrid | 197,424 | 576 | 343:1 | **4.80** |
| 07 | Arch-framed lane, hybrid materials | hybrid | 197,112 | 408 | 483:1 | **4.83** |
| 08 | Evening shopfronts under a framing arch | hybrid | 229,964 | 468 | 491:1 | **4.73** |
| 09 | Thestra lane - full hybrid, deep arch, alleys | hybrid | 197,124 | 420 | 469:1 | **5.03** |

Attempts 01-06 diverge; 07-09 converge on the evaluation of 01-06.

## 5. Blind evaluation (Phase 4)

Two evaluators scored every attempt on 15 criteria, 1-10, from the image alone, in a shuffled presentation order with no material-strategy hint.

**Evaluator independence is weaker than intended.** `OPENROUTER_API_KEY` is present but the account returns `HTTP 402 Payment Required`, so the second evaluator is a different OpenAI model generation (`gpt-4.1`) rather than a second vendor. The two disagree substantially - they rank the top attempt differently - so they are not merely echoing each other, but this is not cross-vendor independence.

| criterion | mean across 9 attempts |
|---|---|
| collapsible to cheap geometry | 8.94 |
| horizontal traversal clarity | 7.83 |
| coherent lighting | 5.61 |
| reads immediately at 426x240 | 5.56 |
| texture scale consistency | 5.33 |
| protagonist legibility | 5.22 |
| side view composition | 5.00 |
| npc legibility and staging | 4.94 |
| material richness | 3.89 |
| architectural depth | 3.61 |
| foreground framing | 3.50 |
| believable surface age | 3.50 |
| late90s prerendered feeling | 3.50 |
| distinctiveness | 2.94 |
| avoids procedural repetition | 2.78 |

The shape of this is the finding: **the collapse to cheap runtime geometry is the strongest thing here (8.94) and traversal clarity is solid (7.78), while distinctiveness (2.78), procedural repetition (2.83) and believable surface age (3.17) are the weakest.** The pipeline works; the art direction is not yet characterful.

Convergence measurably moved the criteria it targeted: foreground framing rose from **1.75** across 01-06 to **3.50** across all nine (5.5 on the winner), and architectural depth from 3.25 to 3.61. Distinctiveness barely moved (2.58 -> 2.78) and remains the clearest unsolved problem.

Representative criticisms, quoted from the raw evaluations (`attempts_next/evaluation.json`):

- *"The huge, visibly tiled cobblestone ground dominates the image with repetitive noise, flattening depth and hurting character legibility."*
- *"Severe tiling/repetition of identical door bays and wall panels, making the scene read as a copied module with shallow depth and no focal variation."*
- *"All building facades and ground plane are very flat."*

## 6. Winner

**Attempt 04 - Timber upper storeys, deep arch.**

Selected as the highest blind mean (**5.67**), and it is also a genuine three-strategy hybrid: CC0 stone and timber field textures, an OpenAI-generated shopfront timber, and a procedural metal, with procedural grime over the library scans.

## 7. Source vs runtime census (Phase 9)

| quantity | value |
|---|---|
| TH_SOURCE triangles | 197,388 |
| TH_RENDER triangles | 540 |
| reduction ratio | 366:1 |
| source materials | 7 |
| runtime materials | 1 (one baked atlas) |
| atlas dimensions | 1024x1024 |
| atlas PNG bytes | 1.3 MiB |
| runtime package bytes | 1.3 MiB |
| .blend bytes | 2.8 MiB |

Material-source breakdown of the winner: `{"openai": 1, "polyhaven": 5, "procedural": 1}`.

`winner_source_vs_baked.png` puts the rich TH_SOURCE render beside the atlas-on-TH_RENDER result at matched framing.

## 8. Projection-window proof (Phase 7)

`town-final-projection-window-strip.png` renders the winner at `projectionWindowOffsetX` = -96 / 0 / +96. The strip builder **asserts** that the lens and the eye transform are identical across all three and fails if they are not; only the window moves.

## 9. Known weaknesses

- **Distinctiveness is the weakest criterion (2.78).** Nothing here yet says "Thestra" rather than "a generic old European street". No signage, no civic landmark, no repeated motif, no colour identity.
- **Facade bays still read as repeated modules** even with per-bay variation.
- **The ground competes with the characters.** Both evaluators independently flagged the cobblestone as too busy at 426x240.
- **Procedural materials get no displaced source geometry.** `height_for()` resolves a height *file*, and node-based materials have none, so attempt 02 reports 1:1 rather than a real reduction. Baking procedural height to an image would fix this and was not done.
- **Rooflines are out of frame by construction.** With a level eye 1.7 m above the street and the horizon at 29% from top, any 5-6 m building exceeds the frame. Height variation in the rhythm is therefore invisible; variation has to come from facade detail, depth stagger and openings.
- **Evaluator independence** is single-vendor (see section 5).
- **One generated sheet in the manifest is an experiment record** (`gen_facade_ornament_img2`), retained as evidence of the 2x2 failure rather than used as a production material.

## 10. Which techniques to retain

| technique | verdict |
|---|---|
| CC0 Poly Haven scans for hero field surfaces | **retain** - strongest richness per effort |
| Generated flat albedo + numerically derived maps | **retain** - best for bespoke carved ornament that no library has |
| Generated 2x2 PBR sheets | **drop** - quadrants are not registered |
| Procedural as a hero field material | **de-prioritise** - lacks micro-detail |
| Procedural as a grime/moss/tonal overlay | **retain** - this is where it genuinely wins, and it breaks library tiling |
| Displaced flat facade panels on TH_SOURCE | **retain** - watertight relief; never displace a box |
| Bake COMBINED to one atlas on coarse geometry | **retain** - the headline result, 8.94/10 collapsibility |

## 11. Recommended next step

**Solve distinctiveness before adding any more material technology.** The pipeline is proven and the collapse is excellent; what is missing is authored identity. Concretely: give Thestra one repeated architectural motif (a specific arch profile or window shape), a restricted colour identity, one civic landmark silhouette visible from several compositions, and hand-placed props with real silhouettes. Quiet the ground material so the protagonist reads. Do that as an art-direction pass on the winning composition rather than as another nine-attempt gauntlet.
