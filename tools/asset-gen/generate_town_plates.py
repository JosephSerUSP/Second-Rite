"""Generate a town plate from a style sheet and a guide that marks, not depicts.

The STYLE sheet is the three modelled screens stacked -- the only frames in this
town built from .blend sources, so the only ones carrying a grammar worth
inheriting.

## A guide marks, it does not depict

The first attempt drew door-shaped blocks standing on a filled ground band and
sent that as the second image. A model handed a composition can only redraw it:
back came flat grey rectangles on a flat band, in the elevation the diagram was
drawn in rather than the perspective the style sheet shows, and the model's
invention was spent reproducing something Blender could have rendered directly.

The guide now carries marks and nothing else -- a line for the ground, a stick for
a person's height, a caret under each opening. "Place a door here", not "this is
the shape of the door". What is genuinely ours is only WHERE those things sit,
because the player walks to a doorway by position and arrives at a height; what
they look like, how deep the street runs, where the light falls, is what the
model is for.

Nor is the screen photographed. Twelve of the fifteen town screens render a
provisional AI plate, so a capture would hand the model its own earlier output
and ask it to improve on it, laundering whatever was wrong with the placeholder
into its replacement.

**No style words.** A written style and a shown style fight each other. The prompt
never says "pixel art" or "muted"; the sheet carries that.

## Tiling

A plate is the whole street and reaches 4.58:1, while the API refuses anything
past 3:1 (measured: 976x240 is rejected). Wide plates are generated as two
overlapping halves and stitched. Overlap alone does not make halves agree -- two
independent generations of one street are two different streets -- so the right
half is shown the left half's finished edge and told to continue it. That is this
run's own output, not the placeholder being replaced.

    python tools/asset-gen/generate_town_plates.py \
        --style out/town-img2img/style-reference.png \
        --positions out/town-positions --output out/town-plates 16
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import time
from pathlib import Path

import requests
from PIL import Image

ENDPOINT = "https://api.openai.com/v1/images/edits"
MODEL = "gpt-image-2"
QUALITY = "low"
USD_PER_INPUT_TOKEN = 8.0 / 1_000_000
USD_PER_OUTPUT_TOKEN = 30.0 / 1_000_000

MAX_ASPECT = 3.0            # measured against the API, not documented by it
OVERLAP = 0.22              # of plate width, shared by both halves

NL = "\n"

BASE_PROMPT = (
    "The attached image is a page of finished screens from one game." + NL + NL
    + "Draw one new screen for the same town, as though it had always belonged "
      "on that page. The place is: {description}" + NL + NL
    + "It is a single continuous view along the street, seen from the side the "
      "way the screens on the page are, and the player walks left and right "
      "across the whole width of it." + NL + NL
    + "The ground the player walks on runs unbroken from edge to edge at about "
      "{ground:.0%} of the way down the picture, and a person standing on that "
      "ground is about {person:.0%} of the picture's height." + NL + NL
    + "The second image is a guide, not a picture. It is blank except for "
      "marks:" + NL
    + "- the white line is how high the ground runs" + NL
    + "- the blue stick is how tall a person is standing on it" + NL
    + "- each red arrow points at a spot where somebody can walk in" + NL
    + "- the yellow line is the horizon" + NL
    + "- the green lines lie flat on the ground, going away from you" + NL
    + "- the amber lines stand upright, facing you" + NL + NL
    + "The camera looks slightly down, so the ground is seen from a little above "
      "and recedes upward toward the horizon. The green lines are parallel and "
      "stay parallel -- they do not meet at a point -- because the view slides "
      "left and right across this picture and must look right at every position. "
      "Build the floor along the green lines and stand the buildings on the amber "
      "ones." + NL + NL
    + "Put a way in -- a door, a gate, an arch, the foot of a stair, whatever "
      "belongs there -- at each red arrow. What it looks like is yours; only "
      "where it sits is fixed." + NL + NL
    + "The guide lines are scaffolding: follow where they go, and draw none of "
      "them. Nothing in the finished picture is a coloured line, and there is no "
      "lettering anywhere in it." + NL + NL
    + "Draw no people."
)

CONTINUE_PROMPT = (
    NL + NL + "The third image is the finished left part of this same street, "
    "and what you draw is the part immediately to its right. Continue it: the "
    "same buildings carry on, the ground meets exactly, and the left edge of "
    "what you draw joins the right edge of that image without a break."
)


def describe(frame):
    """What the screen IS.

    The map's own intro line: authored prose about the place rather than a
    description of a picture, so it says what is being drawn without saying how.
    """
    return (frame.get("intro") or frame.get("title", "")).strip()


def legal_size(width, height):
    """Nearest API-legal request size: both edges /16, at most 3:1, at most 3840."""
    scale = min(3.0, 3840 / max(width, height))
    w = max(16, int(width * scale) // 16 * 16)
    h = max(16, int(height * scale) // 16 * 16)
    while w / h > MAX_ASPECT:
        w -= 16
    return w, h


def tiles_for(width, height):
    """The plate's halves, as (start, end) pixel ranges, or one whole tile."""
    if width / height <= MAX_ASPECT:
        return [(0, width)]
    overlap = int(width * OVERLAP)
    half = (width + overlap) // 2
    return [(0, half), (width - half, width)]


