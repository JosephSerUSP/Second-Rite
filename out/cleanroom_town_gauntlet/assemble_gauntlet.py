from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageChops, ImageEnhance, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ATTEMPTS = ROOT / "attempts"


def font(size, bold=False):
    names = ["arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def contact(scores=None):
    scores = scores or {}
    scale = 2
    cw, ch = 426 * scale, 240 * scale
    pad, label, header = 18, 48, 70
    sheet = Image.new("RGB", (pad + 3 * (cw + pad), header + 3 * (ch + label + pad)), (13, 16, 24))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 12), "SECOND GATE - CLEAN-ROOM TOWN GAUNTLET", fill=(241, 238, 228), font=font(28, True))
    d.text((pad, 45), "426x240 native renders / 0 deg level side view / 43.2676 mm / blind score shown only after selection", fill=(150, 160, 178), font=font(14))
    for n in range(1, 10):
        aid = f"{n:02d}"
        r, c = divmod(n - 1, 3)
        x, y = pad + c * (cw + pad), header + r * (ch + label + pad)
        p = ATTEMPTS / f"attempt_{aid}.png"
        im = Image.open(p).convert("RGB").resize((cw, ch), Image.Resampling.NEAREST)
        sheet.paste(im, (x, y))
        d.rectangle((x, y, x + cw - 1, y + ch - 1), outline=(62, 70, 88))
        d.text((x, y + ch + 6), aid, fill=(242, 242, 242), font=font(20, True))
        if aid in scores:
            d.text((x + 36, y + ch + 8), f"blind aggregate {scores[aid]:.2f}", fill=(248, 210, 100), font=font(14, True))
    path = ROOT / "town-cleanroom-gauntlet-contact-sheet.png"
    sheet.save(path)
    return path


def comparison():
    src = Image.open(ROOT / "selected_source_beauty.png").convert("RGB")
    baked = Image.open(ROOT / "selected_runtime_environment.png").convert("RGB")
    diff = ImageChops.difference(src, baked)
    mean = sum(sum(p) for p in diff.getdata()) / (src.width * src.height * 3)
    amplified = ImageEnhance.Brightness(diff).enhance(5.0)
    out = Image.new("RGB", (src.width * 3 + 32, src.height + 54), (18, 20, 28))
    out.paste(src, (0, 36)); out.paste(baked, (src.width + 16, 36)); out.paste(amplified, (src.width * 2 + 32, 36))
    d = ImageDraw.Draw(out)
    d.text((6, 10), "A  TH_SOURCE beauty", fill=(238,238,238), font=font(16, True))
    d.text((src.width + 22, 10), "B  baked TH_RENDER", fill=(238,238,238), font=font(16, True))
    d.text((src.width * 2 + 38, 10), f"absolute diff x5  mean={mean:.3f}", fill=(238,238,238), font=font(14, True))
    path = ROOT / "town-cleanroom-source-vs-baked.png"
    out.save(path)
    return path, mean


def projection():
    imgs = [Image.open(ROOT / f"projection_{label}.png").convert("RGB") for label in ("left", "center", "right")]
    out = Image.new("RGB", (426 * 3 + 32, 240 + 52), (18,20,28))
    d = ImageDraw.Draw(out)
    for i, (label, im, off) in enumerate(zip(("left","center","right"), imgs, (-96,0,96))):
        x = i * 426 + (i * 16)
        out.paste(im, (x, 42))
        d.text((x + 8, 10), f"{label}  projection-window {off:+d}px", fill=(238,238,238), font=font(14, True))
    path = ROOT / "town-cleanroom-projection-strip.png"
    out.save(path)
    return path


def main():
    scores_path = ROOT / "evaluation.json"
    scores = {}
    if scores_path.is_file():
        scores = json.loads(scores_path.read_text(encoding="utf-8"))
    path = contact(scores)
    cmp_path, mean = comparison()
    proj = projection()
    print(json.dumps({"contact": str(path), "comparison": str(cmp_path), "projection": str(proj), "meanDiff": mean}, indent=2))


if __name__ == "__main__":
    main()
