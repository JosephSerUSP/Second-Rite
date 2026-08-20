"""Compose native-size game sprites over a Blender environment render.

The environment remains an authoring/bake source.  This deliberately models
the runtime presentation: actual 24x48 Walker cells are copied 1:1 with
nearest pixels, rather than being scaled as Blender billboard geometry.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
WALKER = ROOT / 'projects' / 'hichaukitoden-game' / 'assets' / 'character' / 'walker.png'

def keyed_frame(sheet: Image.Image, frame: int) -> Image.Image:
    crop = sheet.crop((frame * 24, 0, frame * 24 + 24, 48)).convert('RGBA')
    pixels = crop.load()
    for y in range(48):
        for x in range(24):
            r, g, b, _ = pixels[x, y]
            # Project walker.png uses its opaque blue chroma background.
            pixels[x, y] = (r, g, b, 0 if b > 220 and b - r > 130 else 255)
    return crop

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('environment', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--anchors', type=Path, help='Blender-projected foot positions JSON')
    args = parser.parse_args()
    out = Image.open(args.environment).convert('RGBA')
    if out.size != (426, 240):
        raise SystemExit(f'environment must be native 426x240, got {out.size}')
    sheet = Image.open(WALKER)
    positions = ((190, 206, 0), (128, 206, 1), (276, 206, 2))
    if args.anchors:
        points = json.loads(args.anchors.read_text(encoding='utf-8'))
        positions = tuple((round(points[name]['x'] - 12), round(points[name]['y']), frame)
                          for name, frame in (('spawn_player', 0), ('npc_merchant', 1), ('npc_guard', 2)))
    for x, y, frame in positions:
        out.alpha_composite(keyed_frame(sheet, frame), (x, y - 48))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.convert('RGB').save(args.output)

if __name__ == '__main__':
    main()
