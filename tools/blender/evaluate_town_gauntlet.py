"""Blind-score town attempts 01-06 with two image-capable evaluators.

This script sends images only for critique/ranking. It never asks a model to
generate or alter art. If an endpoint is unavailable, the raw error is retained
and a deterministic local fallback is written so the gauntlet remains inspectable.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path

import requests


CRITERIA = [
    "immediate readability at native size",
    "protagonist legibility",
    "composition intentionality",
    "clarity of depth layers",
    "usefulness of foreground occlusion",
    "expensive late-90s pre-rendered feeling",
    "viability of horizontal movement",
    "NPC staging and storytelling value",
    "plausibility of a compact coarse-geometry bake",
    "distinctiveness / this is Thestra",
]


def image_data(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return "data:image/png;base64," + encoded


def prompt():
    criteria = "\n".join(f"{i + 1}. {value}" for i, value in enumerate(CRITERIA))
    return f"""You are a blind visual evaluator. Six neutral side-view town scene attempts are attached as A, B, C, D, E, and F. Do not infer authorship, preference, or iteration order; score only what is visible. These are native 426x240 previews for a compact Thestra town, with pixel-art walker stand-ins.\n\nScore every attempt from 1 to 10 on each criterion:\n{criteria}\n\nReturn strict JSON only, with this shape:\n{{\"attempts\":[{{\"label\":\"A\",\"scores\":{{\"readability\":0,\"protagonist\":0,\"intentionality\":0,\"depth\":0,\"occlusion\":0,\"pre_rendered\":0,\"movement\":0,\"npc_story\":0,\"bake\":0,\"thestra\":0}},\"total\":0,\"critique\":\"one compact sentence\"}}]}}\n\nUse integer scores. The total is the mean of the ten criteria. Mention concrete visible strengths and weaknesses in the critique."""


def parse_json(text: str):
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S | re.I)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError("evaluator did not return a JSON object")


def openai_eval(paths):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY missing")
    content = [{"type": "input_text", "text": prompt()}]
    for label, path in zip("ABCDEF", paths):
        content.append({"type": "input_text", "text": f"Attempt {label}"})
        content.append({"type": "input_image", "image_url": image_data(path)})
    payload = {
        "model": os.environ.get("TOWN_GAUNTLET_OPENAI_MODEL", "gpt-4.1-mini"),
        "input": [{"role": "user", "content": content}],
        "max_output_tokens": 4000,
        "temperature": 0.2,
    }
    response = requests.post(
        "https://api.openai.com/v1/responses", headers={"Authorization": f"Bearer {key}"},
        json=payload, timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    texts = []
    for item in data.get("output", []):
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                texts.append(part.get("text", ""))
    return {"model": payload["model"], "raw": "\n".join(texts), "parsed": parse_json("\n".join(texts))}


def openrouter_eval(paths):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    content = [{"type": "text", "text": prompt()}]
    for label, path in zip("ABCDEF", paths):
        content.append({"type": "text", "text": f"Attempt {label}"})
        content.append({"type": "image_url", "image_url": {"url": image_data(path)}})
    model = os.environ.get("TOWN_GAUNTLET_OPENROUTER_MODEL", "openai/gpt-4o-mini")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/JosephSerUSP/Second-Rite"},
        json={"model": model, "messages": [{"role": "user", "content": content}],
              "max_tokens": 4000, "temperature": 0.2}, timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    raw = data["choices"][0]["message"]["content"]
    return {"model": model, "raw": raw, "parsed": parse_json(raw)}


def local_fallback(paths):
    # The fallback is explicitly a non-blind machine heuristic, retained only
    # when external evaluators are unreachable. It rewards visible structure,
    # contrast and actor pixels, and is not presented as human judgment.
    from PIL import Image, ImageStat

    rows = []
    for label, path in zip("ABCDEF", paths):
        image = Image.open(path).convert("RGB")
        stat = ImageStat.Stat(image)
        mean = sum(stat.mean) / 3.0
        variance = sum(stat.var) / 3.0
        # actor colors are bright/yellow and occupy small but visible islands.
        pixels = list(image.getdata())
        actors = sum(1 for r, g, b in pixels if r > 110 and g > 75 and r > b * 1.35)
        actor_ratio = actors / len(pixels)
        base = max(1.0, min(10.0, 5.0 + (variance ** 0.5 - 45.0) / 22.0))
        protagonist = max(1.0, min(10.0, 4.0 + actor_ratio * 180.0))
        scores = {key: round(base, 2) for key in (
            "readability", "intentionality", "depth", "occlusion", "pre_rendered",
            "movement", "npc_story", "bake", "thestra")}
        scores["protagonist"] = round(protagonist, 2)
        total = sum(scores.values()) / 10.0
        rows.append({"label": label, "scores": scores, "total": round(total, 2),
                     "critique": "Fallback image statistics only; inspect the contact sheet before treating this as a verdict."})
    return {"model": "local-fallback-image-statistics", "raw": "", "parsed": {"attempts": rows}}


def main():
    root = Path(__file__).resolve().parents[2]
    render_dir = root / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "renders"
    output_path = render_dir.parent / "town-blind-evaluation.json"
    paths = [render_dir / f"attempt-{index:02d}.png" for index in range(1, 7)]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    results = {"criteria": CRITERIA, "labels": {label: index for index, label in enumerate("ABCDEF", 1)},
               "evaluators": [], "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for name, function in (("openai", openai_eval), ("openrouter", openrouter_eval)):
        try:
            result = function(paths)
            results["evaluators"].append({"name": name, **result})
            print(f"{name}: OK ({result['model']})")
        except Exception as exc:
            results["evaluators"].append({"name": name, "error": repr(exc)})
            print(f"{name}: unavailable: {exc}")
    if not any("parsed" in row for row in results["evaluators"]):
        fallback = local_fallback(paths)
        results["evaluators"].append({"name": "fallback", **fallback})
        print("fallback: used")
    output_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"BLIND EVALUATION OK: {output_path}")


if __name__ == "__main__":
    main()
