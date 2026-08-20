"""Compose left/center/right fixed-eye projection-window renders."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def get_font(size):
    path = Path(r"C:\Windows\Fonts\segoeui.ttf")
    return ImageFont.truetype(path, size) if path.is_file() else ImageFont.load_default()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.input)
    panels = [Image.open(root / f"{label}.png").convert("RGB") for label in ("left", "center", "right")]
    width, height = panels[0].size
    bar = 36
    gap = 8
    result = Image.new("RGB", (width * 3 + gap * 4, height + bar + gap * 2), (18, 19, 26))
    draw = ImageDraw.Draw(result)
    f = get_font(18)
    for index, (label, image, offset) in enumerate(zip(("LEFT", "CENTER", "RIGHT"), panels, (-96, 0, 96))):
        x = gap + index * (width + gap)
        y = gap
        draw.rectangle((x, y, x + width, y + bar), fill=(34, 34, 44))
        draw.text((x + 10, y + 8), f"{label}  projectionWindowOffsetX={offset:+d}", fill=(239, 231, 209), font=f)
        result.paste(image, (x, y + bar))
    result.save(args.output)
    print(f"PROJECTION STRIP OK: {args.output} ({result.width}x{result.height})")


if __name__ == "__main__":
    main()
