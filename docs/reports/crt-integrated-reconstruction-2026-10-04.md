# CRT integrated reconstruction candidate — 2026-10-04

Issue: #1310

## Owner direction

`crt-lab:composite` is currently the most convincing CRT experiment, especially
because its bandwidth loss lets authored low-resolution colour clusters stop
reading as perfectly isolated modern display pixels. The problem is balance:
its chroma bleed is doing much more perceptual integration than the rest of the
stack, while the overall result remains timid compared with the way 1990s CRT
presentation participated in the perception of pixel art.

The goal of this rung is therefore **not more colour bleed**. Composite stays
unchanged as the comparison anchor. A new flat candidate, `crt-lab:integrated`,
asks what happens when luminance, beam shape and bright-pixel spread participate
in the same reconstruction.

No shipping/default decision is made here.

## Candidate: `crt-lab:integrated`

The candidate is Composite-derived but deliberately keeps curvature, grille,
slot mask, convergence error and static noise at zero. It combines four families:

1. **Chroma bandwidth loss** — still strong, but slightly below the isolated
   Composite experiment so colour smear is not the only visible effect.
2. **Luma bandwidth loss** — the same neighbouring-source kernel can now soften
   brightness detail independently from chroma. Adjacent source pixels therefore
   fuse in light as well as hue instead of retaining a razor-sharp luma skeleton.
3. **Neutral phosphor bloom plus warm halation** — bright neighbours contribute
   a neutral light spill before the existing warm-biased halo. This allows
   stronger highlight integration without turning every bright edge orange.
4. **Drive-dependent beam width** — high-drive pixels lose less energy at the
   scanline boundary than low-drive pixels, so bright strokes become physically
   wider while darker pixels retain stronger line separation. This is intended
   to break the modern-screen impression that every source pixel is the same
   hard-edged rectangle.

The ordinary `crt` mode and every existing lab preset remain unchanged.

## Why this is closer to the perceptual target

The useful historical distinction is not simply "blur versus sharp pixels".
A CRT is a reconstruction system: source samples modulate an electron beam,
phosphor emission has spatial extent, beam width changes with drive, analogue
bandwidth treats luma/chroma differently, and bright energy spreads beyond the
nominal source sample. Pixel-art clusters were therefore perceived through a
continuous luminous field rather than as a grid of uniformly bounded LCD
squares.

For Second Gate, the desired consequence is that a 1 px highlight, diagonal,
dither cluster or coloured sprite edge can visually join its neighbours without
applying an indiscriminate full-frame bilinear blur. The authored raster remains
low resolution; the output pass is responsible for reconstructing it.

## Runtime shape

The lab remains one pass and reuses the existing explicit reconstruction taps.
The new luma integration shares the Composite neighbour samples. Neutral bloom
shares the existing four halation taps. Drive-dependent beam expansion adds no
texture samples.

This keeps the new candidate materially cheaper than adding a separate generic
blur/bloom pass, although real GPU timing is still required before promotion.

`userPerform/CRT-lab.bat` exposes **Integrated** immediately after Composite for
direct A/B comparison on the real staged WIDE runtime.

## Review questions

The next owner pass should judge Integrated primarily against Composite, not
against Maximal:

- Do sprite and UI clusters read as *luminous shapes* rather than enlarged pixel
  squares?
- Does small text remain legible while losing the overly digital cut-paper edge?
- Is the colour bleed now proportionate to the beam/bloom/luma stack?
- Do dark contours retain enough separation, or does luma integration wash them
  together?
- Do bright VFX acquire useful apparent intensity from beam expansion/bloom?
- Does ordered dither become perceptually mixed without collapsing into mush?
- At 1080p and on phone panels, does the stronger beam structure remain stable?

If the direction is right but too weak/strong, tune `lumaBleed`,
`beamDriveExpansion`, `bloomStrength` and `beamStrength` before adding masks or
misconvergence. Those are the parameters that directly answer the current
perceptual question.

## Verification policy

The output unit suite now requires:

- nine developer CRT presets while the public mode list remains `nearest`, `crt`;
- Composite's authored chroma-led recipe remains unchanged;
- Integrated is flat and actually enables luma integration, chroma integration,
  neutral bloom and drive-dependent beam expansion;
- native construction and GLES validation continue to cover every lab mode.

Actual visual acceptance still requires live runtime judgement. Automated shader
construction can prove compatibility, not that the reconstruction looks right.
