# Geometry-conditioned AI surface projection

This spike treats image generation as **semantic surface authorship** for real Blender geometry.

Blender remains authority for:

- geometry;
- camera;
- UVs;
- spatial depth;
- final bake.

The image model receives a control packet and returns a view-aligned image. The projection tooling does not call OpenAI, OpenRouter, Stable Diffusion, Flux, or any other provider directly.

## Intended workflow

```text
coarse building mass
    -> capture control packet from calibrated camera
    -> image model authors facade/surface treatment
    -> project returned image onto real mesh
    -> bake projection into ordinary UV space
    -> optional TH_SOURCE displacement / selective geometry promotion
    -> normal source-to-runtime environment bake
```

This is intentionally different from asking an image model for conventional UV islands or another commodity seamless brick texture.

## Control packet

`capture_control_packet(...)` performs **one actual render** using the cheap shared render profiles and writes:

- `control-beauty.png`;
- `control-passes.exr` containing the same render's Combined, Depth/Z, Normal and Object Index passes;
- `control.json` containing exact camera matrix/lens/clipping, object names and pass semantics.

Example inside Blender Python:

```python
from pathlib import Path
import ai_surface_projection

ai_surface_projection.capture_control_packet(
    Path("out/facade-control"),
    objects=[bpy.data.objects["BuildingMass"]],
    render_profile="cycles-draft",
)
```

A provider adapter outside this module can convert the EXR passes as needed and call any current image model.

For a first proof, a useful generation instruction is along the lines of:

> Preserve this exact building mass, silhouette, floor structure, doorway and perspective. Author a richly specific old civic facade onto it: believable construction, windows and surrounds, repairs, masonry/plaster transitions, shallow ornament, weathering and local variation. Treat this as a view-aligned architectural surface treatment, not a new composition.

## Project returned imagery

Given a provider result matching the same camera:

```python
ai_surface_projection.project_image_to_objects(
    Path("out/generated-facade.png"),
    objects=[bpy.data.objects["BuildingMass"]],
)
```

The helper writes `TH_AI_PROJECT` UVs by projecting every real mesh loop through the active camera and applies the image through those UVs.

It does **not** replace the building with a flat image plane.

## Bake to ordinary UVs

The first spike supports one mesh at a time:

```python
ai_surface_projection.bake_projection_to_uv(
    bpy.data.objects["BuildingMass"],
    Path("out/generated-facade-atlas.png"),
    atlas_size=1024,
)
```

This creates an ordinary `TH_AI_BAKE` UV set and bakes the view projection into it. The resulting atlas is then just a normal Blender texture source that can participate in later TH_SOURCE -> TH_RENDER baking.

The one-mesh limitation is deliberate. Prove the camera/projection boundary before adding multi-view blending or multi-object atlas packing.

## What image generation should do

Use image generation where semantic visual authorship is valuable:

- whole facade treatment;
- window/surround language;
- layered repairs;
- civic/religious/industrial material transitions;
- ornamental relief;
- signs/painted architectural detail;
- weathering that follows construction logic.

Commodity materials such as ordinary brick, generic stone, wood and concrete are usually better sourced from established PBR libraries.

## Geometry promotion

The projected image is a **source-authoring aid**, not permission to flatten the environment.

Promote features to real geometry when they matter to:

- silhouette;
- actor occlusion;
- doorway/opening depth;
- traversal;
- large cornices/balconies/canopies;
- strong shadow/depth structure.

Keep shallow masonry, cracks, paint, small ornament and similar detail in the projected/baked source surface where practical.

A later experiment may derive a height/depth representation from the returned facade and use it for TH_SOURCE-only displacement. Do that on suitable subdivided surfaces rather than blindly displacing closed boxes.

## Multi-view follow-up

If one-view projection proves useful, the next step is several geometry-conditioned views of the **same** mass and camera family, projected back to the model and resolved into ordinary UV space.

That is preferable to asking an image model to understand arbitrary UV islands directly.

## Provenance and safety

- provider/API keys stay outside Blender source files and the repository;
- record provider/model/prompt/hash for returned generated images;
- generated source imagery does not become a camera-space runtime background;
- the normal environment contract remains rich TH_SOURCE -> coarse real 3D TH_RENDER + one beauty atlas.

Refs #872 #871 #851 #838
