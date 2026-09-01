"""Check a candidate plate against the map it has to serve.

The plates now in the tree are wrong on collision and scale, and nothing caught
it, because the only evidence anyone had was the picture. Two things are already
known about judging this kind of art:

  * a frame-fraction metric cannot see that a cart dwarfs a person, so every
    judgement is made against the 24x48 player and nothing else;
  * img2img scores well on material and palette while quietly deleting the near
    band, so composition has to be looked at rather than scored.

So this tool does two separate jobs and does not confuse them.

**Assertions** are mechanical and can fail the tool: the plate's width has to
match what the map was generated against, and every authored opening has to
land inside the picture with room for a 24x48 doorway. These are the things a
machine can be certain about.

**The overlay** is for the eye. It draws the authored openings, the ground line
and the player, to scale, on top of the candidate, and writes a contact sheet.
Whether there is actually a door in the art where the map puts a door is not
mechanically decidable, and pretending otherwise would be the frame-fraction
mistake again.

    python tools/towngen/check_plate.py                      # every exterior
    python tools/towngen/check_plate.py --screen market      # one
    python tools/towngen/check_plate.py --candidates DIR     # art under review

`--candidates DIR` looks for `<screen>.png` there and falls back to the plate
the map actually uses, so the same command works before and after a render.
"""

import argparse
import io
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from make_blockout import spec, EXTERIORS, PLAYER_W, PLAYER_H  # noqa: E402
from build_town import ENV_ROOT  # noqa: E402

PLATES = os.path.join(ENV_ROOT, "plates")


def candidate_path(key, s, candidates):
    if candidates:
        p = os.path.join(candidates, "%s.png" % key)
        if os.path.exists(p):
            return p, True
    return os.path.join(ROOT, PLATES, s["plate"]), False


def assertions(s, im):
    """What a machine can be certain of. Anything here failing is a real fault."""
    out = []
    w, h = im.size
    if w != s["plateWidth"]:
        out.append("width %d, but the map was generated against %d - every lane "
                   "bound, door y and NPC y is derived from that number"
                   % (w, s["plateWidth"]))
    if h < s["groundY"]:
        out.append("height %d is above the ground line at y=%d"
                   % (h, s["groundY"]))
    for o in s["openings"]:
        x = o["pixelX"]
        if not (0 <= x <= w):
            out.append("%s falls outside the picture at x=%.1f" % (o["anchor"], x))
        elif o["kind"] == "door" and not (PLAYER_W / 2 <= x <= w - PLAYER_W / 2):
            out.append("%s at x=%.1f has no room for a %dpx doorway"
                       % (o["anchor"], x, PLAYER_W))
    return out


def overlay(s, im):
    im = im.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    g = s["groundY"]
    d.line([(0, g), (im.size[0], g)], fill=(255, 0, 96), width=1)
    for o in s["openings"]:
        x = int(round(o["pixelX"]))
        colour = (86, 156, 214) if o["kind"] == "street" else (232, 126, 52)
        d.rectangle([x - PLAYER_W // 2, g - PLAYER_H,
                     x + PLAYER_W // 2, g], outline=colour, width=2)
        d.text((max(2, x - 24), g - PLAYER_H - 11), o["label"][:16], fill=colour)
    # The player, at three points along the lane. Scale is the whole question:
    # if the architecture does not read as architecture beside these, the plate
    # is wrong however good the material looks.
    for frac in (0.2, 0.5, 0.8):
        x = int(im.size[0] * frac)
        d.rectangle([x - PLAYER_W // 2, g - PLAYER_H,
                     x + PLAYER_W // 2, g], fill=(20, 20, 24), outline=(255, 255, 255))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", action="append")
    ap.add_argument("--candidates")
    ap.add_argument("--out", default=os.path.join("out", "towngen", "plate-check"))
    args = ap.parse_args()
    keys = args.screen or list(EXTERIORS)
    os.makedirs(args.out, exist_ok=True)

    failed, rows = [], []
    for key in keys:
        s = spec(key)
        path, is_candidate = candidate_path(key, s, args.candidates)
        if not os.path.exists(path):
            failed.append("%s: no plate at %s" % (key, path))
            continue
        with Image.open(path) as im:
            problems = assertions(s, im)
            overlay(s, im).save(os.path.join(args.out, "%s.png" % key))
        rows.append((key, s, path, is_candidate, problems))
        if problems:
            failed.extend("%s: %s" % (key, p) for p in problems)

    html = ["<title>Plate check</title><style>",
            "body{font:14px system-ui;background:#111;color:#ddd;margin:20px}",
            "img{width:100%;image-rendering:pixelated;border:1px solid #333}",
            "h2{font-size:15px;margin:26px 0 6px}.bad{color:#ff8a80}",
            ".m{font:11px ui-monospace,monospace;color:#9ab}</style>"]
    for key, s, path, is_candidate, problems in rows:
        html.append("<h2>%s &mdash; map %d %s</h2>" % (
            key, s["mapId"], "(candidate)" if is_candidate else "(in tree)"))
        html.append("<p class='m'>%s &middot; %dpx wide &middot; ground y=%d "
                    "&middot; player 24x48</p>" % (path, s["plateWidth"], s["groundY"]))
        for p in problems:
            html.append("<p class='bad'>%s</p>" % p)
        html.append("<img src='%s.png'>" % key)
    with io.open(os.path.join(args.out, "index.html"), "w",
                 encoding="utf-8", newline="\n") as h:
        h.write("\n".join(html))

    print("checked %d plate(s); overlays in %s" % (len(rows), args.out))
    if failed:
        print("")
        for f in failed:
            print("  FAIL  %s" % f)
        print("")
        print("Scale and composition are NOT asserted here - open index.html and")
        print("look. A plate can pass every line above and still be unwalkable.")
        return 1
    print("assertions passed. Scale and composition still need the eye:")
    print("  %s" % os.path.join(args.out, "index.html"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
