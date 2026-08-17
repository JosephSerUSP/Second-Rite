#!/usr/bin/env python3
import os
import json
import urllib.request
import urllib.error

key = os.environ.get("OPENROUTER_API_KEY")

prompt = "Write a brief 3-sentence game critique of Second Gate: Pale Crossing (an indie first person dungeon crawler featuring a Summoner and their Moa companion Saban exploring a mysterious subterranean São Paulo metro station)."

candidates = [
    "liquid/lfm-2.5-2.6b:free",
    "z-ai/glm-5.2:free",
    "poolside/laguna-s-2.1:free",
    "nvidia/nemotron-3.5-lightning:free",
    "dots-studio/dots-3-note-preview:free"
]

for model in candidates:
    print(f"Testing {model}...", flush=True)
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an incisive indie RPG critic."},
                {"role": "user", "content": prompt}
            ]
        }).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"SUCCESS {model}:", data["choices"][0]["message"]["content"][:100], "...", flush=True)
    except Exception as e:
        print(f"Failed {model}: {e}", flush=True)
