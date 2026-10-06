# Item-model capability exploration (2026-10-06)

Dated evidence, not a contract. Items whose runtime OBJ had no editable
`.blend` source were rebuilt, each by a different construction method, to find
what the item pipeline and the item viewer can and cannot express. Counts and
observations belong to this snapshot (Blender 5.2.2, branch
`claude/stale-item-models-3d`).

Source coverage and gate results do not establish aesthetic success. The owner
has asked that the earlier items remain provisional and that new work improve
on them. The accessory review below follows that direction; none of the batch
counts in this report is an acceptance count.

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

## Open items at the batch-2 snapshot

- `check_item_models.py` is red for two linked reasons, both by design: baselined
  violations no longer reproduce (20 after batch 2), and removing members from a
  shared-mesh group makes the *remaining* members read as a NEW group (three such
  groups: armours, small accessories, foods). An earlier revision of this
  report said "no new violations"; that was wrong. The README makes the
  shrink-only baseline rewrite an owner-signed action, so it was **not** rewritten.
- `tools/blender/tests`: `test_bake_receivers` and `test_courtyard_recipe` fail
  identically on an untouched `main`; unrelated to this work.
- 26 items of 175 have editable sources in the PR. The remaining armours still share old meshes (the
  loft recipe carried the Mage Robe and Plate Armor and is the likely route);
  remaining foods and small accessories are the other large groups.

## Batches 3 and 4: garments, armour and consumable vessels

Follow-up evidence from the same worktree and pinned Blender 5.2.2. The 23
uncommitted garment/armour documents were retained, and all 19 bottle documents
were already present when the follow-up began, contrary to the earlier handoff's
"never run" statement. Only four bottle runtime products had been replaced.
The existing documents were edited directly; no committed source was regenerated.

| Cohort | Items | Construction and refinement |
|---|---|---|
| Cloth, 10 | Black, Cotton, Silk, Sage, Ether and Wind Robes; Holy Vestment; Quarantine, Traveler and Slime Coats | UV cloth lofts, live thickness and mirrored sleeves, hoods/collars, sashes, additive overlays and distinct proportions |
| Armour, 13 | Leather Armor, Ring Mail, Chainmail, Scale Mail, Brigandine, Tin Armor, Fortress Plate, Hero Armor, Adamant Armor, Coral Mail, Flame Mail, Dragon Mail, Cocoon Husk | UV torso lofts, sleeve/shoulder and skirt assemblies, painted materials; editable branching coral curves and flame crest plates distinguish shared family structures |
| Vessels, 19 | Potion, Hi-Potion, X-Potion, Healing Water, Soma, Elixir, Ether, Hi-Ether, Dry Ether, Turbo Ether, Ether Drop, Ether Flask, Soma Drop, Antidote, Eye Drops, Remedy, Hero Drink, Bacchus Wine, Echo Herbs | Profile meshes, live thickness and Boolean windows onto inset liquids, painted label cards, cork/wax/crystal/cage stoppers and distinct vessel proportions |

### Corrections found during verification

The actual corpus report caught identical Coral Mail/Scale Mail geometry. A
prospective strict review, with the 42 cohort names removed from the in-memory
legacy set, exposed 26 cohort violations, including three droppers with no UVs.
Checking against the unchanged legacy list had concealed most of the similar
silhouettes. The final prospective review has **zero violations involving the
42 new items**; every pair of re-authored items is held to the 0.85 threshold.
That includes comparisons against the previously authored corpus, not only
pairs within this cohort. The production baseline was not modified to obtain
this result.

Echo Herbs' original Exact Boolean erased its entire glass shell, leaving a
runtime-pass material absent from the exported MTL. Reducing its thickness from
0.05 to 0.03 retained the shell. A subsequent proportion edit exposed coincident
cut-edge vertices and a degenerate exported triangle; a live Weld modifier at
0.0001 resolved it. Both Boolean cutters remain editable in the source.

All three droppers now have cylindrical UVs. Root proportions, coral branch
curves, flame crest plates, and the herb jar's broad lid are direct document
edits, preserved alongside the original authoring structures.

### Observed checks and limits

- All 42 documents passed `compile_item_blends.py --check` on Windows. After
  the last two proportion edits, those two documents were recompiled and their
  `--check` runs passed again. Source hashes are guarded by the compiler.
