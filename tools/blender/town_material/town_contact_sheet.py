"""town-gauntlet-contact-sheet.png -- 3x3, native renders, aspect preserved."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "projects/hichaukitoden-game/assets/authoring/town/attempts_next"
OUT = ROOT / "projects/hichaukitoden-game/assets/authoring/town/town-gauntlet-contact-sheet.png"

SCALE = 2                     # native 426x240 shown at 2x nearest, aspect intact
CW, CH = 426 * SCALE, 240 * SCALE
PAD, LABEL, HDR = 16, 56, 74
BG, FG, DIM = (18, 19, 23), (238, 238, 244), (150, 154, 168)
BIAS_COLOUR = {"A": (126, 200, 255), "B": (150, 226, 150),
               "C": (255, 186, 120), "hybrid": (215, 170, 255)}
BIAS_LABEL = {"A": "procedural-led", "B": "CC0-library-led",
              "C": "generated-led", "hybrid": "hybrid"}


def _f(sz, bold=False):
    for n in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(n, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def main():
    census = json.loads((SRC / "census.json").read_text(encoding="utf-8"))
    scores = {}
    sp = SRC / "evaluation.json"
    if sp.is_file():
        ev = json.loads(sp.read_text(encoding="utf-8"))
        scores = {k: v.get("mean") for k, v in ev.get("byAttempt", {}).items()}

    ids = [f"{i:02d}" for i in range(1, 10)]
    W = PAD + 3 * (CW + PAD)
    H = HDR + 3 * (CH + LABEL + PAD)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 14), "SECOND GATE - TOWN VISUAL GAUNTLET (next camera)", fill=FG, font=_f(30, True))
    d.text((PAD, 48), "426x240 native renders at 2x nearest  -  level side view, "
                      "0 deg pitch, 43.2676 mm, fixed eye", fill=DIM, font=_f(15))

    for n, aid in enumerate(ids):
        r, c = divmod(n, 3)
        x = PAD + c * (CW + PAD)
        y = HDR + r * (CH + LABEL + PAD)
        p = SRC / ("attempt_%s.png" % aid)
        if p.is_file():
            im = Image.open(p).convert("RGB").resize((CW, CH), Image.NEAREST)
            sheet.paste(im, (x, y))
        else:
            d.rectangle([x, y, x + CW, y + CH], fill=(30, 31, 36))
            d.text((x + CW // 2 - 40, y + CH // 2), "not run", fill=DIM, font=_f(18))
        d.rectangle([x, y, x + CW - 1, y + CH - 1], outline=(62, 64, 74))

        rec = census.get(aid, {})
        bias = rec.get("bias", "")
        col = BIAS_COLOUR.get(bias, DIM)
        d.text((x, y + CH + 6), aid, fill=FG, font=_f(21, True))
        d.text((x + 34, y + CH + 8), rec.get("title", ""), fill=FG, font=_f(16, True))
        sub = BIAS_LABEL.get(bias, bias)
        if rec:
            sub += "   src %s tris -> rnd %s  (%s:1)" % (
                f"{rec.get('sourceTris', 0):,}", f"{rec.get('renderTris', 0):,}",
                f"{rec.get('reductionRatio', 0):.0f}")
        d.text((x + 34, y + CH + 30), sub, fill=col, font=_f(13))
        if aid in scores and scores[aid] is not None:
            s = "%.2f" % scores[aid]
            d.text((x + CW - 62, y + CH + 6), s, fill=(240, 205, 90), font=_f(22, True))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print("wrote %s %s" % (OUT, sheet.size))


if __name__ == "__main__":
    main()
