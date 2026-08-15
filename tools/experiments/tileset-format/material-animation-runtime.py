#!/usr/bin/env python3
"""Independent material-clock normalization proof for #558/#560.

This does not implement the production animation scheduler. It proves the source
contract: independently-authored property frame lists + clocks can be sampled
deterministically and normalized into today's static runtime bundle without a
cartesian set of combined material frames. Every sampled state is then rendered
through the real `preview-map` path by CI.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPIKE_PATH = ROOT / "tools" / "experiments" / "tileset-format" / "material-runtime-spike.py"
GEN = ROOT / "assets" / "experiments" / "tileset-format-material-runtime"
TILESET = ROOT / "data" / "tilesets" / "dungeon_default.json"
MAP = ROOT / "data" / "maps" / "13.json"


def load_spike():
    spec = importlib.util.spec_from_file_location("material_runtime_spike", SPIKE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ALBEDO = {
    "clock": "wall-albedo",
    "fps": 1.0,
    "frames": ["albedo-base.png", "albedo-alt.png", "albedo-base.png"],
}
EMISSION = {
    "clock": "rune-flicker",
    "fps": 4.0,
    "frames": ["emission-off.png", "emission-on.png", "emission-off.png", "emission-on.png"],
}
HEIGHT = "height.png"


def frame_at(animation: dict, time_seconds: float) -> tuple[int, str]:
    index = int(math.floor(time_seconds * float(animation["fps"]))) % len(animation["frames"])
    return index, animation["frames"][index]


def install_sample(time_seconds: float, label: str) -> dict:
    spike = load_spike()
    albedo_index, albedo_file = frame_at(ALBEDO, time_seconds)
    emission_index, emission_file = frame_at(EMISSION, time_seconds)

    runtime_albedo = GEN / "runtime-albedo.png"
    runtime_height = GEN / "runtime-height.png"
    runtime_emission = GEN / "runtime-emission.png"
    spike.pack_runtime_atlas(GEN / albedo_file, runtime_albedo, "albedo")
    spike.pack_runtime_atlas(GEN / HEIGHT, runtime_height, "height")
    spike.pack_runtime_atlas(GEN / emission_file, runtime_emission, "emission")

    tileset = json.loads(TILESET.read_text(encoding="utf-8"))
    tileset["texture"] = runtime_albedo.relative_to(ROOT).as_posix()
    tileset["heightMap"] = runtime_height.relative_to(ROOT).as_posix()
    tileset["glowMap"] = runtime_emission.relative_to(ROOT).as_posix()
    tileset["glowStrength"] = 1.0
    tileset["heightMapScale"] = {"wall": 0.16, "floor": 0, "ceiling": 0}
    tileset["features"] = []
    tileset["fixturePrefabs"] = []
    TILESET.write_text(json.dumps(tileset, indent=2) + "\n", encoding="utf-8")

    map_data = json.loads(MAP.read_text(encoding="utf-8"))
    map_data["tileset"] = "dungeon_default"
    map_data.pop("tilesetOverride", None)
    width = max(len(row) for row in map_data["layout"])
    rows = len(map_data["layout"])
    map_data["light"] = [
        [[0.18, 0.18, 0.18] for _ in range(width + 1)]
        for _ in range(rows + 1)
    ]
    MAP.write_text(json.dumps(map_data, indent=2) + "\n", encoding="utf-8")

    provenance = {
        "label": label,
        "timeSeconds": time_seconds,
        "propertyClocks": {
            "albedo": {
                "clock": ALBEDO["clock"],
                "fps": ALBEDO["fps"],
                "frameIndex": albedo_index,
                "source": albedo_file,
            },
            "emission": {
                "clock": EMISSION["clock"],
                "fps": EMISSION["fps"],
                "frameIndex": emission_index,
                "source": emission_file,
            },
            "height": {
                "clock": None,
                "source": HEIGHT,
                "static": True,
            },
        },
        "runtime": {
            "albedoAtlas": runtime_albedo.name,
            "heightAtlas": runtime_height.name,
            "emissionAtlas": runtime_emission.name,
        },
        "authoredCombinedFrames": 0,
    }
    (GEN / f"animation-{label}.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print("MATERIAL_ANIMATION_SAMPLE " + json.dumps(provenance, separators=(",", ":")))
    return provenance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("time", type=float)
    parser.add_argument("label")
    args = parser.parse_args()
    install_sample(args.time, args.label)


if __name__ == "__main__":
    main()
