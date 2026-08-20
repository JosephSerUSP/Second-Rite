"""Generate Contact Sheet and Projection Window Strip for Town Gauntlet."""

from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ATTEMPT_NAMES = {
    "01": "01: Old Gate Alley",
    "02": "02: Cathedral Plaza",
    "03": "03: Merchant Way",
    "04": "04: Sunken Wharf Road",
    "05": "05: Rusty Anchor Crossroads",
    "06": "06: Watchtower Promenade",
    "07": "07: Refined Merchant Arch",
    "08": "08: Grand Spire Promenade",
    "09": "09: Bellroot Quarter (Winner)"
}


def create_contact_sheet(attempts_dir: Path, eval_json_path: Path | None, output_path: Path):
    # Cell dimensions
    cell_w = 426
    cell_h = 240
    padding = 16
    header_h = 32
    cols = 3
    rows = 3

    sheet_w = cols * cell_w + (cols + 1) * padding
    sheet_h = rows * (cell_h + header_h) + (rows + 1) * padding + 60  # +60 for master title

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (20, 22, 28, 255))
    draw = ImageDraw.Draw(sheet)

    # Master title
    draw.text((padding, 16), "SECOND RITE — V0 FIRST TOWN SCENE VISUAL GAUNTLET (9 ATTEMPTS)", fill=(240, 240, 245, 255))
    draw.text((padding, 38), "Thestra WorldCamera Calibrated 426x240 | Walker Billboard Preview | Late-90s CG Aesthetic", fill=(160, 165, 180, 255))

    # Load scores if available
    scores = {}
    if eval_json_path and eval_json_path.is_file():
        data = json.loads(eval_json_path.read_text(encoding="utf-8"))
        for item in data:
            att_id = str(item.get("attempt_id", "")).zfill(2)
            scores[att_id] = item.get("average_total_score", None)

    for idx, att_num in enumerate(["01", "02", "03", "04", "05", "06", "07", "08", "09"]):
        r = idx // cols
        c = idx % cols

        x = padding + c * (cell_w + padding)
        y = 60 + padding + r * (cell_h + header_h + padding)

        img_path = attempts_dir / f"attempt_{att_num}.png"
        if img_path.is_file():
            attempt_img = Image.open(img_path).convert("RGBA")
            if attempt_img.size != (cell_w, cell_h):
                attempt_img = attempt_img.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
        else:
            attempt_img = Image.new("RGBA", (cell_w, cell_h), (35, 38, 48, 255))

        # Draw cell background card & border
        card_rect = [x - 2, y - 2, x + cell_w + 2, y + header_h + cell_h + 2]
        border_color = (200, 160, 60, 255) if att_num == "09" else (50, 55, 70, 255)
        draw.rectangle(card_rect, fill=(28, 30, 38, 255), outline=border_color, width=2 if att_num == "09" else 1)

        # Header text
        title = ATTEMPT_NAMES.get(att_num, f"Attempt {att_num}")
        score_val = scores.get(att_num)
        score_str = f"Avg Score: {score_val}/100" if score_val else ""
        
        draw.text((x + 8, y + 8), title, fill=(255, 255, 255, 255) if att_num == "09" else (220, 220, 225, 255))
        if score_str:
            draw.text((x + cell_w - 140, y + 8), score_str, fill=(240, 200, 80, 255) if att_num == "09" else (170, 175, 190, 255))

        # Paste rendered image
        sheet.paste(attempt_img, (x, y + header_h), attempt_img)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, "PNG")
    print(f"[contact_sheet] Generated contact sheet: {output_path}")


def create_projection_strip(left_png: Path, center_png: Path, right_png: Path, output_path: Path):
    img_l = Image.open(left_png).convert("RGBA")
    img_c = Image.open(center_png).convert("RGBA")
    img_r = Image.open(right_png).convert("RGBA")

    w, h = img_c.size
    padding = 16
    header_h = 36
    total_w = 3 * w + 4 * padding
    total_h = h + header_h + 2 * padding + 50

    strip = Image.new("RGBA", (total_w, total_h), (18, 20, 26, 255))
    draw = ImageDraw.Draw(strip)

    # Master title
    draw.text((padding, 14), "THESTRA PROJECTION-WINDOW PANNING PROOF — FIXED-EYE PERSPECTIVE (WINNER ATTEMPT 09)", fill=(240, 240, 245, 255))
    draw.text((padding, 34), "Fixed Eye (5.5, 5.5, 0.5) | Zero Camera Strafe | Offset Translations -96px, 0px, +96px across 426x240 Viewport", fill=(160, 165, 180, 255))

    panels = [
        ("LEFT PROJECTION WINDOW (Offset X = -96px)", img_l),
        ("CENTER PROJECTION WINDOW (Offset X = 0px)", img_c),
        ("RIGHT PROJECTION WINDOW (Offset X = +96px)", img_r)
    ]

    for idx, (label, img) in enumerate(panels):
        x = padding + idx * (w + padding)
        y = 50 + padding

        # Card outline
        draw.rectangle([x - 1, y - 1, x + w + 1, y + header_h + h + 1], fill=(26, 28, 36, 255), outline=(60, 65, 80, 255), width=1)
        draw.text((x + 8, y + 10), label, fill=(220, 225, 240, 255))
        strip.paste(img, (x, y + header_h), img)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    strip.save(output_path, "PNG")
    print(f"[projection_strip] Generated projection window strip: {output_path}")
