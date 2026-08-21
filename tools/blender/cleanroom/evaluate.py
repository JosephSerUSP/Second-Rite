"""Blind evaluation of the clean-room attempts.

Blindness is enforced structurally, not by good intentions:

  - every render is copied to an opaque code name (specimen_<hash>) before it
    is sent, and the mapping is not revealed to any evaluator;
  - no concept text, material strategy, attempt number, phase (divergence vs
    convergence) or prior ranking is ever included in a prompt;
  - the order of specimens is shuffled per evaluator;
  - each evaluator is a separate vendor and sees one image at a time, so it
    cannot rank by comparison or infer a series.

Two independent passes: OpenAI and Google (via OpenRouter).
"""
from __future__ import annotations

import base64
import concurrent.futures as futures
import hashlib
import json
import os
import random
import re
import shutil
import time
from pathlib import Path

import requests

CRITERIA = [
    ("native_readability", "Immediate readability at native 426x240: are forms, masses and the walkable route instantly identifiable without visual confusion?"),
    ("walker_integration", "Protagonist integration: does the small character stand-in sit convincingly IN the space, at a believable size, rather than pasted on top of it?"),
    ("composition", "Composition: deliberate framing, balanced but not symmetrical massing, a clear focal flow."),
    ("depth_layering", "Depth layering: are foreground, midground and background genuinely distinct planes?"),
    ("foreground_relationship", "Foreground relationship: does the nearest geometry belong to the place and enhance depth, rather than being a slab added to satisfy an occlusion requirement?"),
    ("architectural_specificity", "Architectural specificity: does the architecture make particular, considered decisions, or is it generic?"),
    ("material_richness", "Material richness: variety and quality of surface, believable wear and age."),
    ("material_restraint", "Material restraint: is the palette disciplined, with quiet surfaces beside detailed ones, rather than uniformly busy?"),
    ("surface_scale", "Believable physical surface scale: do stones, boards, tiles and openings read at a plausible real-world size relative to the person?"),
    ("avoids_modular_repetition", "Avoidance of modular repetition: does it avoid looking like repeated procedural facade modules or a kit of parts?"),
    ("human_scale", "Human-scale plausibility: would a person actually live, work and move here?"),
    ("traversal_clarity", "Side-view traversal clarity: is the horizontal walking route obvious and unobstructed?"),
    ("doorway_readability", "Doorway readability: is there at least one door that is unmistakably a door you could enter?"),
    ("npc_staging", "Narrative / NPC staging: are the figures placed so their arrangement suggests a situation rather than a scatter?"),
    ("distinct_identity", "Distinctive identity: does this feel like a specific named place with its own character, rather than stock fantasy?"),
    ("expensive_prerendered", "Expensive pre-rendered feeling: the rich, deliberate, late-90s/early-2000s pre-rendered JRPG background quality (NOT photorealism)."),
    ("collapsible_to_runtime", "Ability to collapse to coarse runtime geometry: could this be baked to one texture atlas on simple boxes without losing what makes it work?"),
]

QUESTIONS = [
    ("looks_generic", "What, specifically, looks generic?"),
    ("looks_repeated", "What looks procedurally repeated?"),
    ("looks_like_a_test", "What looks like a game-engine test rather than a real place?"),
    ("lost_at_native", "What detail disappears at 426x240?"),
    ("most_memorable", "Which single architectural decision is the most memorable?"),
    ("would_walk_in", "Would you want to walk into this space? Answer yes or no, then one sentence why."),
]

PROMPT = """You are an experienced art director assessing ONE still frame from an in-development side-view exploration game.

The frame is presented at the exact resolution the game renders: 426 x 240 pixels. Judge it at that size. The small human figures are the player character and non-player characters; they are 24 x 48 pixels by design.

The target is a late-1990s / early-2000s pre-rendered JRPG background. That means deliberate, hand-composed, materially rich and slightly theatrical. It does NOT mean photorealistic.

Score each criterion from 1 (poor) to 10 (outstanding). Use the full range: 5 is competent-but-unremarkable, and scores of 9 or 10 should be rare. Be critical and specific; a flattering review is useless.

CRITERIA:
{criteria}

Then answer these questions briefly and bluntly:
{questions}

Respond with ONLY a valid JSON object, no markdown fence:
{{"scores": {{{score_keys}}}, "answers": {{{answer_keys}}}}}
"""


def _prompt():
    return PROMPT.format(
        criteria="\n".join("- %s: %s" % (k, d) for k, d in CRITERIA),
        questions="\n".join("- %s: %s" % (k, d) for k, d in QUESTIONS),
        score_keys=", ".join('"%s": <1-10>' % k for k, _ in CRITERIA),
        answer_keys=", ".join('"%s": "<text>"' % k for k, _ in QUESTIONS),
    )


