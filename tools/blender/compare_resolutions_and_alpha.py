"""Compares supersampling resolutions and downsampling de-haloing/crisp-alpha techniques."""

from __future__ import annotations

import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = ROOT / "experiments" / "tiny-character-pipeline"
STUDY_DIR = EXPERIMENT_DIR / "renders" / "resolution_study"
CONTACT_DIR = EXPERIMENT_DIR / "renders" / "contact_sheets"

ARCHETYPES = ["knight_volumetric", "rogue_faceted", "mage_planar"]
ARCHETYPE_LABELS = {
    "knight_volumetric": "Approach A: Knight",
    "rogue_faceted": "Approach B: Rogue",
    "mage_planar": "Approach C: Mage",
}


def process_variant(
    raw_img: Image.Image,
    target_size=(24, 24),
    alpha_mode="crisp_binary",
    alpha_threshold=120,
    sharpen_amount=0.0,
):
    """Processes a raw render into 24x24 with specified alpha handling and sharpness."""
    img = raw_img.convert("RGBA")

    if sharpen_amount > 0:
        rgb = img.convert("RGB")
        enhancer = ImageEnhance.Sharpness(rgb)
        rgb = enhancer.enhance(1.0 + sharpen_amount)
        img.paste(rgb, (0, 0), mask=img.split()[3])

    if alpha_mode == "standard_soft":
        # The old baseline: continuous Lanczos interpolation of RGBA
        return img.resize(target_size, resample=Image.Resampling.LANCZOS)

    # Crisp Hard-Alpha De-haloing Pipeline:
    arr = np.array(img, dtype=np.float32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]

    # Unpremultiply RGB to preserve true surface colors at border
    alpha_norm = np.maximum(a / 255.0, 1e-4)
    r_unpre = np.clip(r / alpha_norm, 0, 255)
    g_unpre = np.clip(g / alpha_norm, 0, 255)
    b_unpre = np.clip(b / alpha_norm, 0, 255)

    unpre_rgb = np.stack([r_unpre, g_unpre, b_unpre], axis=2).astype(np.uint8)
    rgb_img = Image.fromarray(unpre_rgb, mode="RGB")
    alpha_img = Image.fromarray(a.astype(np.uint8), mode="L")

    # Downsample RGB with Lanczos for smooth internal shading
    rgb_24 = rgb_img.resize(target_size, resample=Image.Resampling.LANCZOS)

    # Downsample Alpha with Box/Area average to measure subpixel coverage
    alpha_24_soft = alpha_img.resize(target_size, resample=Image.Resampling.BOX)

    if alpha_mode == "crisp_binary":
        alpha_arr = np.array(alpha_24_soft)
        alpha_bin = np.where(alpha_arr >= alpha_threshold, 255, 0).astype(np.uint8)
        alpha_final = Image.fromarray(alpha_bin, mode="L")
    elif alpha_mode == "steep_contrast":
        # Steep S-curve alpha: keeps tiny subpixel edge anti-aliasing but clips loose halo
        alpha_arr = np.array(alpha_24_soft, dtype=np.float32) / 255.0
        alpha_steep = np.clip((alpha_arr - 0.25) / (0.75 - 0.25), 0.0, 1.0) * 255.0
        alpha_final = Image.fromarray(alpha_steep.astype(np.uint8), mode="L")
    else:
        alpha_final = alpha_24_soft

    return Image.merge("RGBA", (*rgb_24.split(), alpha_final))


def make_checkered_background(w, h, cell_size=8, col1=(38, 42, 54), col2=(48, 52, 66)):
    bg = Image.new("RGBA", (w, h), col1)
    draw = ImageDraw.Draw(bg)
    for y in range(0, h, cell_size):
        for x in range(0, w, cell_size):
            if (x // cell_size + y // cell_size) % 2 == 1:
                draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=col2)
    return bg


