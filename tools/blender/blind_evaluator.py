"""Blind Evaluation harness for Second Rite town scene attempts.

Uses external vision models (OpenAI GPT-4o and OpenRouter Gemini 2.5 Flash)
to perform neutral, blind evaluations of rendered visual gauntlet attempts.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
import requests

EVALUATION_PROMPT = """You are an expert art director and technical artist specializing in late-90s pre-rendered 3D RPG environments (e.g. Vagrant Story, Final Fantasy IX, SaGa Frontier 2, Xenogears) for a side-view 3D exploration scene in an indie retro RPG.

Evaluate the provided town scene image neutrally and objectively across the following 10 criteria on a scale of 1 to 10 (where 10 is outstanding/masterful and 1 is poor/unacceptable):

1. Immediate readability at native size (426x240): Are forms, paths, and volumes instantly identifiable without visual confusion?
2. Protagonist legibility: Is the main character stand-in clearly separated from the background and immediately located?
3. Composition intentionality: Is there strong framing, balanced massing, and deliberate focal flow?
4. Clarity of depth layers: Are foreground, midground (walkable street & shopfronts), and background layers distinct?
5. Usefulness of foreground occlusion: Does foreground geometry (arches, pillars, lanterns) enhance spatial depth without obstructing the walkable path?
6. "Expensive pre-rendered" feeling: Does it evoke the rich, atmospheric, painterly late-90s Square Enix CG aesthetic?
7. Viability of horizontal movement: Is the horizontal street traversal lane clear, plausible, and easy to navigate?
8. NPC staging / storytelling value: Are NPC stand-ins staged naturally with narrative tension/context (merchants, guards, citizens)?
9. Plausibility of compact coarse-geometry bake: Can this scene be baked onto lightweight geometry with 1 texture atlas without major visual degradation?
10. Distinctiveness / "this is Thestra": Does it possess atmospheric dark-fantasy medieval character rather than generic assets?

Respond ONLY with a valid JSON object in this exact schema:
{
  "scores": {
    "readability": <number 1-10>,
    "protagonist_legibility": <number 1-10>,
    "composition": <number 1-10>,
    "depth_layers": <number 1-10>,
    "foreground_occlusion": <number 1-10>,
    "pre_rendered_feel": <number 1-10>,
    "horizontal_movement": <number 1-10>,
    "npc_staging": <number 1-10>,
    "bake_plausibility": <number 1-10>,
    "distinctiveness": <number 1-10>
  },
  "total_score": <sum of 10 scores, max 100>,
  "key_strengths": ["<strength 1>", "<strength 2>"],
  "key_criticisms": ["<criticism 1>", "<criticism 2>"]
}
"""


def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def evaluate_openai(image_path: Path) -> dict:
    import openai
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    client = openai.OpenAI(api_key=api_key)
    base64_image = encode_image(image_path)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EVALUATION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=800,
        temperature=0.2
    )
    content = response.choices[0].message.content
    return json.loads(content)


def evaluate_openrouter(image_path: Path) -> dict:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set")
    base64_image = encode_image(image_path)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EVALUATION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 800,
        "temperature": 0.2
    }
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=25)
    if res.status_code != 200:
        raise RuntimeError(f"OpenRouter API error {res.status_code}: {res.text[:300]}")
    content = res.json()["choices"][0]["message"]["content"]
    # Strip markdown block if present
    if content.startswith("```json"):
        content = content[7:]
    if content.endswith("```"):
        content = content[:-3]
    return json.loads(content.strip())


def evaluate_attempt(attempt_id: str, image_path: Path) -> dict:
    print(f"[evaluator] Evaluating Attempt {attempt_id} ({image_path.name})...")
    res_openai = None
    res_openrouter = None
    
    try:
        res_openai = evaluate_openai(image_path)
        print(f"  - Evaluator A (GPT-4o) score: {res_openai.get('total_score')}/100")
    except Exception as e:
        print(f"  - Evaluator A error: {e}")

    try:
        res_openrouter = evaluate_openrouter(image_path)
        print(f"  - Evaluator B (Gemini 2.5 Flash) score: {res_openrouter.get('total_score')}/100")
    except Exception as e:
        print(f"  - Evaluator B error: {e}")

    # Combine scores
    scores_list = [r for r in (res_openai, res_openrouter) if r is not None]
    if not scores_list:
        raise RuntimeError(f"All evaluators failed for attempt {attempt_id}")

    avg_total = sum(r["total_score"] for r in scores_list) / len(scores_list)
    combined = {
        "attempt_id": attempt_id,
        "image_file": image_path.name,
        "evaluator_a": res_openai,
        "evaluator_b": res_openrouter,
        "average_total_score": round(avg_total, 1),
    }
    return combined


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Blind Evaluation of Town Attempts")
    parser.add_argument("images", nargs="+", help="Image paths to evaluate")
    parser.add_argument("--output", "-o", default="town_evaluation_results.json", help="Output results JSON")
    args = parser.parse_args()

    results = []
    for img_str in args.images:
        p = Path(img_str)
        attempt_id = p.stem.split("_")[-1]
        res = evaluate_attempt(attempt_id, p)
        results.append(res)

    results.sort(key=lambda x: x["average_total_score"], reverse=True)
    out_path = Path(args.output)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"[evaluator] Saved results for {len(results)} attempts to {out_path}")


if __name__ == "__main__":
    main()
