"""PE Day 1 windowskins: the original's bevelled PS1 panels, as original art.

    python projects/pe-day1/tools/build_windowskin.py

Writes assets/system/windowskin_{back,button,button_highlight}.png in the
engine's windowskin layout (runtime/presentation/presentation.json,
atlas.windowskin): the first 32x32 tiles as the interior, x=32..64 carries the
8px border ring, arrows at 40..56. Everything outside those blocks (digit
glyphs, text-colour ramps) is kept from the main game's sheet so text keeps
the engine's colours.

Look, from the original's menu captures (private reference pack): a dark,
slightly translucent slate interior; a raised bevel -- light on the top and
left, dark on the bottom and right -- with a thin dark outer edge; the
selected row is a blue band.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "projects" / "hichaukitoden-game" / "assets" / "system" / "windowskin_back.png"
OUT = ROOT / "projects" / "pe-day1" / "assets" / "system"

OUTER = (12, 12, 14, 255)
LIGHT = (178, 182, 190, 255)
MID = (118, 122, 130, 255)
SHADE = (54, 56, 62, 255)
INNER = (24, 25, 29, 255)


def interior(img, top, bottom, alpha):
    """The interior tile. It repeats every 32px, so it is a flat colour: a
    gradient here would band, and the PS1 menus are flat-filled anyway."""
    d = ImageDraw.Draw(img)
    for y in range(32):
        t = y / 31
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (alpha,)
        d.line([(0, y), (31, y)], fill=c)


def ring(img):
    """The 8px border ring at x=32..64, y=0..32: outer edge, two-pixel bevel
    (light top/left, dark bottom/right), a mid line, then an inner shadow."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 32, 0, 63, 31
    d.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 0))
    d.rectangle([x0, y0, x1, y1], outline=OUTER)
    for k in (1, 2):
        d.line([(x0 + k, y0 + k), (x1 - k, y0 + k)], fill=LIGHT)          # top
        d.line([(x0 + k, y0 + k), (x0 + k, y1 - k)], fill=LIGHT)          # left
        d.line([(x0 + k, y1 - k), (x1 - k, y1 - k)], fill=SHADE)          # bottom
        d.line([(x1 - k, y0 + k), (x1 - k, y1 - k)], fill=SHADE)          # right
    d.rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], outline=MID)
    # inner shadow: the recessed interior edge, dark on top/left
    d.line([(x0 + 4, y0 + 4), (x1 - 4, y0 + 4)], fill=INNER)
    d.line([(x0 + 4, y0 + 4), (x0 + 4, y1 - 4)], fill=INNER)
    # clear the rest of the ring's inside so the interior tile shows through
    d.rectangle([x0 + 5, y0 + 5, x1 - 5, y1 - 5], fill=(0, 0, 0, 0))
    # the up/down arrows live inside the ring block (40..56, 8..24)
    d.polygon([(48, 10), (44, 14), (52, 14)], fill=LIGHT)
    d.polygon([(48, 21), (44, 17), (52, 17)], fill=LIGHT)


def skin(top, bottom, alpha):
    img = Image.open(BASE).convert("RGBA")
    img.paste((0, 0, 0, 0), (0, 0, 64, 32))
    interior(img, top, bottom, alpha)
    ring(img)
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    skin((28, 30, 35), (28, 30, 35), 214).save(OUT / "windowskin_back.png")
    skin((38, 40, 46), (38, 40, 46), 236).save(OUT / "windowskin_button.png")
    skin((30, 62, 160), (30, 62, 160), 240).save(OUT / "windowskin_button_highlight.png")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
