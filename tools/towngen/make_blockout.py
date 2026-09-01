"""Emit the interaction spec for each St. Maria exterior: a diagram and a JSON.

WHAT THIS IS FOR, AND WHAT IT IS NOT

`SCREENS` in build_town.py knows where every door, street continuation and NPC
stands, to the pixel, and knows that the player is 24x48 on a 426x144 visible
world. That is a **floor plan of interaction**. It is the ground truth a plate
has to agree with, and until now it existed only as Python.

This tool writes it out twice:

  * `<screen>.png`  - a diagram, for a human and for an instruction-following
                      image model ("keep the openings where they are").
  * `<screen>.json` - the same facts as numbers, for tools/towngen/check_plate.py.

**It is NOT a ControlNet conditioning image.** Flat category colours and text
labels encode *semantics* - "this rectangle means a door" - and canny or lineart
would extract the label text and the box outlines, handing the model a picture
of labelled boxes. Conditioning needs *form*: rooflines, wall planes, a depth
ramp. `SCREENS` does not contain form, so form cannot be derived here. A
conditioning-grade image is a third artifact and somebody has to author its
silhouette.

    python tools/towngen/make_blockout.py [--out DIR]
"""

import argparse
import io
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_town import (  # noqa: E402
    SCREENS, lane_of, lane_y_for, screen_scale, WORLD_H, NATIVE_W)

# The player's projected box, from build_town's playerProjection. Every scale
# judgement about a plate is made against this and nothing else: a frame-
# fraction metric cannot see that a cart dwarfs a person.
PLAYER_W, PLAYER_H = 24, 48

EXTERIORS = ("churchyard", "praca", "cortico", "market", "quay", "port")

INK = (30, 30, 34)
GROUND = (176, 176, 182)
SKY = (238, 238, 242)
DOOR = (232, 126, 52)
STREET = (86, 156, 214)
NPC = (60, 160, 110)
PLAYER = (30, 30, 34)


def spec(key):
    """Everything a plate has to agree with, as numbers."""
    screen = SCREENS[key]
    scale = screen_scale(screen)
    lane = lane_of(screen["plate"], scale)
    ground_y = screen["screen_y"]
    bounds = {0.0, lane["maxY"]}
    openings = []
    for anchor, label, target, arrival, pixel_x, _src in screen["doors"]:
        y = lane_y_for(screen["plate"], pixel_x, scale)
        openings.append({
            "anchor": anchor, "label": label, "target": target,
            "pixelX": round(float(pixel_x), 3), "laneY": y,
            # A street continuation sits ON a lane bound and the lane keeps
            # going through it; a door does not. The runtime reads exactly this
            # to decide whether to announce an interaction.
            "kind": "street" if y in bounds else "door",
        })
    return {
        "screen": key,
        "mapId": screen["id"],
        "title": screen["title"],
        "plate": screen["plate"],
        "plateWidth": lane["width"],
        "visibleHeight": WORLD_H,
        "cameraWindow": NATIVE_W,
        "groundY": ground_y,
        "lane": {"minY": lane["minY"], "maxY": lane["maxY"]},
        "pixelsPerLaneUnit": scale,
        "player": {"width": PLAYER_W, "height": PLAYER_H,
                   "feetY": ground_y, "headY": ground_y - PLAYER_H},
        "openings": openings,
        "npcs": [{"anchor": a, "pixelX": px} for a, _s, _sp, px in screen["npcs"]],
    }


def diagram(key, s):
    w, h = s["plateWidth"], s["visibleHeight"]
    im = Image.new("RGB", (w, h), SKY)
    d = ImageDraw.Draw(im)
    g = s["groundY"]
    d.rectangle([0, g, w, h], fill=GROUND)
    d.line([(0, g), (w, g)], fill=INK, width=1)

    # One camera window, so the reader can see how much of this is ever on
    # screen at once. The Praca is several windows of walking.
    for x in range(0, w, s["cameraWindow"]):
        d.line([(x, 0), (x, h)], fill=(214, 214, 220), width=1)

    for o in s["openings"]:
        x = int(round(o["pixelX"]))
        if o["kind"] == "street":
            d.rectangle([x - 3, g - 96, x + 3, g], fill=STREET)
            d.text((min(max(2, x - 20), w - 60), 4), "STREET", fill=STREET)
        else:
            d.rectangle([x - PLAYER_W // 2, g - PLAYER_H,
                         x + PLAYER_W // 2, g], fill=DOOR, outline=INK)
        d.text((min(max(2, x - 24), w - 90), g - PLAYER_H - 12),
               o["label"][:16], fill=INK)

    for n in s["npcs"]:
        x = int(round(n["pixelX"]))
        d.rectangle([x - PLAYER_W // 2, g - PLAYER_H,
                     x + PLAYER_W // 2, g], outline=NPC, width=2)

    # The player, to scale, at the lane centre. Nothing on this diagram is
    # decorative: this box is the only reference for how big anything is.
    cx = w // 2
    d.rectangle([cx - PLAYER_W // 2, g - PLAYER_H,
                 cx + PLAYER_W // 2, g], fill=PLAYER)
    d.text((cx - 34, g - PLAYER_H - 24), "PLAYER 24x48", fill=INK)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("out", "towngen", "blockouts"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    for key in EXTERIORS:
        s = spec(key)
        diagram(key, s).save(os.path.join(args.out, "%s.png" % key))
        with io.open(os.path.join(args.out, "%s.json" % key), "w",
                     encoding="utf-8", newline="\n") as handle:
            json.dump(s, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        doors = sum(1 for o in s["openings"] if o["kind"] == "door")
        streets = len(s["openings"]) - doors
        print("%-11s map %-3d %5dpx  %d doors, %d street exits, %d npcs"
              % (key, s["mapId"], s["plateWidth"], doors, streets,
                 len(s["npcs"])))
    print("wrote %d specs to %s" % (len(EXTERIORS), args.out))


if __name__ == "__main__":
    main()
