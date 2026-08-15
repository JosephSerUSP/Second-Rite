#!/usr/bin/env python3
"""Stage-appropriate height proof for #558/#560.

Uses Thestra's existing `preview-geometry` output as the oracle. The experiment
creates two temporary directory-backed wall surfaces that share albedo and differ
only in their human-readable height.png. `preview-geometry` then returns the
engine-composed height field and compiled mesh facts for comparison.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GEN = ROOT / "assets" / "experiments" / "tileset-format-material-runtime"


def write_asset(directory: Path, asset_id: str, height_name: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(GEN / "albedo-base.png", directory / "albedo.png")
    shutil.copyfile(GEN / height_name, directory / "height.png")
    spec = {
        "id": asset_id,
        "role": "surfaceFixture",
        "topology": "plane",
        "surface": "wall",
        "heightOperation": "add",
        "heightScale": 0.16,
        "meshColumns": 16,
        "meshRows": 16,
        "offset": 0.004,
    }
    (directory / "asset.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")


def prepare() -> None:
    write_asset(GEN / "geometry-relief", "material_probe_relief", "height.png")
    write_asset(GEN / "geometry-flat", "material_probe_flat", "height-flat.png")
    print("prepared real geometry compiler fixtures: relief + flat")


def payload_from_log(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    begin_marker = "GEOMETRY PREVIEW BEGIN"
    end_marker = "GEOMETRY PREVIEW END"
    begin = text.find(begin_marker)
    end = text.find(end_marker, begin + len(begin_marker))
    if begin < 0 or end < 0:
        raise RuntimeError(f"geometry preview markers missing in {path}")
    payload = json.loads(text[begin + len(begin_marker):end].strip())
    if payload.get("error"):
        raise RuntimeError(f"geometry preview error in {path}: {payload['error']}")
    return payload


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compare(relief_log: Path, flat_log: Path, output_dir: Path) -> None:
    relief = payload_from_log(relief_log)
    flat = payload_from_log(flat_log)
    output_dir.mkdir(parents=True, exist_ok=True)

    relief_albedo = base64.b64decode(relief["fields"]["albedo"])
    flat_albedo = base64.b64decode(flat["fields"]["albedo"])
    relief_height = base64.b64decode(relief["fields"]["height"])
    flat_height = base64.b64decode(flat["fields"]["height"])

    albedo_equal = relief_albedo == flat_albedo
    height_equal = relief_height == flat_height
    if not albedo_equal:
        raise RuntimeError("height-only geometry fixtures changed the engine-composed albedo field")
    if height_equal:
        raise RuntimeError("relief and flat semantic height sources produced the same engine height field")

    relief_triangles = int(relief.get("asset", {}).get("triangles") or 0)
    flat_triangles = int(flat.get("asset", {}).get("triangles") or 0)
    if relief_triangles <= 0 or flat_triangles <= 0:
        raise RuntimeError("preview-geometry did not compile a real mesh")

    (output_dir / "relief-height-field.png").write_bytes(relief_height)
    (output_dir / "flat-height-field.png").write_bytes(flat_height)
    (output_dir / "shared-albedo-field.png").write_bytes(relief_albedo)

    report = {
        "oracle": "engine.geometry.debugFields + engine.geometry.load via preview-geometry",
        "semanticSources": {
            "relief": "height.png",
            "flat": "height-flat.png",
            "sharedAlbedo": "albedo-base.png",
        },
        "engineFields": {
            "albedoEqual": albedo_equal,
            "reliefHeightSha256": digest(relief_height),
            "flatHeightSha256": digest(flat_height),
            "heightEqual": height_equal,
        },
        "compiledMeshes": {
            "reliefTriangles": relief_triangles,
            "flatTriangles": flat_triangles,
            "reliefVertices": int(relief.get("asset", {}).get("vertices") or 0),
            "flatVertices": int(flat.get("asset", {}).get("vertices") or 0),
        },
        "interpretation": "height correctness is established at geometry-field/mesh stage; final pixel difference is camera-dependent",
    }
    (output_dir / "height-geometry-proof.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("HEIGHT_GEOMETRY_PROOF " + json.dumps(report, separators=(",", ":")))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("relief_log", type=Path)
    compare_parser.add_argument("flat_log", type=Path)
    compare_parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    if args.command == "prepare":
        prepare()
    elif args.command == "compare":
        compare(args.relief_log, args.flat_log, args.output_dir)


if __name__ == "__main__":
    main()
