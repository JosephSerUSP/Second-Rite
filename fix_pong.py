import json

with open("projects/labs/scene-benchmarks/data/scenes/a001_pong.json", encoding="utf-8") as f:
    pong = json.load(f)

# Put back the terminal condition that got lost in the fresh recreation
pong["terminal"] = {
  "none": "spec requires scoring, reset after score and a restartable lifecycle, but no match-win threshold: an endless rally is the authored contract, and reset is a mid-game transition rather than a terminal state"
}

with open("projects/labs/scene-benchmarks/data/scenes/a001_pong.json", "w", encoding="utf-8") as f:
    json.dump(pong, f, indent=2, ensure_ascii=False)
