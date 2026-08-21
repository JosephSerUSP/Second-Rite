# Second Gate clean-room town gauntlet

Nine independently authored side-view town scenes for issue #838, built from
geometric zero on the camera authority prepared in #859, evaluated blind, and
collapsed to one baked runtime package ready for the #862 playability seam.

---

## 1. Basis

| | |
|---|---|
| Repository | `JosephSerUSP/Second-Rite` |
| Branch | `exp/town-cleanroom-gauntlet`, cut from `main` at `3d391e05` |
| Worktree | `D:\Antigravity\hk-cleanroom` (fresh; created for this task) |
| Blender | 5.1 |
| Nothing merged | no PR merged, no branch pushed |

Read first, as instructed: issues #838 and #695, and PRs #859, #862, #863.
#862 was treated as playability evidence and #863 as material/bake technical
evidence. Neither one's authored environment was used as visual input.

---

## 2. Clean-room compliance

Every attempt begins with `bpy.ops.wm.read_factory_settings(use_empty=True)`
followed by an explicit purge of every remaining datablock
(`cleanroom/scene.py::reset`). No `.blend` is ever opened as a starting point,
including for the three convergence attempts. No attempt module imports
another attempt module; the package's `attempts/__init__.py` states the rule
and nothing violates it.

**Knowledge was inherited. Art was not.**

Inherited (tooling and findings only):

- `thestra_camera.py` — the camera/calibration front-end (generic).
- `town_environment_pipeline.py` — the accepted environment-package contract
  and bake/export tooling (generic; the schema was **not** changed).
- `runtime/presentation/world_camera_calibration.lua` and the LÖVE harness —
  the authority chain from #837/#859.
- `blind_evaluator.py` — read for shape; a new 17-criterion evaluator was
  written because the brief's criteria differ from its ten.
- Written lessons from #863: box winding, the actor basis, depsgraph flushing,
  displacement on flat panels not closed boxes, sRGB-vs-linear colour sockets,
  keeping `TH_RENDER` out of source beauty renders, keeping preview actors out
  of the bake, and not trusting generated normal maps.

Not inherited: no previous town `.blend`, OBJ, MTL, atlas, environment PNG,
render, contact sheet, material texture, generated texture, Poly Haven copy
already in the repository, collision mesh, `TH_SOURCE`/`TH_RENDER` geometry,
environment package, layout, facade, arch, or convergence winner. None of
`town_gauntlet_builder.py`, `town_gauntlet_level.py`, `town_material/*` was
executed or copied; they were read only for the technical bugs listed above.

**walker.png was the only pre-existing visual asset consumed.** See §12.

---

## 3. Camera

Measured, not assumed. The authority chain was run end to end before any art:

```
town-camera-next.json  ->  LÖVE / Thestra  ->  calibration JSON
                       ->  thestra_camera.py  ->  Blender TH_CAMERA_PREVIEW
```

`python tools/blender/check_next_town_camera.py` **passes** on this branch.

| quantity | value | how obtained |
|---|---|---|
| pitch | **0°** (true level side view) | from the calibration |
| horizontal FOV | **28.0724869°** (`fovHalfX` 0.25) | from the calibration |
| Blender lens | **43.2676 mm** | derived by `thestra_camera`, not authored |
| eye | **(0.9, 5.5, 0)**, fixed | from the calibration |
| native output | **426 × 240** | from the calibration |
| horizon row | native **Y = 70** (`viewportCenterX` 213) | from the calibration |
| action-plane depth | **18.6667** units from the eye → **x = 19.5667** | solved numerically in Blender |
| 1.75-unit walker | **47.99999 px** | measured through `world_to_camera_view` |
| scale at the plane | **27.4286 px per world metre** | derived from the above |

The action-plane depth is bisected against Blender's own projection
(`cleanroom/camera.py::solve_action_plane`), so lens shift, pixel aspect and
sensor fit are included rather than re-derived. The camera was never eyeballed
and no attempt authors a lens, pitch or eye.

Two consequences that shaped every scene:

- A level camera at z = 0 puts the horizon at native Y = 70 for *every* depth,
  so the ground plane must sit **below** the eye. Scenes use a street at
  z ≈ −4.2, which places the walker's feet at native Y ≈ 184.
