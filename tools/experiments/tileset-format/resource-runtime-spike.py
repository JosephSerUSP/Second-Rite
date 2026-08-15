#!/usr/bin/env python3
"""Real-viewport consumer for the #558/#559 derived mixed-family bundles."""

from __future__ import annotations

import argparse
import base64
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GEN = ROOT / "assets" / "experiments" / "tileset-format-resource-runtime"
TILESET = ROOT / "data" / "tilesets" / "dungeon_default.json"
MAP = ROOT / "data" / "maps" / "13.json"


def install_bundle(kind: str, source_dir: Path) -> None:
    if kind not in {"dungeon", "mixed"}:
        raise ValueError(kind)
    GEN.mkdir(parents=True, exist_ok=True)
    installed = {}
    for semantic in ("albedo", "height", "glow"):
        source = source_dir / f"{kind}-{semantic}.png"
        if not source.exists():
            raise FileNotFoundError(source)
        target = GEN / f"runtime-{semantic}.png"
        shutil.copyfile(source, target)
        installed[semantic] = target.relative_to(ROOT).as_posix()

    tileset = json.loads(TILESET.read_text(encoding="utf-8"))
    tileset["texture"] = installed["albedo"]
    tileset["heightMap"] = installed["height"]
    tileset["glowMap"] = installed["glow"]
    tileset["glowStrength"] = 1.0
    tileset["heightMapScale"] = {"wall": 0.14, "floor": 0.08, "ceiling": 0.08}
    tileset["features"] = []
    tileset["fixturePrefabs"] = []
    TILESET.write_text(json.dumps(tileset, indent=2) + "\n", encoding="utf-8")

    map_data = json.loads(MAP.read_text(encoding="utf-8"))
    map_data["tileset"] = "dungeon_default"
    map_data.pop("tilesetOverride", None)
    width = max(len(row) for row in map_data["layout"])
    rows = len(map_data["layout"])
    map_data["light"] = [
        [[0.34, 0.34, 0.34] for _ in range(width + 1)]
        for _ in range(rows + 1)
    ]
    MAP.write_text(json.dumps(map_data, indent=2) + "\n", encoding="utf-8")

    provenance = {
        "case": kind,
        "authoredFamilies": ["dungeon", "bellroot"] if kind == "mixed" else ["dungeon"],
        "runtimeBundle": installed,
        "roleSources": {
            "ceiling": "dungeon:[0,0]",
            "floor": "dungeon:[0,1]",
            "wall": "bellroot:[1,1]" if kind == "mixed" else "dungeon:[1,0]",
            "door": "dungeon:[1,1]",
        },
        "mergePrecedence": None,
        "normalization": "derived 2x2 runtime atlas/height/glow bundle",
    }
    (GEN / f"provenance-{kind}.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"installed {kind} runtime bundle -> current single-atlas renderer")


def decode_preview(source: Path, output: Path) -> None:
    text = source.read_text(encoding="utf-8", errors="replace")
    begin = text.find("PREVIEW BEGIN")
    end = text.find("PREVIEW END", begin + 1)
    if begin < 0 or end < 0:
        raise RuntimeError("preview markers missing")
    payload = json.loads(text[begin + len("PREVIEW BEGIN"):end].strip())
    if payload.get("error"):
        raise RuntimeError(payload["error"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(payload["image"]))
    print(f"decoded {output.name} ({output.stat().st_size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    install = sub.add_parser("install")
    install.add_argument("kind", choices=["dungeon", "mixed"])
    install.add_argument("source_dir", type=Path)
    decode = sub.add_parser("decode-preview")
    decode.add_argument("source", type=Path)
    decode.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "install":
        install_bundle(args.kind, args.source_dir)
    elif args.command == "decode-preview":
        decode_preview(args.source, args.output)


if __name__ == "__main__":
    main()
