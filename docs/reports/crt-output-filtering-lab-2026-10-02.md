# CRT output filtering lab — strong preset experiments (2026-10-02)

Issue: #1310

## Purpose

The first CRT implementation deliberately proved the narrow reconstruction/fractional-scaling idea with a mild beam envelope and no curvature, mask, halation, noise, composite bleed, or convergence drift.

This follow-up keeps that implementation unchanged and adds a **developer-only CRT lab** for stronger aesthetic exploration. It is not a shipping/default decision and does not add the experiments to the player-facing output-mode list.

Run a staged Project with:

```text
output=crt-lab:<preset>
```

The ordinary public modes remain:

```text
nearest
crt
```

## Presets

| Preset | Variable isolated / emphasized |
| --- | --- |
| `heavy-beam` | Much deeper source-line beam/scanline envelope with stronger brightness compensation. |
| `halation` | Moderate beam plus warm bright-neighbour spill. |
| `aperture` | Moderate beam plus host-pixel RGB aperture-grille triads. |
| `slot-mask` | Moderate beam plus staggered two-row phosphor slots. |
| `composite` | Softer horizontal chroma bandwidth, faint delayed bright ghost, light halation. |
| `convergence` | Physical-output-pixel RGB registration drift. |
| `curved` | Beam + halation + bowed glass coordinate warp + edge vignette. |
| `maximal` | Deliberately excessive combination of beam, bleed, convergence, halation, grille, curvature, vignette, and deterministic static grain. |

The point of the set is diagnostic separation, not eight candidate settings. In particular, aperture grille and slot mask are separate because physical phone-panel interaction is a different question from beam reconstruction.

## Architecture

The shipping `crt` shader/source is left intact. The lab has a second shader and preset table inside `presentation.output`.

Lab modes:

- share the same fractional aspect-fit geometry as `crt`;
- use the same host->render inverse transform, so touch/mouse mapping stays aligned;
- are accepted by `output.setMode` for explicit developer/CLI use;
- are intentionally omitted from `output.modeIds()`, so Options does not advertise them;
- fall back to `nearest` if the lab shader cannot be constructed.

The lab remains one pass. Depending on enabled features, the shader may spend additional texture samples on halation, composite bleed, convergence, and ghosting. That is acceptable for visual study but **not** evidence that the maximal preset is appropriate for mobile shipping.

## Resolution-aware choices

Beam strength uses the existing physical-output-scale calibration.

Convergence is authored in physical output pixels rather than source pixels so its apparent displacement stays comparable across host resolutions.

Aperture/slot masks fade in only once the physical source-pixel scale is large enough to represent them. This does not solve phone-panel moiré; it merely avoids forcing a high-frequency mask where there are too few output pixels to show it coherently.

## 1080p study sheet

The accompanying 1920×1080 contact sheet was made from a **real G5 Wide renderer frame** (the Options scene over the Gate Room), then processed offline using the same experiment families and numeric targets as the lab presets.

Each sheet cell is a **1:1 crop from a full 1920×1080 treatment**, not a downscaled whole-screen thumbnail. That is deliberate: downscaling a contact sheet would destroy or alias the very scanline/mask frequencies being evaluated.

This sheet is visual-development evidence only. It is **not** a claim that the CPU study exactly matches LÖVE/GLES shader output. Runtime/GPU captures remain required before selecting any preset.

## Verification requirements for this rung

The unit suite now additionally requires:

- public output list remains exactly `nearest`, `crt`;
- every lab preset resolves to CRT fractional geometry;
- every lab mode constructs natively;
- the lab shader validates as GLES when `love.graphics.validateShader` is available;
- preset access returns a copy rather than mutable preset authority;
- the maximal preset actually composes the major experiment families.

Still required before any strong effect is promoted:

1. capture the same 1080p frame through the real LÖVE output shader for every preset;
2. compare the mask presets at 1:1 on the target Windows display;
3. run aperture/slot masks on actual Android panels and inspect moiré/chromatic crawl;
4. record frame time, especially for `composite`, `curved`, and `maximal`;
5. inspect small text, dithering, affine texture noise, thin geometry, and bright VFX separately;
6. choose effects by contribution, then collapse the useful pieces into one or a few deliberately tuned candidates rather than shipping the lab wall of knobs.

## Provenance

The lab shader is original repository code. No Lottes, zfast, CRT-Pi, Easymode, Royale, or other third-party shader source is copied into this rung.
