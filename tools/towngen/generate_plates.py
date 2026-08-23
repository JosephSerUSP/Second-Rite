"""Generate pre-rendered background plates for the St. Maria side-view town.

Plates are generated in **groups**: one image carries several screens stacked
as separate letterbox bands, which are then split apart. That is the cheap way
to buy plates - ten screens cost four generations rather than ten, and far
fewer than outpainting a long street one stretch at a time - and it has a
second benefit, since screens painted in one pass share their palette and light
exactly rather than approximately.

Widths are authored, not uniform. The Praca is the town's heart and the widest
place in it; the Quay is where the town runs out and is deliberately short.
Rooms are short because rooms are short.

Usage:
    python tools/towngen/generate_plates.py              # every group
    python tools/towngen/generate_plates.py exteriors_a
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

import ps1_filter

MODEL = "gpt-image-2"
NATIVE_H = 240
# The persistent dock owns y 144..240, so the world the player sees is 144 tall.
WORLD_H = 144
OUT_DIR = os.path.join("projects", "hichaukitoden-game", "assets",
                       "environments", "st_maria_town", "plates")
RAW_DIR = os.path.join("out", "towngen", "raw")

# MDEC quality and framebuffer dither. Chosen by looking: below about 40 the
# plaster goes blotchy and colours shift, above about 60 the ringing that
# makes it read as compressed at all disappears.
PS1_QUALITY = 50
PS1_DITHER = 0.5

# Authored plate widths, in native pixels at 144 tall. A Classic window is 256
# wide, so these run from roughly 3.4 screens of street down to a single room.
WIDTHS = {
    "churchyard": 520,   # raised, reached by steps; holds the sealed Labyrinth door
    "backstreet": 700,    # the poorer side, reached by an alley, drops into Market Row
    "praca_stair": 880,   # the praca re-cut with the churchyard stair at its centre
    "praca": 880,        # the heart of the town: four doors, the fountain, most of its life
    "market": 760,       # commerce, and the largest cast
    "gate": 600,         # a threshold, entered and left rather than lived in
    "quay": 470,         # where the town runs out; short on purpose
    "weaponsmith": 426, "pub": 426, "chapel": 426,
    "house_laura": 426, "house_alicia": 426, "lodging": 426,
}

# Where the authored crop is taken from within its band. Rooms put their door
# in the left wall, so a centred crop throws the way out away.
ANCHOR = {
    "weaponsmith": "left", "pub": "left", "chapel": "left",
    "house_laura": "left", "house_alicia": "left", "lodging": "left",
}

STYLE = (
    "Pre-rendered background art for a 1990s side-scrolling adventure game, painted in the style of "
    "early pre-rendered CG backgrounds. Every scene is a dreary yet cozy colonial Portuguese village, "
    "in flat side elevation with the camera exactly perpendicular to the facades and no vanishing-point "
    "perspective. Whitewashed lime-plaster walls with damp grey staining and patches of exposed stone, "
    "terracotta barrel-tile roofs, blue-and-white azulejo tile panels, wrought-iron balconies, heavy "
    "dark timber doors with iron fittings. Overcast sea-fog light, cool blue-grey shadows, low warm "
    "lantern glow from windows. Wet stone underfoot. "
    "Keep rooflines LOW and spread everything HORIZONTALLY; only a narrow sliver of sky. Doors and "
    "windows sized for an adult standing about one third the height of a band. Architecture runs off "
    "both ends of each band rather than terminating inside it. "
    "No people, no animals, no text, no lettering, no watermark, no user interface."
)

# PLACEHOLDER beats for the new screens. Pending art-direction references:
# the current plates read as flat elevations rather than pre-rendered scenes,
# so these will be rewritten for perspective, depth and composition before
# the group is generated.
PLACEHOLDER_BEATS = {
    "churchyard": "a raised churchyard above the town, reached by a broad flight of worn stone "
                  "steps, dominated by an iron-bound church door under a carved arch that holds "
                  "the sealed mouth of the Labyrinth, with tall iron lanterns and a low wall "
                  "looking down over terracotta rooftops",
    "backstreet": "a narrow back lane behind the square: rough plaster, laundry lines strung "
                  "overhead, back doors and cellar hatches, stacked crates, a shrine niche, and "
                  "stone steps at one end dropping toward the market",
    "praca_stair": "the village praca with a broad stone stair rising from its centre to a "
                   "raised churchyard, the fountain moved aside, townhouses with iron balconies "
                   "closing the square, and a dark alley mouth at one end",
}

BEATS = {
    "gate": "the head of the street, where a sealed iron-bound church door under a carved stone arch "
            "holds the mouth of the Labyrinth. Two tall iron lanterns burn beside it, stone steps drop "
            "to wet cobbles, a bell hangs in the whitewashed gable, and houses crowd in on both sides",
    "praca": "the village praca: an open square of wet granite cobbles around a low octagonal stone "
             "fountain, closed by two-storey townhouses with iron balconies and hanging laundry, a "
             "stone bench, a notice post, terracotta pots of geraniums, and several deep doorways",
    "market": "a market row under long sagging canvas awnings strung between the housefronts, with "
              "empty wooden trestle stalls, stacked crates, hanging scales, baskets, coils of rope and "
              "barrels of salt fish, and a deep arched doorway into a workshop",
    "quay": "the low end of the town where it meets the water: a stone quay wall with mooring rings "
            "and bollards, grey estuary water and sea fog to one side, a pub front with a warm lit "
            "window and a small chapel door under deep stone lintels, nets and lobster pots",
    "weaponsmith": "the interior of a village weaponsmith seen as a flat cutaway: a stone forge with "
                   "banked orange coals, an anvil, racked blades and billhooks on the rear wall, a "
                   "heavy workbench, leather aprons on pegs, and a plain timber door in the left wall",
    "pub": "the interior of a small tavern seen as a flat cutaway: a dark timber bar with bottles and "
           "pewter mugs, a low beamed ceiling, worn tables and stools, a fireplace with a small fire, "
           "azulejo tiles along the lower wall, oil lamps, and a plain timber door in the left wall",
    "chapel": "the interior of a small colonial chapel seen as a flat cutaway: whitewashed walls with "
              "blue azulejo panels of the sea, a modest gilt altar with candles, wooden pews, a stone "
              "font, cold light from a high window, and an arched timber door in the left wall",
    "house_laura": "the interior of a cramped tidy dwelling seen as a flat cutaway: a cooking hearth "
                   "with a hanging pot, a scrubbed table, a dresser of blue-and-white crockery, dried "
                   "herbs on the beams, a shuttered window, and a timber door in the left wall",
    "house_alicia": "the interior of an upstairs room seen as a flat cutaway: a narrow bed with a "
                    "quilt, a writing desk stacked with papers and a candle, a balcony door ajar onto "
                    "grey light, a chest, a faded rug, and a timber door in the left wall",
    "lodging": "the interior of a bare rented room seen as a flat cutaway: two narrow iron beds with "
               "thin grey blankets, a washstand with a chipped basin, a shuttered window, a travelling "
               "trunk on bare boards, and a plain timber door with an iron latch in the left wall",
}

# One image per group. Wider sources for the streets, so a long plate still has
# real resolution behind it once it is scaled down to 144 tall. The API accepts
# arbitrary sizes up to a 3:1 aspect with both dimensions divisible by 16.
# The raised-churchyard layout (chosen 2026-08-23) needs three new screens.
# They are one grouped generation so their palette and light match by
# construction, and they are deliberately NOT in the default batch: the beats
# below are placeholders pending art-direction references.
GROUPS = {
    "layout_b": ("3072x1024", ["churchyard", "backstreet", "praca_stair"]),
    "exteriors_a": ("3072x1024", ["praca", "market"]),
    "exteriors_b": ("3072x1024", ["gate", "quay"]),
    "interiors_a": ("1536x1024", ["weaponsmith", "pub", "chapel"]),
    "interiors_b": ("1536x1024", ["house_laura", "house_alicia", "lodging"]),
}


# Groups excluded from a bare run because their art direction is not settled.
PENDING = {"layout_b"}


def group_prompt(keys):
    parts = [STYLE,
             "This single image contains %d SEPARATE scenes stacked vertically as wide letterbox "
             "bands of equal height, divided by thick pure black horizontal bars, with black bars "
             "at the very top and the very bottom as well. The scenes are unrelated views of the "
             "same town and must not blend into one another." % len(keys)]
    for index, key in enumerate(keys, 1):
        beat = BEATS.get(key) or PLACEHOLDER_BEATS[key]
        parts.append("Band %d from the top shows %s." % (index, beat))
    return " ".join(parts)


def generate_image(prompt, size):
    body = json.dumps({"model": MODEL, "prompt": prompt, "size": size, "n": 1}).encode()
    request = urllib.request.Request(
        "https://api.openai.com/v1/images/generations", data=body,
        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=900) as response:
        payload = json.load(response)
    return base64.b64decode(payload["data"][0]["b64_json"])


def split_bands(image, expected):
    """Split a stacked image into its lit bands, top to bottom.

    Dividers are found by row brightness rather than by assuming equal shares:
    the model spaces them consistently but not exactly, and a fixed split
    slices architecture.
    """
    width, height = image.size
    pixels = image.convert("L").load()
    rows = [sum(pixels[x, y] for x in range(0, width, 16)) / max(1, width // 16)
            for y in range(height)]
    bands, start = [], None
    for y, value in enumerate(rows):
        lit = value > 14
        if lit and start is None:
            start = y
        elif not lit and start is not None:
            if y - start > height * 0.06:
                bands.append((start, y))
            start = None
    if start is not None and height - start > height * 0.06:
        bands.append((start, height))
    if len(bands) != expected:
        raise ValueError("expected %d bands, found %d" % (expected, len(bands)))
    return [image.crop((0, top, width, bottom)) for top, bottom in bands]


def to_plate(band, width, anchor="center"):
    """Crop the band to the authored length, then scale it to the world height.

    The crop happens in source pixels, before the downscale, so a short plate
    keeps the same pixel density as a long one rather than being a squashed
    version of it.
    """
    scale = WORLD_H / float(band.height)
    source_width = min(band.width, int(round(width / scale)))
    if anchor == "left":
        left = 0
    elif anchor == "right":
        left = band.width - source_width
    else:
        left = (band.width - source_width) // 2
    cropped = band.crop((left, 0, left + source_width, band.height))
    world = cropped.resize((width, WORLD_H), Image.LANCZOS)
    # The console's picture pipeline goes on last, and only over the world
    # strip: the dock band below it is a hard black the DCT would smear into
    # the ground line.
    world = ps1_filter.apply(world, quality=PS1_QUALITY, dither=PS1_DITHER)
    plate = Image.new("RGB", (width, NATIVE_H), (0, 0, 0))
    plate.paste(world, (0, 0))
    return plate


def main():
    wanted = sys.argv[1:] or [key for key in GROUPS if key not in PENDING]
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    failures = []
    for group in wanted:
        if group not in GROUPS:
            print("SKIP unknown group: " + group)
            continue
        size, keys = GROUPS[group]
        if all(os.path.exists(os.path.join(OUT_DIR, key + "_bg.png")) for key in keys):
            print("HAVE " + group)
            continue
        started = time.time()
        raw_path = os.path.join(RAW_DIR, group + ".png")
        reused = os.path.exists(raw_path)
        try:
            if reused:
                with open(raw_path, "rb") as handle:
                    raw = handle.read()
            else:
                raw = generate_image(group_prompt(keys), size)
            bands = split_bands(Image.open(io.BytesIO(raw)).convert("RGB"), len(keys))
        except urllib.error.HTTPError as error:
            print("FAIL %s http %s %s"
                  % (group, error.code, error.read().decode("utf-8", "replace")[:200]))
            failures.append(group)
            continue
        except Exception as error:  # noqa: BLE001 - report and continue the batch
            print("FAIL %s %s" % (group, error))
            failures.append(group)
            continue
        if not reused:
            with open(raw_path, "wb") as handle:
                handle.write(raw)
        for key, band in zip(keys, bands):
            plate = to_plate(band, WIDTHS[key], ANCHOR.get(key, "center"))
            plate.save(os.path.join(OUT_DIR, key + "_bg.png"))
            print("     %-13s %dx%d" % (key, plate.width, plate.height))
        print("OK   %-13s %.1fs  (%d plates, %s)"
              % (group, time.time() - started, len(keys),
                 "re-spliced from saved raw" if reused else "1 generation"))
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("PLATES OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