- Visible half-width is `213 · (x − 0.9) / 512` metres. At x = 14 that is only
  5.5 m, so foreground props must sit near y ≈ 5.5 or they fall out of frame.
  Rooflines only enter the frame for facades at x ≳ 26.

---

## 4. Material vocabulary (Phase 1)

17 materials across three strategies, built from zero.

| strategy | count | notes |
|---|---|---|
| public (CC0) | 5 | Poly Haven, freshly searched and downloaded during this task |
| generated | 3 | gpt-image-2, **one flat albedo each**; all other channels derived |
| procedural | 9 | authored in `cleanroom/mats.py`, colours converted sRGB → linear |

### The generated-material strategy

The brief's warning was confirmed and avoided: no 2×2 pseudo-PBR sheet was
requested, and no generated normal map is used anywhere. Each generated
material is **one flat, evenly lit, tileable albedo**, from which height,
ambient occlusion and roughness are derived numerically
(`cleanroom/derive.py`). Registration is therefore exact by construction.

Measured flatness of the generated albedos (`low_freq_energy` is baked-in
lighting gradient; lower is better — #863 measured 21.02 for a generated
*height quadrant*):

| material | low-freq energy | detail std | seam error |
|---|---|---|---|
| plaster_bone | 1.11 | 8.54 | **0.00000** |
| stone_ashlar_fine | 2.41 | 14.75 | **0.00000** |
| plaster_verdigris | 4.70 | 15.99 | **0.00000** |

The seam figure is worth recording as a method note. The obvious
"make tileable" implementation — cross-fading the leading and trailing bands
into each other — makes the two bands *equal to each other* and leaves the
actual wrap boundary untouched; measured seam error got **worse**
(0.018 → 0.023). A one-sided blend that cross-fades the trailing band toward
the leading content, shifted so the last column lands exactly on the first,
gives an exactly continuous tile. The metric caught the bug; without it the
first implementation would have shipped.

### Phase 1 eliminated four materials before scene production

Swatches were rendered at the scene's **true native density** (27.4286 px/m)
through an orthographic swatch camera, so nothing was judged at a flattering
resolution. On that evidence:

- `render_patched`, `shutter_boards`, `rubble_base` (all public scans) read as
  blank mud and were **dropped**; `mossy_stone_wall` and `dark_planks` were
  freshly downloaded to replace two of them.
