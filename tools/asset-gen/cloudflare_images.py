"""Cloudflare Workers AI image client, and a probe for checking it works.

    python tools/asset-gen/cloudflare_images.py --probe
    python tools/asset-gen/cloudflare_images.py --prompt "a wet stone quay at dusk" \
        --init out/town-positions/19-position.png --strength 0.6 --out out/probe.png

Two environment variables, because the REST path carries the account:

    CLOUDFLARE_ACCOUNT_ID   32 hex characters, the one in every dashboard URL
    CLOUDFLARE_API_KEY      the API token

Both are read from the environment and never logged. ``setx`` only reaches new
processes, so a shell open before they were set will not see them -- which the
probe says plainly rather than failing with an authentication error that looks
like a bad token.

## What these models are, and are not

Stable Diffusion, not the GPT-image family, and the difference decides which half
of the plate pipeline they can serve.

* **One image, not several.** A style sheet AND a layout guide cannot both be
  sent. They would have to be composited into a single picture first.
* **Structure, not instructions.** These follow an init image's shapes; they do
  not act on "put a door at each red arrow". That sentence is a GPT-image
  ability.
* **Which is a fit for the guides.** A guide IS structural conditioning, and a
  low denoising strength keeps its layout while the look is repainted. That is
  the job SD img2img exists for.

So: plausibly good for the guided path, poor for the imaginative one -- the
opposite of the ChatGPT web app, which invents freely and follows a guide loosely.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

import requests

BASE_URL = "https://api.cloudflare.com/client/v4"
ACCOUNT_ENV = "CLOUDFLARE_ACCOUNT_ID"
TOKEN_ENV = "CLOUDFLARE_API_KEY"
DEFAULT_MODEL = "@cf/runwayml/stable-diffusion-v1-5-img2img"
TEXT_TO_IMAGE = "@cf/black-forest-labs/flux-1-schnell"


def credentials():
    """Both values, or a message saying which is missing and why."""
    account = os.environ.get(ACCOUNT_ENV)
    token = os.environ.get(TOKEN_ENV)
    missing = [name for name, value in ((ACCOUNT_ENV, account), (TOKEN_ENV, token))
               if not value]
    if missing:
        raise SystemExit(
            "missing %s.\n"
            "If they were just set with setx, this process cannot see them: setx "
            "reaches new processes only, so the shell (and any session started "
            "before it) has to be restarted." % " and ".join(missing))
    return account, token


def run(model, payload, account=None, token=None, timeout=300):
    """POST to one model. Returns (bytes or dict, content type)."""
    account, token = (account, token) if account and token else credentials()
    response = requests.post(
        "%s/accounts/%s/ai/run/%s" % (BASE_URL, account, model),
        headers={"Authorization": "Bearer " + token},
        json=payload, timeout=timeout)
    kind = response.headers.get("content-type", "")
    if response.status_code != 200:
        raise RuntimeError("workers-ai %s %s %s"
                           % (model, response.status_code, response.text[:400]))
    if "application/json" in kind:
        body = response.json()
        if not body.get("success", True):
            raise RuntimeError("workers-ai %s reported failure: %s"
                               % (model, json.dumps(body.get("errors"))[:400]))
        result = body.get("result") or {}
        if isinstance(result, dict) and result.get("image"):
            # Some models answer with base64 in JSON rather than a binary body.
            return base64.b64decode(result["image"]), "image/png"
        return body, kind
    return response.content, kind


def image_to_image(prompt, init_png, strength=0.6, model=DEFAULT_MODEL, **extra):
    payload = {"prompt": prompt,
               "image_b64": base64.b64encode(init_png).decode("ascii"),
               "strength": float(strength)}
    payload.update(extra)
    return run(model, payload)[0]


def text_to_image(prompt, model=TEXT_TO_IMAGE, **extra):
    payload = {"prompt": prompt}
    payload.update(extra)
    return run(model, payload)[0]


def probe():
    """Check the credentials and each configured model, cheaply and loudly."""
    account, token = credentials()
    print("%s set (%d chars, ends ...%s)" % (ACCOUNT_ENV, len(account), account[-4:]))
    print("%s set (%d chars)" % (TOKEN_ENV, len(token)))

    config = json.loads((Path(__file__).with_name("config.json"))
                        .read_text(encoding="utf-8"))
    provider = config["providers"]["cloudflare"]
    tiny = None
    for entry in provider["models"]:
        model = entry["id"]
        try:
            payload = {"prompt": "a grey stone wall"}
            if "img2img" in model:
                if tiny is None:
                    from PIL import Image
                    import io
                    buffer = io.BytesIO()
                    Image.new("RGB", (64, 64), (90, 90, 96)).save(buffer, format="PNG")
                    tiny = buffer.getvalue()
                payload["image_b64"] = base64.b64encode(tiny).decode("ascii")
                payload["strength"] = 0.5
            body, kind = run(model, payload, account, token, timeout=180)
            size = len(body) if isinstance(body, (bytes, bytearray)) else -1
            print("  OK   %-52s %s %s bytes" % (model, kind, size))
        except Exception as error:                    # noqa: BLE001
            print("  FAIL %-52s %s" % (model, str(error)[:160]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--prompt")
    parser.add_argument("--init", type=Path)
    parser.add_argument("--strength", type=float, default=0.6)
    parser.add_argument("--model")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    if args.probe:
        probe()
        return
    if not args.prompt or not args.out:
        raise SystemExit("--probe, or --prompt with --out")

    if args.init:
        raw = image_to_image(args.prompt, args.init.read_bytes(), args.strength,
                             args.model or DEFAULT_MODEL)
    else:
        raw = text_to_image(args.prompt, args.model or TEXT_TO_IMAGE)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(raw)
    print("WORKERS AI OK %s (%d bytes)" % (args.out, len(raw)))


if __name__ == "__main__":
    main()
