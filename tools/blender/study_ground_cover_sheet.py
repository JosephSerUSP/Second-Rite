"""Contact sheets for the ground-cover placement study (`study_ground_cover_placement.py`).

    python tools/blender/study_ground_cover_sheet.py --dir out/grass-study

Writes two images next to the renders:

  * `placement_sheet.png`: the baseline and every candidate at the plate's native
    906 x 240, the rows the persistent menu covers (144-240) dimmed so you can see
    what the player will and will not see, each labelled with its tuft counts;
  * `placement_zoom.png`: the same, cropped to the lane and building fronts and
    doubled with nearest-neighbour, because a 9 px tuft is hard to judge at 1x.

Numbers rank nothing here. The owner picks by eye.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

LABEL = 18
DIM = 0.42
ZOOM = 2
CROP = (440, 88, 906, 200)   # x0, y0, x1, y1 of the plate: the right-hand lane and fronts


def dimmed(image: Image.Image, top_row: int) -> Image.Image:
    shade = Image.new("RGB", image.size, (0, 0, 0))
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rectangle((0, top_row, image.width, image.height), fill=int(255 * DIM))
    out = image.copy()
    out.paste(shade, (0, 0), mask)
    ImageDraw.Draw(out).line((0, top_row, image.width, top_row), fill=(255, 200, 60), width=1)
    return out


def stack(tiles: list[tuple[str, Image.Image]]) -> Image.Image:
    width = max(t.width for _, t in tiles)
    sheet = Image.new("RGB", (width, sum(t.height + LABEL for _, t in tiles)), (22, 22, 22))
    draw = ImageDraw.Draw(sheet)
    y = 0
    for label, tile in tiles:
        draw.text((4, y + 3), label, fill=(235, 235, 235))
        sheet.paste(tile, (0, y + LABEL))
        y += tile.height + LABEL
    return sheet


def main() -> int:
    parser = argparse.ArgumentParser(prog="study_ground_cover_sheet")
    parser.add_argument("--dir", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads((args.dir / "placement.json").read_text(encoding="utf-8"))
    top = report["menuTopRow"]

    entries = [("baseline: no cover", args.dir / "baseline.png")]
    for key, candidate in report["candidates"].items():
        entries.append((f"{key}  {candidate['label']}: {candidate['tufts']} tufts "
                        f"({candidate['triangles']} tris), {candidate['aboveMenu']} above the menu / "
                        f"{candidate['underMenu']} under it", args.dir / f"{key}.png"))
    full, zoom = [], []
    for label, path in entries:
        image = Image.open(path).convert("RGB")
        shaded = dimmed(image, top)
        full.append((label, shaded))
        crop = shaded.crop(CROP)
        zoom.append((label, crop.resize((crop.width * ZOOM, crop.height * ZOOM), Image.NEAREST)))
    stack(full).save(args.dir / "placement_sheet.png")
    stack(zoom).save(args.dir / "placement_zoom.png")
    print(args.dir / "placement_sheet.png")
    print(args.dir / "placement_zoom.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
