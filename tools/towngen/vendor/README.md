# Vendored third-party code

## `pixelfixer` -- Retro-Diffusion/pixel-art-fixer

* Upstream: <https://github.com/Retro-Diffusion/pixel-art-fixer>
* Commit: `ef376e57e1c272633ca2dbf5f29ec3fcf6596465` (2026-07-14)
* Licence: MIT, kept verbatim in `pixelfixer/LICENSE`
* Requires: `numpy`, `scipy`, `opencv-python`, `Pillow`

Recovers the pixel grid an image was *drawn* on and rebuilds it aligned to that
grid, by consensus between three cheap detectors (autocorrelation, run-length,
self-similarity) with spectral arbitration when they disagree.

### Why it is here

Image models do not draw pixel art; they draw smooth art that resembles it, on
whatever grid they feel like. `tools/towngen/generate_sprites.py` has to land
those figures on an exact 24x48 cell, and a reduction from the model's grid to
ours is non-integer, which smooths the result no matter which resampler runs.
Detecting the source grid first and reducing from *that* measured 63.7 crispness
against 61.1 for block-mode alone and 48.7 for Lanczos.

It was validated against ground truth before being trusted: the five authored
sprites on a generated sheet are upscaled copies of files we already have, and
the detector recovered their grid exactly -- 17x47, 16x47, 16x47, 17x47, 16x47,
which are those sprites' real bounding boxes, at its own "high" confidence.

### Local changes

`cli.py` is NOT vendored. As shipped it does `from detector import detect`, and
no `detector` module exists in the repository, so the CLI cannot run at all. The
library API (`pixelfixer.api.process`) is unaffected and is what we call.

Nothing else is modified. Re-vendor by copying `python/pixelfixer/*.py` from
upstream and dropping `cli.py` again.
