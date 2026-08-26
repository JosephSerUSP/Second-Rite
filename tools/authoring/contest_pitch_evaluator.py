"""Multi-model contest pitching and adversarial critique tool for St. Maria interiors.

Queries OpenRouter (active free tier models) and OpenAI APIs to:
1. Pitch diverse architectural compositions for Alicia's Padaria and Laura's Smithy.
2. Critique each proposal adversarially against docs/design/st-maria-interior-authoring.md rules:
   - Colonial Portuguese vocabulary (whitewash, azulejo dado, dark hardwood, terracotta, wrought iron).
   - Fixed camera contract (Classic 256x240, free 256x144 area, Y=144 floor limit, level lens).
   - Single-axis rule (spend ONE axis for a motivated reason: alcove, side window, platform, or partition).
   - Motivated non-key lighting (no sun/key; light from windows, hearth embers, wall lanterns).
   - Directional thresholds (exit extruded outward toward camera).
   - Spatial readability (counter dividing customer/work zone, clear focal points).
3. Score and synthesize the winning design parameters for implementation.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

OPENROUTER_FREE_MODELS = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "minimax/minimax-m2.7:free",
]

OPENAI_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
]


def post_json(url: str, headers: dict, payload: dict, timeout: int = 60) -> dict | None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"API request failed to {url}: {exc}", file=sys.stderr)
        return None


def call_llm(model: str, system_prompt: str, user_prompt: str) -> str | None:
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if "/" in model or ":free" in model:
        if not openrouter_key:
            print("OPENROUTER_API_KEY missing", file=sys.stderr)
            return None
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Second-Rite",
            "X-Title": "Second Rite Interior Contest",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1600,
        }
        res = post_json(OPENROUTER_URL, headers, payload)
        if res and "choices" in res and res["choices"]:
            return res["choices"][0]["message"]["content"]
    else:
        if not openai_key:
            print("OPENAI_API_KEY missing", file=sys.stderr)
            return None
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1600,
        }
        res = post_json(OPENAI_URL, headers, payload)
        if res and "choices" in res and res["choices"]:
            return res["choices"][0]["message"]["content"]
    return None


PADARIA_PITCH_PROMPT = """
We are designing the 3D interior for Alicia's Padaria (Bakery & General Store) in St. Maria for a retro first-person RPG (Second Rite).
Key Lore & Contract:
- Alicia sells fresh bread (crusty broas, honey rolls), general staples (flour, grain, demijohns of olive oil/wine, cured meats), and summoner supplies (water flasks, herbs/potions, feed bowls).
- Alicia also prepares Laura's lunch (bread, cheese, bruised pear tied in a clean cloth bundle).
- Screen dimensions: Classic 256x240 px. Top 256x144 is free composition area; bottom is status menu. Character stands at native Y=128 (floor limit is Y=144).
- Floor Z=0 is fixed. Floor edge at Y=136. Exit threshold extrudes OUTWARD toward camera at Y=143.
- Material palette: Limewashed masonry (whitewash), azulejo tile dado (waist-high band), dark hardwood timber, terracotta pantiles/crocks/floor, wrought iron, woven straw/burlap.
- Lighting: NO KEY/SUN. Must be motivated by in-room sources: baking oven embers, window daylight, wall lanterns.
- THE 4-AXES RULE: You must spend ONE primary axis (e.g. Alcove with header for the baking oven, OR a Side Window raking morning light across the counter, OR a Platform). Do NOT spend all axes.

Propose a detailed pitch for Alicia's Padaria:
1. Primary Axis Choice & Architectural Justification
2. Spatial Layout & Division (Customer Front Area vs. Baker Back Area)
3. Signature Props & Cultural Details (Counter, oven, shelves, sacks, scales, lunch bundle, summoner supplies)
4. Motivated Lighting Rig (Exact sources, colors, warmth, and shadow casting)
5. Screen Composition in the 256x144 Free Viewport
"""

SMITH_PITCH_PROMPT = """
We are designing the 3D interior for Laura's Smith / Forge in St. Maria for a retro first-person RPG (Second Rite).
Key Lore & Contract:
- Laura is a master smith who crafts and sells weapons (swords, daggers, spears, shields), armor, and reforges rare relics. She is soot-stained, smells like vanilla and iron, and believes metal never lies.
- Screen dimensions: Classic 256x240 px. Top 256x144 is free composition area; bottom is status menu. Character stands at native Y=128 (floor limit is Y=144).
- Floor Z=0 is fixed. Floor edge at Y=136. Exit threshold extrudes OUTWARD toward camera at Y=143.
- Material palette: Limewashed masonry with soot darkening, dark hardwood, rough stone forge masonry, forge scale iron, wrought iron, oxidized bronze, charcoal, water.
- Lighting: NO KEY/SUN. Must be motivated by in-room sources: incandescent forge embers, side window cool daylight, tool rack wall lanterns.
- THE 4-AXES RULE: You must spend ONE primary axis (e.g. Side Window raking cool light across dark forge and anvil, OR Alcove for the forge hearth). Do NOT spend all axes.