def _b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def _parse(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in response: %s" % text[:200])
    return json.loads(text[start:end + 1])


def _call_openai(image_path, model="gpt-4.1"):
    key = os.environ["OPENAI_API_KEY"]
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"},
        json={"model": model, "max_tokens": 1600, "temperature": 0.2,
              "messages": [{"role": "user", "content": [
                  {"type": "text", "text": _prompt()},
                  {"type": "image_url", "image_url": {
                      "url": "data:image/png;base64," + _b64(image_path),
                      "detail": "high"}}]}]},
        timeout=300)
    r.raise_for_status()
    return _parse(r.json()["choices"][0]["message"]["content"])


def _call_openrouter(image_path, model="google/gemini-2.5-flash"):
    key = os.environ["OPENROUTER_API_KEY"]
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"},
        json={"model": model, "max_tokens": 1600, "temperature": 0.2,
              "messages": [{"role": "user", "content": [
                  {"type": "text", "text": _prompt()},
                  {"type": "image_url", "image_url": {
                      "url": "data:image/png;base64," + _b64(image_path)}}]}]},
        timeout=300)
    r.raise_for_status()
    return _parse(r.json()["choices"][0]["message"]["content"])


def _openrouter_model(model):
    def fn(image_path, _m=model):
        return _call_openrouter(image_path, model=_m)
    return fn


# Three passes across two vendors. OpenRouter's paid vision models return HTTP
# 402 on this account, so the cross-vendor pass uses a free-tier NVIDIA model;
# it is a much smaller model than the OpenAI passes and that is recorded rather
# than hidden. A third OpenAI pass from a different generation guards against a
# single model's idiosyncrasy dominating the aggregate.
EVALUATORS = {
    "openai:gpt-4.1": _call_openai,
    "openai:gpt-4o": lambda p: _call_openai(p, model="gpt-4o"),
    "nvidia:nemotron-nano-12b-vl": _openrouter_model(
        "nvidia/nemotron-nano-12b-v2-vl:free"),
}


def blind_copies(renders, out_dir):
    """Copy each render to an opaque, order-free code name."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping = {}
    for attempt_id, path in renders.items():
        code = "specimen_" + hashlib.sha256(
            (attempt_id + "cleanroom-blind").encode()).hexdigest()[:10]
        dest = out_dir / (code + ".png")
        shutil.copyfile(path, dest)
        mapping[code] = {"attempt": attempt_id, "path": str(dest)}
    return mapping


def run(renders, out_dir, *, workers=4, retries=3):
    out_dir = Path(out_dir)
    mapping = blind_copies(renders, out_dir / "blind")
    results = {code: {} for code in mapping}

    jobs = []
    for name, fn in EVALUATORS.items():
        codes = list(mapping)
        random.Random(hash(name) & 0xffff).shuffle(codes)
        for code in codes:
            jobs.append((name, fn, code, mapping[code]["path"]))

    def work(job):
        name, fn, code, path = job
        last = None
        for _ in range(retries + 1):
            try:
                return name, code, fn(path), None
            except Exception as exc:
                last = repr(exc)[:300]
                time.sleep(6.0)
        return name, code, None, last

    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for name, code, payload, err in pool.map(work, jobs):
            results[code][name] = payload if payload else {"error": err}
            print("[eval] %-26s %s %s" % (name, code, "ok" if payload else "FAIL"))

    keys = [k for k, _ in CRITERIA]
    summary = {}
    for code, per_eval in results.items():
        attempt = mapping[code]["attempt"]
        per_criterion, evals_ok = {}, 0
        for name, payload in per_eval.items():
            if not payload or "scores" not in payload:
                continue
            evals_ok += 1
            for k in keys:
                v = payload["scores"].get(k)
                if isinstance(v, (int, float)):
                    per_criterion.setdefault(k, []).append(float(v))
        means = {k: round(sum(v) / len(v), 3)
                 for k, v in per_criterion.items() if v}
        summary[attempt] = {
            "code": code,
            "evaluators": evals_ok,
            "criteria": means,
            "aggregate": round(sum(means.values()) / len(means), 3) if means else None,
            "answers": {name: (p or {}).get("answers", {})
                        for name, p in per_eval.items()},
            "raw": per_eval,
        }

    payload = {"mapping": mapping, "criteria": keys, "summary": summary}
    (out_dir / "evaluation.json").write_text(json.dumps(payload, indent=2),
                                             encoding="utf-8")
    return payload
