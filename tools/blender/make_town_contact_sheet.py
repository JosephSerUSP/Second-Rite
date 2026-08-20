"""Compose the nine native-size town renders into the gauntlet contact sheet."""

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


def load_scores(path):
    if not path or not Path(path).is_file():
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data.get("attempts", data if isinstance(data, list) else [])
    return {int(row["id"]): row for row in rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--renders", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--scores")
    args = parser.parse_args()
    render_dir = Path(args.renders)
    scores = load_scores(args.scores)
    cell_w, cell_h = 426, 240
    bar_h = 34
    gap = 10
    sheet = Image.new("RGB", (cell_w * 3 + gap * 4, (cell_h + bar_h) * 3 + gap * 4), (20, 20, 26))
    draw = ImageDraw.Draw(sheet)
    label_font = font(18, bold=True)
    sub_font = font(13)
    for index in range(9):
        attempt_id = index + 1
        x = gap + (index % 3) * (cell_w + gap)
        y = gap + (index // 3) * (cell_h + bar_h + gap)
        image_path = render_dir / f"attempt-{attempt_id:02d}.png"
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        image = Image.open(image_path).convert("RGB")
        if image.size != (cell_w, cell_h):
            image.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
        sheet.paste(image, (x, y + bar_h))
        draw.rectangle((x, y, x + cell_w, y + bar_h), fill=(31, 31, 40))
        row = scores.get(attempt_id, {})
        name = row.get("name", f"Attempt {attempt_id:02d}")
        rank = row.get("rank")
        total = row.get("total")
        score_text = f"  score {total:.1f}" if isinstance(total, (int, float)) else ""
        rank_text = f"  rank #{rank}" if rank else ""
        draw.text((x + 10, y + 7), f"{attempt_id:02d}  {name}{rank_text}{score_text}",
                  fill=(239, 231, 209), font=label_font)
        if row.get("evaluator_note"):
            note = str(row["evaluator_note"])[:86]
            draw.text((x + 10, y + cell_h + bar_h - 22), note, fill=(220, 215, 198), font=sub_font)
    sheet.save(args.output)
    print(f"CONTACT SHEET OK: {args.output} ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
