"""Generate pre-rendered background plates for the St. Maria side-view town.

One painted plate per screen, downscaled to the native 426x240 target so it
reads as a 1990s pre-rendered CG background rather than as a photograph.

The provider is deliberately behind one function. Nothing else in this script
knows which model produced a plate; swap `generate_image` to change providers.

Usage:
    python tools/towngen/generate_plates.py            # all screens
    python tools/towngen/generate_plates.py gate praca # named screens only
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
SIZE = "1536x1024"
NATIVE_W, NATIVE_H = 426, 240
OUT_DIR = os.path.join("projects", "hichaukitoden-game", "assets",
                       "environments", "st_maria_town", "plates")
RAW_DIR = os.path.join("out", "towngen", "raw")

# Shared style contract. Every plate must read as the same town on the same
# overcast afternoon, so the invariants live here rather than in each prompt.
STYLE = (
    "Pre-rendered background plate for a 1990s side-scrolling adventure game, painted in the "
    "style of early pre-rendered CG backgrounds. Flat side elevation: the camera is exactly "
    "perpendicular to the facades, with no vanishing-point perspective along the street axis. "
    "A dreary yet cozy colonial Portuguese village. Whitewashed lime-plaster walls with damp grey "
    "staining and patches of exposed stone, terracotta barrel-tile roofs, blue-and-white azulejo "
    "tile panels beside the doorways, wrought-iron balconies, heavy dark timber doors with iron "
    "fittings. Overcast sea-fog light, cool blue-grey shadows, low warm lantern glow spilling from "
    "windows. Wet stone underfoot. "
    "Wide horizontal composition with the walkable ground running flat across the lower third. "
    "The architecture continues past both the left and right edges of the frame rather than "
    "terminating inside it. No people, no animals, no text, no lettering, no signage words, "
    "no watermark, no user interface, no frame or border."
)

SCREENS = {
    # --- exteriors, west to east along the town's single street ---
    "gate": (
        "The head of the street: a sealed stone gate set into the flank of a small colonial church. "
        "A heavy iron-bound double door under a weathered stone arch carved with worn saints, "
        "flanked by two tall iron lanterns burning against the grey afternoon. Stone steps rise from "
        "the wet cobbles to the threshold. The church's whitewashed bell wall rises above, one bronze "
        "bell visible in its opening. Ivy and salt damp climb the lower masonry."
    ),
    "praca": (
        "The village praca: a small open square of wet granite cobbles with a low octagonal stone "
        "fountain at the centre, water sheeting down its basin. Two-storey whitewashed townhouses "
        "with iron balconies close the square on the far side, laundry hanging out to dry. A stone "
        "bench, a leaning notice post, terracotta pots of geraniums against the walls."
    ),
    "market": (
        "A market row under a long sagging canvas awning strung between the housefronts. Empty wooden "
        "trestle stalls, stacked crates, hanging scales, baskets, coils of rope, barrels of salt fish. "
        "The whitewashed facades behind are tighter and taller here, their azulejo panels chipped. "
        "Rainwater drips from the awning onto the cobbles."
    ),
    "quay": (
        "The low end of the street where the town meets the water: a stone quay wall along the bottom "
        "with mooring rings and bollards, grey estuary water and sea fog beyond it to the right. "
        "A pub front with a warm lit window and a small chapel door share the left facade, both under "
        "deep stone lintels. Nets and lobster pots stacked against the wall."
    ),
    # --- interiors ---
    "weaponsmith": (
        "Interior of a village weaponsmith, seen in flat side elevation like a doll's-house cutaway. "
        "A stone forge with banked orange coals on the left, an anvil, racked blades and billhooks on "
        "the whitewashed rear wall, a heavy workbench with tools, leather aprons on pegs. "
        "Warm firelight against cold daylight from a small high window. Packed earth floor."
    ),
    "pub": (
        "Interior of a small village tavern, flat side elevation. A dark timber bar with bottles and "
        "pewter mugs, low beamed ceiling, three worn tables with stools, a fireplace with a small fire, "
        "azulejo tiles along the lower wall, oil lamps. Cozy amber light, smoke-darkened plaster."
    ),
    "chapel": (
        "Interior of a small colonial chapel, flat side elevation. Whitewashed walls with blue azulejo "
        "panels depicting the sea, a modest gilt altar with candles, four wooden pews, a stone font. "
        "Cold grey light falling from a high window, warm candlelight below. Worn flagstone floor."
    ),
    "house_laura": (
        "Interior of a cramped, tidy village dwelling, flat side elevation. A cooking hearth with a "
        "hanging pot, a scrubbed table with two chairs, a dresser of blue-and-white crockery, dried "
        "herbs hung from the beams, a shuttered window letting in a bar of grey light. Cozy and poor."
    ),
    "house_alicia": (
        "Interior of an upstairs room in a village townhouse, flat side elevation. A narrow bed with a "
        "quilt, a writing desk stacked with papers and a candle, a small iron balcony door standing "
        "ajar onto grey afternoon light, a chest, a faded rug. Quiet and lived-in."
    ),
}


def generate_image(prompt):
    """Return PNG bytes for one plate. The only provider-aware function here."""
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


def to_native(png_bytes):
    """Crop to the native aspect, then downscale to 426x240.

    The crop is taken from the lower part of the source: the generator puts sky
    at the top and the walkable ground low, and the ground is the part the
    player actually reads. Downscaling a painted plate is what produces the
    pre-rendered look - it is not a resolution compromise.
    """
    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    width, height = image.size
    target_ratio = NATIVE_W / NATIVE_H
    crop_h = int(round(width / target_ratio))
    if crop_h > height:
        crop_h = height
        crop_w = int(round(height * target_ratio))
        left = (width - crop_w) // 2
        box = (left, 0, left + crop_w, height)
    else:
        # Keep 70% of the discarded band off the top: sky is the cheapest loss.
        top = int(round((height - crop_h) * 0.7))
        box = (0, top, width, top + crop_h)
    return image.crop(box).resize((NATIVE_W, NATIVE_H), Image.LANCZOS)


def main():
    wanted = sys.argv[1:] or list(SCREENS)
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    failures = []
    for name in wanted:
        if name not in SCREENS:
            print("SKIP unknown screen: " + name)
            continue
        out_path = os.path.join(OUT_DIR, name + "_bg.png")
        if os.path.exists(out_path):
            print("HAVE " + name)
            continue
        prompt = STYLE + " " + SCREENS[name]
        started = time.time()
        try:
            raw = generate_image(prompt)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:300]
            print("FAIL %s http %s %s" % (name, error.code, detail))
            failures.append(name)
            continue
        except Exception as error:  # noqa: BLE001 - report and continue the batch
            print("FAIL %s %s" % (name, error))
            failures.append(name)
            continue
        with open(os.path.join(RAW_DIR, name + ".png"), "wb") as handle:
            handle.write(raw)
        to_native(raw).save(out_path)
        print("OK   %s  %.1fs  -> %s" % (name, time.time() - started, out_path))
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("PLATES OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
