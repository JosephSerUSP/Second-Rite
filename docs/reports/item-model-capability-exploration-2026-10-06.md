# Item-model capability exploration (2026-10-06)

Dated evidence, not a contract. Items whose runtime OBJ had no editable
`.blend` source were rebuilt, each by a different construction method, to find
what the item pipeline and the item viewer can and cannot express. Counts and
observations belong to this snapshot (Blender 5.2.2, branch
`claude/stale-item-models-3d`).

## Selection (batch 1)

"Stale" = an item whose model has no source in `assets/authoring/items/` (175 of
207 items). Picked mechanically from the largest `duplicate_geometry` groups
(`check_item_models.py --report`), one per slot the data has: two consumables,
one each of Weapon / Armor / Accessory.

| Item | Was | Method | Result |
|---|---|---|---|
| Plate Armor | one of 25 armours sharing one blob | superelliptic **loft** with a front keel, live SOLIDIFY shells, Boolean arm openings, mirrored lame pauldrons, UV-overlay **engraving** pass | 2,825 verts |
| Executioner | one of ~10 unlit black slabs | **polygon loft** blade (ground edges + tapering fuller) with a painted albedo, plate crossguard with live thickness | 578 verts |
| Compass | one of 12 brown boxes | lathed case, **painted `map_Kd` dial**, hinged lid, raised needle | 473 verts |
| Mega-Potion | dark bottle blob | dark glass with three Boolean **windows** onto a **Geometry Nodes SDF liquid** (body unioned with foam spheres, filleted) | 2,248 verts |
| Feijoada | one of 11 brown boxes | **Geometry Nodes weighted scatter** of beans / sausage coins / pork on a heaped stew dome | 3,997 verts |

All five compile byte-stably (`compile_item_blends.py --check`), validate
(`VALIDATE OK`), pass the staged unit suite, and change zero G5 frames
(all 108 standard + 1 wide actual frames are byte-identical to an untouched
`origin/main` render on the same machine).


## Batch 2: families and one-offs (21 more sources)

Same selection rule, aimed at the remaining duplicate groups. Two items per
group is not enough to learn whether a method scales, so two **families** were
authored from one parametric scaffold each (the table is a throwaway; every
resulting `.blend` is its own authority afterwards):

| Items | Method |
|---|---|
| 8 rings (Ruby, Sapphire, Emerald, Onyx, Pearl, Peace, Protect, Medicine) | one recipe: torus band + a stone type (prong round cut, step cut, cabochon, pearl, leaf pair, shield plate, cross plate) + metal |
| 8 swords (Iron Knife, Steel Sword, Knight Sword, Adamant Blade, Glass Blade, Coral Sword, Flame Saber, Venom Knife) | polygon-loft blade with per-sword curvature / wave / tip, plate guard, lathed grip, and a **per-sword painted blade texture** from one painter with five styles |
| Mage Robe | cloth loft with sinusoidal folds, mirrored bell sleeves, **additive** UV overlay (stars on black) |
| Star Pendant | faceted dipyramid star; chain = one two-link unit **ARRAY**-ed and **CURVE**-deformed along a hidden Bezier |
| Hazel Wand | tapered **Bezier tube** (per-point radius) with twig curves, leaf cards, nuts |
| Daifuku | **SDF Boolean DIFFERENCE** (outer ball minus cavity minus bite, filleted) around a cream layer and a painted strawberry |
| Pao de Queijo | baked wicker + checked-cloth albedo, puffs with **SUBSURF + DISPLACE (CLOUDS noise)** crusts |

All 21 compile byte-stably (`--check`), G1 and the staged unit suite pass, and
G5 was re-run against an untouched `origin/main` render with all 26 new models in
place: the 108 standard frames and the wide frame are still byte-identical.

### Additional findings

- **Item textures do not tile.** `mesh.lua` loads images with LOVE's default
  (clamp) wrap, so UV > 1 smears the edge texel. Every pattern (basket weave,
  cloth checks, blade) must be painted at full coverage of its UV range.
- **An additive overlay inverts the usual workflow.** `uv add` with light marks
  on black *brightens* the base, so a sparse pattern (stars, glints, runes)
  survives lighting that would crush a `multiply` mark; stars on the robe read at 96 px.
- **A family is cheap once the primitive exists.** The 8 rings and 8 swords took
  one scaffold each plus one tuning pass; the cost is the first one, and the
  `item_kit` primitives (lofts, plates, torus, curve tube) carried most of it.
- **ARRAY + CURVE exports.** The chain is a live modifier stack on the source and
  evaluates into plain geometry at compile time; the guide curve stays hidden.
- **Procedural noise displacement is deterministic** under `--check` (the CLOUDS
  texture with GLOBAL coordinates gives each puff its own crust).
