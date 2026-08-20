#!/usr/bin/env python3
"""Strategy C: generate 2x2 PBR material source sheets with OpenAI images.

One 1024x1024 sheet -> four ~512x512 maps:
    TL albedo | TR height | BL roughness | BR (AO or metallic mask)

Normals are NEVER taken from the model; Blender derives them from the
generated height map. Secrets are read from the environment and never stored.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "materials" / "generated"
MODEL = os.environ.get("TOWN_IMAGE_MODEL", "gpt-image-1-mini")
SIZE = "1024x1024"
QUALITY = os.environ.get("TOWN_IMAGE_QUALITY", "medium")

COMMON = (
    "A 2x2 grid contact sheet of PBR texture maps for one single material, "
    "seamless and tileable, orthographic top-down flat-on view, no perspective, "
    "the four quadrants perfectly aligned pixel-for-pixel with each other. "
    "TOP-LEFT quadrant: BASE COLOR / ALBEDO - flat even material colour only, "
    "absolutely no directional lighting, no cast shadows, no highlights, no ambient occlusion baked in. "
    "TOP-RIGHT quadrant: HEIGHT / DISPLACEMENT - pure grayscale, white is raised, black is recessed, "
    "physically consistent with the albedo. "
    "BOTTOM-LEFT quadrant: ROUGHNESS - pure grayscale, white is rough and matte, black is smooth and glossy. "
    "BOTTOM-RIGHT quadrant: {fourth}. "
    "Flat technical texture-library reference sheet, no text, no labels, no borders, no watermarks."
)

SHEETS = {
    "gen_facade_ornament": dict(
        fourth="AMBIENT OCCLUSION - pure grayscale, white is exposed, black is occluded crevices",
        subject=(
            "Carved sandstone facade ornament course: a repeating band of shallow relief "
            "moulding, dentils and a weathered floral rosette, chipped edges, fine mortar "
            "lines, aged and dusty, late medieval European townhouse stonework."),
    ),
    "gen_roof_tile": dict(
        fourth="AMBIENT OCCLUSION - pure grayscale, white is exposed, black is deep between tiles",
        subject=(
            "Old terracotta barrel roof tiles in regular overlapping rows, uneven hand-made "
            "clay, colour variation from orange to grey-brown, lichen patches, small chips."),
    ),
    "gen_plaster_patch": dict(
        fourth="AMBIENT OCCLUSION - pure grayscale, white is exposed surface, black is cracks and gaps",
        subject=(
            "Aged lime plaster wall, warm off-white, patchily fallen away to expose the "
            "brick and rubble beneath, hairline cracks, water staining near the bottom."),
    ),
    "gen_cobble_road": dict(
        fourth="AMBIENT OCCLUSION - pure grayscale, white is stone tops, black is deep joints",
        subject=(
            "Worn cobblestone street paving, irregular rounded granite setts of varied grey "
            "and warm brown, packed dirt and moss in the joints, smoothed by long foot traffic."),
    ),
}


def generate(name: str, spec: dict, force=False) -> dict:
    DEST.mkdir(parents=True, exist_ok=True)
    out = DEST / f"{name}.png"
    meta_path = DEST / f"{name}.json"
    prompt = spec["subject"] + " " + COMMON.format(fourth=spec["fourth"])
    if out.is_file() and not force:
        print(f"  {name}: cached")
        return json.loads(meta_path.read_text(encoding="utf-8"))
    body = json.dumps({
        "model": MODEL, "prompt": prompt, "size": SIZE,
        "quality": QUALITY, "n": 1,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations", data=body,
        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as fh:
        payload = json.loads(fh.read().decode("utf-8"))
    out.write_bytes(base64.b64decode(payload["data"][0]["b64_json"]))
    meta = {
        "name": name,
        "source": "openai-generated",
        "model": MODEL,
        "size": SIZE,
        "quality": QUALITY,
        "prompt": prompt,
        "generatedOn": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sheetLayout": {"topLeft": "albedo", "topRight": "height",
                        "bottomLeft": "roughness", "bottomRight": "ao"},
        "normalPolicy": "derived in Blender from the generated height map; never generated",
        "file": out.name,
        "bytes": out.stat().st_size,
        "usage": payload.get("usage"),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  {name}: {out.stat().st_size} bytes  usage={payload.get('usage')}")
    return meta


def main():
    names = sys.argv[1:] or list(SHEETS)
    for n in names:
        generate(n, SHEETS[n])


if __name__ == "__main__":
    main()
