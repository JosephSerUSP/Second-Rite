# Blender authoring assessment: expressive potential, noise, and weak-agent authorability (2026-10-04)

This is a report, not a status record. Each claim about the code names the file
or the command that shows it. The numbers were measured on this branch on
2026-10-04. Re-measure them before acting on them.

It builds on `docs/reports/blender-tooling-audit-2026-09-28.md`, which covered
the version pin, the locator, the Blender 5.2 features and whether to use
Geometry Nodes. Most of that audit has since shipped (#1259, #1267, #1272,
#1275). This report does not repeat it. It asks a different question:

> **How much can an agent at low reasoning effort make with this environment,
> and how much does it have to read, guess, or avoid getting wrong to make it?**

The goal has three parts:

1. Raise **expressive potential**: what can be said per line of authoring.
2. Cut **noise and redundancy**: what an agent has to read past to find the
   one thing that matters.
3. Lower the **intelligence floor**: make the obvious move also the correct
   move.

---

## 0. Executive summary

The core architecture is good and should stay. Three ideas carry it:

- **Source authority.** An adopted `.blend` is edited by hand and never
  regenerated.
- **A read-only compiler.** `compile_item_blends.py` hashes the source before
  and after, so compiling can never change it.
- **Validated grammars.** `house_grammar/recipe.py` raises a `GrammarError`
  that names the bad field.

The trouble sits around that core. Five problems make the environment
expensive for a weaker agent:

| # | Problem | Measured symptom |
|---|---|---|
| 1 | **Silent path rot since #700** (the repo root is no longer a game) | 22 files in `tools/` still build paths under the repo-root `assets/` or `data/`, which no longer exist. The item-corpus gate crashed on start until this branch fixed it. 4 asset-production tests still error. None of this runs in CI. |
| 2 | **No routing.** Nothing says "I want to make X, so open Y" | The Blender skill covers only the low-level core. It never mentions the per-item `.blend` compiler, the interior vocabulary, furnishings, the house grammar, ground cover or the material library. Its material list was 12 of the 23 ids. |
| 3 | **Production, study and one-shot scripts sit together** | 85 top-level `tools/blender/*.py` files. 15 are `study_*` and 13 are revision-surgery scripts for one room, the Passage Office ("Registry"). 6 migration lists are orphaned (0 references). |
| 4 | **New revision = new binary file** | 12 `passage_office_rN.blend` files take 76 MB in one candidate folder, with no LFS. `.git` is 308 MB. One room produced 8 reports in a single day. |
| 5 | **The vocabulary is positional Python, not validated data** | Recipes are bare float tuples such as `WINDOW = (-0.3, 1.3, 1.45, 2.75)` with sign conventions (`side=-1` means screen right). An agent cannot use it correctly without the 728-line brief. |

The biggest gains in expressive potential, ranked by value per unit of cost:

1. **A declarative place spec**: a room or exterior as validated data, compiled
   by the existing `Interior` class and house grammar. Anchors are named, not
   coordinates.
2. **A furnishings and kit catalogue** made by a generator: a contact sheet plus
   a parameter table, with a gate that keeps it complete.
3. **Data templates for item families** (lathe profile, plate outline, sweep
   curve), so the 173 legacy OBJs without a source can be replaced by filling
   in parameters.
4. **Named finish presets** (`sheen.ruby`, `rim.cold`) in place of hand-written
   `sr_runtime_passes_json` strings.
5. **Interior staging predicates**: the brief's rules (character-floor limit,
   no key light, threshold direction) as checks, the same way
   `house_grammar/staging.py` already does it for exteriors.

§7 gives a "capability ladder". For each level of agent capability it says
which tasks are safe and which tooling makes them safe.

---

## 1. Method and evidence

Commands run on this branch:

```text
python tools/asset-language/check.py all                  # ASSET LANGUAGE OK
python tools/asset-production/check_item_models.py        # crashed; fixed here -> ITEM MODELS OK
python -m unittest discover -s tools/asset-production/tests -p "test_*.py"
python -m unittest discover -s tools/blender/tests -p "test_*.py"
```