def generate_comparisons():
    STUDY_DIR.mkdir(parents=True, exist_ok=True)
    CONTACT_DIR.mkdir(parents=True, exist_ok=True)

    pipelines = [
        ("Old Baseline (192px Soft)", 192, "standard_soft", 0, 0.0),
        ("192px + Binary Alpha", 192, "crisp_binary", 120, 0.0),
        ("96px + Binary Alpha", 96, "crisp_binary", 120, 0.0),
        ("72px + Binary Alpha", 72, "crisp_binary", 120, 0.2),
        ("48px Crisp (2x Native)", 48, "crisp_binary", 110, 0.0),
        ("48px Crisp + Sharpen", 48, "crisp_binary", 110, 0.4),
    ]

    cell_w, cell_h = 192, 192
    pad = 16
    header_h = 56
    title_w = 260

    sheet_w = title_w + (len(pipelines) * (cell_w + pad)) + pad
    sheet_h = header_h + (len(ARCHETYPES) * (cell_h + pad)) + pad

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (20, 22, 28, 255))
    draw = ImageDraw.Draw(sheet)

    # Draw header
    for col_idx, (p_name, _, _, _, _) in enumerate(pipelines):
        x = title_w + col_idx * (cell_w + pad) + pad + (cell_w // 2)
        draw.text((x, 16), p_name, fill=(220, 235, 255), anchor="mt")

    for row_idx, arch_id in enumerate(ARCHETYPES):
        y = header_h + row_idx * (cell_h + pad) + pad
        label = ARCHETYPE_LABELS.get(arch_id, arch_id)
        draw.text((pad, y + (cell_h // 2)), label, fill=(240, 240, 245), anchor="lm")

        for col_idx, (p_name, res, alpha_mode, thresh, sh) in enumerate(pipelines):
            raw_path = STUDY_DIR / f"{char_id if 'char_id' in locals() else arch_id}_raw_{res}x{res}.png"
            if not raw_path.is_file():
                continue

            raw_img = Image.open(raw_path)
            sprite_24 = process_variant(
                raw_img,
                target_size=(24, 24),
                alpha_mode=alpha_mode,
                alpha_threshold=thresh,
                sharpen_amount=sh,
            )

            # Save individual 24x24 and 8x
            tag = p_name.replace(" ", "_").replace("(", "").replace(")", "").replace("+", "plus").lower()
            out_24 = STUDY_DIR / f"{arch_id}_{tag}_24.png"
            out_8x = STUDY_DIR / f"{arch_id}_{tag}_8x.png"
            sprite_24.save(out_24)

            sprite_8x = sprite_24.resize((192, 192), resample=Image.Resampling.NEAREST)
            sprite_8x.save(out_8x)

            # Composite onto dark checkered cell
            cell_x = title_w + col_idx * (cell_w + pad) + pad
            cell_bg = make_checkered_background(cell_w, cell_h, cell_size=12)
            cell_bg.paste(sprite_8x, (0, 0), mask=sprite_8x)

            sheet.paste(cell_bg, (cell_x, y))
            draw.rectangle([cell_x - 1, y - 1, cell_x + cell_w, y + cell_h], outline=(55, 62, 78))

    study_sheet = CONTACT_DIR / "alpha_and_resolution_study_8x.png"
    sheet.save(study_sheet)
    print(f"SAVED STUDY CONTACT SHEET: {study_sheet}")

    # Generate Backdrop Test Sheet (Testing against Black, Dark Stone, and Bright Parchment)
    generate_backdrop_test_sheet()


def generate_backdrop_test_sheet():
    """Renders 48px Crisp + Binary Alpha sprites against 3 real in-game backdrop colors."""
    backdrops = [
        ("Pitch Black (RGB 0,0,0)", (0, 0, 0, 255)),
        ("Dungeon Slate (RGB 28,32,44)", (28, 32, 44, 255)),
        ("UI Parchment (RGB 225,218,195)", (225, 218, 195, 255)),
        ("Lava Ember (RGB 80,24,16)", (80, 24, 16, 255)),
    ]

    cell_w, cell_h = 192, 192
    pad = 16
    header_h = 56
    title_w = 260

    sheet_w = title_w + (len(backdrops) * (cell_w + pad)) + pad
    sheet_h = header_h + (len(ARCHETYPES) * (cell_h + pad)) + pad

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (20, 22, 28, 255))
    draw = ImageDraw.Draw(sheet)

    for col_idx, (b_name, _) in enumerate(backdrops):
        x = title_w + col_idx * (cell_w + pad) + pad + (cell_w // 2)
        draw.text((x, 16), b_name, fill=(220, 235, 255), anchor="mt")

    for row_idx, arch_id in enumerate(ARCHETYPES):
        y = header_h + row_idx * (cell_h + pad) + pad
        label = ARCHETYPE_LABELS.get(arch_id, arch_id)
        draw.text((pad, y + (cell_h // 2)), label, fill=(240, 240, 245), anchor="lm")

        # Load 48px raw frame
        raw_path = STUDY_DIR / f"{arch_id}_raw_48x48.png"
        if not raw_path.is_file():
            continue

        raw_img = Image.open(raw_path)
        sprite_24 = process_variant(
            raw_img,
            target_size=(24, 24),
            alpha_mode="crisp_binary",
            alpha_threshold=110,
            sharpen_amount=0.35,
        )
        sprite_8x = sprite_24.resize((192, 192), resample=Image.Resampling.NEAREST)

        for col_idx, (b_name, b_col) in enumerate(backdrops):
            cell_x = title_w + col_idx * (cell_w + pad) + pad
            cell_bg = Image.new("RGBA", (cell_w, cell_h), b_col)
            cell_bg.paste(sprite_8x, (0, 0), mask=sprite_8x)

            sheet.paste(cell_bg, (cell_x, y))
            draw.rectangle([cell_x - 1, y - 1, cell_x + cell_w, y + cell_h], outline=(55, 62, 78))

    backdrop_sheet = CONTACT_DIR / "backdrop_dehaloing_test_8x.png"
    sheet.save(backdrop_sheet)
    print(f"SAVED BACKDROP TEST SHEET: {backdrop_sheet}")


if __name__ == "__main__":
    generate_comparisons()
