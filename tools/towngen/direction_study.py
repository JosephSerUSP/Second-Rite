"""Ask a cheap image model what it would do with a rendered town screen.

A *direction study*, not an asset pipeline. It takes frames rendered out of a
Blender town scene, sends each one back through OpenAI's `/images/edits` route
as an img2img reference, and lays the answers beside the original so a massing
pass can be judged against several possible finishes before anyone commits to
one. Nothing it writes is promotable: the outputs are concept, in the same
sense `roomVolume` plates are concept.

    python tools/towngen/direction_study.py \
        --frames out/renders/market_*.png --out out/direction/market

Why this is affordable enough to run on a whim: `gpt-image-1-mini` at `low`
quality is $0.005 per 1024x1024 image, so a four-frame study in two directions
costs four cents. The script prints the estimated spend BEFORE it sends
anything and refuses to exceed `--budget`.

**Aspect.** A town frame is 256x240 and the API's nearest size is 1024x1024, so
frames are upscaled 4x to 1024x960 and letterboxed to square, then the answer is
cropped back. Sending the 256x240 frame straight up would stretch the street by
6.7% and quietly change every proportion the camera work just established.
"""

from __future__ import annotations

import argparse
import base64
import glob
import json
import os
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "asset-gen"))

import requests  # noqa: E402

CONFIG = ROOT / "tools" / "asset-gen" / "config.json"
API_SIZE = 1024

# St. Maria is a colonial Portuguese town; these are the facts a model has to be
# told or it will hand back generic Mediterranean.
PLACE = (
    "A colonial Portuguese colonial-era town, St. Maria: limewash (caiacao) "
    "walls rather than grey plaster, an azulejo tile dado as a waist-high band "
    "only, dark tropical hardwood joinery, wrought-iron grilles and chest "
    "bands, terracotta roof pans, panelled doors and louvred shutters."
)

DIRECTIONS = {
    "backdrop": (
        "Repaint this exact scene as a pre-rendered background for a "
        "late-1990s console RPG. Keep every object, its position, its scale "
        "and the camera unchanged -- this is a repaint, not a new composition. "
        + PLACE + " Baked ambient occlusion and soft contact shadows in the "
        "joints and recesses; no harsh directional key, no cast sun shadows, "
        "no visible light direction. Slightly blown highlights against deep "
        "shadow. Detail placed at the resolution it will be seen at, not fine "
        "detail that would average away."
    ),
    "painterly": (
        "Repaint this exact scene as a painted illustration of a working "
        "market street, keeping every object, position, scale and the camera "
        "unchanged. " + PLACE + " Push the material identity hard: the "
        "difference between limewash, tile, hardwood, iron and terracotta "
        "should be obvious at a glance. Give the vegetation real foliage "
        "rather than blocked-in mass. Warm humid tropical daylight, strong "
        "local colour, no harsh cast shadows."
    ),
}


def provider_config():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    return config["providers"]["openai"]


def unit_price(provider, model, quality):
    for entry in provider.get("models", []):
        if entry["id"] != model:
            continue
        prices = entry.get("prices")
        if not prices:
            return None
        return prices.get(quality, {}).get(f"{API_SIZE}x{API_SIZE}")
    return None


