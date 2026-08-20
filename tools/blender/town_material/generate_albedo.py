#!/usr/bin/env python3
"""Strategy C (revised): generate ONE flat albedo per material, derive the rest.

The 2x2 sheet format in the original brief was tested and measured to fail --
see docs in derive_maps.py. Registration is only guaranteed when every map
comes from one image, so that is what we do.
"""
from __future__ import annotations

import base64, json, os, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / "projects/hichaukitoden-game/assets/authoring/town/materials/generated"
MODEL = "gpt-image-2"
SIZE = "1024x1024"
QUALITY = "medium"

FLAT = (
    " Seamless tileable texture, orthographic flat-on top-down view, no perspective. "
    "BASE COLOR / ALBEDO ONLY: perfectly flat even illumination, absolutely no directional "
    "lighting, no cast shadows, no highlights, no visible light direction, no vignetting, "
    "no ambient occlusion baked in. Even brightness corner to corner. "
    "Flat technical texture-library reference plate. No text, no labels, no borders, no watermark."
)

MATERIALS = {
    "gen_facade_ornament": "Carved sandstone facade ornament course: a repeating horizontal band of shallow relief moulding, square dentils, and weathered floral rosettes, chipped edges, fine mortar lines, aged and dusty, late medieval European townhouse stonework.",
    "gen_roof_tile": "Old terracotta barrel roof tiles in regular overlapping rows, uneven hand-made clay, colour varying from warm orange to grey-brown, patches of lichen, small chips and cracks.",
    "gen_plaster_patch": "Aged lime plaster wall, warm off-white, patchily fallen away to expose the brick and rubble beneath, hairline cracks, soft water staining, centuries old.",
    "gen_shop_timber": "Dark painted shopfront timber panelling, deep green paint worn and flaking to bare grey wood along the grain, old nail heads, scuffed along the bottom edge.",
}


def gen(name, subject, force=False):
    DEST.mkdir(parents=True, exist_ok=True)
    out, meta_p = DEST / f"{name}_albedo.png", DEST / f"{name}.json"
    if out.is_file() and not force:
        print(f"  {name}: cached"); return
    body = json.dumps({"model": MODEL, "prompt": subject + FLAT,
                       "size": SIZE, "quality": QUALITY, "n": 1}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body,
        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as fh:
        p = json.loads(fh.read().decode())
    out.write_bytes(base64.b64decode(p["data"][0]["b64_json"]))
    meta_p.write_text(json.dumps({
        "name": name, "source": "openai-generated", "model": MODEL, "size": SIZE,
        "quality": QUALITY, "prompt": subject + FLAT,
        "generatedOn": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "generatedMaps": ["albedo"],
        "derivedMaps": ["height", "roughness", "ao"],
        "derivationTool": "tools/blender/town_material/derive_maps.py",
        "normalPolicy": "derived in Blender from the derived height map; never generated",
        "albedoFile": out.name, "bytes": out.stat().st_size, "usage": p.get("usage"),
    }, indent=2), encoding="utf-8")
    print(f"  {name}: {out.stat().st_size} bytes")


if __name__ == "__main__":
    for n in (sys.argv[1:] or list(MATERIALS)):
        gen(n, MATERIALS[n])
