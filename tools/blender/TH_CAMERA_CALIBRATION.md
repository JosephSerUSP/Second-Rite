# Calibrated Blender camera

Blender consumes a serialized `thestra.world-camera-calibration` record. The
runtime resolver remains authoritative; `tools/blender/thestra_camera.py` only
instantiates a preview camera, solves the principal point, and projects points
for authoring checks.

```python
import thestra_camera

record = thestra_camera.load_calibration("camera.json")
camera = thestra_camera.create_or_update_camera(record)
```

The camera transform is derived from the record's eye, horizontal basis and
pitch. Projection-window offsets are lens shifts, so they do not translate the
eye. `create_actor_preview()` creates a preview-only Walker billboard with a
world feet anchor, nearest texture sampling, hard alpha, and world-up height.

Run the focused proof with:

```text
python tools/blender/check_thestra_camera.py
```

The proof checks the calibrated 426x240 perspective projection, fixed-eye
projection-window movement, and the 24x48 Walker contract.
