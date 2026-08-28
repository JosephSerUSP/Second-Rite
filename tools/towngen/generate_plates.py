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

from PIL import Image, ImageFilter

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
PS1_QUALITY = 80
PS1_DITHER = 1.0

# The downscale is the step that decides whether a plate reads as a carefully
# made asset or as mush, and it happens BEFORE any of the console processing.
#
# A pre-rendered background was rendered AT its final resolution -- every pixel
# was placed. We render at 3072 wide and throw away four fifths of it, and no
# amount of dither or compression tuning afterwards can put back detail that
# the resampler averaged away. Two things help: keep the reduction ratio small
# by generating SHORT bands (see BAND_TARGET_H), and restore acutance with an
# unsharp pass, which is exactly what an asset pipeline of the era did.
SHARPEN_RADIUS = 0.6
SHARPEN_AMOUNT = 180

# Authored plate widths, in native pixels at 144 tall. A Classic window is 256
# wide, so these run from roughly four screens of street down to a single room.
# Width is a design statement: a square is not a corridor and a room is not a
# street.
WIDTHS = {
    'praca_stair': 900,
    'backstreet': 850,
    'quay': 1100,
    'market': 1100,
    'churchyard': 980,
    'weaponsmith': 700,
    'pub': 1100,
    'chapel': 1050,
    'house_laura': 700,
    'house_alicia': 700,
    'lodging': 600,
}

# Where the authored crop is taken from within its band.
#
# A plate uses well under half the width of the band it is cut from, so where
# the cut falls decides whether the screen contains the thing it exists for.
# A float is the left edge as a fraction of the available travel, read off the
# full band; rooms put their door in the left wall, so they anchor left.
ANCHOR = {
    'praca_stair': 0.05,
    'backstreet': 0.72,
    'quay': 0.22,
    'market': 1.0,
    'churchyard': 'left',
    'weaponsmith': 'left',
    'pub': 'left',
    'chapel': 'left',
    'house_laura': 'left',
    'house_alicia': 'left',
    'lodging': 'left',
}

STYLE = (
    "Pre-rendered background art for a 1998 PlayStation adventure game. This image is a STAGE for a "
    "side-scrolling character to walk across, not a landscape photograph. "
    "THE WALKING FLOOR MATTERS MORE THAN ANYTHING ELSE IN THE FRAME. The bottom quarter of the band "
    "is one continuous paved surface at a CONSTANT distance from the camera, running unbroken from "
    "the very left edge to the very right edge. It is completely clear: nothing stands on it, "
    "nothing crosses it, no stalls, no crates, no furniture, no steps cutting through it, no "
    "obstacles of any kind. Every building, wall, stall, cart and prop sits BEHIND that strip, "
    "resting on its far edge. It must read unmistakably as level pavement a person could walk from "
    "one end to the other. "
    "CAMERA: fixed, held at the eye level of a standing adult and LEVEL -- not tilted down, not "
    "looking from above. Turned only a few degrees off square, so facades recede gently. Low "
    "horizon. "
    "SCALE: an adult standing on the walking floor is one third of the band's height. Doorways are "
    "only a little taller than that figure. Ground-floor window sills sit at about that figure's "
    "shoulder. Size every step, bench, barrel and railing against that figure -- nothing "
    "monumental, nothing miniature. "
    "EARLY CGI: rendered on a 1998 workstation. Simple polygonal geometry with hard silhouettes and "
    "visible flat facets, obviously repeating tiled textures, hard-edged raytraced shadows, plastic "
    "specular highlights on wet stone, no global illumination, no volumetric light, no lens effects. "
    "Slightly too clean and slightly too contrasty. A render, not a photograph. "
    "BEHIND the walking floor, stage the depth: the subject in the middle distance, then rooftops or "
    "water falling away into flat cold haze. "
    "Dreary yet cozy colonial Portuguese village: whitewashed lime plaster gone grey and damp, "
    "exposed stone where it has fallen away, terracotta barrel tile, blue-and-white azulejo panels, "
    "wrought-iron balconies and lamps, heavy dark timber doors with iron fittings. Desaturated cold "
    "green-grey palette with a little warm lamplight. Overcast marine daylight, blown-out white sky "
    "and windows against deep shadow. "
    "No people, no animals, no text, no lettering, no watermark, no user interface."
)