Plus `grep`/`find` sweeps over `tools/blender`, `tools/asset-production`,
`tools/asset-gen`, `.claude/skills`, `.github/workflows`, the Project's
`assets/authoring` and `data/items.json`, and the docs under
`docs/asset-pipeline`, `docs/design`, `docs/agentic` and `docs/reports`.

Blender itself was not run: this container has no pinned 5.2.2. Statements
about Blender-side behaviour come from code and from the dated reports.

---

## 2. Inventory snapshot

### 2.1 Tooling

| Area | Size | Notes |
|---|---|---|
| `tools/blender/` | 256 files, ~37k lines of Python | 85 top-level scripts |
| top-level script prefixes | `study_` 15, revision surgery for the Passage Office ("Registry", 12 Python and 1 JS) 13, `build_` 4, `inspect_` 3, `atlas_` 3, `tree_` 3, others 1–2 | Only about 30 are production entry points |
| `tools/blender/recipes/` | ~6k lines | `interior.py` 878, `exterior.py` 988, `furnishings.py` 1204 (49 functions) |
| `recipes/house_grammar/` | 10 modules | Validated data grammar. No shipped environment is built from it; it is called only by `study_house_grammar.py` and the live bridge |
| `tools/blender/tests/` | 77 files | 22 need a spawned Blender (`*_blender.py`) |
| `tools/asset-production/` | 4 one-off cohort builders (`build_item_models_53_62.py`, …) | Write to the repo-root `assets/`, which is dead |
| Blender asset library (in-repo) | **1 asset** (`SR_GroundCover`) | Not served, by design |
| semantic materials | 23 ids in `tools/asset-language/materials.json` | Textures are optional per id (`material_library.py`) |

### 2.2 Content

| Content | Count | Source authority |
|---|---|---|
| items with a model (`data/items.json`) | 207 → 205 distinct OBJs | — |
| item models with an editable `.blend` | **32** | `assets/authoring/items/*.blend`, read-only compiled, checked byte-for-byte in CI |
| item OBJs **without UVs** | **124 / 205** | Blocks any texture or projection work |
| duplicate geometry (baselined) | 11 | `item-model-baseline.json` |
| shared OBJ file | 1 (`wind_charm.obj` ×3) | baselined |
| environment `.blend` (shipping folder) | 10 (4 adopted, 4 scaffold, 2 reference) | `environment-sources.json` |
| environment `.blend` (candidates) | 12 revisions of one room, 76 MB | 10 scaffold, 1 superseded |
| shipped environment packages | ~20 St. Maria places | `assets/environments/st_maria_town/` |
| Blender-related reports | ~65 of 135 files in `docs/reports/` | — |

### 2.3 Gates that cover Blender work

| Check | In CI? | State |
|---|---|---|
| `compile_item_blends.py --check` | yes (`blender-item-source.yml`) | green per CI |
| `environment_sources.py --check` | yes (`verify.yml`) | — |
| `build_asset_library.py --check` | yes (`verify.yml`) | — |
| `asset-language/check.py all` | yes (`verify.yml`) | **OK** locally |
| `check_item_models.py` (corpus: duplicates, silhouettes, UVs) | **no** | **was crashing** (`data/items.json` not found). Fixed on this branch |
| `tools/asset-production/tests` | **no** | 4 errors: stale repo-root paths in `test_asset_set`; `test_model_census` imports the deleted `mesh_recipe` |
| `tools/blender/tests` (host part) | partly | `discover` **stops the whole run** with `SystemExit` at the first test that needs Blender, instead of skipping it |

---

## 3. What works, and must be kept

These are what make agent authoring possible at all. Any change should keep
them.

