# Calibrated multiview references

Generate front, right, back and top views of the **same** new object. Inspect
their agreement before building: a generated sheet may have tilted elevations,
unequal scales, different foam placement or incompatible silhouette widths.
It is a reference, not a depth scan. Preserve the original image and prompt.

`multiview_reference.py` is an import library. Host Pillow supplies an RGBA
image to `measure_profile`; Blender can use `atlas_uv` and `combine_profiles`
without importing Pillow.

```python
front = measure_profile(image, center=267, top=115, bottom=550,
                        clip=(25, 625), edge="left", samples=25)
# Independently calibrate side and back; do not reuse the front mask/depth.
rows = combine_profiles(front, side, back, height=2,
                        top_ratio=213/208, top_weight=.25)
uv = atlas_uv(point, {"axes": [0, 2], "center": [267, 332.5],
                      "scale": [217.5, -217.5]}, image.size)
```

Calibrate each panel's body center, lip/base levels, horizontal clip and
unoccluded edge. The measured alpha run must contain the center. Choose the
left or right edge to exclude attached handles; a clipped measured edge or
missing center fails loudly. Radius is normalized by **that view's** height.
Combine matching levels: front/back define width, side defines depth. The top
ratio may apply an explicitly weighted depth correction; do not hide its
disagreement. Tests demonstrate that changing side depth leaves width/height
unchanged. Elliptical lofts suit vessels, not arbitrary concave objects.

Opening, inner rim and handle cross-section are additional measurements. A
visual silhouette alone cannot recover their cavity floors or occluded walls.
Author those surfaces explicitly, and record which are inferred. Keep profiles
and calibration metadata in the newly saved document. After creation, the
`.blend` is the source authority; compilation never reads measurement JSON.

Use calibrated panel projections to place different front/back features.
`atlas_uv` addresses the **unchanged full image**, reverses image Y into OBJ V,
and rejects out-of-bounds/non-finite mappings. Negative scales support back
views. Declare occlusions instead of projecting a foreground handle onto the
body behind it. An observed glaze patch may wrap a handle continuously; this
is surface colour reference, not exact per-texel reconstruction. Missing left
or underside art must be marked inferred. Never derive height from lighting.

Projection seams and baked lighting remain limitations of view photographs.
Inspect more than the front: body, rim, cavity, handle hole and thickness must
read in actual cardinal source views and at **96px in the native viewer**.
Workbench source views establish volume/surface correspondence; they are not
runtime proof. Painted-face UV area, bounds and sampled alpha support matter
even when the model-wide UV check is green. Give cut walls and undersides plain
materials where reference information is absent. Intentional flat liquid and
cut planes should not inherit smooth ceramic normals.

The Mug of Ale pilot records original generation, calibration, actual-source
views, native captures and verification in
`docs/reports/item-model-multiview-review/`. Its once-only scaffolding is not an
authoritative regeneration route. Baselines and G5/G6 references remain owner
decisions.
