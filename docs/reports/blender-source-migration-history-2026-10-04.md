# Blender source migration history (snapshot 2026-10-04)

Historical evidence moved out of the live contracts for #1343. Counts and
version observations below belong to their original episodes; they do not
assert present status or prescribe new authoring. Source snapshot:
`205f99fb26822e289342b69d8c68875aceb6c869`.

## Item migration cohorts

## Migration status

Existing canonical OBJ models are allowed to predate this source convention. Do not manufacture anonymous baked `.blend` wrappers merely to claim migration.

Move a model here when its useful construction intent has actually been represented as an editable Blender document and its compiled output has been reviewed against the current canonical runtime model.

The first production C migration establishes editable curve authority for:

- `barbed_spear.blend`
- `blackroot.blend`
- `cerberus_fang.blend`
- `water_scepter.blend`

These retain separate semantic curve parts, per-point radius/tilt and material bindings rather than importing a baked OBJ as the source.

The second C migration adds explicit editable profile-object authority for:

- `hermes_boots.blend`
- `mimic_tongue.blend`
- `molten_manacle.blend`
- `phoenix_pinion.blend`

Together, all eight Batch-C production items now have real Blender source authority. The second cohort was visually reviewed against the canonical LÖVE item viewer before acceptance; the static-profile limitation remains documented rather than silently replaced by Geometry Nodes.

The production B migration adds editable fabrication authority for:

- `greatsword.blend`
- `death_sickle.blend`
- `silver_glasses.blend`
- `gas_mask.blend`
- `moth_cloak.blend`
- `mirror_armor.blend`
- `angel_feather.blend`
- `rear_mirror.blend`

The canonical and preserved Batch-B viewer boards were byte-identical at migration time, so this cohort changes source authority rather than deliberately redesigning the items. The Blender-authored products were then reviewed against that same real-viewer target before acceptance.

The production A migration adds editable semantic-sculpture authority for:

- `forbidden_lamp.blend`
- `town_portal.blend`
- `crossing_writ.blend`
- `smoke_bell.blend`
- `mourning_ribbon.blend`
- `first_scale.blend`
- `bell_salt.blend`
- `sealed_reliquary.blend`

The canonical and preserved Batch-A viewer boards were also byte-identical at migration time. The Blender sources preserve the accepted relic identities while replacing external recipes with directly editable profile/revolve construction. After the A, B and C migrations, **24 production item models have real per-item Blender source authority**.

### Six-item relic content migration

The next production pass moved six established relics into ordinary editable Blender source authority:

- `black_hinge.blend`
- `chrysalis_sigil.blend`
- `qilin_bell.blend`
- `vial_of_second_breath.blend`
- `meteorite_plate.blend`
- `philosophers_stone.blend`

This cohort deliberately exercised the source model as an **art iteration loop**, not merely a migration. The initial six `.blend` documents compiled correctly, but real-viewer review rejected Black Hinge, Chrysalis Sigil and Vial of Second Breath on visual grounds. Their already-committed Blender documents were then opened and edited directly; the bootstrap was not rerun.

Black Hinge's leaf/halo hierarchy was rebalanced, Chrysalis gained authored depth across its cocoon/ribs/petals, and Vial's six breath gestures ultimately changed from round tube bevels to one shared editable flattened Curve profile. Meteorite Plate was a particularly strong visual improvement from the first Blender pass, while Qilin Bell gained a genuinely hollow editable wall profile and Philosopher's Stone gained independently editable orbit Curves.

After this pass the production corpus contains **30 authoritative per-item `.blend` sources**. The full set reproduces byte-for-byte through `compile_item_blends.py --check`; the individual source files remain the authority and no migration/refinement generator is retained for these six relics.

See `docs/reports/relic-showcase-blender-content-2026-08-15.md` for the visual-review and validation record.

### Salvaged-set completion

The final source-authority pass adds the last two models from the 32-item salvage set:

- `pile_bunker.blend`
- `celestial_fossil.blend`

