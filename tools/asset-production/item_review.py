"""Render item models through the REAL LOVE item viewer and compare takes.

The review loop for item-model work is: change a model, restage the Project,
look at it in the same turntable the game uses, compare it with the previous
take. Doing that by hand was a four-command ritual with a hidden output
directory (LOVE's save dir), so it did not happen often enough.

    python tools/asset-production/item_review.py render --tag before \
        "Plate Armor" "Executioner" --cell 192
    python tools/asset-production/item_review.py compare before after1 after2 \
        --out out/review/board.png

``render`` writes ``out/review/<tag>/<slug>.png`` (one four-view strip per
item) plus ``out/review/<tag>/sheet.png``. ``compare`` stacks the strips of
several tags, one row per item, labelled by tag.

The viewer is the evidence. This tool never judges, it only makes looking cheap.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = ROOT / "out" / "review"
STAGE_DIR = ROOT / "out" / "stage-review"
LOVEC = os.environ.get("LOVEC", r"C:\Program Files\LOVE\lovec.exe")
VIEWS = 4
LABEL = 12
COLUMNS = 14


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def stage():
    subprocess.run(
        ["node", str(ROOT / "tools/ci/stage-project-gates.js"), "--output", str(STAGE_DIR)],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
    )


def render(tag: str, names: list[str], cell: int, restage: bool, timeout: int):
    if restage or not STAGE_DIR.is_dir():
        stage()
    # The sheet sorts by name and lays out `columns` blocks per row; replicate
    # that rather than parsing pixels back out of the image.
    ordered = sorted(names)
    (STAGE_DIR / "review_list.txt").write_text("\n".join(names), encoding="utf-8")
    env = dict(os.environ, ITEM_SHEET_CELL=str(cell))
    out_name = f"review_{tag}.png"
    proc = subprocess.run(
        [LOVEC, ".", "item-sheet", "review_list.txt", out_name],
        cwd=STAGE_DIR, env=env, capture_output=True, text=True, timeout=timeout,
    )
    match = re.search(r"ITEM SHEET OK: (\d+) models.*written to (.+)", proc.stdout)
    if not match:
        sys.exit(f"item-sheet failed:\n{proc.stdout}\n{proc.stderr}")
    if int(match.group(1)) != len(names):
        sys.exit(f"item-sheet matched {match.group(1)} of {len(names)} names: check spelling")
    saved = Path(match.group(2).strip())
    target = REVIEW_DIR / tag
    target.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(saved).convert("RGB")
    sheet.save(target / "sheet.png")
    block_w, row_h = cell * VIEWS, cell + LABEL
    columns = max(1, min(COLUMNS // VIEWS, len(ordered)))
    for index, name in enumerate(ordered):
        col, row = index % columns, index // columns
        box = (col * block_w, row * row_h, (col + 1) * block_w, row * row_h + cell)
        sheet.crop(box).save(target / f"{slug(name)}.png")
    print(f"RENDERED {len(names)} item(s) -> {target}")
    return target


def compare(tags: list[str], names: list[str], out: Path, scale: int):
    rows = []
    for name in names:
        strips = []
        for tag in tags:
            path = REVIEW_DIR / tag / f"{slug(name)}.png"
            if not path.is_file():
                sys.exit(f"missing {path}: render tag {tag!r} first")
            strips.append(Image.open(path).convert("RGB"))
        rows.append((name, strips))
    cell_w = max(img.width for _, strips in rows for img in strips)
    cell_h = max(img.height for _, strips in rows for img in strips)
    gutter = 14
    board = Image.new(
        "RGB",
        (cell_w * scale, (cell_h * scale + gutter) * len(rows) * len(tags)),
        (26, 26, 31),
    )
    draw = ImageDraw.Draw(board)
    y = 0
    for name, strips in rows:
        for tag, img in zip(tags, strips):
            draw.text((3, y + 1), f"{name}  [{tag}]", fill=(190, 190, 200))
            y += gutter
            board.paste(img.resize((img.width * scale, img.height * scale), Image.NEAREST), (0, y))
            y += cell_h * scale
    board = board.crop((0, 0, board.width, y))
    out.parent.mkdir(parents=True, exist_ok=True)
    board.save(out)
    print(f"BOARD {out} ({board.width}x{board.height})")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--tag", required=True)
    r.add_argument("--cell", type=int, default=192)
    r.add_argument("--no-restage", action="store_true")
    r.add_argument("--timeout", type=int, default=240)
    r.add_argument("names", nargs="+", help="item display names, exactly as in items.json")
    c = sub.add_parser("compare")
    c.add_argument("tags", nargs="+")
    c.add_argument("--items", nargs="+", required=True)
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--scale", type=int, default=1)
    args = parser.parse_args()
    if args.cmd == "render":
        render(args.tag, args.names, args.cell, not args.no_restage, args.timeout)
    else:
        compare(args.tags, args.items, args.out, args.scale)


if __name__ == "__main__":
    main()
