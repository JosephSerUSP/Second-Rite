# Next town gauntlet camera handoff

This lane prepares the **next** Second Gate town visual gauntlet without rewriting the historical evidence in draft PR #856.

## Why this exists

The first gauntlet accidentally promoted the #852 **camera-parity test fixture** (30° pitch / very wide lens) into art direction. The subsequent perspective study correctly separated camera choice from calibration correctness.

The owner selected the study's **Candidate A / ~40 mm family** as the preferred baseline for the next gauntlet:

- level side view: **0° pitch**;
- horizontal FOV: **28.0724869°** (`fovHalfX = 0.25`);
- Blender-equivalent lens under the existing 426×240 / 256×144 projection contract: **~43.27 mm**;
- study framing distance: **6.9 world units**;
- fixed eye under projection-window movement.

These are **next-gauntlet art-direction inputs**, not a new Scene schema and not a declaration that every future town shot must use the same distance or lens.

## Authority direction

```text
town-camera-next.json
        ↓
LÖVE / Thestra runtime adapter
        ↓
world_camera_calibration.fromResolved(...)
        ↓
temporary calibration JSON
        ↓
thestra_camera.py
        ↓
Blender TH_CAMERA_PREVIEW
```

Blender never writes camera authority back to Thestra.

## Before running a gauntlet

Run the fail-fast check:

```powershell
python tools/blender/check_next_town_camera.py
```

It must prove:

- the runtime-generated calibration is valid;
- Blender derives a lens in the 40–45 mm range;
- pitch is exactly level;
- `-96 / 0 / +96` projection-window offsets do not move or rotate the camera or change its lens.

## Run the next gauntlet

Use:

```powershell
python tools/blender/run_next_town_gauntlet.py
```

This reuses #856's existing nine-attempt builder/evaluator/contact-sheet/bake procedure, but routes every Blender invocation through `town_gauntlet_next.py`, which injects the generated calibration instead of the old parity fixture.

The original `town_gauntlet_builder.py` remains unchanged so #856's first-gauntlet evidence stays reproducible and legible as history.

## What the next art agent may change

The next gauntlet should re-author **composition, architecture, lighting, staging, and geometry** around this camera. It should not silently alter the camera while evaluating art. If another camera study is desired, do that as an explicit isolated study first.