1. **One-way source authority** (`BLENDER_CORE.md`, `assets/authoring/items/README.md`).
   A script may scaffold a `.blend`. After that the `.blend` wins. The compiler
   hashes the source before and after a run, so "compile" can never mean
   "overwrite the art". `save_source_blend` refuses to overwrite without
   `--force`.
2. **Status as a record, not a guess.** `environment-sources.json` (adopted /
   scaffold / superseded / reference, plus a `basis`) is checked by a gate.
3. **One Blender, one locator** (`blender_locator.py`, `blender-pin.json`, with
   the version asserted). The 09-28 audit's top finding is closed.
4. **Fail loud.** `GrammarError` names the field. `validate_item_obj_runtime.py`
   rejects faces the LÖVE loader would reject. `item_mtl_runtime.py` caps
   overlay passes at the shader's two.
5. **`Interior` reads like prose.** `alicias_padaria.py` is the best worked
   example in the repo. Every prop has a reason from the game's text, the
   variant axes are explicit, and there is one SHIPPED constant. Its comments
   are art direction, not narration.
6. **The corpus gate idea** (`check_item_models.py`). It normalises geometry
   before hashing and compares silhouettes at display resolution. This is the
   right defence against "a renamed box passes every check".
7. **The live bridge's safety model** (fingerprinted mutations, no arbitrary
   Python, no save, one undo step per request).

---

## 4. Flaws, ranked

### F1 — Path rot since #700, and nothing noticed (high)

Since #700 the repository root is only the Thestra installation. Game data and
assets live in `projects/hichaukitoden-game/`. These Python files still build
paths under the root:

```text
tools/asset-production/{asset_set,item_model_corpus,build_food_cohort,
                        build_item_models_53_62,_63_72,_149_158}.py
tools/blender/{build_world_props,depth_baseline}.py
tools/asset-gen/{blendergeom,surface_baselines_v2,make_matcaps,
                 run_first_stratum_overnight,build_*_2026080x}.py, blender/build_surface_v2_preview.py
```

Effects:

- `check_item_models.py`, the only gate against duplicate or indistinct item
  shapes, crashed on start (`FileNotFoundError: data/items.json`). **Fixed on
  this branch**: `item_model_corpus.PROJECT_ROOT`, and model paths now resolve
  against the Project.
- `build_world_props.py` refuses any output outside `ROOT/assets`, a directory
  that no longer exists. The First Stratum world-prop lane documented in
  `tools/asset-production/README.md` is dead.
- `MODEL-CENSUS.md` describes `build_model_census.py` and `mesh_recipe.py`, and
  **neither file exists**. Its test module fails to import.

The root cause is structural. **35 Blender tools hard-code
`projects/hichaukitoden-game`**, and the others hard-code the old root, so
there is no single place that says "the Project". These tools are not in CI, so
they break without anyone noticing. This breaks the AGENTS rule "enforce with
gates, not vigilance".

**Fix.** Add one `tools/shared/project_paths.py`, honouring
`SECOND_RITE_PROJECT` with the game Project as the default, and make every tool
use it. Add `tools/asset-production/tests` and `check_item_models.py` to
`verify.yml`. Delete or archive what cannot be repaired: the census docs and
test, and the cohort builders.

### F2 — No routing layer for intent (high, cheap)

An agent asked to "make a lantern prop", "make a new shop interior" or "give
this sword a source" has to rebuild the map of lanes from `AGENTS.md`'s
"Where things live" paragraph, `BLENDER_CORE.md` (419 lines),
`assets/authoring/items/README.md` (mostly migration history) and the 728-line
interior brief. The Blender skill **sent agents to the wrong layer**:

- it described composing primitives with `second_rite_asset_core` and exporting
  OBJ. That is the item *toolkit's* lane, not the production per-item `.blend`
  lane that CI enforces;
- it never mentioned `compile_item_blends.py`, `recipes/interior.py`,
  `furnishings.py`, `exterior.py`, `house_grammar`, ground cover,
  `material_library.py` or `environment-sources.json`;
- it listed 12 material ids where 23 exist.

