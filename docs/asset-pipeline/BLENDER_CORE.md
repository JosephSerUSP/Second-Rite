# Shared Blender Asset Core

Phase 4 establishes `tools/blender/second_rite_asset_core.py` as the canonical
low-level Blender infrastructure module for scene cleanup, collections,
selection preservation, local transforms, materials, modifiers, metadata,
bmesh objects, bounds, and OBJ export.

The item-model pipeline continues to use Blender as an authoring and export
authority. Surface baselines do not: their canonical numeric field is generated
before Blender and Blender receives it only as an inspection derivative.

## Canonical and vendored core

```text
tools/blender/second_rite_asset_core.py
tools/asset-language/contract.json
tools/asset-language/materials.json
```

The standalone item toolkit vendors byte-identical copies under:

```text
tools/blender/second-rite-item-model-toolkit/vendor/
```

Synchronize and check them with:

```text
python tools/blender/sync_asset_core.py
python tools/blender/sync_asset_core.py --check
```

Generated item-library `.blend` files embed the exporter, shared core, contract,
material registry, and toolkit readme as Text blocks.

## Item-model guarantees

The shared exporter preserves:

- selected geometry only;
- UVs and normals;
- material groups and MTL output;
- applied modifiers and triangulation;
- Blender `-Z` forward and `Y` up OBJ axes;
- authored root transforms;
- selection and active-object state;
- temporary collection cleanup;
- static shape-key variants.

The Phase 4 item checks continue to require 49 marked roots, 53 OBJ outputs,
structural OBJ equivalence, ordered `usemtl` equivalence, parsed MTL semantic
equivalence, vendor synchronization, and no provider or production writes.

## Per-item editable source authority

The production destination for individually authored item models is one Blender
document per item:

```text
assets/authoring/items/<item_id>.blend
        ↓ read-only evaluation
assets/models/items/<item_id>.obj
assets/models/items/<item_id>.mtl
        ↓ runtime-parity validation
LÖVE item geometry
```

The `.blend` is source authority once it has been created and committed. The
runtime OBJ/MTL pair is a compiled product. An external script may scaffold a
new Blender document, but ordinary compilation must never regenerate or save
the source document: doing so creates meaningless binary churn and can overwrite
human art direction.

A production source has exactly one marked export root and uses the ordinary
shared asset metadata plus:

```text
item_export = true
item_export_name = "<item_id>"
sr_source_authority = "blend"
```

The filename stem and `item_export_name` must agree. Blender-native construction
history beneath that root is intentionally open-ended: meshes, profiles, Curve
objects, Boolean cutters, modifiers, instances, Geometry Nodes, guides, and
manual exceptions may all coexist when they are useful authoring handles.

A/B/C from the 2026-08 item studies are therefore authoring vocabularies rather
than separate runtime backends:

- A: profile/revolve and semantic-volume composition;
- B: outline/thickness/Boolean fabrication;
- C: curves/taper/roll/spatial gesture.

Blender is the composition environment that can mix those vocabularies. The
shared architecture belongs below them at evaluation, finalization and runtime
validation.

### Read-only compiler

Use:

```text
python tools/blender/compile_item_blends.py
```

The host wrapper hashes every `.blend` before and after compilation. Blender
opens the existing source and `tools/blender/compile_item_blend.py` evaluates a
temporary duplicate through `second_rite_asset_core.export_asset_root()` without
saving the file. `tools/blender/validate_item_obj_runtime.py` then rejects OBJ
faces the LÖVE geometry loader would reject, including repeated-index and
zero-area triangles.

Blender's stock MTL exporter does not know Second Rite's runtime overlay-pass
vocabulary. A source material may therefore carry `sr_runtime_passes_json`.
`tools/blender/item_mtl_runtime.py` validates at most two passes against the
same `uv`/`sphere` and `add`/`subtract`/`multiply`/`screen`/`mix` vocabulary as
`presentation/retro_mesh_shader.lua`, then the item compiler writes those
passes into the emitted MTL. This binding is per authored Blender material, not
globally implied by a semantic material id; the same `crystal` material family
can legitimately have a ruby sphere sheen in one source and no overlay in
another.

CI uses `--check`: products are compiled into a temporary directory and compared
byte-for-byte with the checked-in OBJ/MTL, while the source hash must remain
unchanged. Blender `.blend1`/`.blend2` backups are workstation state and are not
source assets.

