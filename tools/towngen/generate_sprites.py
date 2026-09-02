"""Generate 24x48 townsperson sprites for the St. Maria side-view town.

The existing `assets/sprites/NPC*.png` sheets are 48x64 nude placeholder
figures - functional for a grid dungeon, wrong for a populated town. The
contract is a single 24x48 cell, hard alpha, limited palette.

Take the STYLE and PROPORTION reference from the owner's hand-authored
sprites in `assets/character/`: npc_alicia, npc_celina, npc_goustav,
npc_laura, player. Those are drawn by hand and have `.gal` sources beside
them; everything this script writes into `character/town/` is generated and
is placeholder until an authored sprite replaces it.

Do NOT use `npc_female_redhead_dress.png` as the reference. It is an early
style study and its proportions are wrong, which this docstring previously
cited as establishing the contract.

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
QUALITY = "low"

# One dense sheet, not several sparse ones. The reference image is charged on
# every request and it is three quarters of the bill, so a second sheet pays for
# the model to re-read the cast rather than to draw anybody. The whole town fits
# on one page, and a single page also holds one style across the entire cast
# instead of re-deriving it per request.
#
# The API accepts free-form sizes up to a 3840px edge (measured, not documented
# here: 4096 is refused, 2160x3840 is accepted).
# Cell aspect follows the FIGURE aspect. A 5x3 page of 432x1280 cells spent most
# of its area on empty air above people who are 2.8 times as tall as they are
# wide. Shorter beats wider here: it removes the dead space AND bills less area,
# so it is the only one of the two that improves cost and quality together.
# The page is sized so that the model's OWN pixel grid lands on our cell.
# Measured with pixel-art-fixer: on a 2000x2880 page the model drew at a step of
# ~7.9px, giving figures 60-64 native pixels tall -- which then had to become 47.
# A 64:47 reduction is non-integer, so it smooths no matter which resampler runs,
# and no downscaler can fix that. Sizing the page so 47 rows x ~8px = ~376px of
# figure makes the reduction integral instead.
SIZE = "1408x1440"          # 5x3 page of 281x480 cells (edges must divide by 16)
REFERENCE_SCALE = 8         # authored sprites upscaled 8x: 47 rows -> 376px
# The reference need only be READABLE, and it is billed by area, so it is sent at
# half the output edge -- same layout, same aspect, a quarter of the input tokens.
REFERENCE_SIZE = (1408, 1440)

# gpt-image-2 bills tokens, not images: $8/1M in, $30/1M out. Measured on this
# exact request shape, one sheet is 1,751 in + 158 out = $0.0188. Three quarters
# of that is the reference image being read, which is why batching pays -- the
# reference is charged once per sheet whether it carries one new figure or four.
USD_PER_INPUT_TOKEN = 8.0 / 1_000_000
USD_PER_OUTPUT_TOKEN = 30.0 / 1_000_000
CELL_W, CELL_H = 24, 48
PALETTE_COLORS = 24
# Magenta is where red and blue both outrun green. Keyed above the first
# threshold, despilled between the two.
KEY_THRESHOLD = 40
SILHOUETTE_COLOR = (90, 90, 96, 255)
DESPILL_THRESHOLD = 12
OUT_DIR = os.path.join("projects", "hichaukitoden-game", "assets", "character", "town")
RAW_DIR = os.path.join("out", "towngen", "sprites_raw")

STYLE = (
    "A single full-body pixel-art character sprite for a 16-bit role-playing game, front-facing, "
    "standing idle, arms at sides, symmetrical stance. Poor colonial Portuguese fishing village, "
    "damp and cold: wool, oilcloth, linen, leather, clogs. Muted dreary palette - slate blue, "
    "wet grey, umber, faded ochre - with at most one warm accent per figure. "
    "Arms hanging straight down against the body, hands empty, nothing held or carried, nothing extended away from the silhouette. Narrow upright build. "
    "Centered, whole body from the top of the head to the soles of the feet with a small margin. "
    "Plain flat pure magenta background. No shadow, no ground, no text, no border, no frame. "
    "Crisp readable silhouette, limited palette, hard pixel edges, no anti-aliased glow."
)

# Only roles with no hand-authored sprite. alicia, laura (the smithy), registrar
# (Celina) and auctioneer (Goustav) are drawn by the owner and live in
# assets/character/;
# leaving them here would regenerate a placeholder over the authored one the
# moment their town/ file is absent, silently undoing the repointing.
#
# No held or carried objects. A rope, a slate, a bundle of papers is a few
# pixels at 24x48, but it extends the silhouette, and the silhouette is what
# the cell is measured by: held props were most of the drift that made the
# generated cast 19-24px wide against the authored 16-17.
CAST = {
    "gate_guard": "A tired town guard in a dented iron helm and a heavy grey cloak over a leather jerkin. "
                  "Middle-aged, stubbled, unimpressed.",
    "pub_owner": "A stout tavern keeper in a stained white shirt with rolled sleeves and a long dark "
                 "apron, balding, ruddy-faced.",
    "scholar": "An elderly scholar in a long faded indigo robe with a shawl, white beard.",
    "euler": "A stooped old mathematician in a patched brown coat and a knitted cap, "
             "round spectacles.",
    "yukio": "A lean travelling swordsman in a dark layered coat over a sash, long black hair tied back, "
             "a single sheathed blade at the hip. Reserved, out of place in this village.",
    "agnes": "An old chapel keeper in a black habit-like dress and a grey headscarf, "
             "a rosary at her waist, gentle and stooped.",
    "fisherman": "A weathered fisherman in a dark blue wool coat and flat cap, grey beard, "
                 "heavy boots.",
    "child": "A small village child in an oversized patched coat and bare feet, "
             "unruly hair.",
}


AUTHORED_DIR = os.path.join("projects", "hichaukitoden-game", "assets", "character")

# The proportion contract, measured from the owner's hand-authored sprites:
# 16-17px of body in a 24px cell over 47 of 48 rows, so about 1:2.8. The
# generated cast drifted to 19-24px wide at 1:1.7-1:2.5 -- npc_child came out as
# wide as an adult and npc_pub_owner reached only 41 rows. Fitting to the cell
# cannot correct that, because it scales whatever aspect the model returned.
# Two things fix it: anchor generation on an authored figure, and refuse a cell
# that lands outside the band.
PROPORTION_MIN, PROPORTION_MAX = 2.55, 3.15
AUTHORED_ROWS = 47                # every authored sprite is 47 drawn rows of 48
HEIGHT_MIN, HEIGHT_MAX = 24, CELL_H   # a child may be short; nobody may overflow
STYLE_ANCHOR = "npc_goustav"      # a plain standing adult, arms down

# Do NOT anchor on npc_female_redhead_dress.png. It is an early style study and
# its proportions are wrong; anything generated from it inherits the error.


def style_reference(name=STYLE_ANCHOR):
    """One authored sprite, upscaled onto the magenta field the keyer expects."""
    sprite = Image.open(os.path.join(AUTHORED_DIR, name + ".png")).convert("RGBA")
    field = Image.new("RGBA", (1024, 1024), (255, 0, 255, 255))
    scale = min(1024 / sprite.width, 1024 / sprite.height)
    figure = sprite.resize((int(sprite.width * scale), int(sprite.height * scale)),
                           Image.NEAREST)
    field.alpha_composite(figure, ((1024 - figure.width) // 2,
                                   (1024 - figure.height) // 2))
    buffer = io.BytesIO()
    field.save(buffer, format="PNG")
    return buffer.getvalue()


COLS, ROWS = 5, 3
SLOTS = COLS * ROWS

# Two of the six slots are people who already exist, and the model is told to
# leave them alone. They are the sheet's own negative control: if a control comes
# back off-style, the page was not drawn in the reference style and the new
# figures on it cannot be trusted either. Without them a batch can only be judged
# by opinion. They are not bulletproof -- a model can paste the originals in and
# invent freely around them, which is measurable as a control that matches its
# source far more closely than the new figures match anything.
CONTROLS = ["npc_goustav", "npc_alicia", "npc_celina", "npc_laura", "player"]

# Every authored figure, so the model can see what they SHARE. One sprite shows a
# person; the whole cast shows a style, and separating the two is the point.
CAST_REFERENCE = ["npc_goustav", "npc_alicia", "npc_celina", "npc_laura", "player"]


def silhouette(sprite, scale):
    """A featureless stand-in: the authored outline, filled flat."""
    figure = sprite.resize((sprite.width * scale, sprite.height * scale),
                           Image.NEAREST)
    solid = Image.new("RGBA", figure.size, SILHOUETTE_COLOR)
    solid.putalpha(figure.getchannel("A"))
    return solid


def sheet_reference(names, placeholders=0):
    """The authored cast on the same grid the model must return.

    Three things this gets right that a naive contact sheet does not.

    **One scale for everybody.** Fitting each sprite to its own cell throws away
    the only thing that carries relative height, and relative height is what a
    child is. Every figure is drawn at the SAME pixels-per-sprite-pixel, so the
    page is a ruler as well as a style sample.

    **One baseline.** Feet sit on a common line in every row, so "shorter" reads
    as shorter rather than as floating.

    **A marked slot for every new person.** Asking for a grid in words gets a
    rough grid; showing the model where each figure stands gets placement it can
    match. The empty slots carry a flat silhouette at exactly the size and
    baseline the new figure should occupy, so the layout AND the scale are shown
    rather than described.
    """
    field = Image.new("RGBA", REFERENCE_SIZE, (255, 0, 255, 255))
    cell_w, cell_h = field.width // COLS, field.height // ROWS
    scale = REFERENCE_SCALE
    if scale * CELL_W > cell_w or scale * CELL_H > cell_h:
        raise ValueError("REFERENCE_SCALE %d does not fit a %dx%d cell"
                         % (scale, cell_w, cell_h))
    baseline = int(cell_h * 0.92)
    anchor = Image.open(os.path.join(AUTHORED_DIR, STYLE_ANCHOR + ".png")).convert("RGBA")
    marker = silhouette(anchor, scale)
    for index in range(min(SLOTS, len(names) + placeholders)):
        if index < len(names):
            sprite = Image.open(
                os.path.join(AUTHORED_DIR, names[index] + ".png")).convert("RGBA")
            figure = sprite.resize((sprite.width * scale, sprite.height * scale),
                                   Image.NEAREST)
        else:
            figure = marker
        column, row = index % COLS, index // COLS
        field.alpha_composite(figure,
                              (column * cell_w + (cell_w - figure.width) // 2,
                               row * cell_h + baseline - figure.height))
    buffer = io.BytesIO()
    field.save(buffer, format="PNG")
    return buffer.getvalue()


def sheet_prompt(control_names, new_names):
    """Continuation, not creation, and not one adjective of style.

    A written style and a shown style fight each other: every word describing the
    look pulls toward whatever the model associates with that word, competing with
    the reference that is already carrying the style. So this says nothing about
    pixels, palette or proportion -- only WHO the new people are, leaving HOW to
    the page.

    It DOES talk about height, because height is not style, it is fact: the
    generated child came back the same size as the adults, which the guard could
    not see because each figure was fitted to its own cell. The page is the ruler,
    so the prompt points at it.
    """
    kept = ", ".join(n.replace("npc_", "") for n in control_names)
    people = "\n".join("- " + CAST[n] for n in new_names)
    return (
        "This is a page from a character sheet. Redraw the whole page as a "
        "%dx%d sheet of %d villagers, read left to right then top to bottom.\n\n"
        "The first %d are %s, the same people already on the page, unchanged, "
        "at the same size they already are.\n\n"
        "The grey blank figures are placeholders. Replace each one, where it "
        "stands and at the size it is drawn, with a different person from the "
        "same village, reimagined onto the same page:\n%s\n\n"
        "Every figure stands on the same ground line in its row and is drawn at "
        "the same scale as the people already on the page, so that a figure who "
        "is shorter is drawn shorter and a figure who is taller is drawn taller. "
        "Each stands alone facing forward, arms down, hands empty, on the same "
        "plain flat magenta background, with no gridlines and no text."
        % (COLS, ROWS, len(control_names) + len(new_names),
           len(control_names), kept, people)
    )


def generate_sheet(prompt, reference_png):
    """One page. Returns (png bytes, usd)."""
    import requests
    response = requests.post(
        "https://api.openai.com/v1/images/edits",
        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
        data={"model": MODEL, "prompt": prompt, "size": SIZE,
              "quality": QUALITY, "n": "1"},
        files={"image": ("sheet.png", reference_png, "image/png")},
        timeout=900,
    )
    if response.status_code != 200:
        raise RuntimeError("images/edits %s %s" % (response.status_code,
                                                   response.text[:300]))
    payload = response.json()
    usage = payload.get("usage") or {}
    usd = (usage.get("input_tokens", 0) * USD_PER_INPUT_TOKEN
           + usage.get("output_tokens", 0) * USD_PER_OUTPUT_TOKEN)
    return base64.b64decode(payload["data"][0]["b64_json"]), usd


def key_magenta(image):
    """Drop the magenta field, and drop what it bled onto.

    A plain "is it bright magenta" test keeps every antialiased pixel around the
    figure, which is what was peeking through: the model does not return a hard
    flat key, it returns a soft edge that is 80% background. So the test is
    chromatic rather than absolute -- magenta is the colours where red and blue
    both sit above green -- and it runs on a spill margin, so half-magenta edge
    pixels go too.

    Survivors are then despilled. A pixel that keeps a magenta tint after keying
    is a pixel whose colour came partly from the background, and at 24x48 one
    such pixel on a silhouette edge is visible.
    """
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            magentaness = min(r, b) - g
            if magentaness > KEY_THRESHOLD:
                pixels[x, y] = (0, 0, 0, 0)
            elif magentaness > DESPILL_THRESHOLD:
                ceiling = g + DESPILL_THRESHOLD
                pixels[x, y] = (min(r, ceiling), g, min(b, ceiling), a)
    return image


def figure_bands(mask, count, axis):
    """Runs of occupied lines along one axis, largest `count` kept, in order.

    The page comes back on ITS grid, not on ours. Slicing into equal rectangles
    assumed a placement the model never promised, and a figure standing a little
    left of centre got cut in half -- which is what produced the 85-89 row
    "figures" (two half-people measured as one tall one). Finding the actual gaps
    tolerates the drift.
    """
    occupied = mask.any(axis=axis)
    runs, start = [], None
    for index, filled in enumerate(occupied):
        if filled and start is None:
            start = index
        elif not filled and start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(occupied)))
    runs.sort(key=lambda run: run[1] - run[0], reverse=True)
    return sorted(runs[:count])


def find_figures(png_bytes):
    """Locate every figure on the page by where it actually is."""
    import numpy as np
    image = key_magenta(Image.open(io.BytesIO(png_bytes)).convert("RGBA"))
    mask = np.asarray(image)[:, :, 3] > 128
    cells = []
    for top, bottom in figure_bands(mask, ROWS, axis=1):
        band = mask[top:bottom]
        for left, right in figure_bands(band, COLS, axis=0):
            box = (left, top, right, bottom)
            crop = image.crop(box)
            inner = crop.getbbox()
            if inner is None:
                continue
            cells.append(crop.crop(inner))
    return cells


def slice_sheet(png_bytes):
    """Backwards-compatible name; placement is found, not assumed."""
    return find_figures(png_bytes)


def sheet_scale(control_cells):
    """Pixels-per-sprite-pixel, read off the figures whose real height we know.

    THIS is what was broken. Every figure used to be scaled to fill its own
    24x48 cell, which normalises height away: a child drawn at adult size came
    out at adult size, and the aspect-ratio guard could not see it because the
    aspect was fine. The controls are the fix -- they are authored at a known 47
    rows, so whatever height they came back at IS the page's ruler, and one
    divisor derived from them applies to everybody.
    """
    heights = [cell.height for cell in control_cells if cell.height > 1]
    if not heights:
        raise ValueError("no control figure survived keying; the page is unusable")
    heights.sort()
    drawn = heights[len(heights) // 2]          # median: one mangled control cannot skew it
    return AUTHORED_ROWS / drawn, heights


def fit_page(scale, cells):
    """Trim the page's scale, once, so the tallest person fits the cell.

    The controls set the ruler at 47 rows, but the cell is 48, so anyone the
    model draws even 5% taller than a control cannot fit -- and it kept drawing
    people at 49-51. Rescaling each offender individually would put us straight
    back to the bug this whole pass fixed. One divisor applied to EVERYBODY keeps
    every relative height intact: the child stays shorter than the adults, the
    whole cast just sits a hair smaller in its cells.
    """
    tallest = max((cell.height for cell in cells), default=0)
    if tallest * scale <= CELL_H:
        return scale, 1.0
    trim = CELL_H / (tallest * scale)
    return scale * trim, trim


def dominant_downscale(figure, width, height, alpha):
    """Per-block dominant colour, on a palette reduced BEFORE downscaling.

    Averaging is what smooths. A block straddling an edge returns the mean of
    both sides -- a colour that exists nowhere in the source -- and at a 10:1
    reduction almost every block straddles something, so a hard-edged figure
    arrives soft. That is not a flaw in the generation: the sheet reads as pixel
    art, and the sampling is what loses it.

    Asking instead which colour a block mostly IS keeps every output pixel a
    colour that was actually drawn. Reducing the palette first is what makes that
    question well-posed -- among 300 near-identical anti-aliased greys the mode
    is noise, among 24 it is the answer.
    """
    import numpy as np
    flat = Image.new("RGB", figure.size, (0, 0, 0))
    flat.paste(figure.convert("RGB"), (0, 0), alpha)
    reduced = flat.quantize(colors=PALETTE_COLORS, method=Image.MEDIANCUT,
                            dither=Image.NONE)
    indices = np.asarray(reduced)
    opaque = np.asarray(alpha) > 0
    palette = reduced.getpalette()
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = out.load()
    for y in range(height):
        y0 = figure.height * y // height
        y1 = max(figure.height * (y + 1) // height, y0 + 1)
        for x in range(width):
            x0 = figure.width * x // width
            x1 = max(figure.width * (x + 1) // width, x0 + 1)
            block = indices[y0:y1, x0:x1].ravel()
            mask = opaque[y0:y1, x0:x1].ravel()
            if not mask.any():
                continue
            value = np.bincount(block[mask]).argmax()
            pixels[x, y] = (palette[value * 3], palette[value * 3 + 1],
                            palette[value * 3 + 2], 255)
    return out


VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")


def grid_align(figure, step=None):
    """Rebuild the figure on the pixel grid it was actually drawn on.

    An image model does not draw pixel art, it draws smooth art that resembles
    it, on whatever grid it feels like -- measured here at roughly 4px while the
    authored figures beside it on the same page sat on exactly 8. Reducing from
    the model's grid to ours is therefore non-integer, and a non-integer
    reduction smooths whatever resampler runs. Snapping to the source grid first
    makes the second step a clean ratio.

    Pass `step` to force the grid instead of detecting one. Detection reads the
    generated figures at ~4px, but that is the FINEST grid consistent with them,
    not necessarily the one they were drawn on -- and 4 is exactly half of 8, so
    the two are indistinguishable from the figure alone. Blanking the controls
    off the page and re-detecting separated them: the controls alone come back at
    8.00/8.00 at high confidence, so the page's grid is 8, and the generated
    figures' 4 is a subharmonic of it. Forcing 8 lands them straight on the cell
    with no second resample at all.

    Returns the figure unchanged if the detector cannot find a grid: no grid is a
    real answer for art that has none, and block-mode alone still handles it.
    """
    if VENDOR_DIR not in sys.path:
        sys.path.insert(0, VENDOR_DIR)
    from pixelfixer.api import process
    buffer = io.BytesIO()
    figure.save(buffer, format="PNG")
    try:
        result = (process(buffer.getvalue(), force_step=step, return_png=True)
                  if step else
                  process(buffer.getvalue(), mode="full", return_png=True))
    except Exception as error:                      # noqa: BLE001
        print("     note: grid detection declined (%s); using the raw figure"
              % error)
        return figure
    aligned = Image.open(io.BytesIO(result["png"])).convert("RGBA")
    box = aligned.getbbox()
    return aligned.crop(box) if box else aligned


# Ranked by eye, not by metric. A "crispness" score -- mean contrast between
# neighbouring pixels -- says page 72.8, grid 63.7, mode 61.1, lanczos 48.7, and
# it is the wrong instrument: it cannot tell a hard edge from noise, and
# grid-snapping wins it by hardening every edge including the ones that should
# stay soft. Judged by looking, the order inverts. Lanczos is the default.
#
# It is a fair fight now in a way it was not before: on the old page the model's
# grid and ours were incommensurate and averaging smeared across the mismatch.
# The page is sized so the reduction is exactly 8:1, and an area filter over
# whole 8x8 blocks is no longer averaging across anything.
DOWNSCALERS = {
    "lanczos": Image.LANCZOS,           # the default
    "page": None,                       # grid forced to the page's own
    "grid": None,                       # grid_align on a detected grid
    "mode": None,                       # dominant_downscale alone
    "box": Image.BOX,
    "nearest": Image.NEAREST,
}
PALETTE_METHODS = ("page", "grid", "mode")      # these already return a small palette


def to_cell_at(cell_image, scale, method="lanczos"):
    """One 24x48 cell at the page's shared scale, feet on the bottom edge."""
    figure = cell_image
    # The target size is fixed by the PAGE's shared scale, measured before any
    # grid alignment -- realigning must not be allowed to resize anybody, or the
    # relative heights the whole page is built on would drift apart.
    width = max(1, round(figure.width * scale))
    height = max(1, round(figure.height * scale))
    if method == "page":
        # The controls fix the page's grid exactly, so force it rather than
        # detect per figure: the reconstruction then lands ON the target size and
        # nothing is resampled a second time.
        figure = grid_align(figure, step=1.0 / scale)
    elif method == "grid":
        figure = grid_align(figure)
    # Alpha is resampled separately and hard-thresholded either way: a soft edge
    # shimmers against a pre-rendered plate.
    alpha_full = figure.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    # Only dominant_downscale returns a reduced palette. Forcing the grid can
    # land the figure on the target size and skip it entirely, so track this
    # rather than infer it from the method -- inferring it shipped sprites with
    # 350-630 colours instead of 24.
    palettised = False
    if figure.size == (width, height):
        small = figure                  # forced to the target grid; already there
    elif method in PALETTE_METHODS:
        small = dominant_downscale(figure, width, height, alpha_full)
        palettised = True
    else:
        small = figure.resize((width, height), DOWNSCALERS[method])
    cell = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    # Feet on the bottom edge: the compositor anchors sprites by their feet.
    # A figure taller than the cell is NOT rescaled to fit -- that would undo the
    # shared scale -- the whole page is trimmed instead, in fit_page.
    cell.alpha_composite(small, ((CELL_W - width) // 2, CELL_H - height))
    alpha = cell.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    if palettised:
        # Already reduced, and quantising again would only re-average it.
        cell.putalpha(alpha)
        return cell, width, height
    # Quantise the COLOUR only. Quantising RGBA folds transparency into the
    # palette, so cleared pixels get a nearest colour and the magenta that was
    # keyed out comes back as a palette entry.
    flat = Image.new("RGB", cell.size, (0, 0, 0))
    flat.paste(cell.convert("RGB"), (0, 0), alpha)
    flat = flat.quantize(colors=PALETTE_COLORS, method=Image.MEDIANCUT,
                         dither=Image.NONE).convert("RGB")
    result = flat.convert("RGBA")
    result.putalpha(alpha)
    return result, width, height


def main():
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in flags
    dry_run = "--dry-run" in flags
    method = next((f.split("=", 1)[1] for f in flags if f.startswith("--downscale=")),
                  "lanczos")
    if method not in DOWNSCALERS:
        print("FAIL unknown --downscale=%s (have: %s)"
              % (method, ", ".join(DOWNSCALERS)))
        return 1

    wanted = [n for n in (argv or list(CAST)) if n in CAST]
    for name in (argv or []):
        if name not in CAST:
            print("SKIP unknown cast member: " + name)
    if not force:
        have = [n for n in wanted
                if os.path.exists(os.path.join(OUT_DIR, "npc_" + n + ".png"))]
        for name in have:
            print("HAVE " + name)
        wanted = [n for n in wanted if n not in have]
    if not wanted:
        print("SPRITES OK (nothing to generate)")
        return 0
    if len(CONTROLS) + len(wanted) > SLOTS:
        print("FAIL %d controls + %d roles exceeds the %dx%d page (%d slots)"
              % (len(CONTROLS), len(wanted), COLS, ROWS, SLOTS))
        return 1

    prompt = sheet_prompt(CONTROLS, wanted)
    print("%s quality=%s size=%s downscale=%s  %d role(s) + %d control(s) on one %dx%d page"
          % (MODEL, QUALITY, SIZE, method, len(wanted), len(CONTROLS), COLS, ROWS))
    if dry_run:
        print(prompt)
        return 0

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    started = time.time()
    raw_path = os.path.join(RAW_DIR, "sheet.png")
    if "--from-raw" in flags:
        # Re-cut a page already paid for. Every change below the API call is a
        # cutting change, and re-billing to test one is waste.
        sheet, usd = open(raw_path, "rb").read(), 0.0
    else:
        sheet, usd = generate_sheet(
            prompt, sheet_reference(CONTROLS, placeholders=len(wanted)))
        with open(raw_path, "wb") as handle:
            handle.write(sheet)
    cells = slice_sheet(sheet)
    expected = len(CONTROLS) + len(wanted)
    if len(cells) != expected:
        print("  WARN found %d figures on the page, expected %d" % (len(cells), expected))
    scale, control_heights = sheet_scale(cells[:len(CONTROLS)])
    scale, trim = fit_page(scale, cells)
    print("SHEET  %.0fs  $%.4f  -> %s" % (time.time() - started, usd, raw_path))
    print("  controls drawn at %s rows; page scale %.4f (%d authored rows)%s"
          % (control_heights, scale, AUTHORED_ROWS,
             "" if trim == 1.0 else "; page trimmed %.1f%% so the tallest fits"
             % (100.0 * (1.0 - trim))))

    failures = []
    for name, cell_image in zip(wanted, cells[len(CONTROLS):]):
        if cell_image.getbbox() is None:
            print("  FAIL %-12s cell is empty after keying" % name)
            failures.append(name)
            continue
        cell, width, height = to_cell_at(cell_image, scale, method)
        # Height is now absolute, measured against the controls, so this catches
        # the child-drawn-as-an-adult case that the aspect guard was blind to.
        if not (HEIGHT_MIN <= height <= HEIGHT_MAX):
            print("  FAIL %-12s %d rows, outside %d-%d at the page scale"
                  % (name, height, HEIGHT_MIN, HEIGHT_MAX))
            failures.append(name)
            continue
        cell.save(os.path.join(OUT_DIR, "npc_" + name + ".png"))
        print("  OK   %-12s %2dx%2d  %.0f%% of an authored figure"
              % (name, width, height, 100.0 * height / AUTHORED_ROWS))
    print("spent $%.4f on one sheet" % usd)
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("SPRITES OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