A weak agent following it would build a parallel exporter, or write a new
`.blend` without registering it.

**Fix (done on this branch, first pass).** The skill now opens with an
intent → lane → entry point → gate table and points at `materials.json` instead
of copying it. Next step: a top-level `tools/blender/README.md` that is
**only** that table plus "never touch" rules, with one link per lane to the
long brief.

### F3 — Production, studies and one-shot surgery in one namespace (medium)

Of the 85 top-level scripts, about 30 are production entry points:

- **15 `study_*`** are investigations whose conclusions now live in reports;
- **13 revision-surgery scripts** for the Passage Office
  (`define_registry_bay`, `extend_registry_frontage`, `fit_registry_ceiling`,
  `finish_registry_shell`, `refine_registry_cabinet`, …). Each turned revision
  `rN` into `rN+1` of one room. They are history, not tools;
- **6 orphaned migration lists** (`a-migration-items.txt`, … 0 references) and
  3 more in `tools/asset-production/`;
- a second, **differing** copy of `second_rite_item_exporter.py` under
  `tools/asset-gen/3d items/`;
- the legacy depth pipeline (`depth_baseline.py`, "historical diagnostics").

For a weak agent, `grep -l interior tools/blender` returns surgery scripts and
studies alongside `recipes/interior.py`, and it will copy the nearest example.
A one-off surgery script that hard-codes a vertex-component heuristic (for
example `define_registry_bay.py: support_counter`, which picks components by
bounding-box volume) is the worst possible template.

**Fix.** Split by role: `tools/blender/{core,authoring,bake,review}/`, plus
`studies/` and `archive/` that are excluded from agent routing (or simply
deleted, since git keeps history). If moving files is too disruptive, add a
`SCRIPTS.json` manifest (`production | study | one-shot | legacy`) with a check
that every new top-level script declares its role, and make the README table
list only `production`.

### F4 — A revision is a new binary file (medium–high, compounding)

`candidates/passage_office/` holds `passage_office_r2.blend` … `r13.blend`,
76 MB of binary snapshots with no LFS. `registry_workflow.py` *requires* a new
output directory per run. The habit is reasonable inside one session: never
mutate the last good state. Committed to the repository it creates:

- permanent clone cost (`.git` is 308 MB);
- ambiguity about which revision is the real one (the
  `environment-sources.json` record says 10 scaffold and 1 superseded, with no
  adopted file);
- one report per step (8 Passage Office reports on 2026-10-02).

**Fix.** Revisions live in git history, not in file names. Keep the adopted
file and at most the newest candidate. Track `*.blend` with LFS, or move
candidates out of the repository. One report per *decision*, not per step.
Teach `registry_workflow.py` a `--scratch` mode that writes under `out/`.

### F5 — The environment vocabulary is positional floats with sign conventions (medium)

`interior.py`'s frame is `+X = camera forward (depth)`, `-Y = screen right`,
`+Z = up`. Recipes pass tuples such as `(y0, y1, z0, z1)` for a back-wall window
but `(x0, x1, z0, z1)` for a side window, and `side=-1` means *screen right*.
`room.part(name, size, location, mat)` is a raw box. This is fine for a careful
agent with the brief open. A weak agent will:

- swap `x` and `y` in a side-wall opening;
- put a prop at the screen-left/right mirror image;
- place furniture inside a wall because nothing checks overlap;
- break the character-floor limit (`CHARACTER_FLOOR_LIMIT = 144`), which is
  documented, not checked.

The house grammar shows the alternative already exists in this repository:
plain data with eager validation, and named elevations (`front`, `back`,
`left`, `right`).

### F6 — No catalogue: nobody can see what exists (medium, cheap)

`furnishings.py` has 49 functions (`bread_oven`, `weapon_rack`, `record_bay`,
`azulejo_dado`, …). Nothing lists them with their parameters, their footprint,
or a picture. The in-repo asset library has one entry. An agent therefore
either reads 1,200 lines or re-invents a `barrel` with `room.part`. Duplicated
props are exactly the drift the corpus gate exists to catch for items, and
nothing catches it for environments.

