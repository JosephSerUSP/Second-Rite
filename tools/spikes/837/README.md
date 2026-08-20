# Spike harness for #837

Evidence generator for **Issue #837: Prototype static-camera projection-window panning for sideview 3D scenes** (R2 after the #841 audit).

## Purpose
Proves that a wide sideview 3D scene can maintain a completely static camera eye transform while translating only the 2D projection window / principal point in screen space:
- Compares ordinary camera follow (A) vs static camera + projection window panning (B) vs multiple master FOV choices (C);
- Verifies that the camera eye position `(x, y, z)` and orientation vectors remain numerically invariant in B;
- Confirms that near-far screen separation is invariant under window panning, whereas camera follow causes parallax shifting;
- Confirms that actors remain aligned with environment geometry;
- Confirms that foreground depth occlusion works correctly within the native-resolution render target;
- Verifies whole-pixel vertex snap and dither-phase quantization boundaries.

## Running the spike

```bash
lovec tools/spikes/837 <repoRoot> <outDir>
```

`<repoRoot>` is the repository root (containing `runtime/`).
`<outDir>` is an output directory for generated comparison PNGs and `spike837.log`.
