#!/usr/bin/env python3
import os
import json
import urllib.request

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")

prompt = """You are an incisive indie RPG systems and narrative design critic.
Please write a concise 4-paragraph critical review of the experimental campaign "Second Gate: Pale Crossing" covering:
1. Mechanical & Thematic Resonance (Summoner MP step-drain vs Saban emotional bond)
2. Stratum Transition (São Paulo Metro Estação Sé surrealism)
3. Pacing, Borrowed Room, and Dual Ending
4. Final Verdict & Rating (1–5 scale). Output ONLY the final review in markdown."""

req = urllib.request.Request(
    "https://openrouter.ai/api/v1/chat/completions",
    data=json.dumps({
        "model": "poolside/laguna-s-2.1:free",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 800
    }).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_KEY}"
    }
)

try:
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"].strip()
        
        critique_path = "projects/labs/pale-crossing/CRITIQUE.md"
        with open(critique_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        parts = content.split("## Critique by OpenRouter Critic B")
        new_content = parts[0].strip() + "\n\n## Critique by OpenRouter Critic B (Laguna S Free)\n\n" + text + "\n"
        with open(critique_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Successfully refreshed Critic B!")
except Exception as e:
    print(f"Error: {e}")