- **SDF Boolean DIFFERENCE with a hollow cavity** works in Geometry Nodes and
  yields soft cut edges with one Fillet iteration.
- **Authoring slips the gates caught**: a grip profile that repeated a ring
  height (zero-width faces; the compile gate rejected it and the viewer fell
  back to the placeholder), and a flat leaf that vanishes edge-on in a pure
  side view (dished instead).

## What the viewer can and cannot do (measured)

1. **There is no pitch.** `modelTilt` rotates about the depth axis, i.e. a
   10 degree *roll in the screen plane*; the turntable spins about vertical. The
   viewer is a pure side view: **nothing is ever seen from above**. The
   "from above / from below" columns of `item-sheet` are rolls, not pitches. A
   bowl or pot interior is invisible, so food must be *heaped* above its rim
   (Feijoada) and a face texture is only seen while that face is toward the camera.
2. **Light caps a camera-facing flat face at about 71%.** Gouraud, one fixed light,
   `0.35 + 0.65 * 0.55`. A texture painted at its "true" colour renders about 30%
   dark; paint face art about 1.4x bright (the compass dial and blade were).
3. **No transparency, no emission.** Glass cannot be see-through.
   Workarounds found: Boolean windows onto an inner body (shipped), or
   **alpha cutout**: the item shader discards `texel.a < 0.01`, so a checker-alpha
   `map_Kd` shows the body through the glass. The stipple is *view dependent*
   (moire against the screen pixel grid), so it was kept as a spike, not shipped.
4. **Two overlay passes per material are enough for real material identity.**
   `sphere add` (matcap sheen) + `uv multiply` (engraving, grime) read clearly at
   96 px: the cuirass emblem, border and fluting survive the dither.
5. **Only `gold` and `ruby` matcaps existed.** `make_matcap.py` now generates
   `steel` and `glass` (and `silver`/`bronze`/`enamel` recipes) deterministically.

## Pipeline limits found

- **Live metaballs do not export.** The shared exporter selects `META` objects but
  `obj_export` silently writes nothing; the failure only surfaces later as a
  missing-file validation. A Geometry Nodes **SDF** graph is the editable
  equivalent and exports normally.
- **Grid-to-Mesh `Threshold` defaults to 0.1**, offsetting an SDF surface 0.1
  outward. Two or more SDF Fillet iterations on a union inflated it a further
  0.14. Merge-by-Distance is needed after Grid-to-Mesh: it leaves coincident
  vertices and zero-area triangles, which the runtime loader rejects (the
  compile gate caught this).
- **A Geometry Nodes result carries no material** unless the tree sets one; the
  MTL then lacks it and a source-declared pass fails loudly (correct behaviour).
- **Overlay-pass textures are outside the compile boundary.** The exporter copies
  `map_Kd` images but never a `pass` image, and `--check` compares only OBJ/MTL
  bytes. `item_textures.py --check` now covers both.
- **`compile_item_blends.py --check` does not compare textures**, only OBJ/MTL.
- Item *sources* must live under `assets/authoring/items`, which made scratch
  spikes need a mirrored path (a sensible guard).

## Tooling added

- `tools/blender/item_kit.py`: scaffold helpers (root + metadata, textured
  materials, `revolve`, `loft`, `loft_polys`, `plate`, `torus`, `curve_tube`,
  `chain_along`, `paint_image`, GN helpers, `cylindrical_uv`, refuse-to-overwrite save). Fixed in-session: `revolve(axis="Y")`
  produced inside-out faces (axis swap is a reflection); this broke a Boolean
  cutter and had lit the first Compass backwards.
- `tools/blender/item_preview.py`: Blender workbench render of a source.
- `tools/blender/item_textures.py` (+ test): authored/promoted/reference check.
- `tools/asset-production/item_review.py`: render/compare through the real viewer.
- `tools/asset-production/make_matcap.py`: procedural sheen maps.
- `runtime/engine/item_model_sheet.lua`: `ITEM_SHEET_CELL` env var for larger
  inspection cells; default output is unchanged.

## Open items

- `check_item_models.py` is red for two linked reasons, both by design: baselined
  violations no longer reproduce (20 after batch 2), and removing members from a
  shared-mesh group makes the *remaining* members read as a NEW group (three such
  groups: armours, small accessories, foods). An earlier revision of this
  report said "no new violations"; that was wrong. The README makes the
  shrink-only baseline rewrite an owner-signed action, so it was **not** rewritten.
- `tools/blender/tests`: `test_bake_receivers` and `test_courtyard_recipe` fail
  identically on an untouched `main`; unrelated to this work.
- 26 items of 175 are done. The remaining armours still share old meshes (the
  loft recipe carried the Mage Robe and Plate Armor and is the likely route);
  remaining foods and small accessories are the other large groups.
