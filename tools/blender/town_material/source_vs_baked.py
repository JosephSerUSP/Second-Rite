"""Phase 9: rich TH_SOURCE vs baked-atlas-on-TH_RENDER, matched framing.

Answers one question: how much visual richness survives the collapse?
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
TOWN = ROOT / "projects/hichaukitoden-game/assets/authoring/town"
OUT = TOWN / "winner_source_vs_baked.png"


def _f(sz, bold=False):
    for n in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(n, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def main():
    a = Image.open(TOWN / "winner_source.png").convert("RGB")
    b = Image.open(TOWN / "winner_baked.png").convert("RGB")
    census = json.loads((TOWN / "winner_census.json").read_text(encoding="utf-8"))

    S = 2
    W, H = a.size[0] * S, a.size[1] * S
    PAD, HDR, LAB = 14, 74, 40
    sheet = Image.new("RGB", (PAD + 3 * (W + PAD), HDR + H + LAB + PAD), (18, 19, 23))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 12), "HOW MUCH SURVIVES THE COLLAPSE?", fill=(238, 238, 244), font=_f(28, True))
    d.text((PAD, 48), "attempt %s   %s tris of rich TH_SOURCE  ->  %s tris of TH_RENDER "
                      "carrying one baked atlas   (%.0f:1)"
           % (census["attempt"], f"{census['sourceTris']:,}",
              f"{census['renderTris']:,}", census["reductionRatio"]),
           fill=(150, 154, 168), font=_f(14))

    diff = ImageChops.difference(a, b)
    arr = np.asarray(diff, dtype=np.float64).mean(2)
    boosted = Image.fromarray(np.clip(arr * 3.0, 0, 255).astype(np.uint8)).convert("RGB")

    for i, (img, label) in enumerate([
            (a, "A  rich TH_SOURCE (displaced, full material graphs)"),
            (b, "B  baked atlas on coarse TH_RENDER"),
            (boosted, "difference (x3)  mean %.1f / 255" % arr.mean())]):
        x = PAD + i * (W + PAD)
        sheet.paste(img.resize((W, H), Image.NEAREST), (x, HDR))
        d.rectangle([x, HDR, x + W - 1, HDR + H - 1], outline=(62, 64, 74))
        d.text((x, HDR + H + 9), label, fill=(240, 205, 90), font=_f(16, True))

    sheet.save(OUT)
    print("wrote %s %s   mean abs difference %.2f/255 (%.1f%%)"
          % (OUT, sheet.size, arr.mean(), arr.mean() / 255 * 100))


if __name__ == "__main__":
    main()
