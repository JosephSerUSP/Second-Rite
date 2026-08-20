#!/usr/bin/env python3
"""Generate 2x2 PBR material sheets using OpenAI image generation for Second Rite town gauntlet."""
from __future__ import annotations

import base64
import datetime
import io
import json
import os
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DEST_DIR = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "textures" / "generated_ai"

AI_MATERIALS = [
    {
        "id": "ai_limestone_ashlar",
        "category": "stone_wall",
        "name": "AI Generated Limestone Ashlar Blocks",
        "prompt": (
            "A seamless 2x2 texture map grid for 3D game material authoring representing aged medieval limestone ashlar masonry blocks. "
            "TOP-LEFT quadrant: ALBEDO/BASE COLOR, completely flat unlit diffuse texture with weathered warm cream-colored stone and subtle mortar, no shadows, no specular highlights, completely orthographic. "
            "TOP-RIGHT quadrant: HEIGHT/DISPLACEMENT map, clean grayscale where stone blocks are raised white/light-gray and mortar grooves are deep black, perfectly matching the albedo structure. "
            "BOTTOM-LEFT quadrant: ROUGHNESS map, grayscale where chalky stone is rough light-gray and smoother areas are darker gray. "
            "BOTTOM-RIGHT quadrant: AMBIENT OCCLUSION map, grayscale with contact shadows in deep crevices and mortar lines. "
            "Strict 2x2 quadrant layout, high texture detail, clean sharp boundaries between the four quadrants."
        )
    },
    {
        "id": "ai_aged_stucco_plaster",
        "category": "plaster_stucco",
        "name": "AI Generated Aged Warm Stucco Plaster",
        "prompt": (
            "A seamless 2x2 texture map grid for 3D game material authoring representing weathered medieval Mediterranean stucco plaster with patches of exposed ancient brick underneath. "
            "TOP-LEFT quadrant: ALBEDO/BASE COLOR, flat diffuse texture of warm buff plaster, subtle dirt staining and exposed terracotta brick patches, no directional lighting, no cast shadows. "
            "TOP-RIGHT quadrant: HEIGHT/DISPLACEMENT map, grayscale where intact plaster layer is raised white and chipped areas exposing brick are recessed darker gray/black. "
            "BOTTOM-LEFT quadrant: ROUGHNESS map, grayscale showing rough matte plaster and slightly smoother brick. "
            "BOTTOM-RIGHT quadrant: AMBIENT OCCLUSION map, grayscale with dark crevices where plaster is chipped away. "
            "Strict 2x2 quadrant layout, orthographic, no perspective."
        )
    },
    {
        "id": "ai_medieval_cobblestone",
        "category": "cobblestone",
        "name": "AI Generated Medieval Town Cobblestones",
        "prompt": (
            "A seamless 2x2 texture map grid for 3D game material authoring representing worn medieval town street cobblestones with dirt and moss in the cracks. "
            "TOP-LEFT quadrant: ALBEDO/BASE COLOR, flat top-down diffuse texture of rounded river-stone cobblestones, earthy gray-brown tones, subtle green moss in cracks, no lighting shadows, no highlights. "
            "TOP-RIGHT quadrant: HEIGHT/DISPLACEMENT map, grayscale where rounded cobblestone crowns are bright white and recessed dirt joints are black. "
            "BOTTOM-LEFT quadrant: ROUGHNESS map, grayscale where damp moss is dark and dry stone crowns are medium gray. "
            "BOTTOM-RIGHT quadrant: AMBIENT OCCLUSION map, deep black in the deep spaces between cobblestones. "
            "Strict 2x2 quadrant layout, orthographic top-down, clean quadrants."
        )
    },
    {
        "id": "ai_weathered_dark_timber",
        "category": "aged_wood",
        "name": "AI Generated Weathered Dark Timber Planks",
        "prompt": (
            "A seamless 2x2 texture map grid for 3D game material authoring representing weathered dark oak medieval timber beams and planks with visible wood grain and iron nail studs. "
            "TOP-LEFT quadrant: ALBEDO/BASE COLOR, flat diffuse texture of dark aged brown wood grain with dark iron studs, no cast shadows, no baked specular highlights. "
            "TOP-RIGHT quadrant: HEIGHT/DISPLACEMENT map, grayscale where wood surface and raised grain ridges/nails are light and deep splits/grain cracks are black. "
            "BOTTOM-LEFT quadrant: ROUGHNESS map, grayscale with rough dry grain and smoother polished spots. "
            "BOTTOM-RIGHT quadrant: AMBIENT OCCLUSION map, grayscale emphasizing deep grain grooves and plank seams. "
            "Strict 2x2 quadrant layout, orthographic, clean quadrant borders."
        )
    },
    {
        "id": "ai_terracotta_roof_tiles",
        "category": "roof_tile",
        "name": "AI Generated Terracotta Roof Tiles",
        "prompt": (
            "A seamless 2x2 texture map grid for 3D game material authoring representing overlapping curved medieval terracotta clay roof tiles with weathering and lichen. "
            "TOP-LEFT quadrant: ALBEDO/BASE COLOR, flat diffuse texture of warm orange-red Spanish-style barrel roof tiles with subtle yellow-green lichen specks, no sun shadows, no highlights. "
            "TOP-RIGHT quadrant: HEIGHT/DISPLACEMENT map, grayscale showing overlapping cylindrical curved tile ridges as smooth white-to-gray gradients and under-tile gaps as black. "
            "BOTTOM-LEFT quadrant: ROUGHNESS map, matte clay texture. "
            "BOTTOM-RIGHT quadrant: AMBIENT OCCLUSION map, dark shadows under the tile overhangs. "
            "Strict 2x2 quadrant layout, clean quadrants, orthographic."
        )
    }
]


