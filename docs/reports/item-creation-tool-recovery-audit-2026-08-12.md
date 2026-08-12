# Item Creation tool recovery audit — 2026-08-12

## 1. Executive summary

The repository has two different Item Creation artifacts:

1. `tools/craft-space/` is a specialized, read-only balancing instrument. It
   derives a visual craft space and reachability/concentration tables from a
   baked data snapshot.
2. The live in-game `Item Creation` scene is `data/scenes/1.json`. It is a
   separate authoring/runtime surface and still contains the pre-derived-
   signature model.

The specialized tool is not a current authoring applet and has no save or
round-trip path. Its committed generated HTML is stale: it contains 46 items
and 22 numeric actor records, while `main` contains 207 items and 66
fragmented symbolic Unit records. Running its builder on current `main` fails
because it still requires the deleted `data/actors.json`.

The current engine and Studio item form are substantially healthier. The
engine has derived signatures, discipline membership, intensity grades,
output/ingredient exclusions, stable numeric item IDs, validator checks, and
craft unit tests. Studio exposes the current item metadata. However, the live
Item Creation scene does not consume `engine/craft.lua`; it still reads deleted
legacy fields such as `meta.potency`, `meta.craftElement`, and
`meta.craftKind`, and presents the explicitly retired numeric-yield/anomaly
model. Item Creation is therefore **broken as a trustworthy player/runtime
surface** and **stale as a balancing tool**, while the underlying engine and
item authoring fields remain usable.

No production data, golden reference, or generated golden screenshot was
changed for this audit.

Status labels used below: **broken**, **stale**, **partial**, **hidden but
functional**, **missing**, **still healthy**.

## 2. Current purpose

### `tools/craft-space` — status: stale, still healthy in its original role

The tool is explicitly described by its builder as a “design instrument”. It
does not create recipes or edit game data. Its purpose is to explore:

- derived item signatures in a Red/Green/Blue hue plane plus White/Black value;
- four discipline spaces;
- crafter pull, reach, scatter, foreign-ingredient worth, and intensity weight;
- output-pool coverage and concentration;
- a derivation audit comparing derived values with legacy authored values.

That specialized balancing workflow remains valuable and should not be
replaced by the ordinary item database.

### Live Item Creation scene — status: broken, stale

The scene is still reachable from the game and is authored as a generic
data-driven `windows` scene. It presents two ingredients, a confirmation step,
a roulette, and a result. Its script is a local `calcYield` SCRIPT and not the
current `engine/craft.lua` implementation.

## 3. Current data contract

### Craft-space inputs

`tools/craft-space/build.py` directly opens:

- `data/items.json` — assumed monolithic item array;
- `data/actors.json` — **missing on current `main`**;
- `data/elements.json`;
- `data/engine.json`;
- `tools/craft-space/lexicon.json`;
- `tools/craft-space/overrides.json`.

It additionally assumes the old actor shape: numeric `id`, `discipline`,
`elements`, and `baseParams`.

Current authored storage says `items` is a monolithic document, but Units are
an ordered fragmented collection under `data/units/index.json` and individual
Unit files. The runtime loader reads `loader.units`, not `loader.actors`.

### Craft-space output

The builder writes only `tools/craft-space/craft-space.html`. It embeds a
minified `DATA` object containing:

- item `id`, `name`, `type`, `equipType`, `category`, `cost`, `description`,
  `effects`, `traits`, and `meta`;
- actor-like `id`, `name`, `discipline`, `elements`, and `baseParams`;
- disciplines, element affinity tables, lexicon, grades, and name-keyed
  overrides.

The current committed HTML contains 46 items with IDs 1–46 and 22 actors with
IDs 1–22. Current canonical data contains 207 items with IDs 1–207 and 66
symbolic Unit records.

### What it writes

The tool does **not** write Items, recipes, synthesis rules, separate creation
data, or any other authored resource. It has no save button, HTTP endpoint,
form submission, local-storage persistence, or export action. Its only write is
the generated HTML when `build.py` is run.

Therefore:

