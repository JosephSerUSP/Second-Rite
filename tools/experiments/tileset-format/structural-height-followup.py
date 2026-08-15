#!/usr/bin/env python3
"""Map fixture helper for #558 structural-profile + height interaction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAP = ROOT / "data" / "maps" / "13.json"


def set_case(profile: str, radius: float, segments: int, wall_height: float) -> None:
    if profile not in {"square", "chamfer", "round"}:
        raise ValueError(profile)
    data = json.loads(MAP.read_text(encoding="utf-8"))
    data["tileset"] = "dungeon_default"
    data["tilesetOverride"] = {
        "structuralProfile": {
            "corner": profile,
            "radius": radius,
            "segments": segments,
        },
        "heightMapScale": {
            "wall": wall_height,
            "floor": 0.08,
            "ceiling": 0.08,
        },
    }
    MAP.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"STRUCTURAL_HEIGHT_CASE profile={profile} radius={radius} segments={segments} wallHeight={wall_height}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", choices=["square", "chamfer", "round"])
    parser.add_argument("--radius", type=float, default=0.22)
    parser.add_argument("--segments", type=int, default=3)
    parser.add_argument("--wall-height", type=float, default=0.10)
    args = parser.parse_args()
    set_case(args.profile, args.radius, args.segments, args.wall_height)


if __name__ == "__main__":
    main()