Pile Bunker keeps its industrial housing, driver, rails, chamber, grip, crank and fittings as a named editable assembly. Celestial Fossil keeps the slab, fossil spiral, mineral veins and embedded nodule separate; its bored-through void is real topology and the hidden cutter remains as an authoring guide after deterministic Boolean materialization.

With these two sources, **all 32 item models salvaged by #582 now have authoritative per-item Blender source documents**. The complete set reproduces through `compile_item_blends.py --check` without source-byte mutation or numbered Blender backups, and the final real-viewer 32-item comparison was accepted before the one-shot migration machinery was removed.

See `docs/reports/final-salvaged-item-blend-authority-2026-08-15.md` for the 32/32 graduation record.

## Profile/revolve migration UVs

The migrated A sources use Blender's native generated revolve UVs and pass the ordinary production `--check`; they do not require the deterministic corner-atlas workaround used by the material-only Batch-B migration.

## Fabrication exporter observations and source exceptions

The migrated B cohort also exposed an OBJ-export detail worth keeping explicit. Blender 5.0 may deduplicate coincident UV corners differently across otherwise identical exports when modifier-generated surfaces overlap in UV space. These material-only migrated sources therefore carry deterministic per-corner UV coordinates. Live mirrored geometry offsets the generated side by one U tile so the useful `MIRROR` relationship can remain live without overlapping the authored side's UV set. If a future item needs painted image textures, replace this migration UV layout with ordinary authored UVs directly in its `.blend`.

Three narrow source exceptions were required by the accepted cohort:

- Death Sickle materializes the crescent's thickness after its editable inner/outer contour is authored;
- Silver Glasses materializes authored-half thickness while preserving live `MIRROR` symmetry;
- Rear Mirror materializes fabrication thickness while preserving its editable planar design geometry.

These are exporter-determinism decisions, not new mandatory B rules.

## Curve frame calibration

When translating old Batch-C roll values, note that its transported sweep frame and Blender's native minimum-twist bevel frame used perpendicular zero-roll bases. That historical migration required one +90° tilt calibration. New Blender-native authoring should simply treat Blender's displayed profile frame as authority rather than preserving that legacy offset as a permanent runtime convention.

## First Curve source migration

The first production C migration places Barbed Spear, Blackroot, Cerberus Fang,
and Water Scepter under this authority as editable Curve-based documents. Their
compiled products were reviewed through the real four-angle item viewer against
the canonical pre-migration models; coordinate-frame and material-pass drift
found during that review were fixed at the source/compiler boundaries rather
than accepted as migration noise.

## Blender version drift

Blender's output is not stable across versions. Under 5.0 the OBJ exporter
occasionally emitted different UV tables for identical sources
(`docs/reports/b-item-blend-source-migration-2026-08-15.md`), and the Geometry
Nodes item `phoenix_pinion` moved by up to about 2 mm between 5.0.1 and 5.2.2. That is why the pin is exact, and why a pin change re-runs
`compile_item_blends.py --check` and may move an asset-regression baseline.

## Frozen editor fixture measurements

Why leaving it stale is safe, measured on 2026-09-30 under Blender 5.2.2: the
fixture's 32 sources compile to products byte-identical to the game project's.
Against the fixture's committed products, 31 differ only in the header comment
and object group names, and `phoenix_pinion` also differs in vertex positions (at
most about 2 mm). G6 previews exactly one model, `bottle_family__basis.obj`,
which is not compiled from any of those 32 sources, and its model-picker list
shows file names only. If the fixture is ever refreshed on purpose, compile with
`--output-dir` into a scratch directory, compare, and run G6 before committing.

## Legacy ray-cast repeatability

The legacy depth pipeline sampled evaluated Blender geometry with first-hit ray
casts. Repeated Blender 5.1.2 diagnostics proved that
`wall_boulders_rough` was not pixel-repeatable on one machine. That experiment
is retained as evidence but no longer defines the future surface contract.
