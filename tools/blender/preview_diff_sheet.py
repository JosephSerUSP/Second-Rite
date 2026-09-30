"""A before / after / difference sheet for renders that should look alike.

    python tools/blender/preview_diff_sheet.py --out sheet.png \
        "chest=old/chest.png:new/chest.png" "props=old/props.png:new/props.png"

Each `LABEL=BEFORE:AFTER` becomes one row: the two images side by side and a difference
strip amplified 4x. It prints, per pair, the mean absolute difference (of 255), the 95th
percentile, and the fraction of pixels more than 8/255 away. The numbers order the pairs;
the sheet is what a person judges. Images of different sizes are refused, not resampled,
because a resample would be the difference.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

LABEL = 16
AMPLIFY = 4


def compare(before: Path, after: Path) -> tuple[Image.Image, Image.Image, Image.Image, dict]:
    a = Image.open(before).convert("RGB")
    b = Image.open(after).convert("RGB")
    if a.size != b.size:
        raise SystemExit(f"{before.name} is {a.size}, {after.name} is {b.size}; refusing to resample")
    x = np.asarray(a, dtype=np.float64)
    y = np.asarray(b, dtype=np.float64)
    delta = np.abs(x - y).max(axis=2)
    strip = Image.fromarray(np.clip(np.abs(x - y) * AMPLIFY, 0, 255).astype(np.uint8))
    # A render that is mostly black background dilutes every whole-frame number, so the
    # same three are also taken over the pixels either image lights at all.
    lit = np.maximum(x.max(axis=2), y.max(axis=2)) > 2
    stats = {"mean": float(delta.mean()), "p95": float(np.percentile(delta, 95)),
             "over8": float((delta > 8).mean()),
             "litMean": float(delta[lit].mean()) if lit.any() else 0.0,
             "litP95": float(np.percentile(delta[lit], 95)) if lit.any() else 0.0,
             "litOver8": float((delta[lit] > 8).mean()) if lit.any() else 0.0,
             "litFraction": float(lit.mean())}
    return a, b, strip, stats


def main() -> int:
    parser = argparse.ArgumentParser(prog="preview_diff_sheet")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("pairs", nargs="+", metavar="LABEL=BEFORE:AFTER")
    args = parser.parse_args()
    rows = []
    for spec in args.pairs:
        label, _, paths = spec.partition("=")
        before, _, after = paths.partition(":")
        if not (label and before and after):
            raise SystemExit(f"expected LABEL=BEFORE:AFTER, got {spec!r}")
        rows.append((label, *compare(Path(before), Path(after))))
    width = max(r[1].width for r in rows) * 3
    sheet = Image.new("RGB", (width, sum(r[1].height + LABEL for r in rows)), (22, 22, 22))
    draw = ImageDraw.Draw(sheet)
    y = 0
    print(f"{'pair':44s} {'mean|d|':>8s} {'p95':>5s} {'>8/255':>7s} | lit region: {'mean':>6s} {'p95':>5s} {'>8/255':>7s} {'lit%':>5s}")
    for label, a, b, strip, stats in rows:
        draw.text((4, y + 2), f"{label}: before | after | difference x{AMPLIFY}   "
                  f"mean {stats['mean']:.2f}  p95 {stats['p95']:.0f}  >8/255 {stats['over8'] * 100:.1f}%  "
                  f"(lit region: mean {stats['litMean']:.2f}, >8/255 {stats['litOver8'] * 100:.1f}%)",
                  fill=(235, 235, 235))
        for column, tile in enumerate((a, b, strip)):
            sheet.paste(tile, (column * a.width, y + LABEL))
        y += a.height + LABEL
        print(f"{label:44s} {stats['mean']:8.2f} {stats['p95']:5.1f} {stats['over8'] * 100:6.1f}% | "
              f"             {stats['litMean']:6.2f} {stats['litP95']:5.1f} {stats['litOver8'] * 100:6.1f}% {stats['litFraction'] * 100:5.1f}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
