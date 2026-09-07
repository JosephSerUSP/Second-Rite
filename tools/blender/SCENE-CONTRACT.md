# Blender scene contract preflight

`scene_contract.py` is the read-only preflight boundary for authored town
scenes. It is deliberately independent of the exporters so a Blender panel,
CI, or an exporter can consume the same versioned result without reimplementing
role rules.

## Roles

Export roles are assigned only by explicit collection membership:

| Collection | Required | Allowed object types | Meaning |
| --- | --- | --- | --- |
| `TH_SOURCE` | yes | `MESH`, `CURVE`, `SURFACE`, `LIGHT` | source appearance and lights |
| `TH_RENDER` | yes | `MESH` | real runtime/depth/silhouette mesh |
| `TH_COLLISION` | no | `MESH` | optional collision export only |
| `TH_ANCHORS` | yes | `EMPTY`, `LOCATOR` | spatial anchors |

`TH_PREVIEW_ACTORS`, `TH_PREVIEW_ONLY`, and `TH_CAMERA_PREVIEW` are known
preview collections and are never export roles. An object linked to both a
preview collection and an export role is reported as leakage. In particular,
`TH_PREVIEW_ONLY` overlap is reported as `guide_leakage`.

Names are labels. A name such as `GUIDE_wall` does not make an object a guide;
the collection membership does. An object in more than one export collection
is an `ambiguous_role` error. The validator also reports missing required
collections, empty required roles, unsupported object types, invalid/singular
world transforms, duplicate anchor labels, and optional render-mesh UV/empty
mesh metadata when supplied.

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

The Blender invocation returns non-zero when `--strict` is present and the
report contains errors. Warnings do not fail the strict result.