- `item_textures.py --check`, `script_index.py --check` (104 scripts), and
  `git diff --check` passed.
- All 42 items were rendered and inspected through the real item viewer at
  96px. [Native review board](item-model-batches3-4-review/sheet96.png).
  Individual four-view strips: `out/review/codex-final42-96/`.
- Staged G1, G2, G3, G4, the unit suite and save/load passed. G1 was repeated
  against a fresh stage after the last two source edits. G2/G3, G4, unit and
  save were run immediately before those final geometry-only proportion edits.
- The actual item corpus gate remains red until an owner-approved baseline
  refresh removes the replaced names from `legacyItems`, drops resolved
  violations and records the smaller surviving legacy groups. The prospective
  corpus contains 75 legacy violations: 8 duplicate groups, 66 no-UV items,
  and 1 shared-file group. None involve this cohort.
- The asset-regression baseline also needs its separate owner-approved refresh,
  generated from a clean checkout of the authored source/product commit.
  Proposals were prepared in `out/work/` from clean commit `8065abaa`, with
  production references left unchanged. Checking the proposed corpus reference
  through the ordinary gate returned `ITEM MODELS OK`; the proposed
  asset-regression reference produced zero diagnostics. The corpus proposal
  reduces 119 violations to 75, removes 42 names from the 141-name legacy list,
  drops 45 resolved keys and adds the surviving Ether Seed/Sigil Ink duplicate
  group as the smaller remainder of its old eight-item group. These are
  proposal checks, not an owner approval or a production-gate pass.
- No G5/G6 references were recaptured. PR #1419's hosted relative run
  `37488502130` stopped before candidate comparison: G5 during base A's
  surface-crop check, G6 during base B's event-modal model-preview readiness.
  These are incomplete captures, with no candidate verdict; existing issues
  #1223 and #1263 cover the capture reliability gaps.
- Linux byte-stability remains unverified. The earlier item-source job stops
  at courtyard tests before that comparison; Windows byte agreement does not
  resolve that missing coverage.

The inherited initial inventory was 175 items without editable sources. The
first two batches added 26 and these cohorts add 42, leaving approximately 107
from that original inventory. Remaining item groups are a follow-up; Curry and
Stew were not touched.

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: stale item models, batches 3 and 4
  base: fd5a2646fa6e027a5f706f1f48eba912362dca1a

## New accessories: eleven provisional sources

Authoring continued from `21c90656` on `codex/stale-item-models-accessories`.
The owner directed this pass toward new items and cautioned against treating
previous batches as successes. This selection replaces ten box placeholders
and the old bell, with construction chosen for each object's function. Previous
documents were left untouched.

[Native 96px review board](item-model-accessories-review/sheet96.png) and
[previous runtime products](item-model-accessories-review/before96.png).
Each row contains four views from the actual LÖVE item viewer. The board is
review evidence, not an owner-approved golden.

| Item | Source handles and visible intent |
|---|---|
| Lantern | Open four-post cage, candle and flame, pitched roof and editable carry-handle Curve. Its contents remain visible through open geometry. |
| Sniper Eye | Sparse live Screw barrel profile, focus-ring knurls, recessed painted reticle and leather strap tabs. |
| Safety Bit | Mirrored plate guards around a faceted garnet, locking crossbar, suspension ring and rear brooch pin. |
| Golem Shard | Irregular fractured mesh, independently tilted cut faces, bevel and broken turquoise conduit Curves following the front surface. |
| Copper Coin | Thick square-pierced flan, raised rim, eight relief petals and rubbed copper/patina paint. |
| Earplugs | Two turned cork plugs with blue flanges and an editable looping safety cord. |
| Iron Nail | Broad battered head and square shank with a bent, tapered point and rust paint. |
| Provoke Badge | Thick sunburst backing and raised scarlet mask with separate eyes, brows, mouth, fangs and rear pin. |
| Rock | Asymmetric faceted mesh with a flattened resting side and a narrow quartz seam. |
| Slime Core | Asymmetric wet rind, editable Boolean opening onto a solid amber seed, soft lobes and a small droplet. |
| Old Bell | Sparse closed wall profile with live Screw, hollow mouth, rolled lip, visible clapper, handle Curve and broad oxidation paint. |

### What native review changed