### F7 — The item corpus's expressive ceiling (medium)

- 173 of 205 item OBJs have no editable source. They were produced by batch
  scripts, and some of those scripts now write to a dead path (F1).
- 124 have **no UVs**, so the texture track, matcaps by UV, or painted detail
  cannot use them.
- Runtime look is flat `Kd` plus at most two overlay passes. The passes are
  authored as a JSON string in a custom property per material
  (`sr_runtime_passes_json`): verbose, easy to get wrong, and invisible in the
  Blender UI.
- The A/B/C vocabularies (lathe, fabrication, sweep) are well documented as
  *prose* in the item README, but there is no template to start from. The
  one-shot migration machinery was deliberately deleted, so each new item
  starts from an empty `.blend`.

### F8 — The feedback loop is expensive for an agent (medium)

- G5 is owner-bound, and Blender is not present in most agent containers.
- `python -m unittest discover -s tools/blender/tests` ends the whole run with
  `SystemExit` ("BLENDER_EXECUTABLE is not set") at the first test that needs
  Blender, so the bpy-free tests that come after it never report. Those tests
  should `skipTest` with the same message.
- There is no one-command "render this recipe through the town camera to a PNG
  plus a metrics JSON" for agents. The pieces exist (`stage_room_model.py`,
  `photograph_room_package.py`, `wide_screen.py`) but each has its own flags.

### F9 — Docs mix contract with history (low–medium)

`BLENDER_CORE.md` and `assets/authoring/items/README.md` are about 60%
narrative history (cohort migrations, 5.0 UV dedup episodes, which items moved
when). That is valuable as reports and costly as instructions. For a weak
agent, every paragraph of history is a chance to copy an obsolete step. The
interior brief (728 lines) is excellent art direction, but its "fixed
contract" and "rules that are not negotiable" sections could be checks (§5.5).

### F10 — Exteriors ship with no worked example "on purpose" (owner decision)

`AGENTS.md` says `exterior.py` "ships with no worked example on purpose". This
probably exists to stop clones of one exterior. For a weaker agent, though, a
worked example is the single most valuable aid. Without one, it improvises
the three-rank near stack and the camera distance and gets them wrong. A
middle path: a worked example that is clearly *not a place* (a neutral test
street in the Gate-Room spirit), so copying it yields correct structure but no
St. Maria identity to clone. This is the owner's call (#1350). It is listed here
because it bears directly on the weak-agent goal.

---

## 5. High-gain areas for expressive potential

Ranked by expressive gain per unit of cost and risk. Each item respects the
non-negotiables: one semantic authority, fail loud, data over code, no
compatibility shims.

### 5.1 Declarative place specs: the biggest lever

Make a room (later an exterior) a **validated data document** that the
existing `Interior`, furnishings and house grammar compile. Do not build a new
engine. Sketch:

```json
{
  "asset": "alicias_padaria",
  "brief": "docs/design/st-maria-shop-briefs.md#padaria",
  "room":  { "depth": 6.8, "ceiling": 3.7, "floor": "terracotta", "beams": 5 },
  "walls": {
    "back":         { "openings": [ { "kind": "window", "at": "center-0.3", "width": 1.6, "sill": 1.45, "head": 2.75 } ] },
    "screen_right": { "openings": [ { "kind": "window", "from_front": 1.5, "width": 1.8, "sill": 1.55, "head": 2.95 } ] }
  },
  "exit": { "at": -3.15 },
  "dado": { "kind": "azulejo", "height": 1.05 },
  "furnish": [
    { "use": "bread_oven", "id": "oven", "against": "back", "at": "screen_left" },
    { "use": "counter",    "id": "counter", "at": [0.5, -0.5], "length": 3.6, "height": 0.88 },
    { "use": "bread_basket", "on": "counter", "at": 0.55 }
  ],
  "lights": [
    { "kind": "fire", "near": "oven", "energy": 34 },
    { "kind": "window", "for": "back.window[0]" }
  ]
}
```

