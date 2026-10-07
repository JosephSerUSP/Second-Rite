# Multiview shape with continuous generated surfaces

The [multiview route](MULTIVIEW_REFERENCES.md) supplies width, depth, openings
and side/back surface intent. Projecting view photographs independently can
leave baked lighting and hard material seams. For a new object, use a second
image-generation pass to interpret those surfaces into a **flat UV atlas**.
Give it a deterministic layout guide and the original multiview reference.
Keep both images, full prompts and provenance. Neither output is a scan.

Separate physical construction from colour. For the clock pilot, hands,
hollow bells, feet and winding key are geometry; the flat dial contains only
hour ticks. For the book, a single connected outer surface spans back, curved
spine and front. Paper thickness, curved binding, corner guards and bookmark
are real components. The generated atlas adds the distinct front/back designs
and leather/paper colour. Missing interior information remains authored.

`surface_atlas.py` is a Blender-free import library:

```python
distance = path_parameters(profile_points)
uv = rectangle_uv(u, v, (.025, .04, .975, .20))
turns = cyclic_face_parameters([.984375, 0, None])
```

`path_parameters` distributes coordinates by actual cumulative path distance,
rejecting coincident or nonfinite points. A connected cover can calibrate its
section intervals to the generated layout while using identical U at every
shared spine vertex. Nonuniform section density is an explicit correspondence
choice, not automatically recovered texel registration.

`rectangle_uv` maps normalized coordinates into a bounded original-image
rectangle. Only float32 endpoint roundoff (1e-7) is accepted; meaningful
out-of-range values fail. It does not crop, repaint, bake or modify pixels.
`cyclic_face_parameters` unwraps a **local** sleeve face at the 0/1 seam and
places pole U between adjacent corners, preventing a cap fan from collapsing.
Choose the physical seam intentionally. Use plain materials for hidden inner
faces or cut caps that have no observed texture correspondence.

In the pilots, the clock's body/domes use one quiet original brass strip.
The book's cover uses one original back/spine/front strip, and page edges use
one paper strip whose V follows the stack's Y axis; U follows X on top and Z
on the fore-edge. The top binding and page block share one world coordinate
frame. There is no per-face repetition of an entire image.

`seam_color_report(image, bounds)` samples the original sleeve's two ends
without editing the image. It reports raw channel differences, **not** a visual
acceptance verdict. The clock's strip ends are not pixel-identical. The book's
source outer-cover shared-edge UV delta is exactly zero, which establishes
coordinate continuity; it cannot erase generated embossing or spine shading.
Do not confuse those two claims with photogrammetric recovery or seamless art.

Verify painted faces individually: UV presence, area and bounds; original-image
opacity; continuous shared edges where promised; flat versus smooth normals;
actual evaluated geometry and physical gaps. Curve conversions can duplicate
cap vertices for normals: record raw topology and use a **temporary positional
weld** to diagnose geometric openings, never silently repair the source/export.
Compare actual orthographic source views and **native 96px** gameplay/cardinal
captures. Workbench is source evidence, not runtime lighting/material proof.

After the first save the `.blend` is authoritative. Compile only that document;
never rerun its scaffold or read an atlas-layout recipe as production authority.
The original generated atlas is retained unchanged under source `_textures`
and in the derived shipping product. Runtime passes must use the existing
bounded material contract. Baseline refreshes and goldens remain owner decisions.

## Several items in one generated atlas

Allocate unique face regions and explicitly shared material strips before
generation. A two-item pilot uses one combined multiview reference and one
flat atlas for Untarnished Signet and Verdigris Coin. Both independent sources
reference the same original `relic_pair_surface_atlas.png`; their gold regions
overlap intentionally, while coin front/back and blank signet table are separate.
This saves generation calls in that pilot, not a measured GPU or monetary cost.

Keep a layout guide and requested allocations, then measure the actual output.
The pilot's generated metal strips moved vertically despite the guide. Correct
the UV correspondence to the original pixels, preserving both requested and
actual rectangles. Do not assume image generation obeys pixel coordinates.

`pixel_rectangle_uv((x0, y0, x1, y1), (width, height), inset=4)` converts
top-left image **pixel edges** to bottom-left OBJ UV bounds without cropping.
The inset reserves sampling clearance inside the measured allocation; it does
not create new gutter pixels. Validate every painted material against its own
region and permitted item users. A model-wide 0..1 check cannot catch sampling
an adjacent item's face. Keep the shared filename intact through compilation,
promotion and texture checks; per-item copies would defeat the shared asset.

Budget pixels by native prominence: the pilot has two 512px coin faces, a 320px
blank seal table and wide metal strips in a 1536x1024 atlas before insets.
Distinct construction still supplies the ring hole, shoulders, raised table,
coin thickness and edge reeds. A shared texture must not turn different items
into color variants of one mesh. Compare native 96px output and plain-material
controls with identical OBJ bytes. The retained
[pilot evidence](../../docs/reports/item-model-shared-atlas-review/README.md)
includes allocations, full prompts and actual source views.

More items trade generation calls against detail pixels, layout drift and
coupled edits: replacing a shared region can alter every consuming source.
After adoption, edit saved sources directly and review all consumers of a
changed shared image. Baseline/golden approval boundaries remain unchanged.