def to_square(path: Path):
    """Fit the frame into the square canvas, letterboxed. Returns
    (image, top_pad, height).

    A native 256x240 town frame goes up 4x by NEAREST, because an integer
    nearest upscale is the only resampling that does not invent intermediate
    colours the pixel art never had. Anything that is not an exact integer
    multiple falls back to LANCZOS.
    """
    frame = Image.open(path).convert("RGB")
    scale = min(API_SIZE / frame.width, API_SIZE / frame.height)
    width = max(1, int(round(frame.width * scale)))
    height = max(1, int(round(frame.height * scale)))
    exact = (width % frame.width == 0 and height % frame.height == 0
             and width // frame.width == height // frame.height)
    tall = frame.resize((width, height),
                        Image.NEAREST if exact else Image.LANCZOS)
    canvas = Image.new("RGB", (API_SIZE, API_SIZE), (0, 0, 0))
    top = (API_SIZE - tall.height) // 2
    canvas.paste(tall, ((API_SIZE - tall.width) // 2, top))
    return canvas, top, tall.height


def edit(provider, prompt, square_path: Path, quality, timeout):
    key = os.environ.get(provider["apiKeyEnv"])
    if not key:
        raise SystemExit(f"{provider['apiKeyEnv']} is not set")
    with open(square_path, "rb") as handle:
        response = requests.post(
            provider["baseUrl"] + "/images/edits",
            data={"model": provider["model"], "prompt": prompt,
                  "size": f"{API_SIZE}x{API_SIZE}", "n": "1",
                  "quality": quality},
            files=[("image[]", (square_path.name, handle, "image/png"))],
            headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
    if not response.ok:
        raise SystemExit(f"openai /images/edits {response.status_code}: "
                         f"{response.text[:400]}")
    data = (response.json().get("data") or [])
    if not data or not data[0].get("b64_json"):
        raise SystemExit("openai /images/edits returned no image")
    return base64.b64decode(data[0]["b64_json"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", nargs="+", required=True,
                        help="rendered town frames (globs are expanded)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--directions", nargs="+", default=sorted(DIRECTIONS),
                        choices=sorted(DIRECTIONS))
    parser.add_argument("--quality", default=None,
                        help="defaults to the provider's configured quality")
    parser.add_argument("--budget", type=float, default=0.25,
                        help="refuse to start if the estimate exceeds this")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--dry-run", action="store_true",
                        help="price the run and write the padded inputs only")
    args = parser.parse_args()

    frames = []
    for pattern in args.frames:
        frames.extend(sorted(Path(p) for p in glob.glob(pattern)))
    frames = [f for f in frames if f.is_file()]
    if not frames:
        raise SystemExit("no frames matched")

    provider = provider_config()
    quality = args.quality or provider.get("quality", "low")
    price = unit_price(provider, provider["model"], quality)
    count = len(frames) * len(args.directions)
    estimate = None if price is None else price * count

    print(f"[study] {len(frames)} frames x {len(args.directions)} directions "
          f"= {count} images via {provider['model']} ({quality})")
    if estimate is None:
        print("[study] this model has no per-image price table; cost unknown")
    else:
        print(f"[study] estimated ${estimate:.3f} "
              f"(${price:.4f} per {API_SIZE}x{API_SIZE})")
        if estimate > args.budget:
            raise SystemExit(f"estimate ${estimate:.3f} exceeds --budget "
                             f"${args.budget:.3f}")

    args.out.mkdir(parents=True, exist_ok=True)
    padded_dir = args.out / "_input"
    padded_dir.mkdir(exist_ok=True)

    produced = []
    for frame in frames:
        square, top, height = to_square(frame)
        square_path = padded_dir / f"{frame.stem}.png"
        square.save(square_path)
        if args.dry_run:
            continue
        for direction in args.directions:
            raw = edit(provider, DIRECTIONS[direction], square_path, quality,
                       args.timeout)
            answer = Image.open(__import__("io").BytesIO(raw)).convert("RGB")
            if answer.size != (API_SIZE, API_SIZE):
                answer = answer.resize((API_SIZE, API_SIZE), Image.LANCZOS)
            cropped = answer.crop((0, top, API_SIZE, top + height))
            out_path = args.out / f"{frame.stem}__{direction}.png"
            cropped.save(out_path)
            produced.append(out_path)
            print(f"[study] {out_path.name}")

    print("DIRECTION STUDY OK " + json.dumps({
        "frames": [str(f) for f in frames],
        "directions": args.directions,
        "images": len(produced),
        "estimatedUsd": estimate,
        "dryRun": bool(args.dry_run),
    }))


if __name__ == "__main__":
    main()