Existing canonical OBJ models may predate this convention. They should be
migrated only when their useful construction intent has actually been preserved
as an editable `.blend`; wrapping a baked OBJ in an anonymous Blender file does
not count as source migration.

The first production C migration places Barbed Spear, Blackroot, Cerberus Fang,
and Water Scepter under this authority as editable Curve-based documents. Their
compiled products were reviewed through the real four-angle item viewer against
the canonical pre-migration models; coordinate-frame and material-pass drift
found during that review were fixed at the source/compiler boundaries rather
than accepted as migration noise.

See `assets/authoring/items/README.md` for the author-facing convention.

## Environment source authority

An environment `.blend` under `projects/*/assets/authoring/environments/` has a
status in `environment-sources.json` beside it, and every shipped
`environment.json` records `provenance.sourceBlend`. Neither is inferred.

| status | meaning |
|---|---|
| `adopted` | the source authority; edit it directly, never regenerate it; packages are baked from it |
| `scaffold` | regenerable recipe output; nothing shipped is baked from it |
| `superseded` | replaced by `supersededBy`; tools refuse to write it, and no package may cite it |
| `reference` | kept for looking at; not a recipe output and not a package source |

Each entry carries a `basis`, the evidence for the status; only
`st_maria_praca_modelled.blend` is marked `ownerConfirmed`, the rest were recorded
from repository evidence. A package with no `.blend` (a 2D plate, an unreferenced
stub) records `sourceBlend: null` with a `sourceBlendNote`.

`python tools/blender/environment_sources.py --check` fails when a package lacks
the record, names a file that does not exist or is not `adopted`/`scaffold`, or a
`.blend` has no entry. It runs in `verify`. Every tool that writes an environment
`.blend` calls `environment_sources.refuse_superseded`; set
`SR_ALLOW_SUPERSEDED_ENVIRONMENT=1` to override it deliberately.

The Praca has two files on purpose (a52a411c): `st_maria_praca_modelled.blend` is
adopted and is what the shipped package is baked from; `st_maria_praca.blend` is a
572-triangle scaffold. The six tools that write it (`recipes/st_maria_praca.py`,
`refine_st_maria_praca.py`, `replace_st_maria_tree.py`, `mark_st_maria_exits.py`,
`reauthor_praca_spiral.py`, and the read-only `study_town_perspective.py`) are
scaffold-only and say so.

## Browsing asset libraries (read-only)

Blender 5.2 remote asset libraries are static JSON over HTTP, and every asset in
one carries a licence, an author, a catalogue and the SHA-256 of the `.blend` that
holds it. `tools/blender/asset_library.py` reads that listing with the standard
library only, so an agent can search it without Blender:

```
python tools/blender/asset_library.py info
python tools/blender/asset_library.py search brick --type MATERIAL --license CC0
python tools/blender/asset_library.py show "Bricks - Regular"
python tools/blender/asset_library.py provenance "Bricks - Regular"
```

It defaults to Blender's Online Essentials (all CC0) and takes `--url` for any
library root. Global options (`--json`, `--url`, `--blender`, `--any-blender`,
`--offline`, `--refresh`) go before the subcommand.

- **It fetches listing files and nothing else.** A `.blend` or a thumbnail is
  reported as a URL and a hash and never requested; a test asserts it.
- **Every listing file is verified** against the hash its parent declares and cached
  under that hash. A tampered or truncated file is an error, and an unchanged one is
  not fetched twice. The meta file is the root of trust (TLS is the only check on it).
- **Results are filtered to the pinned Blender** (`blender-pin.json`, as
  major.minor), because a library can ship one variant of an asset per Blender
  range and only one is usable. `--any-blender` lifts that.
- **`provenance`** prints the record to put in an asset inventory: library, licence,
  author, the file's URL, size and hash, the listing's index hash, and the Blender it
  needs.

It does not download or import anything. Vendoring an asset (copying the `.blend`
into the repository with that provenance record) is a separate, deliberate step,
because CI and builds must not depend on a remote host, and a downloaded `.blend` can
carry scripts: open one with `--disable-autoexec`, and append a named datablock
rather than adopting the file.

## Our own asset library (in the repository, not published)

