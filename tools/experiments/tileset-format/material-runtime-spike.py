#!/usr/bin/env python3
"""Runtime-visible material normalization spike for #558/#560.

The authored side is deliberately loose and semantic: standalone albedo,
height, and emission PNGs. This script compiles those into the aligned 2x2
atlas shape today's dungeon_default renderer expects, then patches only the
disposable CI worktree so `lovec . preview-map` exercises the real runtime.
"""

from __future__ import annotations

import argparse
import base64
import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GEN = ROOT / "assets" / "experiments" / "tileset-format-material-runtime"
TILESET = ROOT / "data" / "tilesets" / "dungeon_default.json"
MAP = ROOT / "data" / "maps" / "13.json"
TILE = 64
ATLAS = TILE * 2


def png_bytes(width: int, height: int, rgba: bytes) -> bytes:
    if len(rgba) != width * height * 4:
        raise ValueError("RGBA byte count does not match dimensions")

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)  # PNG filter: none
        raw.extend(rgba[y * stride:(y + 1) * stride])
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def write_rgba(path: Path, width: int, height: int, pixel_fn) -> None:
    data = bytearray()
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixel_fn(x, y)
            data.extend((int(r) & 255, int(g) & 255, int(b) & 255, int(a) & 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes(width, height, bytes(data)))


def brick_lines(x: int, y: int) -> bool:
    course = y // 12
    offset = 8 if course % 2 else 0
    return y % 12 in (0, 1) or (x + offset) % 24 in (0, 1)


def generate_sources() -> None:
    GEN.mkdir(parents=True, exist_ok=True)

    def albedo_base(x: int, y: int):
        noise = ((x * 13 + y * 7) % 17) - 8
        if brick_lines(x, y):
            return (48, 48, 52, 255)
        return (124 + noise, 116 + noise, 104 + noise, 255)

    def albedo_alt(x: int, y: int):
        noise = ((x * 11 + y * 5) % 15) - 7
        if brick_lines(x, y):
            return (38, 48, 52, 255)
        band = ((x // 8) + (y // 12)) % 2
        return ((86 if band else 112) + noise, (118 if band else 100) + noise, (126 if band else 92) + noise, 255)

    def height_relief(x: int, y: int):
        # Human-readable grayscale: neutral 128, raised brick centres,
        # recessed mortar. No hidden alpha semantics in this fixture.
        if brick_lines(x, y):
            value = 92
        else:
            cx = (x % 24) / 23.0
            cy = (y % 12) / 11.0
            dome = max(0.0, 1.0 - ((cx - 0.5) ** 2 * 3.2 + (cy - 0.5) ** 2 * 5.0))
            value = int(128 + 45 * dome)
        return (value, value, value, 255)

    def height_flat(x: int, y: int):
        return (128, 128, 128, 255)

    def emission_off(x: int, y: int):
        return (0, 0, 0, 255)

    def emission_on(x: int, y: int):
        # Large diamond/rune: obvious as a standalone grayscale mask and as
        # emissive texels after runtime normalization.
        dx, dy = abs(x - 32), abs(y - 31)
        outer = dx + dy <= 14
        inner = dx + dy <= 8
        value = 255 if inner else (150 if outer else 0)
        return (value, value, value, 255)

    write_rgba(GEN / "albedo-base.png", TILE, TILE, albedo_base)
    write_rgba(GEN / "albedo-alt.png", TILE, TILE, albedo_alt)
    write_rgba(GEN / "height.png", TILE, TILE, height_relief)
    write_rgba(GEN / "height-flat.png", TILE, TILE, height_flat)
    write_rgba(GEN / "emission-off.png", TILE, TILE, emission_off)
    write_rgba(GEN / "emission-on.png", TILE, TILE, emission_on)

    manifest = {
        "_experimental": "#560 generated semantic source fixture",
        "surface": "runtime_stone",
        "sources": {
            "albedo": ["albedo-base.png", "albedo-alt.png"],
            "height": "height.png",
            "emission": ["emission-off.png", "emission-on.png"],
        },
        "principle": "one image, one visual meaning; runtime packing is derived",
    }
    (GEN / "semantic-sources.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"generated semantic sources under {GEN.relative_to(ROOT)}")


def read_png_rgba(path: Path):
    # Tiny reader for the exact RGBA8/filter-0 PNGs emitted above. Keeping the
    # experiment stdlib-only avoids adding Pillow merely to prove normalization.
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"not PNG: {path}")
    pos = 8
    width = height = None
    idat = bytearray()
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            width, height, depth, color, comp, filt, interlace = struct.unpack(">IIBBBBB", payload)
            if (depth, color, comp, filt, interlace) != (8, 6, 0, 0, 0):
                raise ValueError("fixture reader only supports RGBA8 non-interlaced PNG")
        elif kind == b"IDAT":
            idat.extend(payload)
        elif kind == b"IEND":
            break
    raw = zlib.decompress(bytes(idat))
    stride = width * 4
    rgba = bytearray()
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        if filter_type != 0:
            raise ValueError("fixture reader expected filter 0")
        rgba.extend(raw[cursor:cursor + stride])
        cursor += stride
    return width, height, bytes(rgba)


def pack_runtime_atlas(source_path: Path, out_path: Path, neutral_kind: str) -> None:
    sw, sh, source = read_png_rgba(source_path)
    if (sw, sh) != (TILE, TILE):
        raise ValueError("semantic source must be 64x64 for this compatibility probe")

    if neutral_kind == "albedo":
        neutral = bytes([92, 88, 82, 255]) * (TILE * TILE)
    elif neutral_kind == "height":
        neutral = bytes([128, 128, 128, 255]) * (TILE * TILE)
    elif neutral_kind == "emission":
        neutral = bytes([0, 0, 0, 255]) * (TILE * TILE)
    else:
        raise ValueError(neutral_kind)

    atlas = bytearray(neutral * 4)
    atlas_stride = ATLAS * 4
    source_stride = TILE * 4

    # Fill all four cells with neutral; install the semantic source only into
    # wall cell row=1,col=0. Current runtime packing remains a compiler detail.
    for cell_row in range(2):
        for cell_col in range(2):
            tile = source if (cell_row, cell_col) == (1, 0) else neutral
            for y in range(TILE):
                dest = ((cell_row * TILE + y) * atlas_stride) + cell_col * source_stride
                src = y * source_stride
                atlas[dest:dest + source_stride] = tile[src:src + source_stride]

    out_path.write_bytes(png_bytes(ATLAS, ATLAS, bytes(atlas)))


def patch_project(case: str) -> None:
    cases = {
        "base": ("albedo-base.png", "height.png", "emission-off.png"),
        "albedo-alt": ("albedo-alt.png", "height.png", "emission-off.png"),
        "emission-on": ("albedo-base.png", "height.png", "emission-on.png"),
        "height-flat": ("albedo-base.png", "height-flat.png", "emission-off.png"),
    }
    if case not in cases:
        raise ValueError(case)
    albedo, height, emission = cases[case]

    runtime_albedo = GEN / "runtime-albedo.png"
    runtime_height = GEN / "runtime-height.png"
    runtime_emission = GEN / "runtime-emission.png"
    pack_runtime_atlas(GEN / albedo, runtime_albedo, "albedo")
    pack_runtime_atlas(GEN / height, runtime_height, "height")
    pack_runtime_atlas(GEN / emission, runtime_emission, "emission")

    tileset = json.loads(TILESET.read_text(encoding="utf-8"))
    tileset["texture"] = runtime_albedo.relative_to(ROOT).as_posix()
    tileset["heightMap"] = runtime_height.relative_to(ROOT).as_posix()
    tileset["glowMap"] = runtime_emission.relative_to(ROOT).as_posix()
    tileset["glowStrength"] = 1.0
    tileset["heightMapScale"] = {"wall": 0.16, "floor": 0, "ceiling": 0}
    # Keep this material probe deterministic and visually uncluttered.
    tileset["features"] = []
    tileset["fixturePrefabs"] = []
    TILESET.write_text(json.dumps(tileset, indent=2) + "\n", encoding="utf-8")

    map_data = json.loads(MAP.read_text(encoding="utf-8"))
    map_data["tileset"] = "dungeon_default"
    map_data.pop("tilesetOverride", None)
    width = max(len(row) for row in map_data["layout"])
    height_rows = len(map_data["layout"])
    map_data["light"] = [
        [[0.18, 0.18, 0.18] for _ in range(width + 1)]
        for _ in range(height_rows + 1)
    ]
    MAP.write_text(json.dumps(map_data, indent=2) + "\n", encoding="utf-8")

    provenance = {
        "case": case,
        "semanticSources": {
            "albedo": albedo,
            "height": height,
            "emission": emission,
        },
        "runtimeOutputs": {
            "albedoAtlas": runtime_albedo.name,
            "heightAtlas": runtime_height.name,
            "emissionAtlas": runtime_emission.name,
        },
        "wallRuntimeCell": {"row": 1, "column": 0},
        "authoredChannelPacking": False,
    }
    (GEN / f"provenance-{case}.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"prepared {case}: {albedo} + {height} + {emission} -> aligned runtime bundle")


def decode_preview(source: Path, output: Path) -> None:
    text = source.read_text(encoding="utf-8", errors="replace")
    begin = text.find("PREVIEW BEGIN")
    end = text.find("PREVIEW END", begin + 1)
    if begin < 0 or end < 0:
        raise RuntimeError("preview markers not found")
    payload = json.loads(text[begin + len("PREVIEW BEGIN"):end].strip())
    if payload.get("error"):
        raise RuntimeError(payload["error"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(payload["image"]))
    print(f"decoded {output.name} ({output.stat().st_size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate-sources")
    case_parser = sub.add_parser("prepare-case")
    case_parser.add_argument("case", choices=["base", "albedo-alt", "emission-on", "height-flat"])
    decode = sub.add_parser("decode-preview")
    decode.add_argument("source", type=Path)
    decode.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "generate-sources":
        generate_sources()
    elif args.command == "prepare-case":
        patch_project(args.case)
    elif args.command == "decode-preview":
        decode_preview(args.source, args.output)


if __name__ == "__main__":
    main()
