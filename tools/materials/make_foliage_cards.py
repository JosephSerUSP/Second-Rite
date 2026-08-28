"""Generate alpha foliage CARDS -- the texture retro vegetation is actually made of.

Low-poly vegetation is not modelled leaf by leaf. It is a handful of quads, each
carrying a cutout texture of a whole leaf CLUSTER with its twigs, arranged as
crossed planes for a tree or laid over a dome for a bush. The mesh supplies the
silhouette and the parallax; the texture supplies every leaf. Building actual
leaf geometry instead produced 8,751 objects for one hedge and still read as
boulders wearing spikes.

Two rules from the technique that drive the prompts here:

- **Less foliage on the texture, more on the mesh.** A card crowded edge to edge
  mipmaps into a solid green block at distance, which is exactly the failure
  mode a 256x240 backdrop cannot afford. Cards are asked for airy clusters with
  gaps the background shows through.
- **The card must be flat and evenly lit.** It is a cutout, not a photograph of
  a bush: any baked directional light or perspective fights the lighting the
  scene puts on it, and the albedo doctrine already forbids baked direct light.

`background: transparent` on the OpenAI image route returns a real alpha
channel, which beats keying a colour backdrop afterwards -- a keyed cutout
leaves a fringe on every leaf edge, and at this resolution a fringe is most of
the leaf.

    python tools/materials/make_foliage_cards.py --out projects/.../materials

Cost is printed before anything is sent and `--budget` refuses to exceed. At
gpt-image-1-mini medium a three-card sheet is about four cents.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import sys
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "tools" / "asset-gen" / "config.json"
API_SIZE = 1024

# Each entry becomes one card in the sheet. Keep the count small: a card is
# reused at many sizes and rotations, so variety comes from placement far more
# cheaply than from more textures.
CARDS = {
    "broadleaf": (
        "One airy cluster of tropical broadleaf foliage on a THIN WOODY TWIG, "
        "photographed flat like a pressed herbarium specimen, seen straight on "
        "with no perspective. Fully transparent background. Leaves must be "
        "SPARSE with clear gaps between them so the background shows through "
        "-- not a solid mass. Even flat neutral lighting, no cast shadows, no "
        "highlights, no visible light direction. Muted dusty green, slightly "
        "desaturated, a few leaves yellowed. The cluster should fill most of "
        "the frame with ragged irregular edges."
    ),
    "palm_frond": (
        "One single pinnate palm frond, flat pressed specimen, seen straight "
        "on with no perspective, running corner to corner across the frame. "
        "Fully transparent background. Individual leaflets clearly separated "
        "along the central rib with gaps between them so the background shows "
        "through. Even flat neutral lighting, no cast shadows, no highlights, "
        "no visible light direction. Muted dusty green, a few dry brown "
        "leaflets near the base."
    ),
    "bush_mass": (
        "One WIDE, DENSE, ROUNDED clump of shrub foliage -- a section of a "
        "clipped hedge seen from the side, wider than it is tall, with a "
        "domed top and a ragged irregular outline. Flat pressed specimen seen "
        "straight on with no perspective. Fully transparent background. Many "
        "small overlapping leaves on short woody twigs, dense in the middle "
        "and breaking up into separate leaves and gaps at the edges so it "
        "layers without turning solid. Even flat neutral lighting, no cast "
        "shadows, no highlights, no visible light direction. Deep muted dusty "
        "green, slightly darker toward the centre."
    ),
    "sprig": (
        "One small sparse sprig of shrub foliage with visible thin woody "
        "stems, flat pressed specimen, seen straight on with no perspective. "
        "Fully transparent background. Very open and airy -- mostly empty "
        "space with scattered small leaves, so it can be layered many times "
        "without turning solid. Even flat neutral lighting, no cast shadows, "
        "no visible light direction. SATURATED DEEP GREEN foliage, clearly "
        "green and not pale, washed out, dried or bleached."
    ),
}


def provider_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))["providers"]["openai"]


def unit_price(provider, model, quality):
    for entry in provider.get("models", []):
        if entry["id"] == model:
            prices = entry.get("prices")
            return None if not prices else prices.get(quality, {}).get(
                f"{API_SIZE}x{API_SIZE}")
    return None


def generate(provider, prompt, quality, timeout):
    key = os.environ.get(provider["apiKeyEnv"])
    if not key:
        raise SystemExit(f"{provider['apiKeyEnv']} is not set")
    response = requests.post(
        provider["baseUrl"] + "/images/generations",
        json={"model": provider["model"], "prompt": prompt,
              "size": f"{API_SIZE}x{API_SIZE}", "n": 1, "quality": quality,
              "background": "transparent", "output_format": "png"},
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        timeout=timeout)
    if not response.ok:
        raise SystemExit(f"openai /images/generations {response.status_code}: "
                         f"{response.text[:400]}")
    data = response.json().get("data") or []
    if not data or not data[0].get("b64_json"):
        raise SystemExit("openai returned no image")
    return base64.b64decode(data[0]["b64_json"])


def trim_and_fit(raw: bytes, size: int) -> Image.Image:
    """Crop to the cluster's own alpha bounds, then fit the card square.

    Trimming matters more than it looks: the model leaves a wide transparent
    margin, and an untrimmed card wastes most of its texels on nothing. Since
    the quad is UV-mapped to the whole card, that margin would also shrink the
    leaves relative to the quad and force every placement larger to compensate.
    """
    image = Image.open(io.BytesIO(raw)).convert("RGBA")
    box = image.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if box:
        image = image.crop(box)
    fitted = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    scale = min(size / image.width, size / image.height)
    scaled = image.resize((max(1, int(image.width * scale)),
                           max(1, int(image.height * scale))), Image.LANCZOS)
    fitted.paste(scaled, ((size - scaled.width) // 2,
                          (size - scaled.height) // 2))
    # Colour under fully transparent texels is undefined and bilinear filtering
    # will drag it into the leaf edges as a dark halo. Flood the RGB of clear
    # texels with the cluster's own mean so the fringe matches the leaves.
    pixels = fitted.load()
    total, count = [0, 0, 0], 0
    for y in range(0, size, 4):
        for x in range(0, size, 4):
            r, g, b, a = pixels[x, y]
            if a > 128:
                total[0] += r
                total[1] += g
                total[2] += b
                count += 1
    if count:
        mean = tuple(channel // count for channel in total)
        for y in range(size):
            for x in range(size):
                r, g, b, a = pixels[x, y]
                if a < 8:
                    pixels[x, y] = (mean[0], mean[1], mean[2], a)
    return fitted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=(
        ROOT / "projects" / "hichaukitoden-game" / "assets" / "materials"
        / "foliage_card"))
    parser.add_argument("--cards", nargs="+", default=sorted(CARDS),
                        choices=sorted(CARDS))
    parser.add_argument("--size", type=int, default=512,
                        help="per-card pixel size in the packed sheet")
    parser.add_argument("--quality", default="medium")
    parser.add_argument("--budget", type=float, default=0.20)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--world-size", type=float, default=1.1,
                        help="metres one CARD spans; a cluster is roughly a "
                             "branch, so about a metre")
    args = parser.parse_args()

    provider = provider_config()
    price = unit_price(provider, provider["model"], args.quality)
    estimate = None if price is None else price * len(args.cards)
    print(f"[cards] {len(args.cards)} cards via {provider['model']} "
          f"({args.quality})")
    if estimate is not None:
        print(f"[cards] estimated ${estimate:.3f}")
        if estimate > args.budget:
            raise SystemExit(f"estimate ${estimate:.3f} exceeds --budget")

    args.out.mkdir(parents=True, exist_ok=True)
    tiles = []
    for name in args.cards:
        raw = generate(provider, CARDS[name], args.quality, args.timeout)
        tiles.append((name, trim_and_fit(raw, args.size)))
        print(f"[cards] {name}")

    # One row, so a card's UV rect is just an equal slice of U.
    sheet = Image.new("RGBA", (args.size * len(tiles), args.size), (0, 0, 0, 0))
    for index, (_, tile) in enumerate(tiles):
        sheet.paste(tile, (index * args.size, 0))
    albedo = args.out / "albedo.png"
    sheet.save(albedo)

    record = {
        "materialKind": "second_gate_material",
        "version": 1,
        "semanticId": "foliage_card",
        "status": "placeholder",
        "worldSizeMetres": float(args.world_size),
        "maps": {"albedo": "albedo.png"},
        "cards": [name for name, _ in tiles],
        "notes": ("Alpha cutout CARDS for retro vegetation: each slice is one "
                  "leaf cluster with its twigs. Vegetation is built from these "
                  "on crossed planes and domes, never from per-leaf geometry. "
                  "Deliberately airy -- a crowded card mipmaps into a solid "
                  "block, and the mesh is supposed to carry the silhouette."),
        "provenance": {
            "origin": f"openai:{provider['model']}",
            "generator": "tools/materials/make_foliage_cards.py",
            "processing": (f"background=transparent, trimmed to alpha bounds, "
                           f"fitted to {args.size}px, clear texels flooded "
                           f"with the cluster mean to stop a dark filtering "
                           f"fringe; packed one row"),
            "license": "generated",
            "sha256": {"albedo.png": hashlib.sha256(
                albedo.read_bytes()).hexdigest()},
        },
    }
    (args.out / "material.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("FOLIAGE CARDS OK " + json.dumps({
        "sheet": str(albedo), "cards": record["cards"],
        "size": list(sheet.size), "estimatedUsd": estimate}))


if __name__ == "__main__":
    main()
