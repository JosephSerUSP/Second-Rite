"""Put a plate through the PlayStation's actual picture pipeline.

A pre-rendered PS1 background did not merely look low-resolution. It was a
still frame that had been through two lossy stages, and both of them left
marks people recognise even when they cannot name them:

1. **MDEC.** Backgrounds shipped compressed with the console's motion decoder,
   which is a DCT codec very close to JPEG: YCbCr, chroma at half resolution,
   quantised 8x8 blocks. That is where the ringing around lintels and window
   frames comes from, and the faint blockiness in flat plaster.

2. **A 15-bit framebuffer.** The console drew in RGB555 - 32 levels per
   channel instead of 256 - so smooth things banded. Studios hid the banding
   by dithering before the truncation, which is why PS1 skies have that fine
   crosshatch in them rather than clean steps.

So the honest way to get the look is to do those two things in that order,
rather than to blur the image and reduce its palette. Everything here is a
local pixel operation and costs nothing; plates can be re-processed from the
cached raws as often as the look needs tuning.
"""

import io

from PIL import Image

# The 4x4 ordered matrix, normalised to [0,1). Bayer is what the hardware and
# the era's tooling used; a random or blue-noise dither reads as film grain
# rather than as a console.
BAYER_4 = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]


def grade(image, gamma=0.75, white=0.85, contrast=1.12):
    """Bring an offline render up to the era's contrast before compressing it.

    A raytraced frame comes out of the renderer sitting in its midtones. The
    look these backgrounds are after does the opposite: blown-out sky and
    windows against shadow that goes almost black, with the readable detail
    squeezed into a narrow band between them. `white` pulls the white point
    down so highlights clip rather than roll off, which is what makes a window
    read as daylight instead of as a pale rectangle.
    """
    source = image.convert("RGB")
    pixels = source.load()
    width, height = source.size
    out = Image.new("RGB", (width, height))
    target = out.load()
    # A 256-entry curve, applied per channel: the whole grade is a lookup.
    curve = []
    for value in range(256):
        v = (value / 255.0) ** gamma
        v = v / white
        v = (v - 0.5) * contrast + 0.5
        curve.append(int(max(0.0, min(1.0, v)) * 255 + 0.5))
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            target[x, y] = (curve[r], curve[g], curve[b])
    return out


def mdec(image, quality=50):
    """Re-encode through a DCT codec with half-resolution chroma.

    Pillow's JPEG encoder is a close enough stand-in for MDEC: the same
    transform, the same subsampling, the same class of artefact. Quality is
    the one dial worth touching - lower ruins the plaster, higher loses the
    ringing that makes it read as compressed at all.
    """
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, "JPEG", quality=quality, subsampling=2,
                              optimize=False)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def rgb555(image, dither=1.0):
    """Quantise to 15-bit colour with an ordered dither, as the framebuffer did.

    `dither` scales the threshold: 1.0 spreads a full quantisation step, which
    is the correct amount to turn a hard band into a crosshatch. 0 truncates
    and bands, which is also period-accurate for studios that did not bother.
    """
    source = image.convert("RGB")
    width, height = source.size
    pixels = source.load()
    out = Image.new("RGB", (width, height))
    target = out.load()
    step = 8  # 256 levels down to 32
    for y in range(height):
        row = BAYER_4[y & 3]
        for x in range(width):
            bias = (row[x & 3] / 16.0 - 0.5) * step * dither
            r, g, b = pixels[x, y]
            values = []
            for channel in (r, g, b):
                v = channel + bias
                v = 0 if v < 0 else (255 if v > 255 else v)
                level = int(v / step)
                level = 31 if level > 31 else level
                # Expand back the way the hardware did, so white stays white.
                values.append((level << 3) | (level >> 2))
            target[x, y] = tuple(values)
    return out


def apply(image, quality=50, dither=0.5, graded=True):
    """The full chain, in the order the console applied it."""
    if graded:
        image = grade(image)
    return rgb555(mdec(image, quality=quality), dither=dither)


def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--quality", type=int, default=50)
    parser.add_argument("--dither", type=float, default=0.5)
    parser.add_argument("--suffix", default="")
    args = parser.parse_args()
    for path in args.paths:
        with Image.open(path) as source:
            result = apply(source, quality=args.quality, dither=args.dither)
        root, extension = os.path.splitext(path)
        result.save(root + args.suffix + extension)
        print("PS1 %-40s q=%d dither=%.2f" % (os.path.basename(path),
                                              args.quality, args.dither))


if __name__ == "__main__":
    main()
