"""Generate image-assisted architectural facade treatments using OpenAI API.

Produces multiple treatments for Direction A (Cinder-Quay) and Direction B (Bell-Weir),
processes images, derives estimated height/displacement maps, and records full provenance.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps
import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[2]
TREATMENTS_DIR = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "second_gate_gauntlet" / "facade_treatments"


TREATMENT_SPECS = [
    # Direction A
    {
        "id": "A1_cinder_quay_apothecary",
        "direction": "direction_a",
        "target_objects": ["SRC_Apothecary_2F_Mass", "SRC_Apothecary_3F_Mass"],
        "prompt": (
            "Frontal architectural orthographic facade of an ancient gothic medieval apothecary guildhouse, "
            "dark hand-hewn timber jetty beams, aged lime plaster infill with cracked patina, "
            "large cantilevered second floor supported by carved wooden gargoyle corbels, "
            "protruding octagonal bay window with glowing amber leaded glass diamond panes, "
            "herbalist painted wooden signboard showing brass mortar and pestle, hanging dried lavender bundles, "
            "dark damp stone masonry ground floor with arched doorway, slate tile roof shingles, "
            "rich atmospheric dark fantasy JRPG background art style, ultra-detailed architectural textures."
        ),
    },
    {
        "id": "A2_cinder_wharf_embalmer",
        "direction": "direction_a",
        "target_objects": ["SRC_Apothecary_2F_Mass", "SRC_Apothecary_3F_Mass"],
        "prompt": (
            "Frontal architectural orthographic facade of a gloomy gothic embalmers' lodge and mortuary scriptorium, "
            "charcoal-blackened oak timbers, steep dark grey slate roofs, "
            "pointed gothic arched windows with cold lantern glow, "
            "carved stone moth and raven heraldic relief seals above the heavy iron-studded doorway, "
            "damp moss and green canal water staining along the lower ashlar masonry foundation, "
            "worn wood planking, dark fantasy JRPG game background art style."
        ),
    },
    {
        "id": "A3_river_customs_house",
        "direction": "direction_a",
        "target_objects": ["SRC_Apothecary_2F_Mass", "SRC_Apothecary_3F_Mass"],
        "prompt": (
            "Frontal architectural orthographic facade of a prosperous river wharf guildhouse and customs station, "
            "rich reddish-brown timber framing with painted geometric patterns, "
            "leaded glass casement windows, brass scales of commerce insignia over arched entrance portal, "
            "copper drain pipes with verdigris patina, clay chimney pots, stacked cargo barrels, "
            "dark fantasy JRPG game art style."
        ),
    },
    # Direction B
    {
        "id": "B1_bell_weir_foundry",
        "direction": "direction_b",
        "target_objects": ["SRC_Foundry_Base_Left", "SRC_Foundry_Base_Right", "SRC_Foundry_CupolaDrum"],
        "prompt": (
            "Frontal architectural orthographic facade of a monumental medieval industrial copper foundry and cloister, "
            "heavy Romanesque brick arches blackened with coal soot, "
            "weathered oxidized verdigris turquoise copper dome and cladding with heavy iron rivets, "
            "massive arched kiln portal with glowing fiery molten orange furnace light pouring out, "
            "iron exhaust flues and venting grates, dark fantasy JRPG background art style, industrial-sacred cathedral aesthetic."
        ),
    },
    {
        "id": "B2_sacred_bell_founders_abbey",
        "direction": "direction_b",
        "target_objects": ["SRC_Foundry_Base_Left", "SRC_Foundry_Base_Right", "SRC_Foundry_CupolaDrum"],
        "prompt": (
            "Frontal architectural orthographic facade of an ancient monastic bell foundry abbey, "
            "monumental soot-stained grey granite flying buttresses and arched cloister niches, "
            "sculpted bronze relief medallions of saints and bells, heavy iron-banded double doors, "
            "glowing alchemical crucibles in lower venting arches, high copper cupola with verdigris patina, "
            "dark fantasy JRPG game background art style."
        ),
    },
    {
        "id": "B3_alchemical_smelting_vault",
        "direction": "direction_b",
        "target_objects": ["SRC_Foundry_Base_Left", "SRC_Foundry_Base_Right", "SRC_Foundry_CupolaDrum"],
        "prompt": (
            "Frontal architectural orthographic facade of a dark volcanic stone alchemical forge and water-weir sluice gate, "
            "massive dark basalt masonry blocks, glowing orange rune vents, "
            "heavy verdigris brass steam pipes and iron tie-rods, heavy vaulted kiln doorway with thick riveted iron doors, "
            "dark atmospheric JRPG environmental art."
        ),
    },
]


def generate_image_openai(prompt: str, api_key: str, out_path: Path) -> dict:
    """Call OpenAI DALL-E 3 / DALL-E 2 to generate an image."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
    }
    print(f"[openai] Generating image for prompt: {prompt[:60]}...")
    resp = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=payload, timeout=90)
    if resp.status_code != 200:
        print(f"[openai] DALL-E 3 returned {resp.status_code}: {resp.text}. Trying DALL-E 2...")
        payload["model"] = "dall-e-2"
        payload["size"] = "1024x1024"
        resp = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"OpenAI image generation failed: {resp.status_code} - {resp.text}")

    data = resp.json()
    img_entry = data["data"][0]
    if "url" in img_entry:
        img_url = img_entry["url"]
        img_resp = requests.get(img_url, timeout=60)
        out_path.write_bytes(img_resp.content)
    elif "b64_json" in img_entry:
        out_path.write_bytes(base64.b64decode(img_entry["b64_json"]))
    else:
        raise ValueError("No url or b64_json in response")

    print(f"[openai] Saved image to {out_path}")
    return {
        "model": payload["model"],
        "revised_prompt": img_entry.get("revised_prompt", prompt),
    }