- recipe authoring: **missing**;
- ingredient quantity authoring: **missing**;
- result selection/authoring: **missing**;
- separate recipe/synthesis storage: **missing**;
- item mutation: **missing**;
- model exploration: **still healthy**, subject to stale inputs.

### Canonical fields and identity

The builder's projection omits current item fields including `icon`,
`iconPalette`, `model`, `params`, `scope`, `target`, `meal`, `savor`,
`foodTags`, and `animation`. It also does not use current `meta.disciplines`,
`meta.intensityGrade`, `meta.craftable`, or `meta.craftIngredient` as its
primary contract; its overlay files are keyed by display name.

Item IDs are copied into the baked payload and remain stable for the records it
does include. Name-keyed overrides are not ID-stable: a rename can silently
detach an override. The applet has no unknown-field preservation requirement
because it does not write canonical records, but its projection necessarily
drops unknown/new fields from the analysis payload.

Classification: current storage contract **still healthy**; applet input
adapter **broken**; field coverage **partial**; name-keyed override identity
**stale**.

## 4. Current runtime consumption

### Current engine

`engine/craft.lua` is current and data-driven. It consumes:

- `traits[]`, `effects[]`, name lexicon, and `cost` to derive signatures;
- `meta.disciplines` with registry-backed defaults for output membership;
- `meta.intensityGrade` for the one authored intensity override;
- `meta.craftable` for output exclusion;
- `meta.craftIngredient` through `craft.isIngredient` for input exclusion;
- `engine.json` craft rules, element sources, lexicon, disciplines, and grades;
- Unit discipline, innate elements, stats, and `CRAFT_YIELD_RATE` for reach.

The current engine tests exercise signature, membership, pool, reach, ideation,
scatter, resolution, and coherence. Reachability also calls `craft.ideate` and
`craft.resolve`.

Classification: engine craft model **still healthy**; live scene consumption
of it **missing**.

### Live scene

`data/scenes/1.json` still uses:

- `yieldFormula` based on `ingredient.meta.potency`;
- `penaltyFormula` based on `meta.craftElement` and tier/stat thresholds;
- `anomalyFormula` with a 5% critical multiplier;
- tier brackets and a roulette pool filtered by `meta.craftKind` and
  `meta.tier`;
- text for “Expected Yield”, “Expected Tier”, “Element conflict”, and
  “CRITICAL ANOMALY”.

Current Items deliberately have no `potency`, `craftElement`, or `craftKind`;
the current item count scan found zero records with any of those legacy fields.
The scene therefore cannot be trusted to calculate current results. G1 still
passes because it validates formula syntax and registry references, not the
semantic availability of arbitrary `meta` fields used inside a SCRIPT.

Classification: live result calculation **broken**; live presentation model
**stale**; data-driven scene host and generic SCRIPT mechanism **still healthy**.

## 5. Current authoring capabilities

### Craft-space applet

Supported operations are exploratory only:

- select a discipline or “every discipline”;
- select a crafter or “every crafter”;
- tune crafter pull, stat-to-intensity alpha, intensity weight, novice
  scatter, reach base, beyond-reach cost, and foreign-ingredient worth;
- toggle dominance-weighted blending, multi-discipline membership, and quest
  exclusion;
- toggle ideation density, item signatures, and labels;
- inspect hue/value plots;
- inspect coverage by discipline, outcome wins, and derivation audit tables.

It does not create a recipe, edit ingredient quantities, choose a permanent
result, batch-edit items, compare saved recipes, validate inventory
availability, or save a balancing decision.

Classification: visualization and comparative reachability **still healthy in
concept**; all canonical authoring operations **missing**.

### Live scene

The scene supports selecting two inventory entries, confirmation/back, a
roulette, consuming two items, and granting one result. These are runtime
operations, not authoring operations. They remain coupled to the stale legacy
formula and pool vocabulary.

## 6. No-op round-trip findings

The requested “open → no-op save → diff” cannot be performed against the
craft-space applet: it has no save path and no canonical writer. This is a
real result, not an unrun test.

The closest safe check was:

```text
current data → run tools/craft-space/build.py → inspect generated payload
```

