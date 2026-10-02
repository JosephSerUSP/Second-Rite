# CRT preset bank — working visual-development set (2026-10-02)

Issue: #1310  
PR: #1320

## Owner direction

The stronger CRT direction is worth keeping available for live comparison.
Curved-glass geometry is the clear exception: it changes the image in a way the
owner does not currently want. Curvature therefore remains an isolated lab
experiment rather than part of the curated working bank.

No shipping/default decision is made here.

## Curated working bank

The current clean `crt` mode remains the control. Six flat developer presets are
kept immediately runnable:

| Presentation | Purpose |
| --- | --- |
| `crt` | Existing clean control. |
| `crt-lab:heavy-beam` | Stronger beam / scanline structure. |
| `crt-lab:halation` | Warm highlight spill / phosphor glow. |
| `crt-lab:aperture` | Visible aperture-grille RGB structure. |
| `crt-lab:slot-mask` | Staggered slot-mask structure. |
| `crt-lab:composite` | Chroma bandwidth loss, bleed, and faint ghosting. |
| `crt-lab:convergence` | RGB convergence error / chromatic fringing. |

`userPerform/CRT-lab.bat` stages the real Second Gate Project and presents these
seven choices as a one-click menu, always using the real runtime at the WIDE
surface. The launcher deliberately omits curvature.

## Non-curated experiments

`crt-lab:curved` and the first `crt-lab:maximal` recipe remain available by
explicit CLI while the lab branch exists, because they are useful experiment
evidence. They are not in the convenience launcher. `maximal` currently contains
curvature and should not be treated as the preferred combined strong preset.

The next combined recipe should be **flat**: strong beam + halation + some signal
bleed / mask / convergence, with curvature held at zero. The intentionally
extreme offline `FERAL` study establishes an upper visual bound for that future
runtime preset, but is not claimed as pixel-equivalent runtime evidence.

## Why presets stay developer-only for now

The point of this bank is repeated visual judgement, not an early settings UX.
Keeping the experiments behind `output=crt-lab:<preset>` lets us:

- compare them in real play without turning each experiment into a supported
  player preference;
- change or remove recipes freely;
- keep the current `nearest` and `crt` public surface stable;
- test mask/moiré behaviour on actual phones before naming any mask recipe a
  supported display mode;
- converge toward a small final set based on use rather than on contact-sheet
  novelty.

No curved-glass preset should be promoted without a later explicit owner change
of direction.
