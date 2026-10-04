# CRT output filtering spike — initial implementation evidence (2026-10-02)

Issue: #1310

## Status

This report records the first implementation rung only. It is deliberately **not**
a shipping/default decision.

Implemented on the spike branch:

- a final-output presentation module, separate from render-surface/aspect policy;
- byte-compatible delegation to the existing integer-nearest transform;
- an experimental fractional aspect-fit transform for CRT mode;
- an original single-pass CRT reconstruction shader (no imported third-party shader source);
- shared host->logical coordinate conversion through the same output transform;
- CLI selection direction (`output=crt`) wired by the host change in this branch;
- native shader compilation and desktop GLES validation coverage in the unit suite.

Still requiring evidence before #1310 can be resolved:

- representative visual A/B captures;
- Windows frame-time measurements;
- actual Android device execution in landscape and portrait;
- Android frame-time/thermal observations;
- phone-panel mask/moiré study if a phosphor mask is attempted;
- owner visual decision on whether CRT reconstruction is worth keeping.

## Architecture finding

The existing final-frame seam is the correct ownership boundary. The renderer
continues to produce one low-resolution logical Canvas. The new output module
owns only reconstruction of that completed surface onto the host framebuffer.

Render-surface profile and output reconstruction are intentionally independent:

```text
logical render surface
    classic / four_three / wide / mobile...
                |
                v
finished low-resolution Canvas
                |
                v
output presentation
    nearest(integer) / crt(fractional experimental)
                |
                v
host framebuffer
```

The important correction found during the audit is that output geometry is also
an input concern. Touch hit-testing previously asked
`presentation.surface.outputTransform` directly. A fractional draw path would
therefore have displayed controls in one transform while hit-testing another.
The spike routes host->render conversion through `presentation.output`, making
the transform used for presentation the authority for inverse input mapping too.

## Shader experiment A: minimal reconstruction

The first CRT candidate is intentionally small and original:

- one pass;
- two explicit horizontal source samples;
- smooth interpolation only along X;
- discrete source-row sampling along Y;
- a weak source-scanline beam envelope;
- beam strength fades away at low physical output scales;
- small brightness compensation;
- no curvature;
- no RGB/phosphor mask;
- no bloom/halation;
- no noise;
- no temporal persistence.

This is not intended to model a specific CRT. It tests the narrower hypothesis
behind #1310: whether display-like reconstruction can make non-integer host
scaling aesthetically coherent while preserving the deliberately low-resolution
source image.

The shader source is authored in this repository for the spike; no Lottes,
zfast, CRT-Pi, Easymode, Royale, or other third-party shader code is copied.

## Why the first candidate omits a phosphor mask

A mask is not needed to test the fractional-scaling hypothesis and is the part
most likely to interact badly with physical phone pixel/subpixel layouts.
Keeping it out of rung 1 makes Android evidence easier to interpret: any moiré
or instability cannot be blamed on an artificial RGB subpixel pattern.

If a later experiment adds a mask, compare it independently from the beam
reconstruction and make it resolution-aware.

## Transform behavior

### Nearest

Delegates verbatim to `presentation.surface.outputTransform`:

- integer scale;
- minimum 1x;
- centered integer offsets;
- existing behavior remains the baseline.

### CRT experimental

Uses the largest aspect-preserving scale that fits the host:

`min(hostWidth / renderWidth, hostHeight / renderHeight)`

The scale is not quantized. Offsets may therefore be fractional. The
experimental path also permits <1x scaling on a host smaller than the logical
surface instead of deliberately cropping at 1x.

That <1x behavior is an experiment, not yet a new engine guarantee.

## Verification in the branch

`tests/test_output_presentation.lua` covers:

- unchanged nearest transform at a known wide fixture;
- fractional CRT transform;
- host-centre -> logical-centre inversion;
- <1x CRT fitting;
- native LÖVE shader construction;
- GLES shader validation when `love.graphics.validateShader` is available;
- safe fallback to nearest for an unknown mode.

The test intentionally treats GLES validation as only one rung. Actual Android
execution remains mandatory.

## Provenance

No third-party CRT shader source is included in this implementation.

External shaders discussed in #1310 remain research references only. That avoids
entangling the experiment with #354 while the visual/technical hypothesis is
still unproven.

## Next experiment

After the branch gates are green:

1. capture the same representative UI/text and 3D scenes under nearest and CRT;
2. include awkward fractional host sizes rather than only integer-friendly sizes;
3. inspect text, dither, affine texture noise, thin geometry, gradients, and UI borders;
4. run the exact candidate under desktop GLES;
5. package/run it on an Android device in both mobile surface profiles;
6. record frame time before considering any extra tap, mask, curvature, or bloom;
7. only then decide whether a second candidate (for example a cleanly
   provenance-tracked Lottes-inspired comparison) is worth implementing.

No default should change from nearest on the strength of this first rung.
