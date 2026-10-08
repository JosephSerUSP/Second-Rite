# Projection paint from an authored camera

`view_projection.py` is a Blender import library. It maps camera-framed paint
onto an existing finalized mesh, without changing vertices or replacing existing
UVs. Its output is a shader recipe that a caller can bake into the existing unique
UV atlas. The caller owns the source document, image correspondence and save.

## Establish correspondence first

A concept/reference image of a different shape is not a usable projection plate.
Matching outer bounds does not establish its internal material boundaries,
occlusion or volume. Use that image for art direction. Render the actual mesh
with its camera framing and visible material regions, then paint that render.

An AI paintover can resize objects, move straps or change outlines even when
asked to preserve them. Compare the paintover with the input render before
projecting: outer silhouette, holes, material boundaries and landmarks all
matter. A silhouette score alone does not prove internal correspondence.
Retain failed plates as failed evidence; do not hide their drift by fitting a
different mesh to them or calling that reconstructed topology.

## API and actual camera frame

Run a Blender-side caller with `tools/blender/run.py`. Choose a finalized mesh
with no modifiers so mesh loops and projection attributes stay associated.
The complete receiver, including its other connected components, forms the
visibility BVH. For separately modelled receivers/occluders the caller may
provide a combined tree explicitly.

```python
from view_projection import project_view, projection_material, visibility_tree

tree = visibility_tree(receiver)
view = project_view(
    receiver, scene, camera, name="front", tree=tree,
    image_size=(1024, 1024), rectangle=(0, 0, 512, 512), clip=(0, 0, 512, 512),
)
recipe, coverage_switch = projection_material(
    "projection_recipe", paint_image, [view], fallback_image,
    fallback_uv="OriginalUV", power=6,
)
```

`rectangle` describes the exact camera render frame within the unchanged source
bitmap. `clip` bounds eligible samples to their assigned panel. Keep a margin
around panel contents because linear filtering can still touch boundary pixels.
All pixels use the original full-image coordinates. Preserve camera transform,
orthographic scale, render dimensions and pixel aspect when rendering the guide
and projecting its paintover. Uniform whole-canvas resizing can be described by
scaling all panel coordinates, but independently resizing objects cannot.

The default `fit_bounds=False` preserves camera coordinates. The explicitly
requested `fit_bounds=True` option can fit measured bounds for a deliberately
approximate reference study; it does not repair shape/semantic correspondence.
Perspective cameras are currently rejected. Existing views require `update=True`
for an explicit saved-source calibration edit. Existing active UVs are retained.

The recipe weights samples by front-facing normal alignment raised to `power`,
source alpha, panel bounds and corner-local occlusion. Visibility rays target a
point 0.001 toward an actual tessellated triangle centre to avoid edge misses.
Samples blend in linear light. Unseen pixels use the declared fallback texture.
For opaque paintovers, pass `mask_image=render_support_image`: the actual render's
RGBA support can gate sampling independently of the paintover's opaque background.
It must share full-canvas aspect and framing; it may be uniformly resized.
Set `coverage_switch.inputs[0].default_value` to 1 to bake green observed/red
fallback evidence; restore 0 for appearance. The evidence reports usable image
samples, not whether the paint itself is correctly registered or aesthetically
accepted.

Reference/paintover illumination becomes surface colour in the baked atlas.
This is appearance transfer, not recovered albedo, normals or PBR properties.
Do not assume view blending removes painted light or incompatible view seams.

## Verification

The real-Blender fixture bakes front paint and unseen fallback, checks coverage,
blends two actual view samples, rejects an occluding component and invalid
calibrations, verifies translated geometry/original UV preservation, and checks
that projection uses camera pixels rather than silhouette fitting:

```text
python -m unittest tools.blender.tests.test_view_projection_blender -v
```

A saved item still needs read-only compilation, UV/topology checks and actual
native yaws at its in-game size. No projection check establishes owner approval.