Propose a detailed pitch for Laura's Smith:
1. Primary Axis Choice & Architectural Justification
2. Spatial Layout & Working Triangle (Forge hearth -> Anvil/Cepo -> Quench tub -> Workbench -> Weapon displays)
3. Signature Props & Craftsmanship Details (Masonry forge, bigorna on cepo, slack tub, tool rail with tongs/hammers, grindstone, ingot stacks, weapon racks)
4. Motivated Lighting Rig (Forge ember glow vs cool daylight rake, chiaroscuro contrast)
5. Screen Composition in the 256x144 Free Viewport
"""

CRITIQUE_SYSTEM_PROMPT = """
You are the Lead Art Director and Architectural Gatekeeper for Second Rite.
Your role is to conduct rigorous, adversarial critique of proposed 3D interior designs against the St. Maria Authoring Specification (docs/design/st-maria-interior-authoring.md).
Rules you enforce strictly:
1. Colonial Portuguese Vocabulary: Warm limewash (caiacao), waist-high azulejo band only, dark turned hardwood, wrought iron, terracotta. No grey generic fantasy plaster or exposed raw brick indoors.
2. Single-Axis Discipline: The proposal must spend exactly ONE axis (Alcove, Side Window, Platform, Partition, Foreground). Penalize severely if multiple axes compete or if the room is a flat unmotivated box.
3. 256x144 Composition & Floor Limit: Geometry must fit the Classic 256px viewport cleanly without unnecessary scrolling, keeping the actor's feet well above Y=144.
4. Lighting Integrity: Zero diorama sun/key. All hard shadows must come from motivated in-room sources (embers, window daylight, wall lamps).
5. Movement Grammar: Outward-extruding exit threshold toward the camera.

Provide an adversarial, incisive evaluation of each pitch, identify weaknesses/traps, score each (0-100), select the Winner, and synthesize the ultimate concrete recipe specification with exact coordinates, axis placement, and dimensions.
"""


def run_contest():
    out_dir = Path(__file__).resolve().parents[2] / "docs" / "design" / "contest_pitches"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "alicias_padaria": {"pitches": {}, "critique_and_synthesis": None},
        "lauras_smith": {"pitches": {}, "critique_and_synthesis": None},
    }

    pitch_models = ["gpt-4o-mini", "google/gemma-4-31b-it:free", "nvidia/nemotron-3-super-120b-a12b:free", "minimax/minimax-m2.7:free"]

    # Step 1: Pitch generation
    print("=== Generating Pitches for Alicia's Padaria ===")
    for model in pitch_models:
        print(f"Pitching Alicia's Padaria via {model}...")
        pitch = call_llm(
            model,
            "You are an expert architectural and 3D game environment designer specializing in Portuguese colonial and retro RPG aesthetics.",
            PADARIA_PITCH_PROMPT,
        )
        if pitch:
            results["alicias_padaria"]["pitches"][model] = pitch
            print(f"  -> Received pitch from {model} ({len(pitch)} chars)")
        time.sleep(1)

    print("=== Generating Pitches for Laura's Smith ===")
    for model in pitch_models:
        print(f"Pitching Laura's Smith via {model}...")
        pitch = call_llm(
            model,
            "You are an expert architectural and 3D game environment designer specializing in Portuguese colonial and retro RPG aesthetics.",
            SMITH_PITCH_PROMPT,
        )
        if pitch:
            results["lauras_smith"]["pitches"][model] = pitch
            print(f"  -> Received pitch from {model} ({len(pitch)} chars)")
        time.sleep(1)

    # Step 2: Adversarial Critique
    print("=== Conducting Adversarial Critique ===")
    judge_model = "gpt-4o" if os.environ.get("OPENAI_API_KEY") else "google/gemma-4-31b-it:free"

    # Critique Padaria
    padaria_critique_prompt = "Here are the competing pitches for Alicia's Padaria:\n\n"
    for name, text in results["alicias_padaria"]["pitches"].items():
        padaria_critique_prompt += f"--- PITCH BY {name} ---\n{text}\n\n"
    padaria_critique_prompt += "Critique each pitch adversarially against the rules. Score each (0-100), select the Winner, and synthesize the ultimate concrete recipe specification with exact coordinates, axis placement, and dimensions."

    print(f"Critiquing Padaria pitches with {judge_model}...")
    padaria_critique = call_llm(judge_model, CRITIQUE_SYSTEM_PROMPT, padaria_critique_prompt)
    results["alicias_padaria"]["critique_and_synthesis"] = padaria_critique
    print(f"  -> Received Padaria critique & synthesis ({len(padaria_critique or '')} chars)")

    # Critique Smith
    smith_critique_prompt = "Here are the competing pitches for Laura's Smith:\n\n"
    for name, text in results["lauras_smith"]["pitches"].items():
        smith_critique_prompt += f"--- PITCH BY {name} ---\n{text}\n\n"
    smith_critique_prompt += "Critique each pitch adversarially against the rules. Score each (0-100), select the Winner, and synthesize the ultimate concrete recipe specification with exact coordinates, axis placement, and dimensions."

    print(f"Critiquing Smith pitches with {judge_model}...")
    smith_critique = call_llm(judge_model, CRITIQUE_SYSTEM_PROMPT, smith_critique_prompt)
    results["lauras_smith"]["critique_and_synthesis"] = smith_critique
    print(f"  -> Received Smith critique & synthesis ({len(smith_critique or '')} chars)")

    # Save results
    json_path = out_dir / "contest_results.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Contest completed! Saved results to {json_path}")
    return results


if __name__ == "__main__":
    run_contest()