- `stone_ashlar_fine` (generated) came back with **no visible coursing at all**
  and was **regenerated once** with an explicit physical-scale prompt ("the
  square field of view is exactly 2.2 metres across and must contain about six
  courses"), which fixed it.
- `stone_coursed` (procedural) read as tidy modern brick and was dropped once
  the regenerated ashlar covered that job.
- `limewash_pale`'s crack voronoi read as crazy paving, `paving_granite`'s wet
  pooling read as mould, and `paint_madder` was a flat card. All three were
  corrected.

### Physical scale (Phase 4)

Every material declares `tile_m`, its real repeat in metres, taken from Poly
Haven's `dimensions` field for scans and authored for the rest. `mats.apply`
generates world-space box-projected UVs at exactly that scale, so UV is world
position divided by a metre value — never a per-object 0..1 normalise. A stone
course is therefore the same physical size on a large wall, a narrow jamb and a
foreground plinth. Blind `surface_scale` scored 6.56 / 6.33 (divergence /
convergence), one of the strongest criteria in the whole panel.

---

## 5. Divergence — attempts 01 to 06

| id | concept | source tris | runtime tris | ratio |
|---|---|---|---|---|
| 01 | **The Cistern Lip** — monumental compression; a broad lip at the foot of one colossal blind retaining wall, cistern shaft on the near side | 133,000 | 62 | 2145 : 1 |
| 02 | **The Sag** — open street, buildings pushed to x ≈ 29 so rooflines enter frame; an authored *gap of sky* between a squat civic shed and three leaning houses | 8,772 | 86 | 102 : 1 |
| 03 | **The Rib Walk** — a covered way with transverse masonry ribs at irregular intervals; almost everything dark, one bright end | 53,434 | 110 | 486 : 1 |
| 04 | **The Buttress Gaps** — four buttresses at different depths and widths; domestic accretion silted into the recesses between them | 96,576 | 86 | 1123 : 1 |
| 05 | **The Overhang** — a jettied upper storey over a shadowed street; four separated depth planes | 61,616 | 122 | 505 : 1 |
| 06 | **The Stepped Lane** — the route itself rises along the walking axis; old mineral stone below, newer domestic plaster above | 68,022 | 76 | 895 : 1 |

Every attempt supports a horizontal route, one useful doorway, a
foreground-depth interaction, true 1.75-unit walker scale and three NPC
stand-ins taken from other frames of walker.png.

Attempts 01, 04, 06, 07, 08 and 09 exploit expensive `TH_SOURCE` geometry;
01 pushes it hardest (133k triangles collapsing 2145 : 1). Relief is real
displacement from the material's own height map, applied to flat subdivided
panels laid out **around** real openings (`geom.slotted_panel`), never to
closed boxes — a displaced box tears along its shared edges.

---

## 6. Blind evaluation

Blindness is structural, not a promise (`cleanroom/evaluate.py`): renders are
copied to opaque `specimen_<hash>` names, the mapping is never sent, no concept
text / attempt number / phase / material strategy / prior ranking appears in any
prompt, specimen order is shuffled per evaluator, and each evaluator sees one
image at a time so it cannot rank by comparison.

Three passes across two vendors:

- `openai:gpt-4.1`
- `openai:gpt-4o`
- `nvidia:nemotron-nano-12b-vl` (via OpenRouter)

Genuine cross-vendor independence was achieved, but with a caveat recorded
rather than hidden: OpenRouter's **paid** vision models return HTTP 402 on this
account, so the cross-vendor pass is a free-tier model far smaller than the two
OpenAI passes. It is also systematically more generous — it answered "yes" to
*would you walk into this space* for six of nine specimens while both OpenAI
passes answered "no" for all nine.

---

## 7. What the divergence round actually taught

Aggregates were tightly clustered (5.55–5.98 / 10), so **the aggregate decided
nothing and the free text decided everything.** Every attempt, from every
evaluator, drew the same complaint in different words: *empty, plain, no props,
no environmental storytelling, a blockout or engine test.*

Weakest criteria across 01–06: `foreground_relationship` 4.56,
`distinct_identity` 4.50, `architectural_specificity` 4.50, `npc_staging` 4.56,
`avoids_modular_repetition` 5.17.

The finding that mattered: **restraint had been over-applied.** The vocabulary
and palette were disciplined and scored well for it (`material_restraint` 6.78,
`surface_scale` 6.56), but a quiet surface only reads as quiet when something
beside it is genuinely dense. Six scenes of quiet-beside-quiet read as
unfinished. The full written findings are in
`tools/blender/cleanroom/FINDINGS.md`, and they are the **only** thing that
crossed into 07–09.

---

## 8. Convergence — attempts 07 to 09

Each was authored from an empty scene against the written findings. None
duplicates, imports, appends to or re-derives any earlier attempt.

| id | concept | source tris | runtime tris | ratio |
|---|---|---|---|---|
| 07 | **The Drying Lane** — a dense band of daily use (five laundry lines at four heights, sheets, ladder, drying rack, sills, bird boxes, a mended gutter) over a deliberately quiet floor; foreground is a laundry trough with a figure working at it | 106,280 | 110 | 966 : 1 |
| 08 | **The Tally Crane** — one bold functional silhouette: a timber treadwheel crane cantilevered from a counting house, with a loaded pallet hanging in the foreground, mid-task | 98,274 | 86 | 1143 : 1 |
| 09 | **The Offering Wall** — several hundred small votive niches (the densest surface in the gauntlet) beneath one completely blank ashlar mass; madder banners and a lit candle field as the only colour | 97,188 | 62 | 1568 : 1 |

Convergence moved exactly the criteria it targeted, and regressed one:

| criterion | 01–06 | 07–09 | Δ |
|---|---|---|---|
| avoids_modular_repetition | 5.17 | 5.67 | **+0.50** |
| architectural_specificity | 4.50 | 4.89 | +0.39 |
| distinct_identity | 4.50 | 4.78 | +0.28 |
| material_restraint | 6.78 | 7.00 | +0.22 |
| npc_staging | 4.56 | 4.78 | +0.22 |
| **doorway_readability** | 6.17 | 5.33 | **−0.84** |

The doorway regression is mine and is stated plainly: in 08 and 09 the new
dominant feature (the crane, the candle field) out-competes the door for
attention even though the door is lit, and in both the door sits far along the
lane. Finding 6 was applied but not applied *hard enough*.

Two composition faults were found and fixed during convergence rather than
shipped: 08's crane initially raked out of the top of frame and read as a stray
pole (the whole machine was brought down into frame), and 09's stall canopy sat
at exactly the height of the niche band and hid the one thing the scene exists
to show (the canopy was removed and the stall shortened).

---

## 9. Winner

**Attempt 07 — The Drying Lane**, blind aggregate **6.00 / 10**, the highest of
the nine.

Raw score is evidence, not authority, so the selection was checked against the
criteria the research had identified as weak. 07 is top or joint-top of all
nine on precisely those: `avoids_modular_repetition` 6.00 (best),
`material_richness` 6.00 (joint best), `architectural_specificity` 5.00 (joint
best), `human_scale` 6.67 (best), `surface_scale` 7.33 (best),
`expensive_prerendered` 5.67 (best). It is also the only specimen any evaluator
described as *lived-in*, and the only one whose most-memorable answer named the
scene's actual subject rather than an incidental prop.

Its weakness is `doorway_readability` 6.00 — mid-pack, and the first thing a
follow-up pass should attack.

---

## 10. Bake, projection window and runtime readiness

See §11 for the measured package figures.

### Projection window

Rendered at −96 / 0 / +96 px. The offset is applied to the authoring study
input's canonical centre, resolved through LÖVE exactly as the zero-offset
calibration was, and consumed by Blender — Blender never authors a camera
value. The strip **asserts** invariance and fails otherwise:

| offset | lens (mm) | eye | shift_x |
|---|---|---|---|
| −96 | 43.267605 | (0.9, 5.5, 0.0) | −0.225352 |
| 0 | 43.267605 | (0.9, 5.5, 0.0) | −0.000000 |
| +96 | 43.267605 | (0.9, 5.5, 0.0) | +0.225352 |

Eye, lens and pitch are identical; only the principal point moves, which is
what a projection window is.

### Readiness for the #862 seam

No runtime engine work was done here and #862's engine work was not duplicated.
The winner provides what #862-style integration consumes:

| requirement | provided |
|---|---|
| spawn anchor | `spawn` at (21.60, 4.70, −4.05) |
| horizontal walk bounds | `walk_min` / `walk_max`, y ∈ [−9.0, 22.0] at x = 21.60, z = −4.05 |
| doorway anchor | `door_lane` at (24.40, 7.85, −4.05) |
| NPC anchors | `npc_1`, `npc_2`, `npc_3` |
| foreground occluder in `TH_RENDER` | the laundry trough proxy, plus five per-cord laundry planes |
| collision | `TH_COLLISION`, exported separately as `collision.obj` |
| environment bounds | in the package manifest |
| valid runtime package | `environment.json` / `.obj` / `.mtl` / `.png` |

The next step is to drop this package into the seam #862 already proved and
walk through it — not to build another town.

---

## 11. Measured package figures

| quantity | value |
|---|---|
| TH_SOURCE triangles | **106,280** |
| TH_RENDER triangles | **182** |
| reduction ratio | **584 : 1** |
| TH_COLLISION triangles | 0 |
| atlas | **1024 x 1024**, 1,487,570 bytes (1.42 MiB) |
| atlas coverage | **90.5%** of texels received bake data |
| runtime package | 1,507,571 bytes (**1.44 MiB**) total |
| render mesh | environment.obj, 17,087 bytes, 124 verts |
| collision mesh | collision.obj, 2,780 bytes |
| bounds | [11.0, -18.0, -4.11, 26.7, 28.0, 3.35] |
| source vs baked | **11.67%** mean absolute difference |
| | p95 76/255, max 129/255, median brightness ratio 1.127 |

The source-vs-baked figure needs its context to be useful. It is **not**
comparable to #863's 1.7%: that scene's runtime geometry closely followed its
source silhouette, whereas this one collapses hanging cloth, cords, a ladder,
a drying rack, downpipes and a broom onto 182 triangles at 584 : 1. Broken
down by band, the residual is spread across the frame rather than concentrated
in the cloth, and the largest single contributor was the colour-encoding
defect described in section 14 -- fixing it took the whole-frame difference
from 19.70% to **11.67%** and the brightness ratio from 0.533 to 1.127.

Preview actors and preview-only helpers are excluded from **both** sides of
the comparison, so the difference image measures the bake and nothing else.

---

## 12. ASSET FIREWALL AUDIT

Machine-checked in `asset-firewall-audit.json`. **Verdict: VALID.**

"Pre-existing" is defined by git, not by location: a file is inherited only if
it was tracked at `3d391e05`, the commit this branch was cut from. That matters
because the task itself writes into the repository during promotion, and a
location-based test reports every promoted figure as a breach.

| | |
|---|---|
| visual assets tracked at the base commit | **1819** |
| of those, consumed by this gauntlet | **1** |
| the one consumed | `projects/hichaukitoden-game/assets/character/walker.png` |
| visual assets created during this task | 132 |
| images inside the shipped `town-cleanroom.blend` | 29 (28 task-created material maps + walker.png) |
| violations | **none** |

Three independent checks back the verdict:

1. every image datablock in the shipped `.blend` is resolved and classified;
2. every asset-path literal reachable in the clean-room package source is
   resolved, and none names a file that existed at the base commit except
   walker.png;
3. the full repository visual inventory at the base commit (1819 files) is
   compared against the consumed set.

### Every visual file consumed

**Inherited (1)**

- `projects/hichaukitoden-game/assets/character/walker.png` -- 144x48, six
  24x48 frames. Frame 0 is the protagonist; frames 1-5 supply the NPC
  stand-ins. sha256 `612974eca0db5694ccc39b530008a0e75572039e5c2c208524b4b2e0a9564032`.

**Created during this task (132)**

- 5 CC0 Poly Haven material sets, freshly searched and downloaded (CC0-1.0, verified at https://polyhaven.com/license on 2026-08-20), each
  4 maps at 512 px: `castle_wall_slates`, `cobblestone_05`, `dark_planks`,
  `grey_roof_tiles_02`, `mossy_stone_wall`. Three further sets
  (`plastered_stone_wall`, `distressed_painted_planks`, `old_stone_wall_02`)
  were downloaded, rejected at Phase 1 and never used.
- 2 generated albedos used by the winner (`plaster_bone`,
  `plaster_verdigris`) plus their numerically derived height / AO / roughness.
  A third (`stone_ashlar_fine`) was generated and used in other attempts.
- 9 procedural materials, which are node networks and consume no files.
- every render, swatch, contact sheet, atlas and mesh produced by the run.

Full per-file provenance with source URL, library, license, retrieval date and
sha256 is in `material-provenance.json` (6.00 MiB of retained material maps,
pruned to exactly the 28 the winning `.blend` references).

**If any other pre-existing repository visual asset had been consumed, the
gauntlet would be invalid.** None was.

---

## 13. Lessons for the next clean-room run

1. **Ship the density first.** Six scenes were authored under a disciplined
   "ration the ornament" premise and all six were called empty. Author the
   dense zone first and carve quiet out of it, rather than the reverse.

2. **Native-density material tests pay for themselves immediately.** Four of
   seventeen materials were eliminated or repaired before a single scene was
   built, on evidence that a 1K swatch view would have hidden.

3. **A tileability metric is not optional.** The first `make_tileable` made the
   seam *worse* and looked plausible. Measure the wrap boundary.

4. **A bake proxy must cover its source and nothing else.** This cost four
   bakes and produced a black facade three times, so it is worth stating
   precisely. Two independent rules are involved.

   *Direction.* Blender's cageless selected-to-active bake pushes the ray
   origin **outward** along the target normal by `cage_extrusion` and casts
   **inward**. It therefore only sees source geometry lying *behind* the
   target face, within `max_ray_distance`:

   | placement of a camera-facing proxy | result |
   |---|---|
   | coplanar with the source | degenerate — bakes **black** |
   | behind the source | source never enters the ray path — bakes **black** |
   | too far in front | source beyond `max_ray_distance` — detail missing |
   | slightly in front, in range | correct |

   `RUN_BACK` was coplanar with the facade, then moved behind it, and both
   times the entire back wall baked black. 0.25 m in front fixed it — under
   one native pixel of shift at 27.4 px/m.

   *Extent.* A proxy also occludes everything behind it, for the bake as much
   as for the render. The laundry went through three forms: one box enclosing
   all five lines (2.5 m deep, so the far sheets were out of ray range and
   never baked); then five **full-width** planes, which was worse, because a
   30 m × 4.65 m opaque surface standing in front of the facade hid the whole
   wall and baked black everywhere a sheet did not happen to be; finally one
   small proxy per *sheet*, which is correct.

   The rule: **place a camera-facing proxy slightly in front of its source,
   never coplanar, never behind — and never larger than the source it stands
   for.** A black region in an otherwise valid beauty bake is far more likely
   to be a proxy placement or extent error than a lighting, UV or winding
   problem, and this is very probably the same class of defect as #862's
   "mechanically valid package whose front-facing beauty bake is mostly
   black".

5. **The blind aggregate was useless; the free text was decisive.** Nine
   specimens spanned 0.45 points. Weight the panel's prose, and keep at least
   one harsh evaluator — the two OpenAI passes discriminated, the small
   free-tier model rated everything highly and agreed to walk into six of nine.

6. **The camera's own maths is the layout brief.** Half-width `213(x−0.9)/512`
   and horizon at Y = 70 decide where foreground props can physically exist and
   how far back a facade must sit to show a roofline. Deriving those three
   formulas before authoring saved every scene after 01.

7. **Fix the generic tooling when it is wrong.** Two real defects were found
   and fixed upstream rather than worked around in scene code (§14).

---

## 14. Generic tooling defects found and fixed

1. **`thestra_camera.create_actor_preview` hung every actor upside-down from
   its own feet anchor.** Thestra's resolved orientation (forward +X, right +Y,
   up +Z) is a **left-handed** triple, so the camera basis has determinant −1.
   A quaternion cannot represent a reflection: `matrix_world.to_quaternion()`
   silently discarded it and returned a rotation mapping the plane's local +Y
   to world −Z. Every walker rendered below the floor and was invisible. Fixed
   by adopting the camera's 3×3 basis directly.

2. **`town_environment_pipeline` never gave the bake target atlas UVs.** A
   selected-to-active bake writes into the *active* object's UV layer; the
   runtime mesh is plain boxes that may carry no UV layer at all, or carry
   world-scale tiling UVs shared between objects. Either way the bake lands on
   top of itself. Fixed by smart-projecting the joined target inside the
   pipeline, where producing a bake target belongs.

3. **The exported atlas was scene-referred linear, so every consumer rendered
   it about half as bright as its source.** The bake result is linear
   radiance, and the pipeline wrote that buffer straight to PNG — while LÖVE,
   a browser and Blender's own default all sample a colour PNG as **sRGB**.

   Measured on the finished package, by interpreting the identical file four
   ways (median baked/source brightness, and whole-frame mean difference):

   | atlas colour space | view transform | median B/A | difference |
   |---|---|---|---|
   | sRGB | Filmic | 0.533 | 19.70% |
   | sRGB | Standard | 0.485 | 21.83% |
   | Non-Color | Filmic | 1.126 | 11.69% |
   | **Non-Color** | **Standard** | **1.064** | **10.49%** |

   The file is unambiguously linear. This is very likely the real cause of
   #862's finding 4 — *"the selected environment package is mechanically
   valid but its front-facing beauty bake is mostly black in the LÖVE
   renderer"*. It is a **content** defect, not a schema defect: the file did
   not mean what its consumers assumed it meant.

   The fix needed two parts, and the first one alone did nothing. Calling
   `save_render` under a Standard view transform is correct but is a no-op on
   an 8-bit image, because the byte buffer has already been quantised and
   there is no transform left to apply — the exported bytes came out
   identical. The bake image must also be created with `float_buffer=True`;
   only then does the display transform actually apply on export.

4. `max_ray_distance` was raised from 1.0 to 2.5 m with the reasoning recorded
   in the source, after it silently dropped detail (see lesson 4).

No change was made to the environment-package schema.
