"""Test and comparison suite for edge treatments, film settings, and white-fringe elimination."""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = ROOT / "experiments" / "tiny-character-pipeline"
STUDY_DIR = EXPERIMENT_DIR / "renders" / "edge_study"
CONTACT_DIR = EXPERIMENT_DIR / "renders" / "contact_sheets"

ARCHETYPES = ["knight_volumetric", "rogue_faceted", "mage_planar"]
ARCHETYPE_LABELS = {
    "knight_volumetric": "Approach A: Knight",
    "rogue_faceted": "Approach B: Rogue",
    "mage_planar": "Approach C: Mage",
}


def color_dilate(rgb_arr: np.ndarray, alpha_arr: np.ndarray, threshold: int = 64) -> np.ndarray:
    """Extends the true surface color of solid pixels outward into transparent pixels.
    Eliminates any background color bleed (white, black, or gray) completely.
    """
    mask = alpha_arr > threshold
    if not np.any(mask):
        return rgb_arr.copy()

    # Find nearest solid pixel coordinates for every transparent pixel
    _, indices = distance_transform_edt(~mask, return_indices=True)
    dilated_rgb = rgb_arr[indices[0], indices[1]]
    return dilated_rgb


def process_true_surface_color(raw_img: Image.Image, target_size=(24, 24), alpha_thresh=110, sharpen=0.3):
    """Method A: True Surface Color Padding.
    Border pixels carry the exact color of the character's armor/fabric - ZERO white or dark halo.
    """
    img = raw_img.convert("RGBA")
    arr = np.array(img)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]

    # Dilate true surface colors into transparent areas
    dilated_rgb = color_dilate(rgb, alpha, threshold=64)
    rgb_clean_img = Image.fromarray(dilated_rgb, mode="RGB")

    if sharpen > 0:
        enhancer = ImageEnhance.Sharpness(rgb_clean_img)
        rgb_clean_img = enhancer.enhance(1.0 + sharpen)

    # Downsample RGB cleanly
    rgb_24 = rgb_clean_img.resize(target_size, resample=Image.Resampling.LANCZOS)

    # Downsample Alpha with Box filter to evaluate true coverage
    alpha_img = Image.fromarray(alpha, mode="L")
    alpha_24_soft = alpha_img.resize(target_size, resample=Image.Resampling.BOX)

    # Apply clean binary alpha threshold
    alpha_24_arr = np.array(alpha_24_soft)
    alpha_24_bin = np.where(alpha_24_arr >= alpha_thresh, 255, 0).astype(np.uint8)
    alpha_final = Image.fromarray(alpha_24_bin, mode="L")

    return Image.merge("RGBA", (*rgb_24.split(), alpha_final))


def process_dark_outline(raw_img: Image.Image, target_size=(24, 24), alpha_thresh=110, outline_color=(20, 22, 28)):
    """Method B: 1-Pixel Dark / Outlined Retro Sprite.
    Adds a clean, grounding 1-pixel dark rim around the solid boundary.
    """
    base_sprite = process_true_surface_color(raw_img, target_size, alpha_thresh=alpha_thresh, sharpen=0.3)
    arr = np.array(base_sprite)
    alpha = arr[:, :, 3]

    # Detect edge pixels of the 24x24 binary mask (pixels where a neighbor is 0)
    solid = alpha > 0
    padded = np.pad(solid, 1, mode="constant", constant_values=False)
    # Check 4-connected neighbors
    up = padded[:-2, 1:-1]
    down = padded[2:, 1:-1]
    left = padded[1:-1, :-2]
    right = padded[1:-1, 2:]

    is_edge = solid & (~(up & down & left & right))

    # Apply outline color on the edge pixels
    out_rgb = arr[:, :, :3].copy()
    out_rgb[is_edge] = outline_color

    return Image.merge("RGBA", (
        Image.fromarray(out_rgb[:, :, 0], mode="L"),
        Image.fromarray(out_rgb[:, :, 1], mode="L"),
        Image.fromarray(out_rgb[:, :, 2], mode="L"),
        Image.fromarray(alpha, mode="L"),
    ))


def process_soft_alpha_clamp(raw_img: Image.Image, target_size=(24, 24), min_clamp=0.25, max_clamp=0.85):
    """Method C: Alpha Clamp with Smoothstep interior.
    Clamps loose fringe while keeping tiny anti-aliased subpixel edge.
    """
    img = raw_img.convert("RGBA")
    arr = np.array(img)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]

    dilated_rgb = color_dilate(rgb, alpha, threshold=64)
    rgb_clean_img = Image.fromarray(dilated_rgb, mode="RGB")
    rgb_24 = rgb_clean_img.resize(target_size, resample=Image.Resampling.LANCZOS)

    alpha_img = Image.fromarray(alpha, mode="L")
    alpha_24_soft = alpha_img.resize(target_size, resample=Image.Resampling.BOX)
    a_norm = np.array(alpha_24_soft, dtype=np.float32) / 255.0

    # Smoothstep clamp
    a_clamped = np.clip((a_norm - min_clamp) / (max_clamp - min_clamp), 0.0, 1.0)
    a_final = Image.fromarray((a_clamped * 255.0).astype(np.uint8), mode="L")

    return Image.merge("RGBA", (*rgb_24.split(), a_final))


