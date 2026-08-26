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
                     "openrouter/free")


def image_part(path: Path) -> dict:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image_url",
            "image_url": {"url": "data:image/png;base64," + data}}


def build_content(images, context: str) -> list:
    """The one prompt both providers see. Built once so a difference in the
    replies is a difference between the MODELS, not between two call sites."""
    roll = "\n".join(f"Image {chr(65 + i)} is {label}."
                     for i, (label, _) in enumerate(images))
    text = RUBRIC + ("\n\n" + context if context else "") + "\n\n" + roll
    parts = [{"type": "text", "text": text}]
    parts.extend(image_part(path) for _, path in images)
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


def call_openai(content: list) -> dict:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return {"provider": "openai", "skipped": "OPENAI_API_KEY is not set"}
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        json={"model": "gpt-4o-mini",
              "messages": [{"role": "user", "content": content}],
              "temperature": 0.6, "max_tokens": 1200},
        timeout=120,
    )
    if not response.ok:
        return {"provider": "openai", "status": response.status_code,
                "error": response.text[:500]}
    payload = response.json()
    message = payload.get("choices", [{}])[0].get("message", {})
    return {"provider": "openai", "model": payload.get("model"),
            "usage": payload.get("usage"), "reply": _reply_text(message)}


def call_openrouter(content: list) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return {"provider": "openrouter",
                "skipped": "OPENROUTER_API_KEY is not set"}
    headers = {"Authorization": f"Bearer {key}",
               "Content-Type": "application/json"}
    failures = []
    for model in OPENROUTER_MODELS:
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
    args = parser.parse_args()

    global RUBRIC
    if args.rubric:
        RUBRIC = args.rubric.read_text(encoding="utf-8")
    context = args.context.read_text(encoding="utf-8") if args.context else ""

    content = build_content(args.image, context)
    result = {
        "rubric": RUBRIC,
        "context": context,
        "evidence": {label: str(path) for label, path in args.image},
        "reviews": [call_openai(content), call_openrouter(content)],
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
