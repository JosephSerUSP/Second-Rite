# #1393 selective-AA regression note — 2026-10-05

## Boundary

The issue's known-good control, `6231d3186519014caa93cdc70d64b93f3960aa03`, is the first parent of selective-AA merge `820bd07a799c80cf5132ceee5f2ec848ee11362c` (#1385 / #836).

The shipping Project opted into the new path with `dungeon.psxRendering.environmentSupersample = 3`. `world_pass_compositor.isEligible` bypasses the compositor when the resolved scale is 1, so setting the Project value back to 1 restores the ordinary pre-#836 world-render path without deleting the compositor implementation or changing authored environment data.

## Recovery decision

Keep the selective-AA implementation available for continued diagnosis, but remove it from the shipping Project until the native environment control visibly renders through the compositor.

This is intentionally a production recovery, not a claim that the compositor defect itself is fixed.

## Separate capture defect

`tools/blender/capture_environment.py` currently validates process completion and the encoded frame payload but does not assert that the world contributed visible output. #1393's black-world capture can therefore still report `ENVIRONMENT NATIVE REVIEW OK` because Walker/UI pixels make the PNG non-empty. That needs a separate capture-readiness/content assertion; no arbitrary golden recapture should hide it.