On current `main`, the builder fails before writing because
`data/actors.json` does not exist. The repository status remained clean.

The committed generated HTML is therefore a stale artifact, not a current
no-op save result. Its counts and fields prove it was built against an older
schema.

Classification: no-op save path **missing**; current build reproducibility
**broken**; production-data safety **still healthy** because the applet has no
canonical writer.

## 7. Controlled-edit findings

A temporary fixture copied the builder, template, overlays, current item,
element, and engine data. The current fragmented Units were assembled into a
temporary compatibility `actors.json` solely to test the projection; no repo
file was changed.

The controlled fixture changed Item 1's cost and added an unknown
`auditSentinel` field. The rebuilt temporary applet:

- loaded all 207 current items;
- preserved Item 1's ID and reflected the changed cost;
- did not preserve `auditSentinel`;
- emitted only the fixed ten-field item projection listed above;
- used the current 66 Unit-derived records once the adapter was supplied.

This proves stable numeric item IDs survive the projection, but it also proves
the applet is lossy as a data view and cannot be treated as a record editor.
There was no unrelated canonical-data rewrite because no canonical writer was
invoked.

Classification: controlled analysis refresh **partial**; unknown-field
preservation **missing by design**; canonical-data corruption through this
tool **not observed**.

## 8. Stale assumptions

| Assumption | Status | Evidence |
|---|---|---|
| Actors are in `data/actors.json` | **broken** | file absent; Units are fragmented under `data/units/` |
| Actors use numeric IDs | **stale** | current Unit IDs are symbolic strings |
| Item Creation metadata is `craftKind`, `craftElement`, `potency` | **broken** | current engine derives signatures; current items have none of these |
| Item membership is inferred from old `craftKind` overlays | **stale** | current canonical field is `meta.disciplines` plus registry defaults |
| Item IDs are the only useful references | **partial** | item IDs remain numeric/stable, but Unit identity changed |
| Four-tier yield brackets define the live result | **stale** | `engine/craft.lua` uses nearest-neighbour resolution in a space |
| Anomaly/critical output is part of the intended model | **stale** | design doc explicitly says there is no anomaly or critical hit |
| The applet can be used as an authoring surface | **broken** | it has no save/write UI |
| Name-keyed overrides are stable | **stale** | renames can detach `overrides.json` entries |
| The scene and analysis tool share one implementation | **broken** | scene-local legacy SCRIPT and JS analysis are separate paths |

## 9. Still-correct architecture

- A specialized Item Creation balancing view is worthwhile and consistent with
  the design intent.
- The engine owns derived signatures and runtime resolution.
- Item Creation is a data-driven scene, not a hard-coded scene kind; the 2026-
  07-10 migration to generic scene-local scripts remains structurally useful.
- `data/engine.json` is the registry for disciplines, formulas, element sources,
  lexicon, grades, and item metadata schema.
- Items remain one canonical resource; no separate recipe table is required by
  the current design.
- Studio already has schema-driven item fields, sorting, and crafting facets.
- The authored-storage manifest and stale-write/token infrastructure are
  appropriate for real future writers.
- Validator, reachability, and unit-test seams are the right verification
  points.

Classification: architecture **still healthy**; connection between these
pieces **partial**.

## 10. Missing current item/crafting concepts

The specialized applet currently does not expose or correctly model:

- current `meta.disciplines` membership and its default-vs-authored distinction;
- `meta.craftable` output exclusion;
- `meta.craftIngredient` input exclusion;
- `meta.intensityGrade` as the only hand-authored intensity override;
- registry-derived element contributions from current effect and trait codes;
- current Unit symbolic IDs, fragmented storage, and Unit discipline data;
- `CRAFT_YIELD_RATE` and the current reach calculation;
- nearest-neighbour resolution and beyond-reach distance cost;
- per-attempt seed/determinism as an analysis dimension;
- current inventory/reward/production reachability reports by canonical ID;
- current item icons, models, scope, targets, meals, savor, and other item
  vocabulary when inspecting a result;
- a distinction between “this item can be produced” and “this item can be an
  ingredient” in the applet's own data path.

