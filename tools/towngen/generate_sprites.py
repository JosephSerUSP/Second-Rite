"""Generate 24x48 townsperson sprites for the St. Maria side-view town.

The existing `assets/sprites/NPC*.png` sheets are 48x64 nude placeholder
figures - functional for a grid dungeon, wrong for a populated town. The
walker and the `assets/character/town/npc_*.png` set establish the real
contract: a single 24x48 cell, hard alpha, limited palette. (This used to
cite `npc_female_redhead_dress.png`, one of five loose sprites in
assets/character/ that were a brighter, higher chroma register than the town
and have since been removed; the town/ sheets are the surviving vocabulary.)

Each sprite is painted large, keyed off a flat magenta field, cropped to its
own silhouette and then downscaled into one 24x48 cell. Painting large and
reducing is what keeps the proportions readable at this size; asking a model
for 24x48 directly does not work.

Usage:
    python tools/towngen/generate_sprites.py           # whole cast
    python tools/towngen/generate_sprites.py gate_guard
"""

import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

from PIL import Image

MODEL = "gpt-image-2"
SIZE = "1024x1024"
CELL_W, CELL_H = 24, 48
PALETTE_COLORS = 24
OUT_DIR = os.path.join("projects", "hichaukitoden-game", "assets", "character", "town")
RAW_DIR = os.path.join("out", "towngen", "sprites_raw")

STYLE = (
    "A single full-body pixel-art character sprite for a 16-bit role-playing game, front-facing, "
    "standing idle, arms at sides, symmetrical stance. Poor colonial Portuguese fishing village, "
    "damp and cold: wool, oilcloth, linen, leather, clogs. Muted dreary palette - slate blue, "
    "wet grey, umber, faded ochre - with at most one warm accent per figure. "
    "Centered, whole body from the top of the head to the soles of the feet with a small margin. "
    "Plain flat pure magenta background. No shadow, no ground, no text, no border, no frame. "
    "Crisp readable silhouette, limited palette, hard pixel edges, no anti-aliased glow."
)

CAST = {
    "gate_guard": "A tired town guard in a dented iron helm and a heavy grey cloak over a leather jerkin, "
                  "one hand resting on a spear shaft. Middle-aged, stubbled, unimpressed.",
    "weaponsmith": "A broad, soot-stained smith in a scorched leather apron over bare forearms, "
                   "close-cropped dark hair, heavy gloves tucked in a belt.",
    "pub_owner": "A stout tavern keeper in a stained white shirt with rolled sleeves and a long dark "
                 "apron, balding, ruddy-faced, a cloth over one shoulder.",
    "auctioneer": "A thin sharp-featured auctioneer in a threadbare black frock coat too large for him, "
                  "a rolled paper under one arm, spectacles.",
    "registrar": "A severe clerk in a dark high-collared coat with a ledger clutched to the chest, "
                 "grey hair pinned tight, ink-stained fingers.",
    "scholar": "An elderly scholar in a long faded indigo robe with a shawl, white beard, "
               "carrying a bundle of papers.",
    "euler": "A stooped old mathematician in a patched brown coat and a knitted cap, "
             "round spectacles, holding a slate.",
    "yukio": "A lean travelling swordsman in a dark layered coat over a sash, long black hair tied back, "
             "a single sheathed blade at the hip. Reserved, out of place in this village.",
    "laura": "A shrewd woman appraiser in a deep green wool dress with a heavy shawl and a leather "
             "satchel of tools, dark hair coiled, arms ready to fold.",
    "alicia": "A young woman in a plain slate-blue dress with a white collar and a knitted wrap, "
              "brown hair loose, quiet and watchful.",
    "agnes": "An old chapel keeper in a black habit-like dress and a grey headscarf, "
             "a rosary at her waist, gentle and stooped.",
    "fisherman": "A weathered fisherman in a dark blue wool coat and flat cap, grey beard, "
                 "heavy boots, a coil of rope in one hand.",
    "child": "A small village child in an oversized patched coat and bare feet, "
             "unruly hair, holding a wooden toy boat.",
}


def generate_image(prompt):
    body = json.dumps({"model": MODEL, "prompt": prompt, "size": SIZE, "n": 1}).encode()
    request = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=body,
        headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        payload = json.load(response)
    return base64.b64decode(payload["data"][0]["b64_json"])


def to_cell(png_bytes):
    """Key out magenta, crop to the figure, and fit one 24x48 cell."""
    image = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, _ = pixels[x, y]
            if r > 150 and b > 150 and g < 110:
                pixels[x, y] = (0, 0, 0, 0)
    box = image.getbbox()
    if box is None:
        raise ValueError("sprite is entirely transparent after keying")
    figure = image.crop(box)
    scale = min(CELL_W / figure.width, CELL_H / figure.height)
    width = max(1, int(figure.width * scale))
    height = max(1, int(figure.height * scale))
    figure = figure.resize((width, height), Image.LANCZOS)
    cell = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    # Feet on the bottom edge: the compositor anchors sprites by their feet.
    cell.paste(figure, ((CELL_W - width) // 2, CELL_H - height))
    # Hard alpha. A soft edge shimmers against a pre-rendered plate.
    alpha = cell.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    cell.putalpha(alpha)
    return cell.quantize(colors=PALETTE_COLORS, method=Image.FASTOCTREE).convert("RGBA")


def main():
    wanted = sys.argv[1:] or list(CAST)
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    failures = []
    for name in wanted:
        if name not in CAST:
            print("SKIP unknown cast member: " + name)
            continue
        out_path = os.path.join(OUT_DIR, "npc_" + name + ".png")
        if os.path.exists(out_path):
            print("HAVE " + name)
            continue
        started = time.time()
        try:
            raw = generate_image(STYLE + " " + CAST[name])
            cell = to_cell(raw)
        except urllib.error.HTTPError as error:
            print("FAIL %s http %s %s" % (name, error.code,
                                          error.read().decode("utf-8", "replace")[:200]))
            failures.append(name)
            continue
        except Exception as error:  # noqa: BLE001 - report and continue the batch
            print("FAIL %s %s" % (name, error))
            failures.append(name)
            continue
        with open(os.path.join(RAW_DIR, name + ".png"), "wb") as handle:
            handle.write(raw)
        cell.save(out_path)
        print("OK   %s  %.1fs" % (name, time.time() - started))
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("SPRITES OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
