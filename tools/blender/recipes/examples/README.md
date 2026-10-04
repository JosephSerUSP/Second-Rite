# Relational serving-corner scaffold

Choose pieces in the [furnishings catalogue](../FURNISHINGS.md), then edit
[serving_corner.json](serving_corner.json). It is an isolated reference scene,
not the adopted bakery or a replacement for its source. Coordinates are metres:
+X is depth, -Y is screen right, and Z=0 is the floor.

Run from the installation root with the pinned Blender executable:

```powershell
& $env:BLENDER_EXECUTABLE --background --factory-startup --python-exit-code 1 --python tools/blender/compile_room_spec.py -- --spec tools/blender/recipes/examples/serving_corner.json --blend out/serving_corner_reference.blend
```

Use a new output path. The compiler retains `save_source_blend`'s overwrite
guard. Once a document is adopted or hand-edited, edit the `.blend` directly.
The JSON is scaffold input; it does not become a second authority for an
adopted environment.

The pilot calls the existing `Interior` shell and public furnishing builders.
Signatures are inspected from those builders. It has no duplicate geometry
implementation. Material bindings use canonical semantic IDs. Shell operations
carry their existing `args` and `params`; furnishing `params` carry the builder's
existing named arguments.

Each furnishing chooses one placement:

| Intent | JSON | What determines the position |
|---|---|---|
| Stand on the floor | `"place": {"at": [0.5, -0.5]}` | Explicit X/Y; measured bottom rests at Z=0 |
| Put bread on a counter | `"place": {"on": "counter", "offset": [0, 1.05]}` | An actual rectangular top face in the counter's evaluated mesh; offsets are from its centre |
| Keep water on the public side of the counter | `"place": {"beside": "counter", "axis": "x", "side": -1, "gap": 0.16}` | Measured faces of both assemblies; a 16 cm gap survives changes to either builder's proportions |

Declare targets before their dependents. A support must have one unambiguous
horizontal rectangular top face. The compiler rejects overhanging footprints,
unknown or forward references, misspelled parameters and entry into a named
`keepClear` volume. Errors identify the furnishing and offending relationship.
Mesh parts and any companion lights move together.

`exit_sightline` in this example protects the bakery-like near band around an
exit. It is an author-declared readability constraint, not a new collision
system or a claim that every intersecting bounding box is invalid joinery.
Change the volume to match the intended room. Touching a boundary is allowed;
positive-volume overlap fails. The source camera and native frames still decide
how the composition reads.

Wall fittings, named openings, variant patches, light-source provenance and
full-room migration remain outside this first compiler. Existing shell rules
(including character-floor and foreground coverage checks) continue to apply.
Use the ordinary recipe for constructs the pilot cannot express. The broader
work remains in #1346 and #1347; this example makes their first relational
operations reviewable without regenerating adopted sources.

After construction, stage an export and inspect native Classic, 4:3, Wide and
device views with actors and entrances present, using the
[ordinary review route](../../README.md#cheap-checks-and-native-review).
Geometric success alone does not establish visual quality, customer reach or
successful gameplay.
