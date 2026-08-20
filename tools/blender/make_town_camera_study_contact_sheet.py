"""Compose five native-size town camera-study renders into a labeled sheet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--renders", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    render_dir = Path(args.renders)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    rows = report["renders"]
    cell_w, cell_h = 426, 240
    bar_h = 56
    gap = 10
    columns, rows_count = 3, 2
    sheet = Image.new(
        "RGB",
        (cell_w * columns + gap * (columns + 1),
         (cell_h + bar_h) * rows_count + gap * (rows_count + 1)),
        (20, 20, 26),
    )
    draw = ImageDraw.Draw(sheet)
    title_font = font(16, bold=True)
    detail_font = font(12)

    for index, row in enumerate(rows):
        x = gap + (index % columns) * (cell_w + gap)
        y = gap + (index // columns) * (cell_h + bar_h + gap)
        image_path = render_dir / f"{row['id']}.png"
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        image = Image.open(image_path).convert("RGB")
        if image.size != (cell_w, cell_h):
            raise RuntimeError(f"{image_path} is {image.size}, expected {(cell_w, cell_h)}")
        sheet.paste(image, (x, y + bar_h))
        draw.rectangle((x, y, x + cell_w, y + bar_h), fill=(31, 31, 40))
        draw.text((x + 9, y + 6), f"{row['id']}  {row['name']}",
                  fill=(239, 231, 209), font=title_font)
        detail = (f"pitch {row['pitchDegrees']:.1f}°   "
                  f"fovHalf {row['fovHalfX']:.6f}/{row['fovHalfY']:.6f}   "
                  f"lens {row['derivedBlenderLensMm']:.2f}mm   actor world 1:1")
        draw.text((x + 9, y + 31), detail, fill=(220, 215, 198), font=detail_font)

    sheet.save(args.output)
    print(f"CAMERA STUDY CONTACT SHEET OK: {args.output} ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
