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

## Arcane objects: carved forms, material contrast and orientation evidence

This cohort adds nine editable sources, stacked on the wearable work at
`5c7b82771712c457bcf9b955b13a23189a3ee50e`. Earlier products are comparisons;
source coverage and technical passes do not establish artistic acceptance.
The owner requested deliberate smoothing and more attention to materials and
textures. These objects remain provisional pending owner visual judgment.

The [native gameplay board](item-model-arcane-review/gameplay96.png) shows two
96px gameplay poses per object. The [prior/new comparison](item-model-arcane-review/before-after96.png)
and [full sheet](item-model-arcane-review/sheet96.png) retain the usual four
viewer poses. The [cardinal-yaw board](item-model-arcane-review/yaw96.png) uses
0, 90, 180 and 270 degrees, all at the gameplay 10-degree roll. This is a
stage-only native probe; production rendering code is unchanged. It is not
evidence from an elevated or below-object camera.

| Item | Authored construction | Native triangles |
| --- | --- | ---: |
| Mystic Egg | Smooth organic shell, two rounded physical apertures, inset jade core, Curve aperture lips and branching ridge; live shell thickness and selected flat cut rims | 3,384 |
| Golden Egg | Smooth gilded egg, eight curved chasing lines, equatorial collar and three-foot cradle | 3,888 |
| Glass Bead | Live off-axis closed Screw profile with an actual drilled bore and recessed dark throat | 1,120 |
| Thrice-Blessed Bead | Drilled opalescent bead, three linked Curve leaf bezels and three separate flat-cut prayer stones | 1,716 |
| Vitality Seal 1 | Uneven poured wax, actual recessed leaf impression and parchment tail; repaired resolved impression mesh with hidden cutter evidence | 1,360 |
| Vitality Seal 2 | Chipped polygonal stone shield, crisp bevel planes, dark incised leaf treatment and twin ivory vein inlays | 1,456 |
| Vitality Seal 3 | Pierced oval metalwork, paired leaf tracery, linked gem claws and smooth jade cabochon | 2,368 |
| Mars Emblem | Thick forged sunburst, raised rim/flame forks and flat-cut garnet | 1,032 |
| Mercury Crest | Editable tapered open crescent, pierced curls, smooth blue cabochon and three faceted hanging drops | 3,404 |

The seal tiers progress through wax, carved stone and pierced metalwork rather
than relying on palette alone. Openings and raised relief are actual geometry.
Smooth shell/glass/cabochon surfaces contrast with flat cut stone, forged faces,
gem facets and stamped planes. The Mystic Egg's generated window walls use a
material-selection Geometry Nodes step to remain flat while both shell
surfaces stay smooth. Sharp boundaries protect the wax face/rounded edge.

### Surface construction and measured controls

Fourteen opaque 128x128 [atlases](item-model-arcane-review/texture-atlases.png)
provide restrained shell veining, warm chased gold, clouded lampwork glass,
radial wax pooling, stone veins, patinated bronze, brushed silver and enamel.
Broad variation and edge bands carry more weight than random fine noise.
Shell UVs follow the surface rings; torus UVs unwrap both major and minor
circles; carved stone/bronze planes use bounded object-wide projections.
Existing materials use plain colours for small unpainted cut faces and tips.

The every-painted-face audit reports zero missing, collapsed or outside-atlas
UV findings for all fourteen painted materials. Source, compiled and shipping
PNG bytes match for every atlas. Source references use `//_textures/<filename>`.
Painted open Curve endpoints meet other geometry; exposed Mercury tips have
plain rounded endcaps. This avoids pretending the Curve generator's collapsed
cap UVs can support painted detail. The general UV gate gap remains #1431.

The [normal comparison](item-model-arcane-review/normals96.png) holds geometry,
UVs and MTL bytes identical for Glass Bead, Golden Egg and Vitality Seals 1/3.
Only Mesh/Screw smoothing changes; Curve normals remain unchanged. At the two
gameplay poses, changed pixel counts are 3,878, 2,620, 950 and 1,849 respectively.
All controls render the full nine-item list, preserving cell backgrounds and
draw order. Counts demonstrate visible effects, not aesthetic superiority.

The [material comparison](item-model-arcane-review/materials96.png) removes
only declared runtime overlays for the same four objects. Geometry and UVs
remain identical, and MTL differences consist only of removed `pass` lines.
Changed gameplay pixels are 2,848 for Glass Bead, 4,043 for Golden Egg and
1,775 for Seal 3. The wax seal is an unchanged zero-pixel control because it
uses no overlays. Appearance uses the supported opaque colour/texture and
low-strength sphere-pass vocabulary; this does not demonstrate transparency,
refraction, anisotropic shading or Blender Principled BRDF parity.

The [surface evidence](item-model-arcane-review/surface-evidence.json) records
source/product hashes, texture hashes, evaluated smooth-face counts, UV results,
triangle counts and controls without machine-specific absolute paths.

### Authoring corrections and visual limits

The first wax Boolean impression exported a degenerate collinear triangle.
The authoritative source was edited directly: the evaluated impression was
materialized once, merged/dissolved, triangulated and checked, with hidden
cutters retained as construction evidence. It is not a live Boolean result in
the final source. Stone/emblem thickness and bevels were also materialized
once to give generated faces usable UVs; hidden outlines remain available.
Golden Egg's chasing curves were simplified from 12,144 to 3,888 triangles.
The egg apertures were rounded and their lips aligned to the real boundaries.

