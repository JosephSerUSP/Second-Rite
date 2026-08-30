"""Pack Kenney grass tufts into the atlas the grass scatter samples.

The foliage card atlas already in the tree holds four full-height BRANCH
sprays, which is why an early grass field read as tiny twigs.  The same CC0
pack ships proper grass tufts; this selects four of them and lays them out in
the same four-column convention.

Two layout rules matter and neither is cosmetic:

- Each tuft is flush with the BOTTOM of its cell.  The card's v=0 edge is
  where the blade meets the ground, so a sprite floated inside its cell would
  hover above the surface by however much padding it was given.
- Each tuft keeps its own aspect ratio inside a square cell rather than being
  stretched to fill it.  Stretching a narrow tuft to a square makes a
  fundamentally different plant, and the scatter already varies width.

    python tools/materials/make_grass_atlas.py

Source is the pack unzipped under ``out/kenney-foliage`` (gitignored); the
produced atlas is committed, so this only needs rerunning to change selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "out/kenney-foliage/PNG/Flat"
TARGET = ROOT / "projects/hichaukitoden-game/assets/materials/foliage_card/kenney_grass_atlas.png"
CELL = 1024
#: Chosen by eye from a contact sheet of all 50 sprites, for variety of tuft
#: silhouette rather than for any measured property.  Metrics ranked broad
#: leaves above grass here, so the selection is deliberately a judgement.
SPRITES = (
    "sprite_0002.png",  # classic tuft, solid base, splayed blades
    "sprite_0004.png",  # broader tuft, blades fanning wider
    "sprite_0012.png",  # mixed blade lengths, airier
    "sprite_0021.png",  # fine grass with seed heads
)


def build(source: Path = SOURCE, target: Path = TARGET) -> dict:
    if not source.is_dir():
        raise SystemExit(f"Kenney pack not found at {source}; unzip it there first")
    atlas = Image.new("RGBA", (CELL * len(SPRITES), CELL), (255, 255, 255, 0))
    for column, name in enumerate(SPRITES):
        sprite = Image.open(source / name).convert("RGBA")
        bbox = sprite.getchannel("A").getbbox()
        if bbox is None:
            raise SystemExit(f"{name} has no opaque pixels")
        sprite = sprite.crop(bbox)
        scale = min(CELL / sprite.width, CELL / sprite.height)
        sprite = sprite.resize((max(1, int(sprite.width * scale)),
                                max(1, int(sprite.height * scale))),
                               Image.LANCZOS)
        # Centred across, flush to the bottom: v=0 is the ground line.
        atlas.alpha_composite(sprite, (column * CELL + (CELL - sprite.width) // 2,
                                       CELL - sprite.height))
    target.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    print(f"wrote {target.relative_to(ROOT)} {atlas.size} cells={len(SPRITES)}")
    print(f"sha256 {digest}")
    return {"cells": list(SPRITES), "sha256": digest, "size": list(atlas.size)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    record = build(args.source, args.target)
    if args.json:
        print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