What this buys:

- **Screen-space names** (`screen_left`, `back`, `on: counter`, `against: back`).
  The grammar resolves them once, so the sign conventions behind F5 stop being
  the author's problem.
- **Eager validation with field names** (the house-grammar pattern): unknown
  furnishing, opening outside the wall, prop overlapping a wall or another
  prop's footprint, floor-limit breach. Each is a `SpecError` that names
  `furnish[2].at`.
- **Variants as data.** `"variants": {"partition": {...patch}}` replaces the
  `if variant == ...` branches.
- **Studio can edit it.** A JSON spec goes through the same schema-form layer
  as everything else (`entity-forms.js`). The Python recipe cannot.
- **Agent authoring becomes filling in fields.** A Tier-0 agent (§7) can add a
  barrel. A Tier-1 agent can compose a new shop.

Constraints:

- **One authority.** For a given room, either the spec or the Python recipe is
  the source, never both. Migrate one room as the pilot (the Padaria is the
  natural choice, because its recipe is already declarative in spirit), then
  delete its Python recipe.
- The spec scaffolds a `.blend` exactly as recipes do today. Adoption rules are
  unchanged: once adopted, the `.blend` wins.
- The Python `Interior` API stays as the escape hatch, the way `SCRIPT` is for
  events. Count escape-hatch uses so their growth stays visible.

### 5.2 A kit catalogue made by a generator, plus a completeness gate

A `catalogue_furnishings.py` that, for each public function in
`furnishings.py` (and later each house-grammar element and kit part):

- builds it with default parameters in an empty room;
- renders a flat-colour thumbnail (the census contact-sheet convention);
- records footprint, height, materials, parameters and defaults from the
  signature and docstring;
- writes `tools/blender/recipes/FURNISHINGS.md` plus a contact sheet.

The gate fails when a public function is missing from the catalogue, or has no
docstring. This is the Blender equivalent of "a context with no editor surface
is a command nobody can write": **a furnishing with no catalogue entry is a
furnishing nobody will reuse.**

Later, publish the catalogue entries into the in-repo asset library
(`build_asset_library.py` already has the pattern: CC0, provenance, a
`--check`). Then the owner can drag them into a scene by hand, the same parts
agents reference by id.

### 5.3 Data templates for item families

Turn the A/B/C prose into three scaffold templates driven by small JSON
parameter sheets:

| Template | Parameters | Blender result |
|---|---|---|
| `lathe` | profile points (r, z), segments, caps, material per span | Curve profile + live `SCREW`; native revolve UVs |
| `plate` | outline points, holes, thickness, mirror axis, bevel | planar mesh + `MIRROR` + `SOLIDIFY` |
| `sweep` | path points with radius and tilt, profile name, cyclic | Curve + hidden `bevel_object` |

The template **scaffolds** a `.blend` once (source authority rules apply after
that). It then runs the compiler, the runtime validator and the corpus gate in
one command:

```text
python tools/blender/new_item.py --template lathe --params my_vial.json --item vial_of_rain
```

This gives cheap, UV-bearing, gate-checked replacements for the 173 legacy
OBJs. The silhouette gate already stops a lazy template use from shipping
another indistinct bottle.

### 5.4 Named finish presets

Add a finish block to `materials.json`, or to a sibling `finishes.json`:

```json
"finishes": {
  "sheen.ruby":  [{ "uvSource": "sphere", "blend": "add", "strength": 1.0, "texture": "assets/models/matcaps/ruby.png" }],
  "rim.cold":    [{ "uvSource": "sphere", "blend": "screen", "strength": 0.6, "texture": "assets/models/matcaps/cold.png" }]
}
```

