#!/usr/bin/env python3
"""Download the CC0 Poly Haven palette for the next town gauntlet.

Records full provenance for every downloaded file. Poly Haven assets are CC0
(verified 2026-08-20 at https://polyhaven.com/license): commercial use and
redistribution permitted, attribution not required.
"""
from __future__ import annotations

import hashlib
import io
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "materials" / "polyhaven"
API = "https://api.polyhaven.com"
RES = "2k"          # GTX 1650 / 4 GB VRAM budget
FMT = "jpg"

# slug -> (palette role, which map slots we need)
PALETTE = {
    "medieval_blocks_02":       "warm_old_limestone",
    "castle_brick_02_white":    "darker_structural_stone",
    "plastered_stone_wall":     "painted_stained_plaster",
    "weathered_peeling_timber": "worn_timber",
    "dark_wooden_planks":       "dark_timber",
    "clay_roof_tiles_02":       "roof_ceramic",
    "cobblestone_floor_02":     "cobblestone",
    "dirt_floor":               "packed_dirt",
    "rust_coarse_01":           "oxidized_iron",
    "rough_pine_door":          "painted_shopfront_wood",
}

# Poly Haven map-slot names -> our canonical slot
SLOTS = {
    "Diffuse": "albedo", "diff": "albedo", "albedo": "albedo",
    "Rough": "roughness", "rough": "roughness",
    "Displacement": "height", "disp": "height",
    "AO": "ao", "ao": "ao",
    "nor_gl": "normal", "nor_dx": "normal_dx",
    "arm": "arm",
}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "second-rite-town-gauntlet/1.0"})
    with urllib.request.urlopen(req, timeout=180) as fh:
        return fh.read()


def _json(url: str):
    return json.loads(_get(url).decode("utf-8"))


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = []
    for slug, role in PALETTE.items():
        info = _json(f"{API}/info/{slug}")
        files = _json(f"{API}/files/{slug}")
        out_dir = DEST / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        got = {}
        for ph_slot, canonical in SLOTS.items():
            node = files.get(ph_slot)
            if not isinstance(node, dict):
                continue
            entry = (node.get(RES) or {}).get(FMT) or (node.get(RES) or {}).get("png")
            if not entry or "url" not in entry:
                continue
            if canonical in got:
                continue
            url = entry["url"]
            name = f"{canonical}{Path(url).suffix}"
            target = out_dir / name
            if not target.is_file():
                data = _get(url)
                target.write_bytes(data)
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            got[canonical] = {"file": name, "sourceUrl": url, "sha256": digest,
                              "bytes": target.stat().st_size}
        manifest.append({
            "slug": slug,
            "paletteRole": role,
            "library": "Poly Haven",
            "assetPage": f"https://polyhaven.com/a/{slug}",
            "displayName": info.get("name"),
            "authors": info.get("authors"),
            "categories": info.get("categories"),
            "license": "CC0-1.0",
            "licenseVerifiedAt": "https://polyhaven.com/license",
            "licenseVerifiedOn": "2026-08-20",
            "commercialUse": True,
            "redistribution": True,
            "attributionRequired": False,
            "resolution": RES,
            "format": FMT,
            "maps": got,
        })
        print(f"  {slug:26s} {role:26s} {','.join(sorted(got))}")
    out = DEST / "polyhaven-provenance.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT)}  ({len(manifest)} assets)")


if __name__ == "__main__":
    main()