def generate_material(mat_info: dict, client) -> dict:
    mat_id = mat_info["id"]
    out_folder = DEST_DIR / mat_id
    out_folder.mkdir(parents=True, exist_ok=True)
    meta_file = out_folder / "metadata.json"
    sheet_file = out_folder / "source_sheet_2x2.png"

    if sheet_file.is_file() and meta_file.is_file():
        print(f"Material {mat_id} already exists on disk, loading metadata...")
        return json.loads(meta_file.read_text(encoding="utf-8"))

    print(f"Generating 2x2 PBR sheet for {mat_id} using OpenAI image generation...")
    res = client.images.generate(
        model="gpt-image-1",
        prompt=mat_info["prompt"],
        size="1024x1024",
        n=1
    )
    b64_data = res.data[0].b64_json
    raw_bytes = base64.b64decode(b64_data)
    sheet_img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    sheet_img.save(sheet_file, "PNG")

    # Slice into 4 quadrants (512x512 each)
    w, h = sheet_img.size
    hw, hh = w // 2, h // 2
    albedo_img = sheet_img.crop((0, 0, hw, hh))
    height_img = sheet_img.crop((hw, 0, w, hh))
    rough_img = sheet_img.crop((0, hh, hw, h))
    ao_img = sheet_img.crop((hw, hh, w, h))

    albedo_path = out_folder / f"{mat_id}_albedo.png"
    height_path = out_folder / f"{mat_id}_height.png"
    rough_path = out_folder / f"{mat_id}_roughness.png"
    ao_path = out_folder / f"{mat_id}_ao.png"

    albedo_img.save(albedo_path, "PNG")
    height_img.save(height_path, "PNG")
    rough_img.save(rough_path, "PNG")
    ao_img.save(ao_path, "PNG")

    record = {
        "strategy": "openai_generated_pbr_sheet",
        "material_id": mat_id,
        "name": mat_info["name"],
        "category": mat_info["category"],
        "prompt": mat_info["prompt"],
        "model": "gpt-image-1",
        "generation_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_resolution": f"{w}x{h}",
        "derived_map_resolution": f"{hw}x{hh}",
        "derived_maps": {
            "albedo": str(albedo_path.relative_to(ROOT)).replace("\\", "/"),
            "height": str(height_path.relative_to(ROOT)).replace("\\", "/"),
            "roughness": str(rough_path.relative_to(ROOT)).replace("\\", "/"),
            "ao": str(ao_path.relative_to(ROOT)).replace("\\", "/")
        }
    }
    meta_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Generated {mat_id} and saved maps.")
    return record


def main():
    import openai
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    client = openai.OpenAI()
    manifest = []

    for mat_info in AI_MATERIALS:
        rec = generate_material(mat_info, client)
        manifest.append(rec)

    manifest_path = DEST_DIR / "generated_ai_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"AI PBR generation complete. Manifest saved to {manifest_path}")


if __name__ == "__main__":
    main()
