"""Contact sheet for the plate picture pipeline.

Two questions, and they are different questions:

1. How much DCT (MDEC) is right? Too much and it reads as a bad JPEG rather
   than as a console; too little and nothing says "compressed" at all.
2. How much dither, and of what kind? The hardware dithered before truncating
   to 15-bit, so dithering is period-accurate whatever amount is chosen. An
   ordered Bayer pattern is what the era used; Floyd-Steinberg is what an
   image OPTIMISER would use, and reads as a carefully prepared asset rather
   than as a framebuffer.

Sheet A varies those two against each other. Sheet B tries the paletted
approaches, because a lot of what people remember as "the PS1 look" is
actually a small indexed palette with a dither over it -- which is what a
carefully optimised background asset looked like, and is nothing like a JPEG.

    python tools/towngen/ps1_contact_sheet.py
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps1_filter  # noqa: E402

PLATES = os.path.join("projects", "hichaukitoden-game", "assets", "environments",
                      "st_maria_town", "plates")
OUT = os.path.join("out", "ps1_sheets")
SCALE = 2
LABEL_H = 16


def sample(name, left):
    """A 256-wide window: one Classic screen of a real plate."""
    with Image.open(os.path.join(PLATES, name)) as image:
        return image.convert("RGB").crop((left, 0, left + 256, 144))


def paletted(image, colours, dither):
    """Quantise to an adaptive palette, the way an asset pipeline would."""
    method = Image.FLOYDSTEINBERG if dither else Image.NONE
    return image.convert("RGB").quantize(
        colors=colours, method=Image.MEDIANCUT, dither=method).convert("RGB")


def floyd_555(image):
    """15-bit, but error-diffused instead of ordered.

    A 5-bit-per-channel grid is 32768 colours, far past the 256 an indexed
    palette can hold, so this diffuses directly rather than going through
    Pillow's quantiser.
    """
    import numpy

    data = numpy.asarray(image.convert("RGB")).astype(numpy.float32)
    height, width, _ = data.shape
    for y in range(height):
        for x in range(width):
            old = data[y, x].copy()
            level = numpy.clip(numpy.round(old / 8.0), 0, 31)
            new = level * 8 + numpy.floor(level / 4)
            data[y, x] = new
            error = old - new
            if x + 1 < width:
                data[y, x + 1] += error * (7 / 16.0)
            if y + 1 < height:
                if x > 0:
                    data[y + 1, x - 1] += error * (3 / 16.0)
                data[y + 1, x] += error * (5 / 16.0)
                if x + 1 < width:
                    data[y + 1, x + 1] += error * (1 / 16.0)
    return Image.fromarray(numpy.clip(data, 0, 255).astype(numpy.uint8))


def sheet(cells, columns, path, title):
    """cells: [(label, image)] laid out row-major."""
    cell_w, cell_h = 256 * SCALE, 144 * SCALE + LABEL_H
    rows = (len(cells) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell_w, rows * cell_h + 22), (18, 18, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 6), title, fill=(235, 235, 225))
    for index, (label, image) in enumerate(cells):
        x = (index % columns) * cell_w
        y = (index // columns) * cell_h + 22
        canvas.paste(image.resize((256 * SCALE, 144 * SCALE), Image.NEAREST), (x, y))
        draw.rectangle([x, y + 144 * SCALE, x + cell_w, y + cell_h], fill=(18, 18, 20))
        draw.text((x + 6, y + 144 * SCALE + 3), label, fill=(210, 210, 200))
    os.makedirs(OUT, exist_ok=True)
    canvas.save(os.path.join(OUT, path))
    print("%-28s %dx%d  (%d cells)" % (path, canvas.width, canvas.height, len(cells)))


def main():
    # The praca stair: flat wet plaster that bands, carved stone that rings,
    # and a lamp highlight. If a setting survives this crop it survives.
    source = ps1_filter.grade(sample("praca_stair_bg.png", 330))

    # --- Sheet A: how much DCT against how much ordered dither -------------
    cells = []
    for quality in (None, 85, 70, 55):
        for dither in (0.0, 0.6, 1.0, 1.6):
            image = source if quality is None else ps1_filter.mdec(source, quality)
            image = ps1_filter.rgb555(image, dither=dither)
            cells.append(("DCT %-4s  dither %.1f"
                          % ("off" if quality is None else quality, dither), image))
    sheet(cells, 4, "sheet_a_dct_vs_dither.png",
          "A - MDEC quality (rows) against ordered dither strength (columns), all at 15-bit")

    # --- Sheet B: the paletted alternatives --------------------------------
    cells = [
        ("source (graded only)", source),
        ("current: DCT 50, Bayer 0.6", ps1_filter.rgb555(
            ps1_filter.mdec(source, 50), dither=0.6)),
        ("15-bit, Floyd-Steinberg", floyd_555(source)),
        ("15-bit, Bayer 1.0, no DCT", ps1_filter.rgb555(source, dither=1.0)),
        ("256 colours, F-S", paletted(source, 256, True)),
        ("128 colours, F-S", paletted(source, 128, True)),
        ("64 colours, F-S", paletted(source, 64, True)),
        ("64 colours, no dither", paletted(source, 64, False)),
        ("DCT 80 then 256 colours F-S",
         paletted(ps1_filter.mdec(source, 80), 256, True)),
        ("DCT 80 then 15-bit Bayer 1.0",
         ps1_filter.rgb555(ps1_filter.mdec(source, 80), dither=1.0)),
        ("DCT 70 then 128 colours F-S",
         paletted(ps1_filter.mdec(source, 70), 128, True)),
        ("DCT 70 then 15-bit F-S", floyd_555(ps1_filter.mdec(source, 70))),
    ]
    sheet(cells, 3, "sheet_b_palette.png",
          "B - paletted and error-diffused alternatives against the current chain")


if __name__ == "__main__":
    main()