Classification: these are **missing** from the applet; the corresponding
engine/Studio concepts are mostly **still healthy**.

## 11. Relationship to Studio

Studio's Database → Items surface is the canonical item editor. Its schema
layer edits current fields and its crafting facets expose:

- Produced By;
- Usable As Ingredient;
- membership source: opted out, authored, default, or none;
- discipline sorting and search.

The editor writes through the shared authored-storage `/save` path. `items` is
currently a monolithic, bulk-editable document, so it is not fragmented today.
The current storage tests cover resource classification and stale-write
behavior, and the Node authored-storage tests pass.

Item Creation should remain a specialized balancing applet. It should not
duplicate the Item form or become the place that owns item identity. The safe
relationship is:

```text
Studio Item editor ──authors canonical item fields──┐
                                                     ├─ current engine analysis
Item Creation applet ──explores/ranks balance space──┘
```

The applet can link to or reuse Studio's canonical item/Unit pickers and
storage metadata later, while keeping its specialized plots and batch balance
workflow. It should not maintain a parallel `overrides` vocabulary for fields
already represented canonically unless an owner-approved design explicitly
keeps a balancing-only override.

Classification: specialized-vs-general separation **still healthy**; shared
current-data integration **missing**.

## 12. Visual/UX debt

### Craft-space applet

Still useful:

- the hue plane makes element direction and saturation legible;
- the value-axis reach line explains beyond-reach outcomes;
- coverage, outcome, and derivation tables support balancing review;
- sliders make model sensitivity explorable.

Misleading or stale:

- “Derivation audit” still has a `legacy` column and reads old authored
  `craftElement` values, even though that vocabulary was deleted;
- the default view is populated from a stale 46-item snapshot;
- discipline/crafter selectors show old numeric actor records;
- controls do not disclose that they are unsaved, baked-data analysis only;
- no current-ID/source indicator or data timestamp is visible;
- no status for missing/stale input sources is shown before analysis;
- the tuning controls are not visibly separated into engine-authoritative
  rules versus analysis-only knobs;
- there is no path from an outcome row to the canonical Studio item.

### Live scene

Its panels are structurally clear (two slots, inventory, confirmation,
roulette, result), and the explicit two-slot interaction remains useful. The
labels “Expected Yield”, “Expected Tier”, “Element conflict”, and “CRITICAL
ANOMALY” are misleading against the current design and current engine. The
scene also depends on item values that are absent, so the UI can render a
plausible shell while being semantically wrong.

Classification: specialized plot/table presentation **still healthy**;
source/status affordances **hidden but functional or missing**; live scene
labels and result readout **stale**.

No G6/contact-sheet artifact was created. No golden reference was recaptured.

## 13. Verification debt

Passed on current `main`:

- `lovec . validate` → `VALIDATE OK`;
- `lovec . unittest` → `ALL UNIT TESTS OK`;
- `node tools/editor/test-authored-storage.js` → `authored-storage node
  tests: OK`.

The validator reported 15 items outside Item Creation entirely and 85 SCRIPT
usages; those are current reports, not failures.

The current builder check failed as expected:

```text
FileNotFoundError: ... data/actors.json
```

Missing verification:

- no test runs the builder against current fragmented Units;
- no test asserts generated HTML counts/IDs match canonical data;
- no test detects stale generated `craft-space.html`;
- no test checks that the applet's projection includes the current crafting
  fields or clearly declares omitted fields;
- no applet visual gate exists in G6; G6 covers `tools/editor`, not
  `tools/craft-space`;
- `scene_1.log` verifies UI events, not semantic alignment with
  `engine/craft.lua` or rendered correctness;
- the live scene has no test proving current Items can produce a result.

Classification: repository engine/storage verification **still healthy**;
Item Creation tool verification **missing**; current live-scene semantic
coverage **broken**.

## 14. Minimal recovery path

This is a recovery sequence, not a redesign:

1. **Restore a current read contract.** Make the builder consume the shared
   authored-storage view: `data/items.json`, `data/units/index.json` plus Unit
   fragments, and current engine registries. Fail loudly on missing or stale
   sources. Do not recreate `data/actors.json` as a compatibility shim.
