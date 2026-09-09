# Blender scene contract preflight

`scene_contract.py` is the read-only preflight boundary for authored town
scenes. It is deliberately independent of the exporters so a Blender panel,
CI, or an exporter can consume the same versioned result without reimplementing
role rules.

## Roles

Export roles are assigned only by explicit collection membership:

| Collection | Required | Allowed object types | Meaning |
| --- | --- | --- | --- |
| `TH_SOURCE` | yes | `MESH`, `CURVE`, `SURFACE`, `LIGHT`, `EMPTY` | source appearance, lights and transform parents |
| `TH_RENDER` | yes | `MESH` | real runtime/depth/silhouette mesh |
| `TH_COLLISION` | no | `MESH` | optional collision export only |
| `TH_ANCHORS` | yes | `EMPTY`, `LOCATOR` | spatial anchors |

`TH_PREVIEW_ACTORS`, `TH_PREVIEW_ONLY`, and `TH_CAMERA_PREVIEW` are known
preview collections and are never export roles. An object linked to both a
preview collection and an export role is reported as leakage. In particular,
`TH_PREVIEW_ONLY` overlap is reported as `guide_leakage`.

The exterior exporter uses explicit object and scene properties in addition to
collection membership. `sr_export=true` opts a source mesh into the runtime
render mesh and `sr_ground=true` classifies its faces for ground atlas
allocation. The supported adapter key is `sr_runtime_y_mode`, with `direct` as the
default and `lane_mirror` requiring numeric `sr_lane_center_y`. In mirror mode
the exporter reflects the authored lane axis, reverses OBJ winding/normals,
and records the adapter in the package provenance. This keeps the lane
conversion shared and explicit instead of embedding a map-specific exporter
path.

An object with `sr_floor_mesh=true` is a separate walkable-floor source, not a
beauty-atlas surface. The exporter requires exactly one such mesh, positive
`sr_floor_grid_spacing` and `sr_floor_texture_period` properties,
a source-bound `sr_floor_texture_image`, and a three-channel `sr_floor_tint`
in [0,1], and preserves
its authored per-vertex Z values in `floor.obj`; the source grid must not also
be marked `sr_export=true`. The package manifest points `floorMesh` at the
separate OBJ and records `provenance.floor` with the source object, world-unit
spacing, texture period, vertex/face counts, texture dependency, and SHA-256
hashes for `floor.obj`, `floor.mtl`, and `floor.png`. The runtime package
loader rejects a malformed floor contract rather than silently dropping it.

A source-derived distant scenery card may be installed as a package
`backgroundLayers` entry after review. It is a world-space, depth-tested
OBJ/MTL layer rendered from the authored source at the canonical pitched
camera; it must record `cameraSpace=false`, `reactsToPitch=true`, source
representation, and SHA-256 hashes for mesh, material library, and texture.
The card is non-interactive and must not include a second floor bridge: the
separate `floorMesh` remains the only authoritative walkable surface. Runtime
consumption uses the ordinary placed-model queue, preserving foreground
occlusion and camera parallax.

`TH_SOURCE` must contain at least one `MESH`, `CURVE`, or `SURFACE`; lights and transform empties are
valid source inputs for illumination but cannot be the only selected-to-active
bake source. `TH_RENDER` must contain a mesh. If render mesh metadata is
available, a missing UV layer or empty vertex/polygon count is also an error.

Names are labels. A name such as `GUIDE_wall` does not make an object a guide;
the collection membership does. An object in more than one export collection
is an `ambiguous_role` error. The validator also reports missing required
collections, empty required roles, unsupported object types, invalid/singular
world transforms, duplicate anchor labels, malformed snapshot input, and
optional render-mesh UV/empty mesh metadata when supplied.

The report has schema `thestra.scene-contract-report`, schema version `1`, and
is suitable for a later Blender panel. Collision is intentionally described as
`optional_export_only; does_not_claim_walkability`; this preflight does not
turn collision geometry into a traversal guarantee.

## Usage

From a plain Python process, validate a snapshot:

```text
python tools/blender/scene_contract.py --snapshot snapshot.json --output report.json --pretty --strict
```

The same CLI can launch Blender for a `.blend` directly when `BLENDER` is set
or `blender` is on `PATH`:

```text
python tools/blender/scene_contract.py --blend path/to/scene.blend --output report.json --pretty --strict
```

Against an opened `.blend`, run the same module inside Blender. It serializes
the current file, validates it, writes the report, and never saves or mutates
the source scene:

```text
blender -b path/to/scene.blend --python tools/blender/scene_contract.py -- --output report.json --pretty --strict
```

The Blender invocation uses Blender's `--python-exit-code 1` so validator or
report-writing exceptions propagate to the outer CLI. It returns non-zero when
`--strict` is present and the report contains errors. Warnings do not fail the
strict result.

## Compiler integration

The environment compiler runs this preflight before changing scene data and
includes the report in each successful candidate manifest. Validation errors
abort the build; the external compiler propagates Blender script failures and
removes its temporary candidate. Existing output directories are never replaced.
Bake palette metrics remain diagnostic for production scenes; fixture tests
assert their expected colours separately.
