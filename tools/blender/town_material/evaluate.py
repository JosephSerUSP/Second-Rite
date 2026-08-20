"""Phase 4: blind visual evaluation of the town attempts.

Two independent evaluators (OpenAI and OpenRouter) score each attempt on the
fifteen criteria and answer the four diagnostic questions. Attempts are shown
under neutral labels with no material-strategy hint, so the evaluator cannot
score the technique instead of the picture.

Evaluators inspect and critique. They never generate scene art.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import random
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "projects/hichaukitoden-game/assets/authoring/town/attempts_next"

CRITERIA = [
    "reads_immediately_at_426x240", "protagonist_legibility", "npc_legibility_and_staging",
    "side_view_composition", "architectural_depth", "foreground_framing",
    "material_richness", "texture_scale_consistency", "avoids_procedural_repetition",
    "believable_surface_age", "late90s_prerendered_feeling", "coherent_lighting",
    "horizontal_traversal_clarity", "distinctiveness", "collapsible_to_cheap_geometry",
]

PROMPT = """You are judging concept frames for a late-1990s / early-2000s pre-rendered
JRPG town, presented as a fixed side-on view at a native 426x240 resolution.
The player walks left and right through this space. The small figures are the
protagonist and NPC stand-ins at their true in-game pixel size.

Judge the IMAGE ONLY. Do not guess how it was made.

Score each criterion from 1 (bad) to 10 (excellent):
%s

Then answer these, concretely and specifically, naming actual surfaces:
- surfaces_that_look_fake
- surfaces_that_look_flat
- surfaces_that_are_too_busy
- details_that_will_disappear_at_game_size
- single_biggest_weakness
- single_biggest_strength

Reply with ONLY a JSON object:
{"scores": {"criterion": int, ...}, "surfaces_that_look_fake": "...",
 "surfaces_that_look_flat": "...", "surfaces_that_are_too_busy": "...",
 "details_that_will_disappear_at_game_size": "...",
 "single_biggest_weakness": "...", "single_biggest_strength": "..."}""" % (
    "\n".join("- " + c for c in CRITERIA))


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


def _post(url, payload, key):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as fh:
        return json.loads(fh.read().decode())


def _parse(text):
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        t = t[4:] if t.startswith("json") else t
    a, b = t.find("{"), t.rfind("}")
    return json.loads(t[a:b + 1])


def ask_openai(png: Path, model="gpt-5"):
    payload = {"model": model, "messages": [{"role": "user", "content": [
        {"type": "text", "text": PROMPT},
        {"type": "image_url",
         "image_url": {"url": "data:image/png;base64," + b64(png)}}]}]}
    r = _post("https://api.openai.com/v1/chat/completions", payload,
              os.environ["OPENAI_API_KEY"])
    return _parse(r["choices"][0]["message"]["content"])


def ask_openrouter(png: Path, model="google/gemini-2.5-pro"):
    payload = {"model": model, "messages": [{"role": "user", "content": [
        {"type": "text", "text": PROMPT},
        {"type": "image_url",
         "image_url": {"url": "data:image/png;base64," + b64(png)}}]}]}
    r = _post("https://openrouter.ai/api/v1/chat/completions", payload,
              os.environ["OPENROUTER_API_KEY"])
    return _parse(r["choices"][0]["message"]["content"])


def ask_openai_41(png: Path):
    return ask_openai(png, model="gpt-4.1")


# OPENROUTER_API_KEY is present but the account returns HTTP 402 Payment
# Required, so the second evaluator is a different OpenAI model generation
# rather than a second vendor. Independence is weaker than cross-vendor and
# that is recorded in the report.
EVALUATORS = {"openai:gpt-5": ask_openai, "openai:gpt-4.1": ask_openai_41}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attempts", nargs="*", default=None)
    ap.add_argument("--out", type=Path, default=SRC / "evaluation.json")
    args = ap.parse_args()

    ids = args.attempts or sorted(
        p.stem.split("_")[1] for p in SRC.glob("attempt_??.png"))
    # blind: shuffle presentation order and hide the attempt id from the model
    order = list(ids)
    random.Random(20260820).shuffle(order)

    raw, by_attempt = {}, {}
    for aid in order:
        png = SRC / ("attempt_%s.png" % aid)
        raw[aid] = {}
        for name, fn in EVALUATORS.items():
            try:
                raw[aid][name] = fn(png)
                sc = raw[aid][name]["scores"]
                print("  %s  %-28s mean %.2f" % (aid, name,
                      sum(sc.values()) / len(sc)))
            except Exception as exc:
                raw[aid][name] = {"error": "%s: %s" % (type(exc).__name__, exc)}
                print("  %s  %-28s FAILED %s" % (aid, name, exc))

    for aid, evs in raw.items():
        means, per = [], {}
        for c in CRITERIA:
            vals = [e["scores"][c] for e in evs.values()
                    if "scores" in e and c in e["scores"]]
            if vals:
                per[c] = sum(vals) / len(vals)
                means.append(per[c])
        by_attempt[aid] = {"mean": sum(means) / len(means) if means else None,
                           "perCriterion": per,
                           "evaluators": list(evs)}

    args.out.write_text(json.dumps(
        {"presentationOrder": order, "criteria": CRITERIA,
         "byAttempt": by_attempt, "raw": raw}, indent=2), encoding="utf-8")
    print("\nRanking:")
    for aid, v in sorted(by_attempt.items(),
                         key=lambda kv: kv[1]["mean"] or 0, reverse=True):
        print("  %s  %.2f" % (aid, v["mean"] or 0))
    print("EVALUATION_OK -> %s" % args.out)


if __name__ == "__main__":
    main()