At 96px, silhouettes, apertures and material masses read more strongly than
fine grain. The flat seals and emblems intentionally become narrow edge-on;
their backs do not repeat every front motif. The yaw board exposes that limit.
Glass remains an opaque stylization. Small prayer stones and shallow chasing
remain subtle. Native evidence supports assessment, not a claim of acceptance.

### Observed verification and remaining boundaries

- All nine final sources pass read-only shipping `compile_item_blends.py
  --check`; source hashes remain unchanged and OBJ/MTL bytes match. An
  independent repeat also matched all nine final candidate products.
- Texture/reference check, script index, asset contract and diff checks pass.
  Native shipping/candidate board RGB pixels match exactly.
- Strict prospective comparison against all 207 item models finds zero cohort
  violations, with the 0.85 silhouette threshold for sourced pairs.
- Fresh staged G1, G2, G3, G4, unit and save/load pass. Seven native Effekseer
  world-effect assertions remain explicitly unavailable. G5/G6 were not run
  or recaptured, and Linux byte stability remains unverified.
- Actual corpus remains red for 80 accepted keys no longer reproducing;
  three duplicate groups, 37 UV-less models and one shared-file group remain.
  Asset regression remains red for 86 changed Model records across the stack.
  Baseline files remain unchanged; reconciliation and merging are owner calls.
- Inherited Lantern integration blockers remain #1434; static item shape-key
  policy remains #1436. This cohort changes no runtime code, game data, recipes
  or previously authored source documents/products.

Referenced source absence falls from 73 to 64 of 207 item assignments. This
counts coverage only. Once-only scaffolds, recorded direct edits, throwaway
controls and logs remain ignored under `out/work/`. Production `.blend` files
and their source images are authority; control products must never be promoted.

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: nine arcane objects with carved forms and controlled surface evidence
  base: 5c7b82771712c457bcf9b955b13a23189a3ee50e

## Shadow volumes: sculpting a solid from three drawings

The owner requested an unorthodox construction technique with reusable tooling
value. Six new sources are stacked on the arcane cohort at
`744ee09eb01b3fa265691afa00ae33bf127c8353`. Earlier products remain comparisons;
technical coverage does not establish visual acceptance.

Each main body is the intersection of three extruded polygon drawings: front
X/Z, side Y/Z and top X/Y. Drawn cut stencils remove actual through openings.
The named planar controls, Boolean intersections, bevels and generated UVs
remain live in the saved source. This is a small visual-hull authoring grammar,
without a voxel grid or new runtime renderer. It provides shape constraints,
not exact reconstruction of an object from its silhouettes.

The [saved-controls/native board](item-model-shadow-review/shadows-to-native.png)
plots the actual control vertices inspected from the final documents and pairs
them with two native 96px gameplay poses. The [gameplay board](item-model-shadow-review/gameplay96.png),
[prior/new comparison](item-model-shadow-review/before-after96.png),
[usual four poses](item-model-shadow-review/sheet96.png) and
[cardinal-yaw probe](item-model-shadow-review/yaw96.png) expose different aspects
of the result. The yaw probe changes only a throwaway staged renderer to
0/90/180/270 degrees at gameplay roll; the camera remains a side view.

| Item | Construction and surface choice | Native triangles |
| --- | --- | ---: |
| Obsidian Shard | Three asymmetric cut profiles, crisp flat planes, fine bevel rims, dark conchoidal bands and restrained glass sphere pass | 530 |
| Ember Bit | Charred flat-cut hull, real drawn opening, smooth recessed opaque hot core, separate char/core atlases | 1,432 |
| Cinder Ruby | Unequal cut profiles with flat gemstone facets, warm internal bands and restrained ruby sphere pass | 578 |
| Adamant Weight | Thick intersected forged mass, actual carry slot, flat faces, directional metal texture, pale raised face marks and restrained steel sphere pass | 1,036 |
| Melted Wax | Pooled three-profile hull, live subdivision and relaxation, smooth faces, broad wax colour variation and plain curved wick | 5,244 |
| Moth Scale | Thin asymmetric intersected scale, smooth faces, directional painted ridges and plain curved quill | 886 |

### Durable tool and measured geometry

[Shadow-volume authoring](../../tools/blender/SHADOW_VOLUMES.md) documents four
routes: host-only spec validation, labelled three-view SVG preview, new-source
construction through the pinned Blender launcher, and read-only inspection of
saved sources. Outputs refuse overwrite. After first save, the `.blend` is
authority; initial JSON drawings are not consulted by compilation. Authors
can reuse `build_volume` and `inspect_body` independently of ignored scaffolds.
Both entry points are registered in the authoring route and script catalogue.

Nine host tests cover malformed polygons and settings, winding normalization,
projection bounds, concave controls, preview semantics and overwrite refusal.
One real Blender integration test exercises several independent facts:

- A known 2x4x6 intersection has volume 48; moving one saved side-control edge
  changes it to 42 without rebuilding from its initial spec.
- A 0.4x0.6 stencil through depth 4 removes volume 0.96, leaving 47.04.
- Valid projections with overlapping coordinate bounds can still produce an
  empty intersection; construction rejects that evaluated case.
- Generated faces have noncollapsed bounded UVs after live construction.
- Exporting with the root translated to (5,7,11) retains the pierced volume
  and remaps modifier controls into the temporary export hierarchy.
- An asymmetric bevel fixture exports through the real OBJ/runtime validator
  without the rounded-position degenerate triangles seen during authoring.

The public example also builds, inspects and compiles successfully. Existing
asset-core host tests (15) and item-compiler host tests (16) pass; canonical
vendor synchronization and integrity checks pass.

