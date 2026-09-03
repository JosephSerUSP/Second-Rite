"""Pollinations image client, and a probe for checking what the key can reach.

    python tools/asset-gen/pollinations_images.py --probe
    python tools/asset-gen/pollinations_images.py --prompt "a wet stone quay" \
        --width 1065 --height 240 --out out/probe.png

The key is `POLLINATIONS_API_KEY`, read from the environment or, if the session
started before it was set, from the user environment behind it (see user_env).

## The one thing this does that nothing else here can

**It draws at the plate's exact aspect.** 1065x240 -- 4.44:1 -- comes back as
1065x240. OpenAI refuses anything past 3:1 outright, which is why plates have to
be generated as two overlapping halves and stitched there. This needs no tiling
and no seam, which for a scrolling backdrop is worth a great deal.

There is a ceiling: 2130x480 at the same ratio comes back as 1617x364, so the
service caps total pixels and scales the request down rather than refusing it.
Ask for the plate's real size and it is honoured; ask for a supersample of it and
the answer is quietly smaller than requested, so check what came back.

## What it cannot do

Text to image only, on this key. ``/models`` lists exactly one model, ``sana``;
the img2img-capable ones (kontext, gptimage) belong to higher tiers. An ``image=``
parameter is accepted and ignored, which is worse than an error -- it returns a
plausible picture that owes nothing to the reference -- so the layout guides
cannot condition it.
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import user_env

BASE_URL = "https://image.pollinations.ai"
TOKEN_ENV = "POLLINATIONS_API_KEY"
DEFAULT_MODEL = "sana"


def headers():
    token, = user_env.require(TOKEN_ENV)
    return {"Authorization": "Bearer " + token}


def models():
    response = requests.get(BASE_URL + "/models", headers=headers(), timeout=60)
    response.raise_for_status()
    return response.json()


def generate(prompt, width=1024, height=1024, model=DEFAULT_MODEL, seed=None,
             timeout=300):
    """One image. Returns (bytes, actual size), because the two can differ."""
    query = {"model": model, "width": int(width), "height": int(height),
             "nologo": "true"}
    if seed is not None:
        query["seed"] = int(seed)
    url = "%s/prompt/%s?%s" % (BASE_URL, urllib.parse.quote(prompt),
                               urllib.parse.urlencode(query))
    response = requests.get(url, headers=headers(), timeout=timeout)
    if response.status_code != 200 or "image" not in response.headers.get(
            "content-type", ""):
        raise RuntimeError("pollinations %s %s"
                           % (response.status_code, response.text[:300]))
    import io
    from PIL import Image
    image = Image.open(io.BytesIO(response.content))
    return response.content, (image.width, image.height)


def probe():
    print("%s set" % TOKEN_ENV)
    print("models reachable with this key: %s" % (models(),))
    for width, height in ((1065, 240), (2130, 480)):
        raw, got = generate("a grey stone wall", width, height, seed=1)
        note = "" if got == (width, height) else "  <- SCALED DOWN, capped by pixels"
        print("  asked %dx%d (%.2f:1) -> got %dx%d, %d KiB%s"
              % (width, height, width / height, got[0], got[1],
                 len(raw) / 1024, note))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--prompt")
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    if args.probe:
        probe()
        return
    if not args.prompt or not args.out:
        raise SystemExit("--probe, or --prompt with --out")
    raw, got = generate(args.prompt, args.width, args.height, args.model, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(raw)
    print("POLLINATIONS OK %s (%dx%d, %d bytes)%s"
          % (args.out, got[0], got[1], len(raw),
             "" if got == (args.width, args.height) else "  <- not the size asked for"))


if __name__ == "__main__":
    main()