The first coin and badge exports exposed collapsed bevel faces. Their thin
reliefs now use bevel widths below half the plate thickness, and the runtime
validator passes. No validator tolerance was loosened.

The first shard looked too regular. Direct edits chipped its perimeter and
tilted its fracture planes; its small conduit was repositioned to follow those
surfaces. The rune remains subtle at 96px. Earplug tips and the rock's quartz
seam are also small at that size; they are refinement candidates, not evidence
that the work has been accepted.

The bell's missing paint exposed absent UVs on its turned body despite the
coarse whole-item UV check passing. Sparse Screw profiles now declare a UV
layer before evaluation in all four new sources using that modifier. The
evaluated bell body and clapper span both UV axes from 0 to 1. A stale packed
paint copy and a broken optical image path were corrected in the source;
painted PNGs were verified separately from OBJ/MTL recompilation.
The broader mixed-mesh painted-UV verification gap is tracked in
[#1431](https://github.com/JosephSerUSP/Second-Rite/issues/1431).

Lantern is already a registered Model, so previewing a replacement OBJ alone
initially displayed the old compiled bundle. Its authored recipe now binds
each new material appearance to a separate slot, retaining `frame` and `body`.
The canonical stage exporter regenerates its compiled bundle. The final
candidate and canonical shipping preview boards have identical RGB pixels.

### Observed verification and remaining limits

- All eleven sources pass Windows Blender 5.2.2 `compile_item_blends.py --check`;
  the compiler requires unchanged source hashes and matching OBJ/MTL bytes.
- `item_textures.py --check`, `script_index.py --check` and `git diff --check`
  pass. The four authored PNGs have byte-identical promoted copies.
- All eleven were inspected in the real viewer at 96px. A strict in-memory
  corpus review compares them against all 207 referenced models, removing all
  currently sourced names from the legacy exemption. No violation involves
  these eleven; pairs of sourced items face the 0.85 silhouette threshold.
- Fresh staged G1, G2, G3, G4, unit and save/load pass. Unit includes 29
  `test_model_resource` checks of Lantern's OBJ/compiled Model uploads,
  bounds, item rendering at multiple dimensions/angles, world rendering and
  instance transport. The suite reports seven unrelated world-effect
  assertions unavailable because this stage has no native Effekseer shim.
- The actual corpus gate remains red: 58 accepted keys no longer reproduce.
  Current records comprise 6 duplicate groups, 55 UV-less items and 1 shared
  file group. The smaller Ether Seed/Sigil Ink legacy group is still new
  relative to the old accepted group. No corpus reference was rewritten.
- Asset contract passes; asset regression remains red for 53 changed model
  records, including the 42 inherited products and these eleven replacements.
  Its reference remains unchanged. Earlier `out/work/` baseline proposals
  describe the parent cohort and are stale for this branch.
- No G5/G6 references were recaptured. Those gates were not run for this
  accessory pass. Linux source/product byte stability and owner visual
  acceptance remain unverified.

Source absence falls from 107 to 96 items in the original stale inventory.
That is a coverage measurement, not a quality verdict. Sources carry explicit
provisional review metadata. Curry, Stew and all earlier source documents
remain unchanged.

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: stale item models, new accessories
  base: 21c90656fd59da77dfed1fe70081b4a752ab04c8

## Owner feedback follow-up: incense and armour shoulders

The owner liked the accessory results and flagged the earlier armour shoulders
as weak. This pass adds four new incense sources and edits fourteen existing
armour documents directly, including Plate Armor from the first cohorts.
It starts at `9e40e7e9` on `codex/stale-item-models-incense-shoulders`.

[Four incense models at 96px](item-model-incense-shoulders-review/incense96.png),
[armour shoulders before/after](item-model-incense-shoulders-review/shoulders-before-after96.png),
and [complete native board](item-model-incense-shoulders-review/sheet96.png).
The comparison retains the same four native views at their original pixel size.
These new incense models and shoulder revisions await owner review.

| New item | Authored structure |
|---|---|
| Power Incense | Three vermilion sticks with ash/ember tips in a squat footed copper brazier, soot bed and ash poker. |
| Guard Incense | Square footed censer, separate roof strips leaving actual ventilation slots, green enamel, shield clasps and a visible resin cone. |
| Magic Incense | Violet spiral Curve on a silver fork and tripod, with an ash dish and blue ember point. |
| Spirit Incense | Hollow turned brass bowl, open petal cage around resin grains, three linked suspension chains and a carry loop. |

The incense sources mix sparse Screw profiles with declared cylindrical UVs,
fabricated plates and frames, editable paths, and linked-looking mesh rings.
Their game effects and data entries remain unchanged.

### Shoulder revision

Shoulder shells now span from the upper torso across a front/back arch and
fall over the upper arm. This replaces the old tipped-dome caps where present
and adds shoulder coverage where absent. The changed documents are Leather
Armor, Ring Mail, Chainmail, Scale Mail, Brigandine, Tin Armor, Plate Armor,
Fortress Plate, Hero Armor, Adamant Armor, Coral Mail, Flame Mail, Dragon Mail
and Cocoon Husk.

Leather and brigandine use bound folded shoulders and rivets; mail uses draped
caps and weighted edges. Plate variants use layered shells and visible overlap
lips, with broader layered coverage on Fortress Plate and gilded lames on Hero
Armor. Coral has branching shoulders; Cocoon Husk has overlapping lateral
carapace lobes. Dragon Mail received a wider stance and swept-back shell after
its first revision collided with Scale Mail under the strict silhouette check.

Old shoulder objects remain hidden construction guides. The new shells retain
editable meshes and live Mirror symmetry. Repeat exports exposed intermittent
UV rounding and deduplication differences in the new Solidify/Bevel geometry:
the changed vertex positions were identical, but UV indices and last decimal
digits were unstable. Thickness and bevel were therefore materialized once in
the authoritative source, with dyadic per-corner UVs. Copies of the original
outline/modifier structures remain as hidden guides. Nothing was regenerated
from an external recipe.

### Observed checks and limits

- All eighteen affected documents pass Windows Blender 5.2.2 compile `--check`,
  preserving source hashes and matching shipping OBJ/MTL bytes.
- Brigandine and Chainmail match in four additional repeat exports each after
  UV stabilization. This is bounded Windows evidence, not Linux byte proof.
- Texture/reference checks, the 104-script Blender index and diff checks pass.
- Native 96px candidate and canonical shipping boards have identical pixels;
  the final board was inspected after UV stabilization.
- Strict in-memory corpus comparison against all 207 models has zero findings
  involving these eighteen. Sourced pairs face the 0.85 silhouette threshold.
- Fresh staged G1, G2, G3, G4, unit and save/load pass. Unit still reports seven
  unavailable native Effekseer world-effect assertions.
- Actual corpus remains red: 63 accepted keys no longer reproduce; remaining
  records are 5 duplicate groups, 51 UV-less items and 1 shared-file group.
  The inherited smaller Ether Seed/Sigil Ink group remains new relative to
  the accepted old group. Asset contract passes; asset regression remains red
  for 58 changed model records. Production references remain unchanged.
- Hosted #1432 results now expose two integration regressions from the new
  Lantern: the Model server test hardcodes its old two slots, and the generic
  native/Three proof uses the shipping item despite Three deliberately
  refusing its overlay materials. [#1434](https://github.com/JosephSerUSP/Second-Rite/issues/1434)
  records these failures and the controlled-fixture follow-up. They are not
  described as unrelated failures or as passing checks here.
- G5/G6 were not run or recaptured. Linux byte stability and acceptance of
  the new incense/shoulder cohort remain unverified. Mail texture is still
  busy at 96px; the board supports judging whether its new shoulder mass is
  sufficient.

Items without editable source fall from 96 to 92. That count measures source
coverage. The accessory sources, garments, Curry and Stew are unchanged in
this pass, as are gameplay, engine code and the Lantern recipe.

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: incense and armour shoulder feedback
  base: 9e40e7e9b87622519a8cf1633f056a3b08f44027

## Next food cohort: deformation, instancing and shaped sections

The owner liked the preceding results and requested another batch using new
techniques. This pass starts from `b55f09b3` and adds nine previously absent
source documents. These are new food studies awaiting owner review, not an
assertion that prior sources or this cohort have completed visual acceptance.

The review is available as a [gameplay-angle board](item-model-food-studies-review/gameplay96.png),
a [same-pose before/after comparison](item-model-food-studies-review/before-after96.png),
and the [complete native sheet](item-model-food-studies-review/sheet96.png).
Every cell is rendered by the actual LÖVE item viewer at 96px. The smaller
board uses the first two sheet poses, at gameplay tilt. The other two poses
are diagnostic rolls: inspecting the shader confirms local-Y rotation then
Z-axis yaw, so their labels/comments must not be taken as proof of an elevated
camera or a visible top surface. No engine camera change was made here.

| Food | Construction and useful source handles | Resolved triangles |
| --- | --- | ---: |
| Coxinha | Pinched sculpt in the Basis, rounded shape-key alternative, Geometry Nodes breadcrumb instances, folded paper sleeve | 1,452 |
| Onigiri | Rounded triangular rice volume, separate front/back/bottom nori wrap, editable rice-grain seeds and realized Geometry Nodes instances | 1,700 |
| Moa Tamagoyaki | Rounded rectangular omelette sections and two cut slices with spiral layer relief; bamboo tray and pick | 2,736 |
| Mooncake | Twelve-lobed pastry loft, raised six-petal Curve seal and side flutes; displayed on its edge to expose the seal in a side viewer | 2,436 |
| Mochi | Three rice cakes with separate live 3-by-3-by-3 Lattice cages, pink/white/green materials and a bamboo skewer | 1,288 |
| Sushi | Rice grains, a salmon Curve with a broad rectangular bevel profile, fat stripes, and a front-facing cut nori roll with cucumber/salmon cores | 2,088 |
| Tempura | Two tapered shrimp Curves, red tail plates, live Array + Curve breadcrumb paths, additional surface-bound grain instances and folded paper | 1,732 |
| Kimchi | Corrugated, anisotropic Curve sections with adjustable path tilt, pale leaf ribs, scallions and a hollow stoneware dish | 3,856 |
| Mandrake Tempura | Editable branching mesh skeleton with live Skin and Subdivision modifiers, a tapered leaf crown, face and fried crumbs | 1,272 |

The grain systems use authored point coordinates and a hidden UV-bearing
prototype, then explicitly Realize Instances. Their placement is not resampled
randomly at compile time. Kimchi and Sushi retain independent editable bevel
profiles. Mochi keeps its live deformation cages, and the mandrake keeps its
branch skeleton and radii. Fixed food colours use ordinary material `Kd`;
there are no new PNGs or runtime material passes in this cohort.

### Observed limits and direct source refinements

- Static item export resets copied shape-key values to zero through the shared
  variant exporter. The first Coxinha therefore looked pinched in Blender but
  compiled as its spherical Basis. The source was edited directly so that its
  pinched sculpture is the Basis, with the rounded version retained as a
  zero-value alternative. [#1436](https://github.com/JosephSerUSP/Second-Rite/issues/1436)
  records the silent mismatch and the static-item policy follow-up. This pass
  does not change shared exporter semantics.
- Bevel width reaching half the thickness of paper/nori produced collapsed
  runtime faces. Thin components now have narrower bevels. Onigiri's rounded
  thickness was materialized once and degenerate cap edges dissolved in its
  authoritative mesh; a hidden original outline/modifier guide remains.
- Kimchi sections were widened and rolled, and their tips folded down after
  native review. Tempura gained larger surface-bound crumbs where its first
  coating read too sparsely. Kimchi's small corrugations remain noisy at 96px;
  Sushi's salmon and omelette slice layers are clearest in their front poses.
  The boards expose those limits for owner judgment.
- Dense relief points initially generated 10,216 triangles for Tamagoyaki and
  8,196 for Mooncake. Reducing the already dense Curve interpolation and tube
  sections brings them to 2,736 and 2,436, respectively, while retaining the
  spiral and flower in the reviewed native-size images. The point controls
  themselves remain editable.

Once saved, each `.blend` was edited directly. Scaffolding and recorded surgery
scripts stay in ignored `out/work/` and must not be rerun over these documents.
The previous source documents, armour, garments, accessories, incense, Curry
and Stew are unchanged. Item effects, recipes, game data and runtime code are
unchanged in this pass.

### Verification and remaining boundaries

- All nine final sources pass read-only `compile_item_blends.py --check`:
  source hashes remain unchanged and compiled OBJ/MTL match shipping bytes.
  An earlier all-nine independent candidate re-export also matched, before the
  two relief sampling reductions; final `--check` verifies those reductions.
- Texture/reference check, script index and diff checks pass. Canonical
  shipping and final candidate native 96px boards have identical RGB pixels.
- The final strict in-memory corpus review compares all 207 models, removing
  sourced names from the legacy set. It reports zero findings involving these
  nine, with the 0.85 threshold applying to pairs of sourced items.
- Fresh staged G1, G2, G3, G4, unit and save/load pass. The unit suite reports
  seven unavailable native Effekseer world-effect assertions, not coverage of
  those assertions. No G5/G6 run or reference recapture was performed. Linux
  source/product byte stability remains unverified.
- Production baseline files are unchanged. The actual corpus check remains
  red: 67 accepted keys no longer reproduce, with five remaining duplicate
  groups, 48 UV-less models, one shared-file group, and the inherited reduced
  Ether Seed/Sigil Ink group reported as new. Replacing three members of the
  old duplicate food group similarly makes its five remaining legacy members
  a new group key; none of those members belongs to this cohort. The asset
  contract passes, while asset regression remains red for 67 changed Model
  records across the stack. These do not establish owner baseline approval.
- The inherited Lantern integration failures in #1434 remain separate merge
  blockers. This food-only pass does not alter its shipping recipe, the Model
  server fixture, or the shared native/Three proof.

Items lacking editable source fall from 92 to 83. This measures source coverage;
it is not a count of visually accepted products.

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: nine food sources with new construction techniques
  base: b55f09b311f06b2a006742b9da3ad35d2a0d2868

## Wearables: intentional normals, material separation and painted UVs

The owner requested more attention to which faces should be smooth, and to
materials and textures. This cohort starts from `8275ec85` and gives ten more
items editable sources. Earlier source documents and their products remain
unchanged. These wearables await owner visual review; the source inventory is
not a visual-acceptance count.

Review the [gameplay-angle board](item-model-wearables-review/gameplay96.png),
[previous/new comparison](item-model-wearables-review/before-after96.png),
[normal controls](item-model-wearables-review/normals96.png),
[complete sheet](item-model-wearables-review/sheet96.png), and
[twelve texture atlases](item-model-wearables-review/texture-atlases.png).
The native cells are 96px. The first two poses use gameplay tilt; the later
sheet poses retain the diagnostic roll limitation described above.

| Item | Surface and construction choices |
| --- | --- |
| White Cape | Smooth draped grid with a scalloped hem, ivory satin weave and embroidered border; flat thickness rims, smooth piping and brass clasp |
| Ribbon | Rose woven silk, broad folded loop sections softened by a live Subdivision modifier, a wrapped knot and two hanging tails; flat cut rims |
| Thief Glove | Smooth rounded leather palm, curved soft fingers, stitched cuff and back seams; planar loft caps stay flat |
| Sprint Shoes | Rounded leather uppers, canvas tongues and laces, small polished eyelets; sharp cap boundaries, flat rubber grip blocks and firmer sole edges |
| Moa Saddle | Scooped leather seat, quilted skirt atlases, raised pommel/cantle and iron stirrups; smooth broad panels and flat cut rims |
| Chef Hat | Smooth gathered linen crown, firm cylindrical band with a sharp cap boundary, weave and band seams |
| Apron | Striped ecru canvas on a smooth folded bib/skirt, neck loop and waist ties, separate pocket and stitching; flat cut edges |
| Black Belt | Dark cotton weave and stitches, substantial knot and unequal tails with embroidered rank bars; flat strap rims and knot caps |
| Cat Bell | Smooth turned brass with wear/patina atlas, hollow interior and two actual Boolean slots, clapper, attachment loop and rose bow; flat slot-cut faces |
| Moa Harness | Teal leather yoke, crossed braces and lower girth with stitched atlas edges; smooth broad strap faces, flat cut rims and separate brass buckles |

### Normals are observed runtime evidence

The OBJ exporter writes normals, and `engine/geometry/obj_source.lua` passes
the authored corner normals into the neutral Model. The item shader uses them
for lighting and sphere-pass sampling. Consequently, choosing smooth faces in
the source can change the native render without changing its silhouette.

The new sources retain named surface roles and authored sharp-edge boundaries.
Rounded leather and soft cloth use smooth broad faces; loft end caps are
explicitly flat. Strap thickness faces use their separate rim material and
flat normals. For live Solidify cloth, a small Geometry Nodes material-selection
step sets only the generated cut-edge faces flat. Rubber grip blocks are flat,
while curved metal loops and piping stay smooth. Bell Boolean cut faces retain
flat shading around the smooth outer shell.

For example, read-only evaluated inspection reports Cape cloth at 144 smooth
faces out of 180, Chef Hat's band at 24/26 and crown at 192/194, and the bell
shell at 296/312. Each of the eight shoe grip blocks has zero smooth faces.
Sharp-edge splitting additionally protects planar boundaries.

Throwaway source copies provide a flat Mesh/Screw control for all ten items;
Curve piping is held unchanged. The controls and candidates have identical
triangle positions, UVs and MTL bytes. Native gameplay-pose comparisons change
3,250 pixels for Cat Bell, 3,168 for Chef Hat and 3,009 for White Cape across
their first two 96px cells. The committed board exposes the actual lighting
differences. Those counts prove a visible normal change, not aesthetic approval.

### Texture and material evidence

Twelve opaque 128-by-128 atlases encode linen/cotton weave, satin/ribbon grain,
canvas stripes, leather pores and stitches, saddle quilting, and brass wear.
UVs are bounded and coherent over each broad panel/loft surface, rather than
repeating a complete atlas on every quad. New loft caps receive a real planar
atlas mapping; the shared scaffold's default collapsed cap coordinates would
not support painted cap detail. Plain edge, seam, finger and grip materials
retain controlled colours for those small components.

The scoped runtime audit examines every face using `map_Kd`, by material. All
twelve painted materials have zero missing UVs, zero collapsed UV triangles
and zero coordinates outside the atlas. Source atlas, compiled copy and
shipping copy bytes match for all twelve images. Every source image path is
portable and relative to its document (`//_textures/<filename>`).

Satin/ribbon sheen and metal highlights use explicit low-strength runtime
sphere passes. The material treatment is carried by colour, image and declared
pass data; this pass makes no claim that Blender's Principled roughness or
metallic settings become runtime BRDF controls. The native texture filter,
lighting cap and dithering still limit fine weave/pores at 96px. Dark glove
and belt detail remains subtle; coloured seams, silhouette and the comparison
boards support owner judgment.

The [surface evidence](item-model-wearables-review/surface-evidence.json)
records source hashes, evaluated smooth-face counts, texture hashes, painted
face UV results and the ten normal controls without machine-specific absolute
paths. The per-material audit is scoped evidence for these assets; the general
UV-coverage gate gap remains tracked in #1431.

### Observed verification and remaining boundaries

- All ten final sources pass read-only `compile_item_blends.py --check`, with
  source hashes unchanged and OBJ/MTL bytes matching shipping. A separate
  candidate repeat export also matched all ten before the final relative-path
  normalization; final `--check` verifies the normalized sources.
- Texture/reference check, script index and diff checks pass. Canonical
  shipping and final candidate native boards have identical RGB pixels.
- Strict prospective review of all 207 models finds zero violations involving
  these ten; sourced pairs face the 0.85 silhouette threshold.
- Fresh staged G1, G2, G3, G4, unit and save/load pass. Seven native Effekseer
  world-effect assertions remain explicitly unavailable. G5/G6 were not run or
  recaptured; Linux byte stability remains unverified.
- Actual corpus remains red for 79 accepted keys no longer reproducing, with
  three duplicate groups, 38 UV-less models and one shared-file group left.
  The inherited reduced Ether Seed/Sigil Ink and remaining legacy food group
  still appear as new group keys. Asset contract passes; asset regression is
  red for 77 changed Model records across the stack. Production baseline files
  are unchanged, and owner baseline/merge approval is still absent.
- Lantern's inherited integration blockers remain tracked in #1434. The static
  item shape-key policy follow-up remains #1436. This pass changes no runtime
  code, game data, recipes, earlier sources or baseline references.

Source absence falls from 83 to 73 referenced items. Once-only scaffolds,
recorded source surgery, normal-control documents and local verification logs
remain ignored under `out/work/`; the saved production documents are authority.

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: ten wearables with intentional normals and painted materials
  base: 8275ec857b4567977422620c41f21e116b28ebd9
