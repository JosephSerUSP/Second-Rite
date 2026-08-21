"""Contact-sheet assembly (plain CPython, no Blender)."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BG = (22, 23, 26)
FG = (232, 230, 224)
DIM = (150, 148, 142)
ACCENT = (196, 122, 96)


def _font(size):
    for name in ("consola.ttf", "seguisb.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def material_sheet(micro_json, out_path, *, scale=2, cols=5):
    data = json.loads(Path(micro_json).read_text(encoding="utf-8"))
    items = sorted(data.items(), key=lambda kv: (kv[1]["kind"], kv[0]))
    sw = 128 * scale
    pad, label_h, head = 14, 40, 74
    rows = (len(items) + cols - 1) // cols
    W = pad + cols * (sw + pad)
    H = head + rows * (sw + label_h + pad) + pad
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title, f_lab, f_sub = _font(24), _font(16), _font(13)
    d.text((pad, 18), "Clean-room material vocabulary", font=f_title, fill=FG)
    d.text((pad, 48),
           "rendered at the scene's true native density, 27.4286 px per world metre",
           font=f_sub, fill=DIM)

    for i, (mid, meta) in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (sw + pad)
        y = head + r * (sw + label_h + pad)
        try:
            s = Image.open(meta["swatch"]).convert("RGB")
            s = s.resize((sw, sw), Image.NEAREST)
            img.paste(s, (x, y))
        except Exception:
            d.rectangle([x, y, x + sw, y + sw], fill=(60, 30, 30))
        kind = meta["kind"]
        col = {"public": (120, 175, 200), "generated": (200, 165, 110),
               "procedural": (150, 190, 140)}.get(kind, FG)
        d.rectangle([x, y, x + sw - 1, y + sw - 1], outline=(70, 72, 78))
        d.text((x + 2, y + sw + 4), mid, font=f_lab, fill=FG)
        d.text((x + 2, y + sw + 22),
               "%s  -  %.2f m tile%s" % (kind, meta["tile_m"],
                                         "  -  relief" if meta["displaceable"] else ""),
               font=f_sub, fill=col)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path


def gauntlet_sheet(entries, out_path, *, scale=2, cols=3, title=None,
                   subtitle=None):
    """3x3 sheet of true 426x240 renders with labels and blind scores."""
    tw, th = 426 * scale, 240 * scale
    pad, label_h, head = 16, 58, 88
    rows = (len(entries) + cols - 1) // cols
    W = pad + cols * (tw + pad)
    H = head + rows * (th + label_h + pad) + pad
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title, f_id, f_lab, f_sub = _font(30), _font(24), _font(18), _font(15)
    d.text((pad, 18), title or "Clean-room town gauntlet", font=f_title, fill=FG)
    if subtitle:
        d.text((pad, 56), subtitle, font=f_sub, fill=DIM)

    for i, e in enumerate(entries):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = head + r * (th + label_h + pad)
        try:
            s = Image.open(e["render"]).convert("RGB").resize((tw, th), Image.NEAREST)
            img.paste(s, (x, y))
        except Exception:
            d.rectangle([x, y, x + tw, y + th], fill=(60, 30, 30))
        d.rectangle([x, y, x + tw - 1, y + th - 1], outline=(70, 72, 78))
        d.text((x + 2, y + th + 5), e["id"], font=f_id, fill=FG)
        score = e.get("score")
        if score is not None:
            sx = x + tw - 108
            d.text((sx, y + th + 5), "%.2f" % score, font=f_id,
                   fill=ACCENT if e.get("winner") else FG)
            d.text((sx + 62, y + th + 12), "/ 10", font=f_sub, fill=DIM)
        concept = e.get("concept", "")
        while concept and d.textlength(concept, font=f_lab) > tw - 8:
            concept = concept[:-2]
        d.text((x + 2, y + th + 32), concept, font=f_lab, fill=DIM)
        if e.get("winner"):
            d.rectangle([x - 3, y - 3, x + tw + 2, y + th + 2], outline=ACCENT, width=3)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path


def strip(images, out_path, *, labels=None, scale=2, title=None):
    imgs = [Image.open(p).convert("RGB") for p in images]
    w, h = imgs[0].size
    tw, th = w * scale, h * scale
    pad, head, label_h = 14, 62 if title else 14, 34
    W = pad + len(imgs) * (tw + pad)
    H = head + th + label_h + pad
    out = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(out)
    if title:
        d.text((pad, 18), title, font=_font(26), fill=FG)
    f = _font(18)
    for i, im in enumerate(imgs):
        x = pad + i * (tw + pad)
        out.paste(im.resize((tw, th), Image.NEAREST), (x, head))
        d.rectangle([x, head, x + tw - 1, head + th - 1], outline=(70, 72, 78))
        if labels:
            d.text((x + 2, head + th + 6), labels[i], font=f, fill=DIM)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)
    return out_path