2. **Use canonical IDs and fields.** Replace display-name overlays and old
   `craftKind`/`craftElement`/`potency` reads with current item IDs and the
   engine's membership/signature concepts. Keep any balancing-only override
   explicit and owner-reviewed.
3. **Make the applet’s source state visible.** Show source commit/data version,
   record counts, and whether the page is generated or live. A stale snapshot
   must be an obvious failure, not a plausible dashboard.
4. **Add isolated tool tests.** Use temporary fixtures to prove a no-op
   refresh, controlled cost/membership changes, stable IDs, and explicit
   unknown-field behavior. The test must never write production data.
5. **Reconcile the live scene separately.** Route runtime Item Creation through
   the current craft model, or explicitly declare the scene out of service
   until that owner-approved runtime change lands. Remove stale labels only as
   part of that runtime task; do not hide the mismatch in the applet.
6. **Add verification after behavior is approved.** Add a builder drift check,
   a semantic live-scene test, and a visual review path. Do not recapture G5/G6
   references as part of recovery.

The first four steps are the minimal path to make the specialized balancing
tool trustworthy as an analysis surface. The fifth is required before the
player-facing Item Creation scene can be called trustworthy.

## 15. Things deliberately deferred until First Stratum balancing

- bulk item rebalance or target prices;
- adding the missing discipline content and reagent coverage;
- deciding the final balance knobs, scatter curve, reach curve, or weighting;
- adding recipe tables or abandoning the current ideation model;
- expanding crafting into new disciplines or new item categories;
- tuning pools, rewards, shop availability, or First Stratum economy;
- redesigning the specialized plots, tables, or visual language;
- deciding whether a balancing-only intensity override remains necessary after
  more item prices are authored;
- broad item-schema migration or symbolic Item ID migration;
- any golden recapture.

These are design/balance decisions, not prerequisites for documenting the
current recovery boundary.

## 16. Recommended issues in dependency order

### Issue A — Repair Craft-space input adapter and stale generated snapshot

**Classification:** broken/stale. The builder depends on deleted
`data/actors.json`, while the committed output is a 46-item/22-actor snapshot.

**Acceptance criteria:** builder reads current Units through authored storage;
current `main` builds successfully; generated counts and canonical IDs are
checked; no compatibility `actors.json` read path is added; production data is
unchanged by the test.

### Issue B — Define the canonical Item Creation analysis export

**Classification:** partial/missing. The applet currently reimplements parts
of the model in JS and uses name-keyed overlays.

**Acceptance criteria:** the applet consumes current engine-declared signature,
membership, exclusion, discipline, and reach concepts; any analysis-only
knobs are clearly labeled; item and Unit identity is canonical and stable; the
export documents intentional projection/omission.

### Issue C — Add Item Creation tool round-trip/drift tests

**Classification:** missing. There is no no-op refresh, controlled-edit, stale
snapshot, or unknown-field contract test.

**Acceptance criteria:** temporary fixtures cover current storage, no-op
refresh, one safe edit, stable IDs, omitted fields, and generated-output
determinism; the test cannot write repository `data/`.

### Issue D — Reconcile the live Item Creation scene with `engine/craft.lua`

**Classification:** broken/stale. The scene still reads removed legacy fields
and exposes retired yield/anomaly concepts.

**Acceptance criteria:** the live scene and engine agree on inputs, resolution,
consumption, result production, and user-facing concepts; current Items can be
used in a deterministic test; stale `meta.*` reads are gone; the existing
data-driven scene architecture is preserved unless an owner approves a change.

### Issue E — Add semantic and visual verification for Item Creation

**Classification:** missing. Existing unit/G1/G3 checks do not prove the
current scene is semantically aligned, and G6 does not cover craft-space.

**Acceptance criteria:** a semantic scene test covers current data and a
read-only visual review/gate covers the specialized applet and live scene.
Golden references are changed only by an owner-approved, separately reviewed
capture.

No GitHub issues were opened by this audit; these are recommended issue
boundaries for owner triage, in dependency order.
