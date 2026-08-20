#!/usr/bin/env python3
"""Download public CC0 PBR materials from Poly Haven for Second Rite town gauntlet."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST_DIR = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "textures" / "public_cc0"

TEXTURES_TO_DOWNLOAD = [
    {
        "id": "cobblestone_05",
        "category": "cobblestone",
        "name": "Cobblestone 05 (Worn Square Pavers)",
        "license": "CC0",
        "source_url": "https://polyhaven.com/a/cobblestone_05",
        "maps": ["Diffuse", "Rough", "nor_gl", "Displacement"]
    },
    {
        "id": "rough_plaster_brick_04",
        "category": "plaster_stucco",
        "name": "Rough Plaster Brick 04 (Weathered Stucco)",
        "license": "CC0",
        "source_url": "https://polyhaven.com/a/rough_plaster_brick_04",
        "maps": ["Diffuse", "Rough", "nor_gl", "Displacement"]
    },
    {
        "id": "rustic_stone_wall",
        "category": "stone_wall",
        "name": "Rustic Stone Wall (Medieval Ashlar Masonry)",
        "license": "CC0",
        "source_url": "https://polyhaven.com/a/rustic_stone_wall",
        "maps": ["Diffuse", "Rough", "nor_gl", "Displacement"]
    },
    {
        "id": "medieval_wood",
        "category": "aged_wood",
        "name": "Medieval Wood (Aged Structural Timber)",
        "license": "CC0",
        "source_url": "https://polyhaven.com/a/medieval_wood",
        "maps": ["Diffuse", "Rough", "nor_gl", "Displacement"]
    },
    {
        "id": "clay_roof_tiles",
        "category": "roof_tile",
        "name": "Clay Roof Tiles (Terracotta / Ceramic)",
        "license": "CC0",
        "source_url": "https://polyhaven.com/a/clay_roof_tiles",
        "maps": ["Diffuse", "Rough", "nor_gl", "Displacement"]
    },
    {
        "id": "rusty_metal_02",
        "category": "metal_fixture",
        "name": "Rusty Metal 02 (Oxidized Wrought Iron)",
        "license": "CC0",
        "source_url": "https://polyhaven.com/a/rusty_metal_02",
        "maps": ["Diffuse", "Rough", "nor_gl", "Displacement"]
    }
]


def download_file(url: str, target: Path):
    if target.is_file() and target.stat().st_size > 0:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "SecondRite/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp, open(target, "wb") as f:
        f.write(resp.read())


def main():
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    for tex in TEXTURES_TO_DOWNLOAD:
        tex_id = tex["id"]
        out_folder = DEST_DIR / tex_id
        out_folder.mkdir(parents=True, exist_ok=True)
        print(f"Fetching files metadata for {tex_id}...")
        api_url = f"https://api.polyhaven.com/files/{tex_id}"
        req = urllib.request.Request(api_url, headers={"User-Agent": "SecondRite/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            files_meta = json.loads(resp.read().decode("utf-8"))

        downloaded_files = {}
        for map_type in tex["maps"]:
            map_data = files_meta.get(map_type, {})
            # Try 1k jpg first, then png
            res_1k = map_data.get("1k", {})
            file_info = res_1k.get("jpg") or res_1k.get("png")
            if not file_info:
                print(f"Warning: map {map_type} 1k not found for {tex_id}")
                continue
            file_url = file_info["url"]
            ext = Path(file_url).suffix
            dest_file = out_folder / f"{tex_id}_{map_type.lower()}_1k{ext}"
            print(f"  Downloading {map_type} -> {dest_file.name}...")
            download_file(file_url, dest_file)
            downloaded_files[map_type.lower()] = str(dest_file.relative_to(ROOT)).replace("\\", "/")

        record = {
            "strategy": "public_library_pbr",
            "material_id": tex_id,
            "name": tex["name"],
            "category": tex["category"],
            "license": tex["license"],
            "source_library": "Poly Haven",
            "source_url": tex["source_url"],
            "downloaded_files": downloaded_files
        }
        manifest.append(record)
        (out_folder / "metadata.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    manifest_path = DEST_DIR / "public_cc0_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Public PBR download complete. Manifest saved to {manifest_path}")


if __name__ == "__main__":
    main()