def call(model, quality, prompt, size, images):
    response = requests.post(
        ENDPOINT,
        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
        data={"model": model, "prompt": prompt, "size": "%dx%d" % size,
              "quality": quality, "n": "1"},
        files=[("image[]", (name, blob, "image/png")) for name, blob in images],
        timeout=900,
    )
    if response.status_code != 200:
        raise RuntimeError("images/edits %s %s"
                           % (response.status_code, response.text[:300]))
    payload = response.json()
    usage = payload.get("usage") or {}
    cost = (usage.get("input_tokens", 0) * USD_PER_INPUT_TOKEN
            + usage.get("output_tokens", 0) * USD_PER_OUTPUT_TOKEN)
    return base64.b64decode(payload["data"][0]["b64_json"]), cost


def as_png(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def stitch(left, right, overlap):
    """Cross-fade the halves through their shared strip.

    A hard cut shows wherever the halves disagree by even a little, and they
    always disagree a little. The fade spends the whole overlap moving from one to
    the other, so a small disagreement becomes a gradient instead of an edge.
    """
    width = left.width + right.width - overlap
    out = Image.new("RGB", (width, left.height))
    out.paste(left, (0, 0))
    out.paste(right.crop((overlap, 0, right.width, right.height)), (left.width, 0))
    if overlap > 0:
        band = Image.new("L", (overlap, left.height))
        band.putdata([int(255 * (x / max(1, overlap - 1)))
                      for _ in range(left.height) for x in range(overlap)])
        blended = Image.composite(
            right.crop((0, 0, overlap, right.height)),
            left.crop((left.width - overlap, 0, left.width, left.height)), band)
        out.paste(blended, (left.width - overlap, 0))
    return out


def plate_name(map_id, title):
    stem = title.replace("St. Maria - ", "").replace("/", "-").replace(chr(39), "")
    return "%02d-%s.png" % (map_id, stem)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("maps", nargs="*", type=int)
    parser.add_argument("--style", required=True, type=Path)
    parser.add_argument("--positions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--quality", default=QUALITY)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest = json.loads((args.positions / "inputs.json").read_text(encoding="utf-8"))
    frames = {f["mapId"]: f for f in manifest["frames"]}
    wanted = args.maps or sorted(frames)
    missing = [m for m in wanted if m not in frames]
    if missing:
        raise SystemExit("no position record for map(s) %s" % missing)

    style = args.style.read_bytes()
    args.output.mkdir(parents=True, exist_ok=True)
    print("%s quality=%s  %d screen(s)" % (args.model, args.quality, len(wanted)))

    spent = 0.0
    for map_id in wanted:
        frame = frames[map_id]
        plate_w, plate_h = frame["plateSize"]
        guide = Image.open(args.positions / frame["file"]).convert("RGB")
        ranges = tiles_for(plate_w, plate_h)

        if args.dry_run:
            print("  map %-3d %-38s %dx%d -> %d tile(s)"
                  % (map_id, frame["title"], plate_w, plate_h, len(ranges)))
            print("-" * 70)
            print(BASE_PROMPT.format(
                description=describe(frame),
                ground=frame["groundFraction"],
                person=frame["personHeightFraction"]))
            print("-" * 70)
            continue

        started = time.time()
        pieces = []
        cost = 0.0
        for index, (x0, x1) in enumerate(ranges):
            size = legal_size(x1 - x0, plate_h)
            scale = guide.width / plate_w
            crop = guide.crop((int(x0 * scale), 0, int(x1 * scale), guide.height))
            images = [("style.png", style), ("guide.png", as_png(crop))]
            prompt = BASE_PROMPT.format(
                description=describe(frame),
                ground=frame["groundFraction"],
                person=frame["personHeightFraction"])
            if index > 0:
                overlap = ranges[index - 1][1] - x0
                previous = pieces[-1]
                edge = previous.crop((previous.width - overlap, 0,
                                      previous.width, previous.height))
                images.append(("continue.png", as_png(edge)))
                prompt = prompt + CONTINUE_PROMPT
            raw, tile_cost = call(args.model, args.quality, prompt, size, images)
            cost += tile_cost
            tile = Image.open(io.BytesIO(raw)).convert("RGB").resize(
                (x1 - x0, plate_h), Image.LANCZOS)
            pieces.append(tile)

        plate = pieces[0]
        for index in range(1, len(pieces)):
            overlap = ranges[index - 1][1] - ranges[index][0]
            plate = stitch(plate, pieces[index], overlap)
        if plate.size != (plate_w, plate_h):
            raise SystemExit("stitched to %s, expected %s"
                             % (plate.size, (plate_w, plate_h)))
        name = plate_name(map_id, frame["title"])
        plate.save(args.output / name)
        spent += cost
        print("  OK  map %-3d %5.0fs  $%.4f  %d tile(s)  %dx%d  %s"
              % (map_id, time.time() - started, cost, len(ranges),
                 plate.width, plate.height, name))
    if not args.dry_run:
        print("spent $%.4f" % spent)


if __name__ == "__main__":
    main()