def derive_height_map(image_path: Path, out_path: Path):
    """Derive estimated height/relief map from facade diffuse image."""
    img = Image.open(image_path).convert("L")
    # Enhance local contrast and smooth high-frequency noise
    arr = np.array(img, dtype=np.float32) / 255.0
    # Invert so recessed areas (shadows/crevices) are lower height
    # Apply bilateral-like smoothing
    smoothed = Image.fromarray((arr * 255.0).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=2))
    edges = smoothed.filter(ImageFilter.FIND_EDGES)
    # Combine luminance and edge relief
    arr_smooth = np.array(smoothed, dtype=np.float32)
    arr_edges = np.array(edges, dtype=np.float32)
    relief = np.clip(arr_smooth - arr_edges * 0.3, 0.0, 255.0).astype(np.uint8)
    height_img = Image.fromarray(relief)
    height_img.save(out_path)
    print(f"[height] Saved derived height map to {out_path}")


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[generator] OPENAI_API_KEY not found in environment; using local procedural synthesis fallback.")

    TREATMENTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    for spec in TREATMENT_SPECS:
        t_id = spec["id"]
        t_dir = TREATMENTS_DIR / t_id
        t_dir.mkdir(parents=True, exist_ok=True)

        image_path = t_dir / "facade.png"
        height_path = t_dir / "height.png"
        meta_path = t_dir / "treatment.json"

        model_info = {"model": "local_fallback", "revised_prompt": spec["prompt"]}
        if api_key and not image_path.exists():
            try:
                model_info = generate_image_openai(spec["prompt"], api_key, image_path)
                # Sleep briefly to avoid API rate limits
                time.sleep(2.0)
            except Exception as e:
                print(f"[error] Failed generating {t_id} via OpenAI: {e}")

        if not image_path.exists():
            print(f"[generator] Generating procedural texture for {t_id}...")
            # Create rich high-res architectural texture matching the prompt theme
            w, h = 1024, 1024
            if spec["direction"] == "direction_a":
                # Medieval timber frame with plaster and leaded windows
                arr = np.zeros((h, w, 3), dtype=np.uint8)
                # Base plaster
                arr[:, :] = [165, 158, 140]
                # Heavy timber grid
                for y in (0, 300, 650, 1000):
                    arr[max(0, y-25):min(h, y+25), :] = [55, 40, 28]
                for x in (0, 250, 500, 750, 1000):
                    arr[:, max(0, x-20):min(w, x+20)] = [55, 40, 28]
                # Diagonal timber braces
                for i in range(250):
                    if i < h and i < w:
                        arr[i+300:i+325, i:i+25] = [50, 35, 25]
                        arr[i+300:i+325, 500-i:525-i] = [50, 35, 25]
                # Leaded amber glass windows
                arr[400:600, 320:440] = [215, 175, 75]
                arr[400:600, 560:680] = [215, 175, 75]
                # Lower damp stone base
                arr[750:, :] = [90, 95, 100]
                img = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=1))
                img.save(image_path)
            else:
                # Industrial monastic brick & verdigris copper
                arr = np.zeros((h, w, 3), dtype=np.uint8)
                # Brick base
                arr[:, :] = [80, 55, 45]
                # Verdigris copper dome upper band
                arr[:350, :] = [55, 122, 112]
                # Iron rivet bands
                for y in (340, 360, 680, 700):
                    arr[y-8:y+8, :] = [30, 30, 32]
                # Arched kiln portal with fiery glow
                for y in range(400, 900):
                    for x in range(350, 674):
                        dx = (x - 512) / 160.0
                        dy = (y - 550) / 350.0
                        if dy > 0 or dx*dx + dy*dy <= 1.0:
                            arr[y, x] = [255, 115, 25]
                # Soot darkening
                for y in range(h):
                    factor = max(0.4, 1.0 - (abs(y - 500) / 600.0) * 0.5)
                    arr[y, :] = (arr[y, :] * factor).astype(np.uint8)
                img = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=1))
                img.save(image_path)

        if not height_path.exists():
            derive_height_map(image_path, height_path)

        record = {
            "id": t_id,
            "direction": spec["direction"],
            "target_objects": spec["target_objects"],
            "prompt": spec["prompt"],
            "image": str(image_path.relative_to(ROOT)),
            "height_image": str(height_path.relative_to(ROOT)),
            "provenance": model_info,
        }
        meta_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        manifest.append(record)

    (TREATMENTS_DIR / "treatments_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[generator] Successfully generated {len(manifest)} facade treatments.")


if __name__ == "__main__":
    main()
