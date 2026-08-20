"""Phase 1 output: town-material-gauntlet-contact-sheet.png

Groups samples by surface family so competing strategies sit side by side, and
shows each at BOTH the close-up study scale and the real 426x240 town scale.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "projects/hichaukitoden-game/assets/authoring/town/material_gauntlet"
OUT = ROOT / "projects/hichaukitoden-game/assets/authoring/town/town-material-gauntlet-contact-sheet.png"

CLOSE = 300
GAME_W, GAME_H = 284, 160
PAD = 14
HDR = 58
LABEL = 46

BG = (20, 21, 25)
FG = (238, 238, 244)
DIM = (152, 156, 170)
STRAT_COLOUR = {
    "procedural": (126, 200, 255),
    "public-library": (150, 226, 150),
    "openai-generated": (255, 186, 120),
}


def _font(size, bold=False):
    for n in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            continue
    return ImageFont.load_default()


def main():
    records = json.loads((SRC / "samples.json").read_text(encoding="utf-8"))
    families = OrderedDict()
    for r in records:
        families.setdefault(r["family"], []).append(r)

    cols = max(len(v) for v in families.values())
    cell_w = CLOSE + PAD
    cell_h = CLOSE + GAME_H + LABEL + PAD * 2
    W = PAD + cols * cell_w + PAD
    H = HDR + sum(cell_h + 30 for _ in families) + PAD

    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    f_title = _font(26, True)
    f_fam = _font(19, True)
    f_lab = _font(15, True)
    f_sub = _font(13)

    d.text((PAD, 12), "TOWN MATERIAL MICRO-GAUNTLET", fill=FG, font=f_title)
    d.text((PAD, 40), "identical geometry / camera / lighting / exposure  -  "
                      "upper: 512px study    lower: actual 426x240 town scale",
           fill=DIM, font=f_sub)
    lx = W - 470
    for i, (k, c) in enumerate(STRAT_COLOUR.items()):
        d.rectangle([lx + i * 156, 20, lx + i * 156 + 14, 34], fill=c)
        d.text((lx + i * 156 + 20, 19), k, fill=DIM, font=f_sub)

    y = HDR
    for fam, items in families.items():
        d.text((PAD, y + 4), fam.upper(), fill=FG, font=f_fam)
        y += 30
        for i, r in enumerate(items):
            x = PAD + i * cell_w
            col = STRAT_COLOUR.get(r["strategy"], DIM)
            close = Image.open(SRC / r["close"]).convert("RGB").resize((CLOSE, CLOSE), Image.LANCZOS)
            sheet.paste(close, (x, y))
            # game-scale plate shown at native size, centred, hard nearest upscale
            game = Image.open(SRC / r["game"]).convert("RGB")
            sheet.paste(game.resize((GAME_W, GAME_H), Image.NEAREST), (x + (CLOSE - GAME_W) // 2, y + CLOSE + PAD))
            d.rectangle([x, y, x + CLOSE - 1, y + CLOSE + PAD + GAME_H - 1], outline=(58, 60, 70))
            ty = y + CLOSE + PAD + GAME_H + 6
            d.rectangle([x, ty + 3, x + 10, ty + 13], fill=col)
            d.text((x + 16, ty), r["strategy"], fill=col, font=f_lab)
            d.text((x + 16, ty + 17), r["sourceId"], fill=DIM, font=f_sub)
        y += cell_h + 30

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"wrote {OUT}  {sheet.size}")


if __name__ == "__main__":
    main()