A material then carries `sr_finish = "sheen.ruby"`. The compiler expands it,
validates it against the same two-pass vocabulary, and writes it to the MTL.
This keeps the README's intent (passes are per material, not implied by the
semantic id) while making the common case one word instead of a JSON string.
`sr_runtime_passes_json` stays the escape hatch.

### 5.5 Staging predicates for interiors (the brief, checked)

`house_grammar/staging.py` already tests camera predicates before anything
renders. Do the same for `Interior.finish()`. These need no render, only the
camera record:

- no walkable geometry below `CHARACTER_FLOOR_LIMIT`; floor reaches
  `FRAME_BOTTOM_NATIVE_Y`;
- exit threshold faces outward (the brief's threshold-direction rule);
- no light of type `SUN`, or anything the brief calls a key light;
- every light either sits within a set distance of an emissive or source
  object, or carries an explicit `reason`;
- no prop's bounds intersect a wall's or another prop's (with an explicit
  `allow_overlap` for intentional nesting).

Every rule moved from the brief into a check is one less thing a weak agent
must remember, and one less review round for the owner.

### 5.6 States and articulation as first-class data

`first_stratum/treasure_chest.py` exports `closed` and `open` from one recipe.
`architectural-assembly-authoring.md` defines hinge semantics (0° closed, 180°
folded). Making "states" a generic part of the spec (`"states":
{"open": {"lid.hinge": 110}}`) would let doors, shutters, chests and gates use
one mechanism, with each state as a static export the event system can swap.
That is expressive reach the engine's event-page model can use right away.

### 5.7 A read-only "describe" for the live bridge

The bridge already fingerprints the scene. A `describe` operation that returns
a compact, human-readable outline would let a weak agent understand an adopted
document before proposing a change. The outline would give collections, each
object's role, material and bounds, and its relation to the source-authority
root. Today that agent would have to interpret raw `inspect` JSON.

---

## 6. Noise and redundancy: a deletion list

Each line is safe to remove or archive, by the evidence shown.

| Path | Evidence | Action |
|---|---|---|
| `tools/blender/{a,b,c-profile,c-source}-migration-items.txt`, `organic-hybrid-items.txt`, `relic-showcase-blend-items.txt` | 0 references | delete |
| `tools/asset-production/{newest-batch,salvaged-item-models}.txt` | 0 references | delete |
| `tools/asset-production/build_item_models_{53_62,63_72,149_158}.py`, `build_food_cohort.py` | one-shot cohorts; write to the dead root `assets/` | archive (git history) |
| `tools/asset-production/MODEL-CENSUS*.md`, `tests/test_model_census.py`, `materialize_model_census.py`, `census-bootstrap/` | describe deleted `build_model_census.py` / `mesh_recipe.py`; test fails to import | delete, or restore the tool deliberately |
| `tools/blender/*registry*.py` (13) | one-off r→r+1 surgery on one candidate room | move to `archive/` or delete |
| `tools/blender/study_*.py` (15) | conclusions recorded in reports | move to `studies/`; exclude from routing |
| `candidates/passage_office/passage_office_r2…r12.blend` | superseded snapshots, about 70 MB | keep newest + adopted only (owner call) |
| `tools/asset-gen/3d items/second_rite_item_exporter.py` | second, differing copy of the toolkit exporter | delete, or make it a byte-checked vendor copy |
| history sections in `BLENDER_CORE.md` and the item README | narrative, not contract | move to `docs/reports/`, leave one-line links |

---

## 7. The capability ladder

A practical map from agent capability to safe work. The aim is to push each
task **one rung down** by building the tooling in the right column.

