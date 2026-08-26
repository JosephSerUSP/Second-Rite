"""Adversarial visual review for the St. Maria shop authoring pass.

This is deliberately a small, provider-agnostic review harness rather than a
second authoring path. It sends the same rendered evidence and the same rubric
to OpenAI and OpenRouter, preserving raw replies and model provenance. Keys are
read only from OPENAI_API_KEY and OPENROUTER_API_KEY.

    python tools/blender/town_shop_critique.py \
        --bakery out/alicias-padaria-256.png \
        --smith out/lauras-smith-256.png \
        --out out/st-maria-shop-critiques.json
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path

import requests


RUBRIC = """You are an adversarial art director reviewing two native 256x240
side-view Blender renders for a colonial Portuguese town in a first-person
dungeon RPG. Score each 0-10, then compare them head-to-head. Be specific and
uncomfortable: identify anything that reads as generic boxes, a dark unreadable
silhouette, a floating prop, a missing causal light, or a set edge. Check:
1) instant place identity and colonial Portuguese vocabulary; 2) spatial depth
and foreground/action/background separation; 3) readable hero workflow; 4)
character-specific meaning from the supplied story; 5) native-size contrast and
material hierarchy; 6) lighting motivation and black-backdrop discipline.
Do not reward intent that is not visible. End with one winner and the three
highest-leverage changes for the next pass. Return concise markdown."""

STORY_CONTEXT = """Story constraints the art must visibly support:
- Alicia sells baked goods, staples and summoner supplies; she reminds people
  to drink water, bakes Laura's bread/cheese/bruised-pear lunch, and hides a
  summon lantern under the counter during the Vigil.
- Laura sells equipment and repairs lantern frames; Alicia's lunch waits in
  her forge, and the forge can be cold during the Vigil while she works on
  lantern frames for the chapel.
"""


def image_part(path: Path) -> dict:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": "data:image/png;base64," + data}}


def call_openai(bakery: Path, smith: Path) -> dict:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return {"provider": "openai", "error": "OPENAI_API_KEY is not set"}
        content = [{"type": "text", "text": RUBRIC + "\n" + STORY_CONTEXT +
                "\nImage A is Alicia's Padaria. Image B is Laura's smith."},
               image_part(bakery), image_part(smith)]
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "gpt-4o-mini",
              "messages": [{"role": "user", "content": content}],
              "temperature": 0.6, "max_tokens": 1200},
        timeout=120,
    )
    if not response.ok:
        return {"provider": "openai", "status": response.status_code,
                "error": response.text[:500]}
    payload = response.json()
    return {"provider": "openai", "model": payload.get("model"),
            "usage": payload.get("usage"),
            "reply": payload.get("choices", [{}])[0].get("message", {}).get("content", "")}


def call_openrouter(bakery: Path, smith: Path) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return {"provider": "openrouter", "error": "OPENROUTER_API_KEY is not set"}
        content = [{"type": "text", "text": RUBRIC + "\n" + STORY_CONTEXT +
                "\nImage A is Alicia's Padaria. Image B is Laura's smith."},
               image_part(bakery), image_part(smith)]
    headers = {"Authorization": f"Bearer {key}",
               "Content-Type": "application/json",
               "HTTP-Referer": "https://github.com/openai/codex"}
    # Free vision pools are shared and can rate-limit one model while another
    # is available. Try a short, recorded fallback list rather than silently
    # converting this into a paid call.
    models = ["google/gemma-4-31b-it:free", "google/gemma-4-26b-a4b-it:free",
              "dots-studio/dots-3-note-preview:free", "openrouter/free"]
    failures = []
    for model in models:
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
        body = message.get("content", "")
        if isinstance(body, list):
            body = "\n".join(part.get("text", "") for part in body
                              if isinstance(part, dict))
        # Some free reasoning models place the useful review in the reasoning
        # field and leave content null; preserve that text instead of reporting
        # a misleadingly empty successful review.
        if not body:
            body = message.get("reasoning", "")
        return {"provider": "openrouter", "model": payload.get("model", model),
                "attempts": failures, "usage": payload.get("usage"),
                "reply": body}
    return {"provider": "openrouter", "attempts": failures,
            "error": "all configured free vision models were unavailable"}


def main() -> None:
    parser = argparse.ArgumentParser(prog="town_shop_critique")
    parser.add_argument("--bakery", type=Path, required=True)
    parser.add_argument("--smith", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.bakery, args.smith):
        if not path.is_file():
            raise SystemExit(f"missing render: {path}")
    result = {
        "rubric": RUBRIC,
        "storyContext": STORY_CONTEXT,
        "evidence": {"bakery": str(args.bakery), "smith": str(args.smith)},
        "reviews": [call_openai(args.bakery, args.smith),
                    call_openrouter(args.bakery, args.smith)],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for review in result["reviews"]:
        print(f"[{review['provider']}] model={review.get('model', '?')}")
        if review.get("error"):
            print(f"ERROR: {review['error']}")
        else:
            print(review.get("reply", ""))
        print()


if __name__ == "__main__":
    main()