LAYOUT_BEATS = {
    "churchyard": "a raised churchyard standing above the rooftops of the town, reached by a broad "
                  "flight of worn stone steps climbing from the lower left. The subject is an "
                  "iron-bound church door under a deep carved stone arch, sealed with a heavy bar "
                  "and lit by two tall wrought-iron lanterns. Beyond the low churchyard wall the "
                  "terracotta rooftops and the estuary fall away into cold haze",
    # --- the upper town ---------------------------------------------------
    "praca_stair": "the upper village square. At the FAR LEFT of the band, a flight of worn stone "
                   "steps descends steeply out of the square toward the water far below, with an "
                   "iron handrail. In the MIDDLE, a second flight climbs up to a raised churchyard "
                   "terrace, the church gable just visible over its wall. A low octagonal stone "
                   "fountain stands to one side, and two-storey townhouses with iron balconies and "
                   "a deep arched chapel door close the square. At the FAR RIGHT the square narrows "
                   "and the pavement carries on into a lane",
    "backstreet": "a back lane on the upper level of the town, continuing straight on from a square "
                  "at the FAR LEFT of the band. Rough grey plaster and exposed stone, laundry lines "
                  "strung overhead between the upper storeys, back doors, cellar hatches, a small "
                  "lit shrine niche. At the FAR RIGHT the lane ends at the head of a flight of worn "
                  "stone steps dropping steeply down to a market street below, with the market's "
                  "awnings and rooftops visible under the parapet",
    # --- the lower town, at the water -------------------------------------
    "quay": "the waterside street at the lowest level of the town. At the FAR LEFT the town ends: "
            "a stone quay wall with mooring rings and iron bollards, grey estuary water and heavy "
            "sea fog beyond, nets and lobster pots. In the MIDDLE, a steep flight of worn stone "
            "steps climbs up between two houses toward the upper town, with an iron handrail and a "
            "lamp at its foot. A pub front with a warm lit window stands beside it. At the FAR "
            "RIGHT the street carries on toward a market",
    "market": "a market street on the lower level, continuing from a waterside street at the FAR "
              "LEFT. Long sagging canvas awnings strung overhead between the housefronts, empty "
              "wooden trestle stalls, stacked crates, barrels of salt fish and coils of rope, all "
              "standing well back against the buildings. A deep arched doorway opens into a "
              "blacksmith's workshop. At the FAR RIGHT a flight of worn stone steps climbs steeply "
              "up between the houses toward a lane above",
    # --- interiors -------------------------------------------------------
    # A room is a stage too. The old room beats described what was IN the room
    # and got furniture standing in the walking line; these lead with the
    # floor and push everything against the walls.
    "weaponsmith": "the inside of a village weaponsmith. A clear swept stone floor runs the whole "
                   "width of the frame with nothing on it. Pushed back against the rear wall: a "
                   "stone forge with banked orange coals throwing the only warm light, an anvil on "
                   "its block, a heavy workbench, racked blades and billhooks, leather aprons on "
                   "pegs, a barrel of quenching water. A plain timber door with iron fittings in "
                   "the wall at the FAR LEFT",
    "pub": "the inside of a small tavern on TWO LEVELS. The near half of the room is a clear tiled "
           "floor with worn tables and stools pushed back against the walls. At the FAR RIGHT, a "
           "short flight of three or four worn stone steps rises to a raised platform where a dark "
           "timber bar stands with bottles and pewter behind it. Low beamed ceiling, a fireplace "
           "with a small fire, azulejo tiles along the lower wall, oil lamps. A plain timber door "
           "in the wall at the FAR LEFT",
    "chapel": "the inside of a small colonial chapel. A clear flagstone aisle runs the whole width "
              "of the frame with nothing standing in it. Wooden pews are set back against both "
              "walls, whitewashed walls carry blue azulejo panels of the sea, a modest gilt altar "
              "with candles stands at the FAR RIGHT, a stone font and cold light falling from a "
              "high window. An arched timber door in the wall at the FAR LEFT",
    "house_laura": "the inside of a cramped tidy dwelling. A clear scrubbed floor runs the whole "
                   "width of the frame. Pushed back against the walls: a cooking hearth with a "
                   "hanging pot and a low fire, a scrubbed table, a dresser of blue-and-white "
                   "crockery, dried herbs hanging from the beams, a shuttered window. A timber "
                   "door in the wall at the FAR LEFT",
    "house_alicia": "the inside of an upstairs room. A clear tiled floor runs the whole width of "
                    "the frame. Pushed back against the walls: a narrow bed with a quilt, a "
                    "writing desk stacked with papers and a burning candle, a chest, a chair. At "
                    "the FAR RIGHT a balcony door stands ajar onto flat grey daylight. A timber "
                    "door in the wall at the FAR LEFT",
    "lodging": "the inside of a bare rented room. A clear boarded floor runs the whole width of "
               "the frame. Pushed back against the walls: two narrow iron beds with thin grey "
               "blankets, a washstand with a chipped basin and jug, a travelling trunk, a "
               "shuttered window letting in a hard bar of daylight. A plain timber door with an "
               "iron latch in the wall at the FAR LEFT",
}
BEATS = {
    'weaponsmith': 'the interior of a village weaponsmith, the camera standing inside the room looking into it so the back wall and both side walls are visible: a stone forge with banked orange coals, an anvil, racked blades and billhooks on the rear wall, a heavy workbench, leather aprons on pegs, and a plain timber door in the left wall',
    'pub': 'the interior of a small tavern, the camera standing inside the room looking into it so the back wall and both side walls are visible, the bar on a raised level by the door and the tables down a short flight of steps below it: a dark timber bar with bottles and pewter mugs, a low beamed ceiling, worn tables and stools, a fireplace with a small fire, azulejo tiles along the lower wall, oil lamps, and a plain timber door in the left wall',
    'chapel': 'the interior of a small colonial chapel, the camera standing in the nave looking toward the altar so both side walls and the beamed ceiling are visible: whitewashed walls with blue azulejo panels of the sea, a modest gilt altar with candles, wooden pews, a stone font, cold light from a high window, and an arched timber door in the left wall',
    'house_laura': 'the interior of a cramped tidy dwelling, the camera inside the room looking into it so the back wall, both side walls and the ceiling beams are visible: a cooking hearth with a hanging pot, a scrubbed table, a dresser of blue-and-white crockery, dried herbs on the beams, a shuttered window, and a timber door in the left wall',
    'house_alicia': 'the interior of an upstairs room, the camera inside the room looking into it so the back wall, both side walls and the ceiling beams are visible: a narrow bed with a quilt, a writing desk stacked with papers and a candle, a balcony door ajar onto grey light, a chest, a faded rug, and a timber door in the left wall',
    'lodging': 'the interior of a bare rented room, the camera inside the room looking into it so the back wall, both side walls and the ceiling beams are visible: two narrow iron beds with thin grey blankets, a washstand with a chipped basin, a shuttered window, a travelling trunk on bare boards, and a plain timber door with an iron latch in the left wall',
}

