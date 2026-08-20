# Thestra WorldCamera -> Blender preview calibration

This helper is an authoring preview boundary, not a camera-authoring format.
The authority flow is strictly:

`presentation.world_camera` -> serialized calibration record -> Blender `TH_CAMERA_PREVIEW`

The Blender camera never writes values back into Scene/Map camera data.

## Record

`runtime/presentation/world_camera_calibration.lua` copies the optical facts from
an already-resolved `WorldCamera`: eye, horizontal forward/right basis and pitch,
projection kind/scales/extents, clipping planes, target/base viewport sizes,
principal point, projection-window offset, and an explicit Thestra/Blender
coordinate-system declaration. It requires target width/height explicitly so a
tool cannot silently guess which render surface it is calibrating.

For example, runtime tooling can serialize the result of the real resolver with:

```lua
local calibration = require("presentation.world_camera_calibration")
local text = calibration.encode(session, {
    profile = "first_person",
    projectionWindowOffsetX = 48,
    projectionFrame = {
        targetWidth = 426, targetHeight = 240,
        compositionWidth = 256,
        canonicalCenterX = 213, canonicalHorizonY = 70,
    },
})
```

## Blender helper

From Blender Python:

```python
import sys
sys.path.insert(0, r"<repo>\tools\blender")
import thestra_camera

record = thestra_camera.load_calibration(r"camera.json")
camera = thestra_camera.create_or_update_camera(record)
```

The helper derives lens/orthographic scale from the resolved projection
coefficients, maps Thestra's right-handed Z-up frame to Blender's `-Z` camera
forward convention, solves Blender lens shift against the resolved principal
point, and sets output framing to the record's native target. Changing only
`projectionWindowOffsetX/Y` changes lens shift, never camera transform.

## Numerical parity fixture

Run:

```text
python tools/blender/check_thestra_camera.py
```

`tools/blender/tests/fixtures/thestra_camera_parity.json` covers the Wide 426x240 target with
the 256x144 base projection, a pitched camera, optical-centre/near/far/left/
right/height samples, and offsets `-96, -48, 0, +48, +96` pixels. The runtime LÖVE harness
regenerates the same camera facts through the real `presentation.world_camera`
resolver and checks every serialized field/sample. The Blender test then checks
those same world points through Blender's own `world_to_camera_view`, asserts the
camera transform is invariant across projection-window offsets, and includes
wrong-shift and translated-camera negative controls.

## Actor reference plane

`create_actor_preview()` is preview-only. Its object origin is the feet/world
anchor; it uses nearest image sampling, hard alpha cutoff, and an emission shader
so Blender lights do not recolor the reference.

The helper does **not** infer a sprite-sheet layout. The caller supplies the
frame dimensions and `inspect_sprite_sheet()` first verifies they divide the
actual image. The current `walker.png` on `main` is 144x48, which is compatible
with a 6x1 grid of 24x48 frames; the #850 stack predates that asset commit, so
this tooling branch deliberately does not copy/cherry-pick the image into the
stack. Once the stack contains the asset, `frame_width=24, frame_height=48`
validates that grid before selecting a frame.