def make_checkered_background(w, h, cell_size=8, col1=(38, 42, 54), col2=(48, 52, 66)):
    bg = Image.new("RGBA", (w, h), col1)
    draw = ImageDraw.Draw(bg)
    for y in range(0, h, cell_size):
        for x in range(0, w, cell_size):
            if (x // cell_size + y // cell_size) % 2 == 1:
                draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=col2)
    return bg


def generate_edge_study():
    STUDY_DIR.mkdir(parents=True, exist_ok=True)
    CONTACT_DIR.mkdir(parents=True, exist_ok=True)

    methods = [
        ("Old Baseline (White Halo)", "old_white_halo"),
        ("A: True Surface Color (No Halo)", "true_surface_color"),
        ("B: 1-Pixel Dark Outline", "dark_outline"),
        ("C: Alpha Clamp (Steep Curve)", "alpha_clamp"),
    ]

    backdrops = [
        ("Pitch Black", (0, 0, 0, 255)),
        ("Dungeon Slate", (28, 32, 44, 255)),
        ("UI Parchment", (225, 218, 195, 255)),
        ("Checkered BG", None),
    ]

    cell_w, cell_h = 192, 192
    pad = 16
    header_h = 56
    title_w = 240

    sheet_w = title_w + (len(methods) * len(backdrops) * (cell_w // 2 + pad)) + pad
    # Let's organize cleanly: Grid with Methods as Rows or Backdrops as Columns
    # Let's make: Rows = Archetypes (3), Columns = 4 Methods, Sub-divided by 3 Backdrops!

    # Create master comparison sheet:
    col_w = cell_w
    cols_total = len(methods)
    master_w = title_w + cols_total * (col_w + pad) + pad
    master_h = header_h + len(ARCHETYPES) * (cell_h + pad) + pad

    for bd_name, bd_color in backdrops:
        sheet = Image.new("RGBA", (master_w, master_h), (20, 22, 28, 255))
        draw = ImageDraw.Draw(sheet)

        # Draw header
        for col_idx, (m_title, _) in enumerate(methods):
            x = title_w + col_idx * (col_w + pad) + pad + (col_w // 2)
            draw.text((x, 16), m_title, fill=(220, 235, 255), anchor="mt")

        for row_idx, arch_id in enumerate(ARCHETYPES):
            y = header_h + row_idx * (cell_h + pad) + pad
            label = ARCHETYPE_LABELS.get(arch_id, arch_id)
            draw.text((pad, y + (cell_h // 2)), label, fill=(240, 240, 245), anchor="lm")

            raw_path = EXPERIMENT_DIR / "renders" / "resolution_study" / f"{arch_id}_raw_48x48.png"
            if not raw_path.is_file():
                continue

            raw_img = Image.open(raw_path)

            for col_idx, (_, m_code) in enumerate(methods):
                if m_code == "old_white_halo":
                    # Simulate the un-padded white unpremult
                    old_path = EXPERIMENT_DIR / "renders" / "resolution_study" / f"{arch_id}_48px_crisp_plus_sharpen_24.png"
                    if old_path.is_file():
                        sprite_24 = Image.open(old_path)
                    else:
                        sprite_24 = raw_img.resize((24, 24), resample=Image.Resampling.LANCZOS)
                elif m_code == "true_surface_color":
                    sprite_24 = process_true_surface_color(raw_img, (24, 24), alpha_thresh=110, sharpen=0.35)
                elif m_code == "dark_outline":
                    sprite_24 = process_dark_outline(raw_img, (24, 24), alpha_thresh=110)
                elif m_code == "alpha_clamp":
                    sprite_24 = process_soft_alpha_clamp(raw_img, (24, 24))

                # Save individual 24 and 8x
                s_name = f"{arch_id}_{m_code}"
                sprite_24.save(STUDY_DIR / f"{s_name}_24.png")
                sprite_8x = sprite_24.resize((192, 192), resample=Image.Resampling.NEAREST)
                sprite_8x.save(STUDY_DIR / f"{s_name}_8x.png")

                cell_x = title_w + col_idx * (col_w + pad) + pad
                if bd_color is None:
                    cell_bg = make_checkered_background(cell_w, cell_h, cell_size=12)
                else:
                    cell_bg = Image.new("RGBA", (cell_w, cell_h), bd_color)

                cell_bg.paste(sprite_8x, (0, 0), mask=sprite_8x)
                sheet.paste(cell_bg, (cell_x, y))
                draw.rectangle([cell_x - 1, y - 1, cell_x + cell_w, y + cell_h], outline=(55, 62, 78))

        tag = bd_name.replace(" ", "_").lower()
        out_p = CONTACT_DIR / f"edge_treatment_on_{tag}_8x.png"
        sheet.save(out_p)
        print(f"SAVED: {out_p}")


if __name__ == "__main__":
    generate_edge_study()