`tools/blender/asset-library/` is a Blender asset library holding one asset, the
`SR_GroundCover` Geometry Nodes group, licensed CC0 (the owner's choice, 2026-09-30).
It has the same layout as a remote library (`_asset-library-meta.json`, `_v1/`, a
catalogue file), so the browser reads it like one:

```
python tools/blender/asset_library.py --url file:///D:/path/to/tools/blender/asset-library/ show SR_GroundCover
```

and Blender can add the directory as a local library in Preferences.

- The node group is defined by `ground_cover.build_group()`. The library `.blend` is a
  derived product and is never edited by hand. It is not byte-reproducible, so a
  rebuild changes its hash and the listing: run `python tools/blender/build_asset_library.py`
  only when the group changes, and commit the result.
- `build_asset_library.py --check` (in `verify`) fails when the listing no longer
  describes the file, the licence, author or catalogue is not the declared one, or an
  asset appears that `ASSETS` does not declare. `test_asset_library_group` (in the Blender
  workflow) fails when the group in the file is not the one the builder builds now.
- The library file holds the asset and nothing else, and the build refuses a group that
  something else uses, because a remote-style library asset must be self-contained.

**It is deliberately not served.** The direction is to consume content published
online, not to publish ours. Serving a library publicly puts our assets into the online
asset ecosystem, which needs stricter criteria than an in-repo library: at least an
owner-approved licence per asset, a provenance record, a demonstrated use in a shipped
scene, a review of the listing by a person, and a stable version story. Until those are
written down and met, nothing here is hosted or registered anywhere, and adding an asset
to `ASSETS` does not publish it.

## Ground cover on the adopted Praça

`tools/blender/recipes/adopt_praca_ground_cover.py` puts the `SR_GroundCover` modifier into
`st_maria_praca_modelled.blend` (#1270). It is a surgical edit in the style of
`replace_st_maria_tree.py`: it adds one collection, `GROUND_COVER_SET`, as a child of `TH_SOURCE`
(the exterior exporter walks `TH_SOURCE`; a collection linked to the scene alone is never baked),
and touches nothing else. The set holds the scratch terrain guide whose vertex group
`cover_density` carries the painted density, a copy of the walkable lane as the keep-out, the
tuft cards and the `GROUND_COVER` host. Run it again and it reports "already adopted" and writes
nothing. Placement layouts live in `tools/blender/ground_cover_placement.py`; the owner chose E
(building bases, tree rings and lane edges) at a 375-tuft budget met by scaling density, not by
truncation. After adoption the paint on the guide is the authority, not the layout function.

Saving through Blender drops any datablock nothing uses. The document carries a few (unused
actor-sprite preview materials), so the recipe gives them a fake user first and names them in its
output rather than losing them without a word. `test_ground_cover_adoption` runs the recipe on a
copy of the real document and checks that nothing that existed changed, that only cover datablocks
were added, that a second run writes nothing, and that every tuft is inside the frame, off the lane
and out from under the buildings. The shipped package is not regenerated by the recipe; a
regeneration is an owner-signed step.

## Lighting an EEVEE render from a source room

EEVEE draws emission but does not cast it, and a lamp inside a housing smaller than its own radius is
shadowed by it, where Cycles lets the glow out. Two render-time options close those gaps; neither writes the
source `.blend` (measurements and limits: `docs/reports/eevee-emissive-lights-2026-09-30.md`).

- `--emissive-lights` (`tools/blender/emissive_lights.py`) puts a rectangular area light on each room-facing
  emissive patch: watts = pi x emission strength x area, colour from the material, with an explicit reach.
  It turns off the probe volume's `capture_emission` so the glow is not counted twice.
- `--fixture-lights` (`tools/blender/light_fixtures.py`) switches off shadow casting on a small mesh that
  encloses a point or spot light and is smaller than the light's radius.

Both are on `stage_room_model.py`, `study_eevee_atlas.py` and `study_eevee_pilot.py`, and only apply to
`--engine eevee`. They are tested headless in the Blender workflow (`test_emissive_lights`,
`test_light_fixtures`).

EEVEE has no bake, so an EEVEE atlas is made by camera projection: `tools/blender/eevee_projection.py` is the
shared core (a beauty frame and a UV frame per lane camera, splatted into the atlas by UV). The interior
and exterior comparisons are `study_eevee_atlas.py` and `study_eevee_exterior.py`
(`docs/reports/eevee-exterior-praca-2026-09-30.md`; it found that the shipped Praça package's ground bakes
black, #1287).

### Baking a package's atlas with EEVEE

Both exporters (`export_room_environment.py`, `export_exterior_environment.py`) take `--bake-backend
cycles|eevee`; `eevee` is the default. `cycles` is the selected-to-active comparison bake.
`eevee` runs `eevee_bake.py` in its place: the beauty frames photograph the source meshes (with the joined
render mesh hidden), the UV frames the joined mesh, and the package contract, files and geometry are the
same. An EEVEE package records how it was made in `environment.json` at `provenance.bake`; a Cycles package's
manifest is unchanged.

The EEVEE settings (`--exposure`, `--probe-cells`, `--emissive-lights`, `--fixture-lights`,
`--eevee-option NAME=VALUE`) fall back to the environment's `eevee` record in `environment-sources.json`, then
to their defaults, and a setting on the command line wins. The record is checked by
`environment_sources.py --check`: known keys, right types, options as `NAME=VALUE`, and a `basis` saying
where the numbers came from. The current records are pilot-solved starting points for test subjects, not
sign-offs. Exposure defaults to neutral 0 EV. The earlier Cycles-matching studies are comparisons,
not a target brightness or an automatic exposure policy.

```
blender -b --python tools/blender/export_room_environment.py -- --blend .../alicias_padaria.blend ^
    --output out/padaria_3d --exit-y 6.5 --bake-backend eevee
```

### The Praça ground (#1287)

`ARCH_square_ground` is a zero-thickness double-sided sheet. The exterior exporter now keeps only its upward
face (in memory, never saved: the Cycles bake casts at the source, and a coplanar underside makes it bake
black), clips it to what the lane cameras can see, and allocates the atlas by view (`--atlas-layout view`,
the default; `legacy` and `--keep-full-ground` are the old behaviour). See the docstring of
`export_exterior_environment.py`.

## Which Blender runs what

Repository tooling that launches Blender (the item compiler, the map `.blend`
export, the town/room environment pipeline, the camera-parity check, and the
world-prop and asset-gen builders) finds it in one place:
`tools/blender/blender_locator.py`. It reads `BLENDER_EXECUTABLE` and requires
the exact version recorded in `tools/blender/blender-pin.json`; any other
version fails with a message naming both. CI installs Blender through
`.github/actions/install-blender` from the same file, so a pin change is one
edit. There is no `PATH` search and no fallback.

Blender's output is not stable across versions. Under 5.0 the OBJ exporter
occasionally emitted different UV tables for identical sources
(`docs/reports/b-item-blend-source-migration-2026-08-15.md`), and the Geometry
Nodes item `phoenix_pinion` moved by up to about 2 mm between 5.0.1 and 5.2.2. That is why the pin is exact, and why a pin change re-runs
`compile_item_blends.py --check` and may move an asset-regression baseline.

Two places are deliberately outside that rule.

**The item toolkit** (`tools/blender/second-rite-item-model-toolkit/`) is a
self-contained bundle meant to be extracted and run away from this repository. It
vendors its own core and carries an integrity manifest (`SHA256SUMS.txt`,
`TOOLCHAIN_MANIFEST.json`), so it cannot call the repo's locator or read the
repo's pin, and its scripts are not edited to follow it. It locates Blender
itself, accepts "5.0 or newer", and records the Blender it was validated with in
`validated_blender`. `tools/blender/tests/test_blender_locator.py` names it as the
only place an install-directory search may exist, and fails if that exemption
widens or points at a directory that is gone.

**The frozen editor fixture** (`projects/editor-fixture/`) exists so G6 does not
move with game content. Its item products under `assets/models/items/` were
compiled by an earlier Blender and are not re-checked: CI's `--check` covers the
game project only, and a pin change does not require regenerating the fixture.
Do not run `compile_item_blends.py --check --project-root projects/editor-fixture`
expecting green.

Why leaving it stale is safe, measured on 2026-09-30 under Blender 5.2.2: the
fixture's 32 sources compile to products byte-identical to the game project's.
Against the fixture's committed products, 31 differ only in the header comment
and object group names, and `phoenix_pinion` also differs in vertex positions (at
most about 2 mm). G6 previews exactly one model, `bottle_family__basis.obj`,
which is not compiled from any of those 32 sources, and its model-picker list
shows file names only. If the fixture is ever refreshed on purpose, compile with
`--output-dir` into a scratch directory, compare, and run G6 before committing.

## Surface baseline authority

The legacy depth pipeline sampled evaluated Blender geometry with first-hit ray
casts. Repeated Blender 5.1.2 diagnostics proved that
`wall_boulders_rough` was not pixel-repeatable on one machine. That experiment
is retained as evidence but no longer defines the future surface contract.

The V2 authority is:

```text
tools/asset-gen/surface_baselines_v2.py
assets/geometry/2_procedural_surface_baselines/
```

Canonical V2 outputs are fixed-point scalar fields serialized as `height_metric.png` and `depth_guide.png` by a repository-owned fixed PNG encoder. Source provenance normalizes line endings. Blender creates a 3×3 repeated or edge-padded preview patch only after checking the recorded field hash, and never ray-casts it back into canonical pixels.

See `docs/asset-pipeline/SURFACE_BASELINES_V2.md` for recipes, encodings,
commands, assets, and validation gates.

## Project modeling skills

Claude/Luna guidance is installed at:

```text
.claude/skills/second-rite-blender-modeling/SKILL.md
.claude/skills/second-rite-surface-baselines/SKILL.md
```

The Blender skill is adapted from the Apache-2.0 `blender-3d-modeling` terminal
skill and adds Second Rite coordinate, metadata, determinism, low-poly, preview,
and production-safety rules.

## Legacy diagnostic status

The following remain historical diagnostics rather than V2 acceptance gates:

```text
assets/geometry/1_blender_depth_maps/
tools/blender/depth_baseline.py
```

They must not overwrite or become hidden inputs to the V2 baseline set.

## Neutral EEVEE workflow

EEVEE is the default for room plates and both environment atlas exporters. Exposure starts at 0 EV; the room test records no longer carry gains fitted to Cycles. Adjust authored lighting, world fill, probe density and lighting shims to resolve lighting problems. Exposure overrides remain available for deliberate artistic choices. Cycles is an explicit comparison via `--engine cycles` or `--bake-backend cycles`; shipping packages are promoted separately after visual review.

Room plates read the same source lighting records as atlas exports. EEVEE enables emissive companion lights and fixture shadow release by default; `--no-emissive-lights` and `--no-fixture-lights` disable them for controls. Room plates default to two probe cells per metre; records retain the corridor density and threshold override. Exterior atlas records may leave probes off.

## Cutout alpha in environment atlases

`atlas_alpha.py` evaluates authored Principled alpha separately from lighting and camera coverage. Render copies preserve source UVs before atlas unwrapping. A temporary mesh in receiver UV space rasterises the opacity with EEVEE; the EEVEE projection UV pass uses this mask so leaf gaps reveal the geometry behind them. Both backends receive the same opacity, and texels outside geometry stay opaque rather than becoming accidental facade holes. Cycles exterior beauty allows eight transparent bounces so alpha cards do not block direct light at their transparent pixels.

The opacity adapter accepts UV-based Principled alpha. Geometry-dependent alpha and Transparent-BSDF graphs fail explicitly rather than silently yielding an opaque atlas. Package photographs use atlas alpha just as the runtime does. Source documents are never saved by these steps.

## Shared render quality profiles

`tools/blender/render_profiles.py` owns quality selection without importing Blender. `draft`, `lookdev`, `review` and `export` use Cycles with 64, 64, 128 and 64 samples respectively. Atlas size defaults to 1024 in drafts and exports. All resolve to native-size rendering and neutral exposure. Source photographs use Open Image Denoise; Cycles atlas exports use the bundled OIDN RT FAST filter independently on each UV chart. Charts smaller than 256 texels or eight texels across retain their raw detail. Padding contains only that chart's colors; alpha and gutters remain unchanged. Before baking, valid UV chart boundaries snap inward to texel centres at the actual atlas size; any chart with a collapsed/flipped triangle or a newly shared texel across islands retains its original UVs. Bake dilation remains in place. `--no-uv-texel-align` provides the unsnapped control. Alignment affects receiver UVs, never the source geometry. This is beauty-only filtering, so new materials still need detail inspection. `--atlas-denoise none` on the room/exterior exporters provides a raw control; `--samples 128` provides a higher-sample control. `cycles-comparison` remains an explicit eight-sample photograph comparison. Profiles do not own cameras, lighting, dimensions, probe density or output encoding.

Room staging, package photographs and wide-screen review accept `--render-profile`. Room staging defaults to `review`; `--samples`, `--engine` and `--supersample` are explicit overrides recorded in its report. Supersampling with a visible Walker fails: use `--no-walker` for an environment-only supersampled review. Walker is still measured before hiding. EEVEE camera projection remains an explicit comparison backend and retains its separate single-sample UV data pass; the production backend is Cycles selected-to-active. Town source photographs use review quality rather than inheriting the source engine. No tool saves an adopted source as a consequence of selecting a profile.
