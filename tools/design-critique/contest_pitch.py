"""Adversarial contest pitches and critique for St. Maria 3D environment authoring.

Uses OpenAI and OpenRouter APIs to generate competing layout/prop/lighting
proposals and conduct multi-perspective adversarial judging (Architectural
Historian, Camera/Gameplay Director, Narrative Stylist).
"""

from __future__ import annotations

import json
import os
import socket
import sys
import urllib.request
import urllib.error
from pathlib import Path

socket.setdefaulttimeout(10)


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def call_openai(prompt: str, system_prompt: str = "", model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    req = urllib.request.Request(
        OPENAI_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"OpenAI API error {e.code}: {body}") from e


def call_openrouter(prompt: str, system_prompt: str = "", model: str = "google/gemma-4-31b-it:free", temperature: float = 0.7) -> str:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set")

    free_candidates = [
        model,
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "minimax/minimax-m3:free",
        "liquid/lfm-2.5-2.6b:free",
        "z-ai/glm-5.2:free",
    ]

    for candidate in free_candidates:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com/JosephSerUSP/Second-Rite",
            "X-Title": "Second Rite Environment Authoring",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": candidate,
            "messages": messages,
            "temperature": temperature,
        }

        req = urllib.request.Request(
            OPENROUTER_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                if content:
                    print(f"Successfully generated pitch via OpenRouter ({candidate})", flush=True)
                    return content
        except Exception as e:
            print(f"OpenRouter candidate {candidate} failed: {e}, trying next...", flush=True)

    raise RuntimeError("All OpenRouter free candidates failed")


def run_pitch_contest(environment_name: str, brief: str, output_path: Path):
    print(f"=== Starting Pitch Contest for: {environment_name} ===", flush=True)

    architect_system = """You are a master 3D environment artist and architect for Second Rite, a dark retro PSX/PC-98 inspired Portuguese colonial fantasy dungeon RPG.
Camera contract:
- 256x240 native view (Classic), with bottom 96px blocked by UI, leaving 256x144 free composition space.
- Floor level is Z=0, camera distance 18.667m, eye height 2.2604m, level pitch.
- Character stands at Y=128 (48px tall).
- Colonial Portuguese architecture: limewash (caiação), azulejo tile dado (waist-high only), dark tropical timber, wrought iron, unglazed terracotta, panelled doors/shutters.
- No sun/key light. In-room sources only (windows, lamps, oven/forge fire).
- Thresholds extrude outward towards camera.
- Background outside walls/ceiling is pitch black.

Propose an architectural composition, spatial layout, furniture placements, lighting setup, and character details. Be concrete with exact coordinates and dimensions in metres (+X depth forward, -Y screen right, +Z up)."""

    print("Generating Pitch A (Classic Authentic Vernacular via OpenRouter)...", flush=True)
    try:
        pitch_a = call_openrouter(
            f"Generate Pitch A for {environment_name}.\n\nBrief:\n{brief}\n\nFocus on grounded, historically rich Portuguese colonial vernacular details, authentic workbench/furnishing placement, and clear focal planes.",
            system_prompt=architect_system,
            model="google/gemma-4-31b-it:free",
        )
    except Exception as e:
        print(f"OpenRouter free model error: {e}, falling back to OpenAI gpt-4o-mini for Pitch A", flush=True)
        pitch_a = call_openai(
            f"Generate Pitch A for {environment_name}.\n\nBrief:\n{brief}\n\nFocus on grounded, historically rich Portuguese colonial vernacular details, authentic workbench/furnishing placement, and clear focal planes.",
            system_prompt=architect_system,
            model="gpt-4o-mini",
        )

    print("Generating Pitch B (Dramatic Value & Atmosphere via OpenAI)...", flush=True)
    pitch_b = call_openai(
        f"Generate Pitch B for {environment_name}.\n\nBrief:\n{brief}\n\nFocus on high-contrast lighting, dramatic depth layers (foreground silhouette, glowing midground focus, deep shadowed back), and powerful narrative environmental storytelling.",
        system_prompt=architect_system,
        model="gpt-4o-mini",
    )

    print("Conducting Adversarial Multi-Judge Critique...", flush=True)
    judges_system = """You are a panel of 3 demanding adversarial judges reviewing two competing 3D environment pitches for Second Rite:
1. Judge 1: Colonial Portuguese Architectural Historian (demands strict vernacular authenticity: caiação, azulejo dado constraints, timber/iron/clay materials, no anachronisms or generic fantasy tropes).
2. Judge 2: Retro Camera & Visual Legibility Director (evaluates 256x144 visible screen area, silhouette contrast, depth staging, foreground frames, walker scale, zero distraction on walkable floor).
3. Judge 3: Narrative & Character Stylist (evaluates environmental storytelling, lived-in details, character personality, emotional resonance).

Evaluate Pitch A and Pitch B thoroughly. Point out specific flaws, strengths, and missed opportunities in both. Then synthesize the ultimate winning compromise specification that combines the best parts of both into an exact implementation recipe."""

    evaluation_prompt = f"""Environment: {environment_name}
Brief: {brief}

--- PITCH A ---
{pitch_a}

--- PITCH B ---
{pitch_b}

Provide:
1. Detailed critique from Judge 1 (Architectural Historian) for both pitches.
2. Detailed critique from Judge 2 (Visual Legibility Director) for both pitches.
3. Detailed critique from Judge 3 (Narrative & Character Stylist) for both pitches.
4. Score breakdown out of 10 for each judge.
5. The Unified Master Specification: A definitive blueprint combining the highest-scoring layout, props, lights, and materials, with exact spatial coordinates (+X, -Y, +Z) for the Blender recipe."""

    verdict = call_openai(evaluation_prompt, system_prompt=judges_system, model="gpt-4o-mini")

    contest_record = {
        "environment": environment_name,
        "brief": brief,
        "pitch_a": pitch_a,
        "pitch_b": pitch_b,
        "verdict_and_master_spec": verdict,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(contest_record, indent=2), encoding="utf-8")
    print(f"Saved contest record to {output_path}")
    return contest_record


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python contest_pitch.py <env_name> <output_json>")
        sys.exit(1)
    env = sys.argv[1]
    out = Path(sys.argv[2])
    brief = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "Create authored St. Maria interior"
    run_pitch_contest(env, brief, out)
