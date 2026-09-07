import json

with open("projects/labs/scene-benchmarks/data/scenes/a003_snake.json", "r") as f:
    data = json.load(f)

# Modify the terminal script to actually lose quickly for testing
data["terminal"]["script"] = [{"key": "up"}] * 10

with open("projects/labs/scene-benchmarks/data/scenes/a003_snake.json", "w") as f:
    json.dump(data, f, indent=2)
