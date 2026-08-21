#!/usr/bin/env python3
"""Make compact review sheets for the Second Gate town handoff."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def panel(path: Path, label: str, scale=2):
    image = Image.open(path).convert("RGB")
    image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (image.width, image.height + 28), (18, 24, 29))
    canvas.paste(image, (0, 28))
    ImageDraw.Draw(canvas).text((8, 6), label, fill=(235, 232, 219), font=font(16))
    return canvas


def sheet(items, output, columns=3):
    cards = [panel(path, label) for path, label in items]
    width = max(card.width for card in cards)
    height = max(card.height for card in cards)
    rows = (len(cards) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * width, rows * height), (7, 12, 16))
    for index, card in enumerate(cards):
        canvas.paste(card, ((index % columns) * width, (index // columns) * height))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    clay = root / "renders" / "clay"
    refined = root / "renders" / "refined"
    final = root / "renders" / "final"
    sheet([
        (clay / "direction_a_initial.png", "A / canal arcade / clay"),
        (clay / "direction_b_initial.png", "B / terraced rookery / clay"),
        (clay / "direction_c_initial.png", "C / bell foundry / clay"),
    ], root / "renders" / "architectural_directions_clay.png")
    sheet([
        (refined / "direction_a_refined.png", "A / refined"),
        (refined / "direction_b_refined.png", "B / refined"),
        (refined / "direction_c_refined.png", "C / winning refined"),
    ], root / "renders" / "architectural_directions_refined.png")
    sheet([
        (final / "th_source_rich_matched.png", "TH_SOURCE / rich"),
        (final / "projection_window_+0.png", "TH_RENDER / baked atlas"),
    ], root / "renders" / "source_vs_baked_native.png", columns=2)
    sheet([
        (final / "projection_window_-96.png", "projection window -96"),
        (final / "projection_window_+0.png", "projection window 0"),
        (final / "projection_window_+96.png", "projection window +96"),
    ], root / "renders" / "projection_window_strip.png")
    print("SECOND_GATE_CONTACT_SHEETS_OK")


if __name__ == "__main__":
    main()