The shared exporter now remaps hierarchy-owned modifier object pointers when
normalizing a translated root. At exactly zero translation it retains the
existing dependencies: indiscriminate remapping changed an older Mirror-based
product's rounded OBJ coordinates despite equivalent transforms. The final
conditional behavior preserves that observed zero-shift product comparison.
This is an exporter correction exercised by the geometry test, not a claim
that the entire historical corpus is byte-stable.

### Surface evidence and limits

Seven opaque 128x128 [atlases](item-model-shadow-review/texture-atlases.png)
provide directional metal grain, dark fractured bands, ruby colour strata,
char and hot-core contrast, pooled wax variation and scale ridges. Main cut
stone/forged hulls deliberately retain flat normals. The ember core, wax and
scale surfaces use smooth normals; small plain-colour marks, wick and quill
remain separate assemblies. Sphere overlays use the existing low-strength
runtime vocabulary. The ember's bright inset is opaque painted geometry;
this is not evidence of emission or transmitted light.

All exported faces using the seven painted materials have zero missing,
collapsed or outside-atlas UV findings. The live surface graph projects
dominant face planes into current object bounds, including faces created by
Booleans and bevels. Source, compiled and shipping PNG bytes match. The
[surface evidence](item-model-shadow-review/surface-evidence.json) records
source/product hashes, actual saved control polygons, evaluated bounds and
volumes, face smoothness, triangle counts and material-level UV results without
machine-specific absolute paths. Read-only source inspections preserve hashes.

Box projection can produce pattern seams. Silhouette intersections cannot
recover concavities hidden from every drawing; those need explicit cutters or
further source modeling. Large control edits must also expand the working
Solidify envelope. Weld steps around bevels, triangulation and a near-zero-area
filter address almost coincident Boolean corners; runtime validation still
decides whether an OBJ is valid at its six-decimal position precision.

Melted Wax remains angular in silhouette at 96px despite subdivision and
relaxation, and has the highest triangle cost in this cohort. Smooth normals
alone cannot turn a constrained polyhedral envelope into a convincing poured
mass. It is the clearest visual limitation of this technique here. Moth Scale
becomes very narrow edge-on; small weight marks and fine grain remain subtle.
The carry slot and ember opening remain readable physical cuts. These are
review observations, not an owner acceptance claim.

### Observed verification and remaining boundaries

- All six sources pass read-only shipping `compile_item_blends.py --check`.
  Separate repeat exports are byte-identical; source hashes remain unchanged.
- Final native shipping/candidate boards have identical RGB pixels. Texture
  reference, script catalogue (106 entries), diff and asset contract checks
  pass. Strict prospective comparison against all 207 models reports zero
  cohort violations under the 0.85 sourced-pair silhouette threshold.
- Fresh staged G1, G2, G3, G4, unit and save/load pass. Seven native Effekseer
  world-effect assertions remain explicitly unavailable. G5/G6 were not run
  or recaptured; Linux byte stability remains unverified.
