# Sculpting a volume from drawn shadows

`shadow_volume.py` scaffolds a **new** source from three orthographic outlines.
The front drawing uses X/Z, the side drawing Y/Z, and the top drawing X/Y.
Their extrusions intersect to make a solid. Optional drawn stencils remove
through openings. No voxel grid, raster tracing, external package or renderer
extension is involved.

Use this for cut stones, irregular relics, forged parts and broad organic
masses whose shape is easier to describe in profiles. It gives editable
silhouette constraints, not an exact reconstruction from photographs: a
concavity hidden from every outline needs an explicit cut or further modeling.
Bevel, subdivision and other Blender modifiers can refine the saved volume.

## Start without Blender

The neutral [example](recipes/examples/shadow_volume.json) is an API example,
not a production asset recipe. Closure is implicit: do not repeat the first
corner. Profiles must be finite, simple polygons with no zero-length edges or
collinear corners. Clockwise drawings are normalized without modifying input.
Projection bounds must overlap; that alone does not prove a nonempty hull.

```text
python tools/blender/shadow_volume.py check tools/blender/recipes/examples/shadow_volume.json
python tools/blender/shadow_volume.py preview tools/blender/recipes/examples/shadow_volume.json --output out/shadow-example.svg
python tools/blender/shadow_volume.py build tools/blender/recipes/examples/shadow_volume.json --output out/shadow-example/shadow_example.blend
python tools/blender/shadow_volume.py inspect-source out/shadow-example/shadow_example.blend --output out/shadow-example/source-inspection.json
```

Set `BLENDER_EXECUTABLE` to the pinned executable before `build` or
`inspect-source`. The host routes those actions through `run.py`. Output paths
must be new; building refuses to overwrite an existing `.blend`. An empty
evaluated intersection fails before a source is saved.

Version 1 fields are `id`, `front`, `side`, `top`, optional `cuts`, `bevel`,
`smooth` and `color`, plus `version: 1`. Each cut has exactly `plane` and
`outline`. Coordinates are item-display units; colour channels are 0..1.
The output source filename must match `id`. `smooth` affects normals; it does
not replace geometrical rounding.

## Edit the saved source

After the first save, the `.blend` is authority. The input JSON/SVG is only
initial scaffolding evidence and is not consulted by compilation. Do not
rebuild the saved document from JSON.

The visible `A_ShadowHull` shares mesh data with `SHADOW_A_ShadowHull_front`.
Changing front silhouette vertices therefore changes the visible hull. The
side and top `SHADOW_...` meshes are hidden from rendering and act as live
Boolean controls. `CUT_...` objects define drawn openings. Select a named
control in the Outliner, enter Edit Mode and move its vertices in its named
plane. Keep its normal-axis coordinate at zero. Its Solidify modifier supplies
the working depth, so there is only one polygon to edit.

The temporary working envelope is deliberately larger than the initial
profiles. Very large edits must enlarge the controls' Solidify thickness and
the hull's matching front thickness together. Wire controls are construction
objects; compilation exports the visible resolved hull only. Smoothness, bevel
widths, cut positions and ordinary material nodes remain editable.

The live surface graph maps every Boolean/bevel face with bounded dominant-plane
UVs computed from the current geometry bounds. This supports small painted
atlases without tiled per-face repeats. It is box projection: chart boundaries
can still show seams on continuous patterns. Material detail must be reviewed
in the native viewer. Hand UVs are appropriate when continuity is more valuable
than automatically updating after a silhouette edit.

Boolean intersections and bevels can create almost coincident corners. Weld
steps surround the bevel; triangulation resolves collinear polygons; a
near-zero-area filter protects the runtime OBJ's six-decimal position precision.
This is not a waiver of runtime validation. The compiler still rejects bad
products, and painted faces must still pass per-material UV checks.

Read-only `inspect-source` reports actual evaluated volume, local bounds,
triangle/smooth-face counts, UV findings and the source control outlines. It
hashes the saved document before and after inspection. It requires at least
one shadow body and does not assert aesthetic acceptance or native pixel parity.

## Reuse and verify

Inside Blender, import `shadow_volume_blender.build_volume(name, spec, root,
material)` when scaffolding a new source. It returns `(body, masks)` so the
caller can add named assemblies and materials. `inspect_body(body)` measures
the live graph. Neither function is a replacement for read-only item compilation.

```text
python -m unittest discover -s tools/blender/tests -p test_shadow_volume.py
python -m unittest discover -s tools/blender/tests -p test_shadow_volume_blender.py
python tools/blender/script_index.py --check
python tools/blender/sync_asset_core.py --check
```

Integration exercises known intersection/cut volumes, a live silhouette edit,
generated-face UV coverage, genuinely empty overlapping projections, translated
export-root dependencies and an asymmetric bevel's actual OBJ output. Without
configured Blender it is an explicit skip; required Blender CI fails instead.
