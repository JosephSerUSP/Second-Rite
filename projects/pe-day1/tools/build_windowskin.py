"""PE Day 1 windowskins: the original's bevelled PS1 frames, as original art.

    python projects/pe-day1/tools/build_windowskin.py

Writes assets/system/windowskin_{back,button,button_highlight}.png in the
engine's windowskin layout (runtime/presentation/presentation.json,
atlas.windowskin): the first 32x32 tiles as the interior, x=32..64 carries the
8px border ring, arrows at 40..56. Everything outside those blocks (digit
glyphs, text-colour ramps) is kept from the main game's sheet so text keeps
the engine's colours.

Look, from the original's menu captures (private reference pack, zoomed):
panels have NO fill -- the room, already darkened behind the menu, shows
straight through. The frame is a thin translucent grey bar with mitred 45
degree corners, lighter along the top and left, darker along the bottom and
right, like a picture frame. Buttons are raised square tiles; the selected
row is a blue band.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "projects" / "hichaukitoden-game" / "assets" / "system" / "windowskin_back.png"
OUT = ROOT / "projects" / "pe-day1" / "assets" / "system"

BAR = 3                       # frame bar width in pixels


def frame(img, light, dark, edge):
    """Mitred bevel bar around the 32x32 ring block at x=32..64: each side is
    a trapezoid, so the corners meet on the diagonal."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 32, 0, 63, 31
    d.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 0))
    b = BAR
    sides = {
        "top": ([(x0, y0), (x1, y0), (x1 - b, y0 + b), (x0 + b, y0 + b)], light),
        "left": ([(x0, y0), (x0 + b, y0 + b), (x0 + b, y1 - b), (x0, y1)], light),
        "bottom": ([(x0, y1), (x0 + b, y1 - b), (x1 - b, y1 - b), (x1, y1)], dark),
        "right": ([(x1, y0), (x1, y1), (x1 - b, y1 - b), (x1 - b, y0 + b)], dark),
    }
    for poly, colour in sides.values():
        d.polygon(poly, fill=colour)
    # a 1px darker line on the bar's inner edge sets it off from the room
    d.line([(x0 + b, y0 + b), (x1 - b, y0 + b)], fill=edge)
    d.line([(x0 + b, y0 + b), (x0 + b, y1 - b)], fill=edge)
    # scroll arrows (inside the ring block, 40..56 x 8..24)
    d.polygon([(48, 10), (44, 14), (52, 14)], fill=light)
    d.polygon([(48, 21), (44, 17), (52, 17)], fill=light)


def skin(fill, light, dark, edge):
    img = Image.open(BASE).convert("RGBA")
    img.paste((0, 0, 0, 0), (0, 0, 64, 32))
    if fill:
        ImageDraw.Draw(img).rectangle([0, 0, 31, 31], fill=fill)
    frame(img, light, dark, edge)
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    grey_l, grey_d, edge = (170, 172, 176, 190), (96, 98, 104, 190), (30, 31, 34, 150)
    # panels: no fill at all; the darkened room is the background
    skin(None, grey_l, grey_d, edge).save(OUT / "windowskin_back.png")
    # buttons: raised tiles with a faint fill so they read as solid
    skin((70, 72, 78, 120), (196, 198, 202, 220), (70, 72, 78, 220), edge).save(OUT / "windowskin_button.png")
    # the selected row: the original's blue band
    skin((36, 72, 200, 210), (120, 150, 240, 230), (20, 40, 120, 230), edge).save(OUT / "windowskin_button_highlight.png")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