- A prior-source corpus `--check` stops at Chrysalis Sigil's known rounded
  normal mismatch (#1355/#1369). Isolated original/current exporter runs
  produce identical OBJ bytes to each other and both differ from shipping at
  that normal. The check does not establish full corpus byte stability, and
  that earlier source/product was not rewritten.
- Actual corpus remains red for 82 accepted keys no longer reproducing, with
  three duplicate groups, 35 UV-less models and one shared-file group left.
  Reduced inherited groups remain new keys. Asset regression remains red for
  92 changed Model records across the stack. Baselines are unchanged; their
  reconciliation and merging remain owner decisions.
- Inherited Lantern integration blockers remain #1434; the general painted-UV
  gate gap remains #1431; static item shape-key policy remains #1436. This pass
  changes no runtime code, game data or earlier production documents/products.

Referenced source absence falls from 64 to 58 of 207 item assignments. That
measures coverage only. Initial six-item scaffolds, direct-edit helpers,
source backups and verification logs remain ignored under `out/work/`; the
general tooling and its neutral example are durable repository files.

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: six shadow-sculpted items and reusable silhouette tooling
  base: 744ee09eb01b3fa265691afa00ae33bf127c8353

## Painted silhouettes: generated surfaces, curved solids and an armour rejection

The owner found the shadow-volume results underwhelming and suggested combining
the process with image generation. This cohort adds Passage Buckler, Warding
Charm and Bone Plate sources on `3e880ea4eaf934f061c7fea3c55cebf3760e1436`.
The owner called the shield and charm decent and rejected the first armour.
The final armour is a direct source rework, still awaiting visual judgment.
No technical check or source-coverage number establishes artistic acceptance.

Three separate built-in image-generation calls produced front artwork and
alpha silhouettes. Original PNG bytes are preserved in the Project's source
texture directory and copied unchanged through compilation into shipping.
[Generation provenance](item-model-painted-review/generation.json) records
the complete prompts, source-image paths, dimensions via inspection, and hashes;
the [art board](item-model-painted-review/generated-art.png) is a review
derivative. The images contain painted depth cues despite requests for nearly
unlit colour; they are not measured albedo or physical depth maps.

The [native gameplay board](item-model-painted-review/gameplay96.png),
[prior/new products](item-model-painted-review/before-after96.png),
[usual four poses](item-model-painted-review/sheet96.png) and
[cardinal yaws](item-model-painted-review/yaw96.png) show the actual runtime
result. Cardinal yaws are a stage-only probe at gameplay roll, with no production
renderer change. All cameras remain side views.

| Item | Final construction | Native triangles |
| --- | --- | ---: |
| Passage Buckler | Alpha-supported eight-sided outline, authored convex front/back and physical thickness, generated arch/patina artwork, separate rear leather grip and braces | 4,528 |
| Warding Charm | Alpha-supported ceramic outline, authored convex depth, eye/fracture artwork, actual suspension bail and red cord, separate rear glaze seal | 4,112 |
| Bone Plate | Five separate curved ribs, six hollow layered shoulder shells, two substantial front shoulder masses, collar/sternum pieces and actual leather rear/waist harness; generated ivory patch on selected bone faces | 6,964 |

### What image binding contributes

The new [painted-relief route](../../tools/blender/PAINTED_RELIEFS.md) reads
image alpha into an initial silhouette mesh, with explicit width, height,
thickness and convex bow. Host-side Pillow reads pixels without modifying
the image. A mesh JSON bridge lets Blender bind it without installing Pillow
inside Blender. The source retains editable mesh topology/UVs/materials;
optional boundary relaxation and decimation are live modifiers. Both report
and mesh outputs refuse overwrite. After first save, the `.blend` is authority;
the mesh JSON is not consulted by ordinary compilation.

Accepted cells require alpha support at corners, edge midpoints and centre.
The largest edge-connected body is retained, with discarded detached cells
reported. All three initial images discarded zero sampled cells. Separate
local vertex fans protect closed extrusion topology at point-only contacts.
Sampled holes remain actual openings. Original front UVs address the unchanged
full image; backs and thickness use separate plain materials.

Interpreting fine painted colour as shallow height introduced noisy geometry.
The final shield/charm source vertices were edited directly to retain only the
explicit convex envelope. Colour-derived displacement is zero, and the public
tool now defaults to zero. The image supplies painted detail, while the source
supplies its deliberately authored shape. This is not 3D reconstruction.
Live perimeter relaxation and decimation reduced the shield from 9,564 to
4,528 triangles and the charm from 7,804 to 4,112.

All three painted materials declare one existing UV-add pass at strength 0.18
using their own image. This adjusts native colour gain while preserving the
original bitmap. The buckler's plain brass edge also retains a restrained
gold sphere pass. It is a shader material choice, not regenerated texture
colour or a new lighting model.

The [paint-disabled control](item-model-painted-review/paint-controls96.png)
has identical OBJ bytes for every item. It removes only each generated
`map_Kd` binding and that material's UV-add gain; other materials remain.
Changed pixels across two gameplay poses are 2,739 for the buckler, 1,454 for
the charm and 1,251 for Bone Plate. These counts demonstrate contribution,
not aesthetic superiority. In the armour, the contribution is a small ivory
surface patch, not the full generated chest painting.

### The armour failure and direct source rework

The first Bone Plate mapped its entire generated front onto a curved thick
envelope, with extra shoulder pieces behind it. Its front painting carried
too much structure, and rotation exposed the slab. The owner rejected it.
The [rejected/reworked comparison](item-model-painted-review/armor-rework96.png)
preserves that failure beside the final open harness, without promoting the
initial product.

The original painted envelope and first assemblies remain hidden construction
studies inside the authoritative source. They do not export. Direct source
edits added separate curved ribs with real gaps, hollow shoulder shells that
wrap front/top/back, broad front shoulder masses and leather straps around
the rear and waist. Ivory bone faces sample a bounded cream patch of the
unmodified generated image; cut rims and inner walls use plain bone material.
The original art guides material and shape choices rather than standing in
for a complete garment.

The final surface audit caught 24 collapsed painted UV faces on the new
shoulder masses' thickness walls. Those walls share X/Z coordinates across
their depth and cannot use the front projection. A direct material edit made
them plain crisp bone edges in production and the throwaway control. Geometry
and UV coordinates stayed unchanged. The final audit reports zero findings.

### Observed verification and limits

- Eight host tests and one real Blender integration test pass. They cover
  source-image byte preservation, authored dimensions/thickness, full-image
  UV binding, closed edge topology, physical mask holes, reported detached
  fragments, malformed inputs and overwrite refusal. Actual Blender export
  verifies manifold geometry, positive volume, final painted UVs, runtime OBJ
  validity and preserved source mesh/modifier state.
- All three final sources pass shipping read-only `compile_item_blends.py
  --check`. Independent final candidate repeats match bytes; source hashes
  remain unchanged. Native final shipping/candidate RGB pixels match exactly.
- Every exported painted face has zero missing, collapsed or outside-atlas
  UV findings. Final per-face corner/edge/centre sampling gives 23,647 samples
  for the buckler, 16,822 for the charm and 35,308 for Bone Plate. Minimum
  alpha is 242, 243 and 252 respectively, with zero samples below 240.
  This is sampled support, not an exhaustive test of every interior texel.
- Original/source/compiled/shipping image bytes match for all three PNGs.
  Source image paths are document-relative. The [surface evidence](item-model-painted-review/surface-evidence.json)
  records hashes, smooth-face counts, modifiers, hidden rejected-study status,
  triangle counts, UV/alpha findings and native controls without absolute
  machine paths.
- Strict prospective comparison against all 207 models reports zero cohort
  violations at the 0.85 sourced-pair silhouette threshold. Texture/reference,
  script catalogue (108 entries), diff and asset contract checks pass.
- Fresh staged G1, G2, G3, G4, unit and save/load pass after the final source
  correction. Seven native Effekseer world-effect assertions remain explicitly
  unavailable. G5/G6 were not run or recaptured; Linux byte stability remains
  unverified. The historical Chrysalis mismatch (#1355/#1369) remains an
  inherited corpus-verification boundary, not a newly reproduced full check.
- Actual corpus remains red for 83 accepted keys no longer reproducing, with
  three duplicate groups, 34 UV-less models and one shared-file group left.
  Asset regression remains red for 95 changed Model records across the stack.
  Baselines remain unchanged; reconciliation and merging remain owner calls.
- Inherited Lantern integration blockers remain #1434, the general painted-UV
  coverage gap #1431 and the static shape-key policy #1436. Runtime, game data,
  earlier production documents/products and baseline references are unchanged.

Rigid prominent faces suit this image-binding method better than a wearable
whose structure must remain convincing from the side and back. Grid sampling
can lose small spikes, holes or detached details; relaxation and decimation
need native review. Generated painted highlights do not track changing lights.
The buckler/charm sides and backs use modeled assemblies and simpler materials;
they do not repeat the full front designs. Bone Plate's open harness is a new
visual proposal, not an approved repair.

Referenced source absence falls from 58 to 55 of 207 assignments, a coverage
measure only. Once-only scaffolds, rejected candidates, direct-edit records,
control documents and local logs remain ignored under `out/work/`. The general
image-to-mesh route and its tests are durable repository tooling.

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: three image-assisted items and painted silhouette tooling
  base: 3e880ea4eaf934f061c7fea3c55cebf3760e1436

## Multiview volume and surface pilot: Mug of Ale

The owner approved the reworked Bone Plate, then clarified that image generation
was intended to provide **multiview volume and surface information**, not just
front artwork. That approved source is unchanged. This new pilot uses one
built-in image generation call for a front/right/back/top atlas of the same mug.
The full prompt, original image hash and intended view use are recorded in
[generation.json](item-model-multiview-review/generation.json). The unchanged
RGBA 1254-square atlas is retained in source `_textures` and shipping products.

[Reference versus actual source](item-model-multiview-review/reference-to-source.png)
shows four real orthographic source renders beside the generated views. These
are read-only, flat-light Workbench renders, not gameplay proof. The
[native 96px sheet](item-model-multiview-review/native96.png),
[cardinal yaws](item-model-multiview-review/yaw96.png) and
[prior product comparison](item-model-multiview-review/before-after96.png)
use the actual item viewer. Its camera is side-on; the apparent high-angle
diagnostic poses roll the object rather than providing a true top camera.

Measured construction and surface choices:

- Twenty-five independent body levels per elevation. Front's unoccluded left
  edge and back's unoccluded right edge determine averaged width; side determines
  depth. Radius/height maxima are front .517, back .510, side .487. A declared
  25-percent top ratio correction reconciles the measured depth discrepancy.
  All measured scaffold rings match the saved source vertices within 1e-6.
- Front handle centerline controls plus side/top thickness make a real handle
  hole and .414-unit handle depth. Top outer/inner radii determine a hollow
  rounded rim. The cavity floor is explicitly authored; recessed ale is a
  separate solid component. Ceramic walls/handle are smooth, liquid and base
  cut faces intentionally flat. The shell, handle and liquid each have zero
  nonmanifold edges and positive signed volume in the actual saved source.
- Front barley emblem, back repair, observed right flank and top foam use
  separate original-atlas regions. The final exported painted triangles use
  front 1620, back 1620, right 1716, top 574. Right handle glaze is wrapped
  continuously from an observed strip to avoid disconnected projection patches;
  this supplies surface colour, not exact per-texel registration. Unseen underside
  is plain buff ceramic. UV-add gain .16 is a supported runtime pass; Blender
  roughness/specular alone is not claimed as exported surface information.
- The first projection audit found alpha-unsupported samples and collapsed UVs
  on lip/liquid thickness faces. Direct document edits fixed correspondences,
  assigned hidden liquid thickness plain material, inset rim/body sampling and
  replaced fragmented handle projections. Geometry and original pixels were
  preserved during these edits. Final painted faces have zero missing,
  collapsed or out-of-bounds UVs. All 71890 alpha samples are at least 243;
  this is sampled support, not exhaustive raster coverage.
- The [ochre control](item-model-multiview-review/surface-control96.png) keeps
  OBJ bytes identical, removes the generated colour and UV gain, and changes
  3742 pixels across the two gameplay poses. This establishes substantial image
  contribution, not owner acceptance or visual superiority.

Generated views are not consistent scans. Elevations are tilted and disagree
slightly in width; the top omits the belly that protrudes beyond the rim in the
elevations. The modeled top therefore exposes that actual wider body. Foam
positions disagree across views: the top supplies the liquid surface authority.
The handle occludes part of the side body; no left/underside view exists.
Hidden cavity geometry and left colour are inferred. Baked lighting and hard
projection seams remain visible in enlarged source views. The result is a
calibrated vessel pilot, not automatic reconstruction or a general solution
for arbitrary concavities. Volume/surface correspondence and 96px readability
are the review criteria; this pilot's owner acceptance remains open.

The reusable import library `multiview_reference.py` measures alpha profiles,
combines independently observed width/depth, and maps signed panel calibration
into the unchanged full atlas. Six host tests cover unoccluded-edge selection,
alpha preservation, clipped/missing body failures, reversed/non-square atlas
coordinates, invalid calibrations and independent side-depth influence.
[The guide](../../tools/blender/MULTIVIEW_REFERENCES.md) describes calibration,
occlusion, inferred surfaces and source authority. The catalogue now classifies
109 scripts. Compilation consumes only the saved `.blend`, never calibration
JSON or the once-only scaffolder.

Verification after final source edits:

- Shipping `compile --check` and an independent temporary repeat export are
  byte-identical, with source hashes unchanged. Original/source/compiled/shipping
  image bytes match. Candidate/shipping native RGB matches. Actual product:
  2930 vertices and 5848 nondegenerate triangles.
- Strict prospective corpus review against all 207 assignments reports zero
  findings involving this pilot. Actual corpus gate remains red: 83 accepted
  keys no longer reproduce, 3 duplicate groups, 34 UV-less models and 1 shared
  file group. Asset regression remains red for 96 changed Model records across
  the stack. Baselines are unchanged; source absence is 54 of 207, coverage only.
- Texture check, asset contract, script index, six host tests and diff check
  pass. Fresh staged G1/G2/G3/G4, unit and save pass locally. Seven Effekseer
  native world-effect assertions are explicitly unavailable. No G5/G6 runs or
  recaptures; Linux byte stability remains unverified. The inherited Chrysalis
  mismatch #1355/#1369, Lantern blockers #1434 and UV-policy gap #1431 remain
  outside this pilot. No prior item source/product, runtime or game data changes.

Calibration, source graph evidence, material/UV sampling and original provenance
are under [the review folder](item-model-multiview-review/). Once-only scaffolds,
direct source-edit records, throwaway controls and exact local gate logs stay in
ignored `out/work/`. The draft stacks on the painted-item branch.

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: calibrated multiview volume and surface pilot
  base: 8c87ad189573589a3332e86ca62265796bf8921f

### Follow-on: continuous surfaces from multiview references

The next two new sources are Alarm Clock and Tome: Wind Blade. The approved
Bone Plate and previous mug remain untouched. These new items have not received
owner acceptance. [Native 96px review](item-model-continuous-review/native96.png),
[before/after](item-model-continuous-review/before-after96.png),
[plain controls](item-model-continuous-review/surface-control96.png) and
[cardinal yaws](item-model-continuous-review/yaw96.png) show the actual viewer.
Its camera remains side-on; diagnostic poses roll the object.

Each item used two built-in image-generation calls. First, front/right/back/top
references supply volume and material intent. Second, the original reference
and a deterministic layout diagram guide a flat surface atlas. All four
generated originals are unchanged, and both production atlases are opaque RGB.
Full prompts, input hashes and retained original paths are in
[generation provenance](item-model-continuous-review/generation.json). The saved
source documents and original `_textures` atlases are production authority;
compilation never reads the ignored scaffolding or measurement recipe.

The clock's front case span is 464 pixels over a 455-pixel body-height datum;
the unoccluded side depth is 242 pixels. At model body height 2 this yields
width 2.03956 and depth 1.06374. Measured depth overrides the prompt's thinner
requested case. The rolled radial lip expands the datum by 1.5 percent.
Nineteen evaluated components include a real deep case, hollow double-wall bell
domes, raised hands/hub, hammer, rear carry arch, feet and winding key holes.
Domes/case/pads are smooth; dial/rear plates are flat. Dial ticks and rear
engraving come from separate atlas regions; quiet original brass wraps the
case and domes, with deliberate underside/local sleeve seams. Final product:
2980 vertices and 5636 nondegenerate triangles.

The tome's matching 460-pixel front/back widths and 543-pixel height determine
width 1.69429 at height 2. The 174-pixel side and 165-pixel top thicknesses are
averaged to depth .62431; measured spine bulge is .28361. The inconsistent larger
generated top width is not imposed on the cover. One connected surface spans
back, curved spine and front with 127 shared painted edges at exactly zero UV
coordinate delta. Covers/paper planes are flat; rounded spine, folded binding
and bookmark are smooth. Paper top/bottom and binding share world-X/stack-Y
coordinates; fore-edge U follows Z. A real binding volume closes the previously
visible interior gap. Four L guards and a curled bookmark are actual geometry.
Final product: 910 vertices and 1788 nondegenerate triangles.

All evaluated components have positive signed volume and no geometric openings
after an audit-only positional weld. Raw topology is also recorded because
curve conversion duplicates cap vertices for normal boundaries. No audit weld
repairs production. Painted runtime faces have zero missing/collapsed/outside
UVs; flat dial/rear/paper faces have constant corner normals. RGB opacity is
exhaustive, while UV opacity sampling records 21632 clock and 2782 tome samples.
Independent plain-material controls preserve OBJ bytes and remove generated
`map_Kd` plus its UV gain: 4138 clock and 5005 tome gameplay pixels change.
That establishes image contribution, not visual quality.

The front tick/hand hierarchy and wind-blade emblem remain readable at 96px;
the bell gap and page thickness help distinguish the silhouettes. Guard shapes
simplify the reference's ornate metal corners. Native brass/leather grain can
still be busy. Generated engraving, embossing and spine shading remain partly
baked into colour. The brass strip endpoints differ (mean absolute channel
delta 15.08; max 62), despite a deliberately hidden body seam. Continuous UV
coordinates cannot make art seamless. The generated views disagree in case
depth, top width and bookmark curl; wall thickness and hidden attachment geometry
are authored. [Calibration](item-model-continuous-review/calibration.json) names
those choices. [Clock](item-model-continuous-review/alarm_clock-reference-to-source.png)
and [tome](item-model-continuous-review/tome_wind_blade-reference-to-source.png)
correspondence boards use read-only orthographic Workbench source views, not
runtime lighting. This is calibrated manual modeling rather than reconstruction.

A repeated pinned-host export initially found different tome UV alias and face
indices: 9 removed/added `vt` records and 663 removed/added `f` records, with no
changed vertex/normal records. Decoded ordered attributes/materials were exactly
equal. Directly materializing only this new saved cover's SOLIDIFY/BEVEL,
asserting evaluated positions match at seven-decimal precision, and quantizing source UVs to six
decimals restored byte-stable repeats. The shared compiler and earlier sources
were unchanged. [Issue #1447](https://github.com/JosephSerUSP/Second-Rite/issues/1447)
preserves the narrower same-host investigation with
[pre-fix evidence](item-model-continuous-review/repeat-uv-evidence.json) and a
[read-only source fixture](item-model-continuous-review/repro/). This does not
resolve #1355 or establish Windows/Linux equality under #1369.

The reusable `surface_atlas.py` import library supplies path-distance coordinates,
bounded atlas mapping, local cyclic seams/poles and read-only endpoint-colour
diagnostics. Four host tests cover distance density, local seam/pole support,
invalid mapping bounds and original-image preservation. The
[guide](../../tools/blender/CONTINUOUS_SURFACES.md) records source authority,
coordinate-versus-image continuity, flat/smooth decisions and native review.
Script catalogue: 110 classified scripts.

Final verification: shipping `compile --check`, independent repeated bytes,
source-hash preservation, original/source/compiled/shipping atlas identity and
candidate/shipping native RGB identity pass. Texture/asset contract/script index,
four host tests and diff check pass. Fresh staged G1/G2/G3/G4, unit and save pass
locally; seven native Effekseer world-effect assertions were unavailable.
Strict prospective review of all 207 assignments finds no violations involving
these items. Actual corpus gate remains red: 85 stale accepted keys, 2 duplicate
groups, 33 UV-less models and 1 shared-file group. The reduced Ether Seed/Sigil
Ink and remaining five-food groups are inherited and marked new relative to
the old keys. Asset regression remains red for 98 changed Model records across
the stack. Baselines are unchanged; missing editable sources are 52/207, coverage
only. No G5/G6 runs or recaptures and no Linux byte claim. Full-corpus compile
was not rerun; inherited #1355/#1369, #1434, #1431 and #1436 remain outside this
batch. Runtime and game data were unchanged.

Complete review/provenance/source evidence lives in
[the review folder](item-model-continuous-review/). Exact local logs, once-only
scaffolds and direct-edit records remain in ignored `out/work/`. This draft
stacks on the multiview pilot branch, #1446.

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: multiview volume with continuous generated surfaces
  base: 8b7b4a64631b3eef9227ef9b2360c6db1b38aa73

## Follow-on: two items per generated texture

The 2026-10-07 pilot gives **Untarnished Signet** and **Verdigris Coin** separate
saved sources using one unchanged generated RGB atlas. One combined multiview
reference and one flat-atlas generation served both, rather than two calls per
item. Unique coin faces and blank signet table remain separate allocations;
both models consume the same gold strip. This measures fewer generation calls,
not cost, memory or draw-call savings.

The ring's actual finger hole, thick widening band and beveled blank table are
geometry; the coin has measured depth, recessed stamp planes, raised rim and
64 physical edge reeds. Rounded band/rim surfaces are smooth, broad faces flat.
The stamp's apparent relief is mainly painted. Generated view inconsistency
and authored hidden construction are recorded. The single atlas displaced its
requested gold/bronze strip positions; measured UV correspondence preserves
original pixels instead of assuming guide adherence. Shared `surface_atlas`
now converts pixel-edge allocations and sampling insets into OBJ UV bounds.

Both exports repeat exactly, sources remain byte-unchanged during inspection,
and native 96px candidate/shipping captures match. Painted-face region/area
checks and raw closed positive-volume component checks pass. Identical-OBJ
plain controls isolate generated surface contribution. Quiet regions are still
grainy, strip endpoints differ, and shared edits couple both consumers.

Five host tests, texture/asset contract/index, strict prospective cohort review,
fresh G1-G4/unit/save pass locally. Seven Effekseer assertions are unavailable.
Actual baselines remain red and unchanged: corpus 85 stale keys, two inherited
duplicate groups, 33 UV-less items and one shared-file group; asset regression
100 changed model records across the stack. No G5/G6 recapture/run or Linux
byte-stability claim. Prior adopted sources were not regenerated. Full prompts,
allocations and native/source comparisons are in
[the shared-atlas review package](item-model-shared-atlas-review/).

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: two independent items from one generated surface atlas
  base: cfe1006e10abbb26d3a3201d64ca36d902b6ac97


## Follow-on: complex weapons sharing surface art

Dark Scepter Lucille and Hook Spear extend the paired-atlas trial beyond simple
solids. One combined multiview reference and one unchanged surface atlas guide
a four-rib open crown with a suspended faceted crystal, swept horns and hollow
cup, plus a thick asymmetric hooked blade with a real cutting bevel, socket,
rivets and raised lacing. Silver and leather regions are intentionally shared.
Hidden joints and thickness remain authored; reference views disagree in scale.

The new Blender-free `path_sweep` helper transports elliptical sections with
minimum rotation and gives side faces distance UVs plus flat radial cap fans.
This avoids a fixed world-axis tube pinch; it does not guarantee no overlap.
A direct saved-source scepter edit exposed silver faces/ridges after native
review. Prior adopted documents were not regenerated. Crystal facets and blade
planes are flat; rounded sections are smooth. All 37 evaluated components are
closed and positive-volume; painted faces pass assigned-region and area checks.

Local three sweep tests, texture/contract/index checks, repeated export and
shipping compile, strict prospective corpus, staged G1-G4/unit/save pass.
Seven native Effekseer assertions were unavailable. Actual baselines stay red
and unchanged: 86 stale corpus keys and 102 changed asset-regression records
across the stack. No G5/G6 run/recapture or Linux byte-stability claim.
Generated grain and baked shading remain, fine details simplify at 96px, and
owner visual acceptance is open. Full prompts and actual comparisons are in
[the complex-weapon review](item-model-weapons-atlas-review/).

## Follow-on: six casting tools with stronger family direction

Silver Rod, Mage Staff, Sage Staff, Ether Staff, War Staff and Healing Staff
extend the shared-atlas method to six different constructions. An initial
direction lineup chooses crafted ritual tools with broad heads, strong joins,
quiet surfaces and one focal face per item. Two three-item multiview sheets
guide volume, and one unchanged RGB atlas supplies fifteen bounded regions.
Four generation calls serve six items; no monetary or rendering-cost savings
were measured. The returned atlas is 1254 square rather than the requested
2048, so measured allocations and five-pixel insets replace assumed guide UVs.

Hexagonal rim, timber hook, forked tablet, opposing crescents, four-flange iron
head and ceramic halo remain distinct in identical-OBJ plain-material controls.
Round shafts/wraps and jade are smooth; cut planes, crystal facets, tablet,
crescents, petals and flanges are flat. All 112 evaluated components are closed
and positive-volume. Hidden support and thickness remain authored; generated
view discrepancies and independent side-proportion adjustments are explicit.
The Sage mark is painted, not recovered relief. Fine clips/wraps simplify at
96px; visual acceptance remains open.

Authoring exposed cached transform bounds in `item_kit.report`; updating the
view layer and a pinned-Blender transform regression test fix the report.
Export validation caught Ether bevel tips collapsing after six-decimal rounding.
Direct saved-source merges repair those tips without moving remaining vertices
or relaxing the compiler. Earlier adopted sources were not regenerated.

Local shipping compile, independent repeat export, texture/contract/index,
strict prospective cohort review and staged G1-G4/unit/save pass. Seven native
Effekseer assertions were unavailable. Actual baselines remain red and
unchanged: 92 stale accepted keys, two inherited duplicate groups, 26 UV-less
assignments, one shared-file group; asset regression 108 changed records across
the stack. Missing source coverage is 42/207, not quality acceptance. No G5/G6
run/recapture, full-corpus recompile or Linux byte claim. Complete prompts,
original references, source cardinal views and native controls are in
[the six-item family review](item-model-staff-family-review/README.md).

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: six distinct casting tools with shared generated surfaces
  base: 588e0a59a34a284d90c07701c5c2b634ec579187

## Follow-on: crossing construction methods

The 2026-10-07 experiment compares two art directions and three hybrid routes
for one asymmetric containment capsule. Shadow intersections pair with a loft
and transported sweeps; fabricated plates pair with a live SDF core and sweeps;
separate image-alpha panels pair with live surface conformance, thickness and
the loft/sweeps. Four built-in image-generation calls supply two multiview
references, one shared RGB atlas and four component stencils on one RGBA sheet.
The six saved sources and runtime products remain nonshipping study assets.

Bounded alpha sampling now selects components without changing original PNG
bytes or losing full-image UV coordinates. A reusable Blender helper projects
only the front surface onto a root-owned guide before adding thickness, can
relax sampled boundaries beforehand, and separates smooth fronts from flat
back/cut rims. Generated thickness has no independent paint chart, so UV
textures/overlays on the cut-rim material are rejected. Direct saved-source
edits remove redundant empty hull modifiers and repair rim materials/shading.

The study holds each direction's reference, overall front/right bounding ratios,
atlas and runtime view poses. Whole routes still change multiple factors and
root fits alter component proportions. A separate SDF-core control keeps the
noncore evaluated geometry and exported bounds identical while returning the
core to its saved loft. The SDF versions cost 7,764/7,532 triangles versus
1,712/1,480 for those controls, with little visible silhouette benefit at 96px
in this object. Pixel changes record contribution, not quality. Conformed panels
retain slender side profiles and some sampled perimeter steps; the reference's
thick sculpted cheeks are not faithfully reproduced. Generated views disagree
and hidden construction remains authored, rather than recovered from scans.

All 84 visible evaluated components are raw closed and positive-volume, painted
faces pass assigned-region/area checks, and original/source/compiled atlases
match bytes. A fresh temporary six-source compile check matches retained
products and leaves sources untouched. Identical-OBJ plain controls and actual
native/source comparisons are retained. Ten host relief tests, existing real
relief export integration, new real conformance integration, sixteen compiler
cases and the 112-tool index pass locally. Canonical shipping-Project G1-G4,
unit and save pass; seven native Effekseer assertions are unavailable. No
shipping assets/data, previous adopted sources, baselines or G5/G6 references
changed. No Linux stability, visual approval or merge claim is made.

Full prompts, controls, saved study sources and review boundaries are in
[the hybrid study package](item-model-hybrid-study/README.md).

Agent-Signature:
  platform: Codex
  model: platform-selected/unknown
  role: implementation
  task: compare hybrid item construction across two art directions
  base: b2ea564e69d9f07dbe384b2bfd47fcea01efef87
