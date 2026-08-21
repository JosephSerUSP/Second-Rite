"""Make compact visual evidence sheets from native-size render outputs."""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "out" / "blender" / "second-gate-human-assets-20260821" / "evidence"


def sheet(output, entries, cols=2, scale=2):
    thumbs = []
    for label, path in entries:
        image = Image.open(path).convert("RGB")
        image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
        thumbs.append((label, image))
    cell_w = max(im.width for _, im in thumbs)
    cell_h = max(im.height for _, im in thumbs) + 26
    rows = (len(thumbs) + cols - 1) // cols
    canvas = Image.new("RGB", (cell_w * cols, cell_h * rows), (24, 28, 38))
    draw = ImageDraw.Draw(canvas)
    for i, (label, image) in enumerate(thumbs):
        x = (i % cols) * cell_w
        y = (i // cols) * cell_h
        canvas.paste(image, (x, y + 26))
        draw.text((x + 8, y + 5), label, fill=(240, 240, 240))
    canvas.save(output)


def main():
    out = EVIDENCE / "contact-sheet.png"
    sheet(out, [
        ("early A", EVIDENCE / "direction-A" / "early_A.png"),
        ("early B", EVIDENCE / "direction-B" / "early_B.png"),
        ("developed A / winner", EVIDENCE / "direction-A" / "developed_A.png"),
        ("developed B", EVIDENCE / "direction-B" / "developed_B.png"),
        ("winner source center", EVIDENCE / "winner" / "source-center.png"),
        ("winner runtime baked", EVIDENCE / "winner" / "runtime-baked.png"),
    ])
    sheet(EVIDENCE / "winner-extremes-sheet.png", [
        ("source left -96", EVIDENCE / "winner" / "source-left.png"),
        ("source center 0", EVIDENCE / "winner" / "source-center.png"),
        ("source right +96", EVIDENCE / "winner" / "source-right.png"),
        ("runtime baked", EVIDENCE / "winner" / "runtime-baked.png"),
    ])
    sheet(EVIDENCE / "source-vs-runtime.png", [
        ("source center", EVIDENCE / "winner" / "source-center.png"),
        ("runtime baked", EVIDENCE / "winner" / "runtime-baked.png"),
    ], cols=2, scale=3)
    print(out)


if __name__ == "__main__":
    main()
