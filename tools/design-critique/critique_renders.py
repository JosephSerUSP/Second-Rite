"""Adversarial visual review of authored renders.

Deliberately a small, provider-agnostic review harness rather than a second
authoring path. It sends the SAME rendered evidence and the SAME rubric to
OpenAI and OpenRouter and preserves the raw replies with model provenance, so
a critique is reproducible and attributable rather than remembered.

Two things this harness has already been wrong about, kept as guard rails:

- **Judge the picture, not the pitch.** An earlier version scored written
  proposals instead of renders and rewarded intent nobody could see. Every
  review here is anchored to an image on disk.
- **A review is evidence, not a gate.** It has no authority to reject a pass.
  If a score should be able to send work back, that belongs in a gate script
  with a threshold -- not here. Say so out loud rather than letting a 6/10
  land unremarked.

    python tools/design-critique/critique_renders.py \\
        --image "Alicia's Padaria=out/alicias-padaria-256.png" \\
        --image "Laura's smith=out/lauras-smith-256.png" \\
        --context docs/design/st-maria-shop-briefs.md \\
        --out out/critique.json

Keys are read only from OPENAI_API_KEY and OPENROUTER_API_KEY. A provider with
no key is recorded as skipped, not silently dropped.

Two more things learned by running it:

- **A weak judge invents the roll.** The first round here was reviewed by
  gpt-4o-mini, which reported "Image B: Laura's smith" in a contest whose three
  images were all the Padaria. Its complaints were still useful and still
  agreed with the other judge -- but its VERDICT was worthless, because it was
  not looking at what it said it was. Pick a model that can read a 256px frame,
  and treat a review that misnames the roll as void.
- **Native size is the authority, legibility is not the same question.**
  A 256x240 frame is below what a vision model resolves, so images are sent
  point-upscaled by `--scale` (nearest neighbour, default 3). Not one pixel of
  judgement is changed by this -- the same pixels arrive, larger -- but a
  reviewer that cannot see the counter cannot tell you anything about it. The
  scale used is recorded with the review.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path

import requests


RUBRIC = """You are an adversarial art director reviewing native 256x240
side-view Blender renders for a colonial Portuguese town in a first-person
dungeon RPG. Score each 0-10, then compare them head-to-head. Be specific and
uncomfortable: identify anything that reads as generic boxes, a dark unreadable
silhouette, a floating prop, a missing causal light, or a set edge. Check:
1) instant place identity and colonial Portuguese vocabulary; 2) spatial depth
and foreground/action/background separation; 3) readable hero workflow; 4)
character-specific meaning from the supplied context; 5) native-size contrast
and material hierarchy; 6) lighting motivation and black-backdrop discipline.
Do not reward intent that is not visible. If two images differ only in which
props stand against the back wall, say so plainly -- that is the failure this
review exists to catch. End with one winner and the three highest-leverage
changes for the next pass. Return concise markdown."""

# Free vision pools are shared and rate-limit one model while another is up.
# Try a short RECORDED fallback list rather than silently escalating to a paid
# call: which model actually answered is part of the provenance.
OPENROUTER_MODELS = ("google/gemma-4-31b-it:free",
                     "google/gemma-4-26b-a4b-it:free",
                     "dots-studio/dots-3-note-preview:free",
                     "minimax/minimax-m3:free",
                     "openrouter/free")

# One judge agreeing with itself is not a panel. `--panel N` asks this many
# free models INDEPENDENTLY and keeps every reply, so a verdict two unrelated
# models reach separately can be told apart from one model's opinion.
DEFAULT_PANEL = 1

# gpt-5 and later reject `temperature` and renamed the token budget. Kept as a
# rule rather than a per-model table so a newer id does not silently 400.
def _openai_body(model, content, budget=1600):
    body = {"model": model, "messages": [{"role": "user", "content": content}]}
    if model.startswith(("gpt-5", "o1", "o3", "o4")):
        body["max_completion_tokens"] = budget
    else:
        body["max_tokens"] = budget
        body["temperature"] = 0.6
    return body


def image_part(path: Path, scale: int = 1) -> dict:
    """The render, optionally point-upscaled so a reviewer can resolve it.

    Nearest neighbour and an integer factor, so every source pixel becomes an
    exact block: the picture being judged is still the authored 256x240 frame,
    not a resampled interpretation of it.
    """
    data = path.read_bytes()
    if scale > 1:
        from PIL import Image
        import io as _io

        image = Image.open(_io.BytesIO(data))
        image = image.resize((image.width * scale, image.height * scale),
                             Image.NEAREST)
        buffer = _io.BytesIO()
        image.save(buffer, format="PNG")
        data = buffer.getvalue()
    return {"type": "image_url",
            "image_url": {"url": "data:image/png;base64,"
                                 + base64.b64encode(data).decode("ascii")}}


def build_content(images, context: str, scale: int = 1) -> list:
    """The one prompt both providers see. Built once so a difference in the
    replies is a difference between the MODELS, not between two call sites."""
    roll = "\n".join(f"Image {chr(65 + i)} is {label}."
                     for i, (label, _) in enumerate(images))
    text = RUBRIC + ("\n\n" + context if context else "") + "\n\n" + roll
    parts = [{"type": "text", "text": text}]
    parts.extend(image_part(path, scale) for _, path in images)
    return parts


def _reply_text(message: dict) -> str:
    body = message.get("content", "")
    if isinstance(body, list):
        body = "\n".join(part.get("text", "") for part in body
                         if isinstance(part, dict))
    # Some free reasoning models put the useful review in `reasoning` and leave
    # content null. Preserve that rather than reporting a misleadingly empty
    # successful review -- and note it, because raw reasoning is not a review.
    if not body:
        body = message.get("reasoning", "")
        if body:
            return "[model returned reasoning, not a formatted review]\n" + body
    return body


def call_openai(content: list, model: str = "gpt-4o-mini") -> dict:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return {"provider": "openai", "skipped": "OPENAI_API_KEY is not set"}
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        json=_openai_body(model, content),
        timeout=300,
    )
    if not response.ok:
        return {"provider": "openai", "status": response.status_code,
                "error": response.text[:500]}
    payload = response.json()
    message = payload.get("choices", [{}])[0].get("message", {})
    return {"provider": "openai", "model": payload.get("model"),
            "usage": payload.get("usage"), "reply": _reply_text(message)}


def call_openrouter_panel(content: list, panel: int) -> list:
    """Ask `panel` different free models the same question, independently."""
    reviews, used = [], 0
    for model in OPENROUTER_MODELS:
        if used >= panel:
            break
        review = call_openrouter(content, only=model)
        reviews.append(review)
        if review.get("reply"):
            used += 1
    return reviews


def call_openrouter(content: list, only=None) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return {"provider": "openrouter",
                "skipped": "OPENROUTER_API_KEY is not set"}
    headers = {"Authorization": f"Bearer {key}",
               "Content-Type": "application/json"}
    failures = []
    for model in ((only,) if only else OPENROUTER_MODELS):
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions", headers=headers,
            json={"model": model,
                  "messages": [{"role": "user", "content": content}],
                  "temperature": 0.6, "max_tokens": 1200}, timeout=120,
        )
        if not response.ok:
            failures.append({"model": model, "status": response.status_code,
                             "error": response.text[:500]})
            if response.status_code in (429, 500, 502, 503, 504):
                continue
            return {"provider": "openrouter", "attempts": failures}
        payload = response.json()
        message = payload.get("choices", [{}])[0].get("message", {})
        return {"provider": "openrouter",
                "model": payload.get("model", model), "attempts": failures,
                "usage": payload.get("usage"), "reply": _reply_text(message)}
    return {"provider": "openrouter", "attempts": failures,
            "error": "all configured free vision models were unavailable"}


def parse_image(value: str):
    label, sep, raw = value.partition("=")
    if not sep:
        raise argparse.ArgumentTypeError(
            f"--image wants LABEL=path, got {value!r}")
    path = Path(raw)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"missing render: {path}")
    return label, path


def main() -> None:
    parser = argparse.ArgumentParser(prog="critique_renders")
    parser.add_argument("--image", type=parse_image, action="append",
                        required=True, metavar="LABEL=PATH",
                        help="a render to review; repeatable")
    parser.add_argument("--context", type=Path,
                        help="text file of story/design constraints the art "
                             "must visibly support")
    parser.add_argument("--rubric", type=Path,
                        help="override the built-in rubric")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--openai-model", default="gpt-4o-mini",
                        help="a model that can actually resolve a 256px "
                             "frame; a review that misnames the roll is void")
    parser.add_argument("--panel", type=int, default=DEFAULT_PANEL,
                        help="how many free OpenRouter models to ask "
                             "independently")
    parser.add_argument("--scale", type=int, default=3,
                        help="point-upscale factor for the images sent; the "
                             "pixels judged are unchanged")
    args = parser.parse_args()

    global RUBRIC
    if args.rubric:
        RUBRIC = args.rubric.read_text(encoding="utf-8")
    context = args.context.read_text(encoding="utf-8") if args.context else ""

    content = build_content(args.image, context, args.scale)
    result = {
        "rubric": RUBRIC,
        "context": context,
        "scale": args.scale,
        "evidence": {label: str(path) for label, path in args.image},
        "reviews": ([call_openai(content, args.openai_model)]
                    + call_openrouter_panel(content, args.panel)),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    for review in result["reviews"]:
        print(f"[{review['provider']}] model={review.get('model', '?')}")
        for key in ("skipped", "error"):
            if review.get(key):
                print(f"{key.upper()}: {review[key]}")
        if review.get("reply"):
            print(review["reply"])
        print()
    print(f"wrote {args.out}")
    print("This is evidence, not a gate: a low score here does not stop a "
          "pass from landing. Read it before you land one.")


if __name__ == "__main__":
    main()
