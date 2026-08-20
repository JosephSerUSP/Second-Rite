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

EVALUATION_PROMPT = """You are an expert art director and technical artist specializing in late-1990s / early-2000s pre-rendered 3D RPG environments (e.g. Vagrant Story, Final Fantasy IX, SaGa Frontier 2, Xenogears, Resident Evil) for a side-view 3D town exploration scene in an indie retro RPG at native 426x240 resolution with a ~43mm level camera.

Evaluate the provided town scene image neutrally and objectively across the following 15 criteria on a scale of 1 to 10 (where 10 is outstanding/masterful and 1 is poor/unacceptable):

1. readability: Reads immediately at native 426x240 resolution without visual confusion
2. protagonist_legibility: Main character stand-in is clearly separated from background and immediately located
3. npc_staging: NPC stand-ins staged naturally with narrative context/life
4. sideview_composition: Strong theatrical side-view composition and focal balance
5. architectural_depth: Believable spatial depth, facade rhythm, and volume layering
6. foreground_framing: Foreground occluders enhance depth without obstructing traversal
7. material_richness: Tactile, varied, believable surface materials (masonry, plaster, wood, roof, iron)
8. texture_scale: Consistent and believable real-world texture scale across elements
9. procedural_naturalism: Avoidance of obvious flat procedural repetition or artificial CG perfection
10. surface_age: Believable weathering, age, grime, and lived-in history
11. prerendered_feel: Expensive late-90s Square Enix pre-rendered CG aesthetic
12. coherent_lighting: Coherent lighting (warm interior/lantern glow, cool ambient fill, rim light)
13. horizontal_traversal: Clear, readable horizontal walking lane across the frame
14. distinctiveness: Unique dark-fantasy medieval character ("Thestra") rather than generic assets
15. bake_plausibility: Plausibility of collapsing rich source detail onto lightweight TH_RENDER geometry with 1 baked atlas

Also provide specific qualitative answers:
- fake_surfaces: Which surfaces look fake or synthetic?
- flat_surfaces: Which surfaces look flat or lack depth/shadows?
- busy_surfaces: Which surfaces are overly noisy or busy?
- disappearing_details: Which small details will disappear at 426x240 native game size?
- best_material_strategy: Which material strategy appears most successful in this composition (Procedural, Scanned PBR, AI-generated source, or Hybrid)?

Respond ONLY with a valid JSON object in this exact schema:
{
  "scores": {
    "readability": <1-10>,
    "protagonist_legibility": <1-10>,
    "npc_staging": <1-10>,
    "sideview_composition": <1-10>,
    "architectural_depth": <1-10>,
    "foreground_framing": <1-10>,
    "material_richness": <1-10>,
    "texture_scale": <1-10>,
    "procedural_naturalism": <1-10>,
    "surface_age": <1-10>,
    "prerendered_feel": <1-10>,
    "coherent_lighting": <1-10>,
    "horizontal_traversal": <1-10>,
    "distinctiveness": <1-10>,
    "bake_plausibility": <1-10>
  },
  "total_score": <sum of 15 scores, max 150>,
  "percentage_score": <total_score / 150 * 100 rounded to 1 decimal place>,
  "qualitative_critique": {
    "fake_surfaces": "<specific surfaces or 'none'>",
    "flat_surfaces": "<specific surfaces or 'none'>",
    "busy_surfaces": "<specific surfaces or 'none'>",
    "disappearing_details": "<specific details or 'none'>",
    "best_material_strategy": "<Procedural / Public CC0 / AI Source / Hybrid>"
  },
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
        max_tokens=1000,
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
        "model": "google/gemini-3.7-flash",
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
        "max_tokens": 1000,
        "temperature": 0.2
    }
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
    if res.status_code != 200:
        raise RuntimeError(f"OpenRouter API error {res.status_code}: {res.text[:300]}")
    content = res.json()["choices"][0]["message"]["content"]
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
        print(f"  - Evaluator A (GPT-4o) score: {res_openai.get('total_score')}/150 ({res_openai.get('percentage_score')}%)")
    except Exception as e:
        print(f"  - Evaluator A error: {e}")

    try:
        res_openrouter = evaluate_openrouter(image_path)
        print(f"  - Evaluator B (Gemini 3.7 Flash) score: {res_openrouter.get('total_score')}/150 ({res_openrouter.get('percentage_score')}%)")
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