GROUPS = {
    # The churchyard still comes from the earlier grouped render; keeping
    # its entry keeps that raw addressable and the plate reproducible.
    "layout_b": ("3072x1024", ["churchyard", "backstreet", "praca_stair"]),
    # Four bands rather than two: a band is ~230px tall instead of ~490, so the
    # reduction to a 144-tall plate is far smaller and much less of the render
    # is thrown away before it is ever compressed.
    "exteriors_two_level": ("3072x1024",
                            ["praca_stair", "backstreet", "quay", "market"]),
    # 640 tall rather than 1024 for the same three bands: each band is ~190px
    # instead of ~325, so the reduction to a 144-tall plate is 1.3x instead of
    # 2.3x. The bands come out very wide, which suits a side-scrolling room -
    # the plate is 3:1 and we crop a slice out of the middle anyway.
    "interiors_a": ("1536x640", ["weaponsmith", "pub", "chapel"]),
    "interiors_b": ("1536x640", ["house_laura", "house_alicia", "lodging"]),
}

# Groups excluded from a bare run because their art direction is not settled.
PENDING = set()


def group_prompt(keys):
    parts = [STYLE,
             "This single image contains %d SEPARATE scenes stacked vertically as wide letterbox "
             "bands of equal height, divided by thick pure black horizontal bars, with black bars "
             "at the very top and the very bottom as well. The scenes are unrelated views of the "
             "same town and must not blend into one another." % len(keys)]
    for index, key in enumerate(keys, 1):
        beat = LAYOUT_BEATS.get(key) or BEATS[key]
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
    world = world.filter(ImageFilter.UnsharpMask(
        radius=SHARPEN_RADIUS, percent=SHARPEN_AMOUNT, threshold=0))
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
