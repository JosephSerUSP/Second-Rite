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
python tools/blender/compile_item_blends.py --blender /path/to/blender
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
