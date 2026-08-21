# Geometry-conditioned facade projection

This is an authoring spike for Second Gate environments. It tests whether an
image model can add facade-level architectural detail to a correctly
proportioned Blender blockout while Blender remains the authority for camera,
geometry, UVs, openings and depth-critical silhouette.

The projection core is provider-agnostic. It accepts a local image and an
optional local height image; it does not call an image API, contain provider
SDK branches, read credentials, or store API keys. Provider invocation and
image-generation provenance stay outside `tools/blender/facade_projection.py`.

## Workflow

```text
TH_SOURCE building mass + calibrated camera
    -> control/beauty render, depth, normals, object-index mask
    -> external image-generation provider (outside this repository boundary)
    -> returned facade image (+ optional estimated height image)
    -> camera projection onto explicitly named TH_SOURCE faces
    -> ordinary UV bake / atlas
    -> optional TH_SOURCE-only Displace modifier
    -> source / projected / baked comparison renders
```

Doors, openings, traversal surfaces and silhouette/depth-critical features
remain real geometry. The returned image is never treated as a finished flat
background and the spike does not write runtime OBJ/MTL/PNG products.

## Commands

The host wrapper launches Blender without mutating the input `.blend`:

```text
python tools/blender/run_facade_projection.py control \
  --blend path/to/source.blend \
  --output path/to/control

python tools/blender/run_facade_projection.py project \
  --blend path/to/source.blend \
  --control-packet path/to/control/control.json \
  --image path/to/provider-output.png \
  --height path/to/optional-height.png \
  --target SRC_BuildingMass \
  --output path/to/projection
```

The source mesh must be in `TH_SOURCE` and must already have an ordinary UV
map (normally `UVMap`). The target list is explicit. Omitting face indices in
the Python API selects every face of a named target; the tool does not guess a
surface from a material name or borrow `TH_RENDER`.

For a partial facade, pass explicit polygon indices, for example
`--face-indices 1,3`. Faces that extend beyond the calibrated frame fail by
default; `--allow-outside-camera` is an explicit escape for a deliberate
partial projection.

The control command writes `control.json`, `beauty.png`, and floating-point
`depth.exr` and `normal.exr` products. Blender builds that expose an object
index compositor pass also write `mask.exr`; the packet records when that
optional product is unavailable. The packet records the
active camera transform and calibration fields so a provider-side result can
be checked against the exact control frame. The projection command writes:

- `source_blockout.png`;
- `generated_projection.png`;
- one ordinary-UV baked image per target;
- `baked_result.png`;
- `projection.json` with image hashes, target faces, provenance and authority;
- `projection_inspection.blend`, a derived inspection file.

`projection_inspection.blend` and all images belong in a temporary or review
directory. Promotion into a Project's authored assets is a separate human
decision and is outside this spike.

## Height safety

An optional height image creates a Blender `Displace` modifier and a matching
vertex group only on the selected faces of named objects in `TH_SOURCE`, using
their ordinary UV map. The tool rejects targets that also belong to
`TH_RENDER`, `TH_COLLISION`, `TH_ANCHORS` or `TH_PREVIEW_ACTORS`. A generated
image-derived height field is an authoring estimate, not automatically the
metric `height_metric.png` product defined by the unified asset contract;
normalization, range and runtime promotion require a separate reviewed
adapter.

## Fast protocol check

The provider seam, packet schema and source-only displacement guard can be
checked without Blender or a render:

```text
python tools/blender/check_facade_projection.py
```

The first proof may use a deterministic fixture image or a manually supplied
provider result. No provider call is part of the check.