| Rung | Who | Safe tasks today | Tooling that moves more work to this rung |
|---|---|---|---|
| 0 | lowest effort; follows a table | Run a gate and read its verdict. Compile items. | **Routing table** (F2, done). Skip-not-exit host tests (F8). |
| 1 | fills in fields | Edit a parameter in an existing recipe (risky: F5) | **Place spec** (5.1), **item templates** (5.3), **finish presets** (5.4): authoring becomes valid-or-rejected data |
| 2 | composes known parts | Write a new interior with `Interior` and furnishings (needs the 728-line brief) | **Catalogue** (5.2) and **staging predicates** (5.5): it can see the parts, and mistakes fail fast |
| 3 | extends the vocabulary | Add a furnishing, opening family or grammar operation | Catalogue gate (every new part documented and pictured). One `project_paths` (F1) so new tools are not born broken |
| 4 | owner-level judgment | Adopt or hand-edit a `.blend`; rebake shipped packages; recapture G5 | Unchanged by design. These stay owner calls |

Rule of thumb for future tooling: **if a mistake at rung N can only be caught
by a rung N+2 reviewer, a check is missing.**

---

## 8. Recommended sequence

Ordered so that each step makes the next one cheaper. These are candidates for
Issues, not a checklist. Each carries an acceptance test.

| Step | Work | Accept when |
|---|---|---|
| 1 (#1341) | `project_paths.py`; migrate the 22 root-path files; add `asset-production/tests` and `check_item_models.py` to `verify.yml` | Both run green in CI. `grep` finds no repo-root `assets`/`data` path in `tools/` |
| 2 (#1342) | Deletion list (§6) | The 85 top-level scripts drop to ≤ 35 production entries. No orphan lists |
| 3 (#1343) | `tools/blender/README.md` routing table; history moved out of `BLENDER_CORE.md` and the item README | Each lane reachable in ≤ 2 hops from `AGENTS.md` |
| 4 (#1344) | Host tests `skipTest` without Blender | `discover` reports every bpy-free test without a Blender install |
| 5 (#1345) | Furnishings catalogue + gate (5.2) | Every public furnishing has a docstring, thumbnail and parameter row; gate red otherwise |
| 6 (#1346) | Interior staging predicates (5.5) | Each rule has a negative-control test |
| 7 (#1347) | Place-spec pilot on the Padaria (5.1) | Spec-built `.blend` is geometrically equivalent to the recipe-built scaffold; Python recipe deleted |
| 8 (#1348) | Item templates (5.3) + finish presets (5.4) | One legacy item replaced end to end by a rung-1 agent through `new_item.py`, passing compile, runtime and corpus gates |
| 9 (#1349) | Revision policy for candidates (F4) | Candidate folder holds ≤ 2 `.blend`; LFS or out-of-repo decided by the owner |

---

## 9. Changes made with this report

- `tools/asset-production/item_model_corpus.py`: item data and model paths
  resolve against the Project (`PROJECT_ROOT`), not the old repo root. The
  corpus gate runs again: `ITEM MODELS OK` with the owner-signed baseline
  unchanged (11 duplicate geometry, 124 without UVs, 1 shared file).
- `tools/asset-production/check_item_models.py`: the `shared_file` detail is
  computed relative to the Project. It no longer assumes four path levels,
  which crashed the negative-control test on a temp directory.
  `test_item_model_corpus.py` passes 19/19 (it had 3 errors).
- `.claude/skills/second-rite-blender-modeling/SKILL.md`: an intent-routing
  table at the top, the correct production lane for items (per-item `.blend` →
  `compile_item_blends.py`), the environment lane, and a pointer to
  `materials.json` in place of a stale copy of its ids.

Still broken, not fixed here (each is step 1 above): `test_asset_set.py`
(3 errors, repo-root paths), `test_model_census.py` (imports a deleted module),
`build_world_props.py` (refuses every output path), and the other root-path
tools listed in F1.

### Follow-up (owner approved, 2026-10-04)

- #1349: Passage Office revisions r2–r12 (and the r3 dependency record) were
  removed from the tree. r13 stays as a `reference`; it is byte-identical to the
  adopted `environments/passage_office.blend`. `environment_sources.py --check`
  now covers candidate folders: same record, no `adopted` candidate, at most two
  `.blend` files. The policy is in `BLENDER_CORE.md`.
