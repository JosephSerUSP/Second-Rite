#!/usr/bin/env python3
"""CI-only facing-space zone palette spike for #558/#559.

The shipping renderer still chooses one base wall tile for every face. This
script patches only the disposable CI worktree so an exposed wall face may
select a pre-normalized runtime wall cell from the zone of the traversable cell
it faces. Logical topology and collision remain unchanged.
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VIEWPORT = ROOT / "presentation" / "viewport_3d.lua"
TILESET = ROOT / "data" / "tilesets" / "dungeon_default.json"
MAP = ROOT / "data" / "maps" / "13.json"
GEN = ROOT / "assets" / "experiments" / "tileset-format-zone-runtime"
MARKER = "-- #558 FACING-SPACE ZONE WALL SPIKE"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_renderer() -> None:
    text = VIEWPORT.read_text(encoding="utf-8")
    if MARKER in text:
        print("renderer already carries zone wall spike")
        return

    old = "        local side = (kind == \"north\" or kind == \"south\") and 1 or 0\n"
    new = (
        f"        {MARKER}\n"
        "        -- Normal material/door/base-wall resolution has already picked\n"
        "        -- an origin. A facing-space zone may now override only that\n"
        "        -- presentation source. The solid wall cell remains unchanged.\n"
        "        local zoneGrid = structure.mapData and structure.mapData.zoneGrid\n"
        "        local zoneRow = zoneGrid and zoneGrid[ny]\n"
        "        local zoneId = zoneRow and zoneRow[nx]\n"
        "        local zoneCells = atlas and atlas.manifest and atlas.manifest.zoneWallCells\n"
        "        local zoneCell = zoneId and zoneId ~= \"\" and zoneCells and zoneCells[zoneId]\n"
        "        if zoneCell then\n"
        "            originY = zoneCell[1] * ATLAS_TILE\n"
        "            originX = zoneCell[2] * ATLAS_TILE\n"
        "        end\n"
        "        local side = (kind == \"north\" or kind == \"south\") and 1 or 0\n"
    )
    text = replace_once(text, old, new, "post-resolution wall source hook")
    VIEWPORT.write_text(text, encoding="utf-8")
    print("patched real viewport with facing-space zone wall lookup")


def install_bundle(pack_dir: Path) -> None:
    GEN.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for semantic, source_name in {
        "albedo": "zone-albedo.png",
        "height": "zone-height.png",
        "glow": "zone-glow.png",
    }.items():
        source = pack_dir / source_name
        if not source.exists():
            raise FileNotFoundError(source)
        target = GEN / f"runtime-{semantic}.png"
        shutil.copyfile(source, target)
        outputs[semantic] = target.relative_to(ROOT).as_posix()

    tileset = json.loads(TILESET.read_text(encoding="utf-8"))
    tileset["texture"] = outputs["albedo"]
    tileset["heightMap"] = outputs["height"]
    tileset["glowMap"] = outputs["glow"]
    tileset["glowStrength"] = 1.0
    tileset["heightMapScale"] = {"wall": 0, "floor": 0, "ceiling": 0}
    tileset["features"] = []
    tileset["fixturePrefabs"] = []
    tileset["zoneWallCells"] = {"crypt": [1, 1]}
    TILESET.write_text(json.dumps(tileset, indent=2) + "\n", encoding="utf-8")
    print("installed normalized zone bundle: default wall=[1,0], crypt wall=[1,1]")


def make_zone_grid(use_crypt: bool) -> list[list[str]]:
    grid = [["" for _ in range(9)] for _ in range(5)]
    if use_crypt:
        for y in (1, 2, 3):
            for x in (5, 6, 7):
                grid[y][x] = "crypt"
    return grid


def set_map_case(use_crypt: bool) -> None:
    data = json.loads(MAP.read_text(encoding="utf-8"))
    data["title"] = "#558 Zone Face Ownership Probe"
    data["layout"] = [
        "#########",
        "#...#...#",
        "#...#...#",
        "#...#...#",
        "#########",
    ]
    data["tileset"] = "dungeon_default"
    data.pop("tilesetOverride", None)
    data["ceilingStyle"] = "solid"
    data["events"] = []
    data["lightObjects"] = []
    data["materials"] = []
    data["zoneGrid"] = make_zone_grid(use_crypt)
    data["zones"] = {"crypt": {"palette": "bellroot_probe"}}
    data["spawn"] = {"x": 2, "y": 2, "dir": "E"}
    data["light"] = [
        [[0.55, 0.55, 0.55] for _ in range(10)]
        for _ in range(6)
    ]
    MAP.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("zone map case=" + ("crypt-right" if use_crypt else "all-default"))


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
    sub.add_parser("patch-renderer")
    install = sub.add_parser("install-bundle")
    install.add_argument("pack_dir", type=Path)
    case = sub.add_parser("set-map-case")
    case.add_argument("case", choices=["default", "crypt"])
    decode = sub.add_parser("decode-preview")
    decode.add_argument("source", type=Path)
    decode.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "patch-renderer":
        patch_renderer()
    elif args.command == "install-bundle":
        install_bundle(args.pack_dir)
    elif args.command == "set-map-case":
        set_map_case(args.case == "crypt")
    elif args.command == "decode-preview":
        decode_preview(args.source, args.output)


if __name__ == "__main__":
    main()
