# Bind painted silhouettes to editable geometry

This route pairs generated or authored images with thick curved 3D surfaces.
Alpha constrains the initial silhouette; explicit width, height, bow and
thickness define its depth. It works best for prominent rigid faces such as
shields and amulets. A front image alone does not describe a wearable harness;
separate open ribs, curved shoulder shells and back straps need actual modeling.

`painted_relief.py` reads source pixels without changing the PNG. Pillow is
required on the host. Blender receives mesh JSON and needs no Pillow package.
The tool requires a genuine alpha channel and a transparent boundary, samples
only cells supported at corners/edge midpoints/centre, keeps the largest
edge-connected body and reports discarded detached cells. Holes in the sampled
mask remain physical openings. Local vertex fans are split to avoid nonmanifold
contacts where cells touch only at a point.

```text
python tools/blender/painted_relief.py out/my-painted-face.png --width 2 --depth .2 --bow .25 --grid 56 --output out/face-report.json --mesh-output out/face-mesh.json
python -m unittest discover -s tools/blender/tests -p "test_painted_relief*.py"
python tools/blender/script_index.py --check
```

Both outputs refuse overwrite. The report hashes the original PNG and records
alpha bounds, sample counts, disconnected fragments, dimensions and depth
controls. `--grid` is samples along the long mask edge (8..192). `--alpha`
defaults to 240: generated opaque interiors may be 252/253 rather than 255.
`--height` overrides mask aspect; otherwise the image bounds set that ratio.

`--relief` is an optional colour-luminance displacement amplitude. It defaults
to zero. Painted shading is not recovered depth: interpreting small colour
variation as height produced unnecessary noisy geometry during this study.
Choose geometry depth deliberately and retain the painting as surface colour.

Inside a once-only new-source script launched with `run.py`:

```python
import json
from pathlib import Path
import item_kit as kit
from painted_relief_blender import create_relief, add_boundary_finish

root = kit.begin("painted_example", "painted_silhouette", "Bowed painted face")
front = kit.material("painted_face", image=Path("out/my-painted-face.png"))
edge = kit.material("painted_edge", color=(.65, .45, .2))
data = json.loads(Path("out/face-mesh.json").read_text())
body = create_relief("PaintedBody", data, root, front, edge)
add_boundary_finish(body, iterations=3, ratio=.45)
kit.save_new(Path("out/painted_example.blend"))
```

The optional finishing helper creates a named boundary vertex group, live
Smooth modifier and live Decimate modifier. Original mesh topology, UVs and
materials remain editable. It refuses a duplicate finish. Review perimeter
relaxation and decimation in the actual runtime: a lower triangle count does
not prove the silhouette or painting stayed correct.

After first save, edit the `.blend` directly. Mesh JSON is initial scaffolding,
not a generator authority. Keep project image dependencies beside the source
and make paths document-relative before production compilation. Preserve
original generated images and record prompts/provider and hashes separately;
never leave project dependencies only under the generator's default directory.

Front UVs bind to the full original image coordinates, without cropping or
repainting the bitmap. Back and thickness faces use a separate plain material.
Image alpha controls the mesh outline; this is not a claim of transmissive
glass or reconstructed surface normals. Runtime lighting, painted shading,
dithering and texture filtering still affect the result. Optional existing
runtime material passes can adjust colour gain without changing image bytes;
record those choices and compare them at native size.

The grid trades silhouette fidelity for mesh cost. Fine spikes, tiny holes and
detached ornaments may be lost or explicitly excluded. UV interiors are checked
at nine samples per original cell, not every source texel. Decimation can span
additional pixels. Audit final exported painted faces for missing/collapsed/
outside UVs and alpha support, compile read-only, and inspect gameplay and
cardinal yaws. Use separate actual geometry wherever rotation exposes the
limitations of a prominent painted face.
