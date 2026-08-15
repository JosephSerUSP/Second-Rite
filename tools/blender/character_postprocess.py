"""Post-processing, downsampling, inspection image generation, and metric analysis for tiny 24x24 character pipeline."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageStat, ImageEnhance

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = ROOT / "experiments" / "tiny-character-pipeline"
RAW_DIR = EXPERIMENT_DIR / "raw_frames"
RENDERS_24_DIR = EXPERIMENT_DIR / "renders" / "24x24"
RENDERS_8X_DIR = EXPERIMENT_DIR / "renders" / "enlarged_8x"
ANIMATIONS_DIR = EXPERIMENT_DIR / "renders" / "animations"
DIRECTIONS_DIR = EXPERIMENT_DIR / "renders" / "directions"
REFERENCE_DIR = EXPERIMENT_DIR / "renders" / "reference_highres"
CONTACT_DIR = EXPERIMENT_DIR / "renders" / "contact_sheets"
ROUNDS_DIR = EXPERIMENT_DIR / "renders" / "gauntlet_rounds"

DIRECTIONS = [
    "south",
    "south_east",
    "east",
    "north_east",
    "north",
    "north_west",
    "west",
    "south_west",
]

ARCHETYPES = ["knight_volumetric", "rogue_faceted", "mage_planar"]
ARCHETYPE_LABELS = {
    "knight_volumetric": "Approach A: Volumetric Knight",
    "rogue_faceted": "Approach B: Faceted Rogue",
    "mage_planar": "Approach C: Planar Mage",
}


def ensure_postprocess_directories():
    for d in (
        RENDERS_24_DIR,
        RENDERS_8X_DIR,
        ANIMATIONS_DIR,
        DIRECTIONS_DIR,
        REFERENCE_DIR,
        CONTACT_DIR,
        ROUNDS_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


import numpy as np
from scipy.ndimage import distance_transform_edt


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


def downsample_image(
    src_path: Path,
    dst_24_path: Path,
    dst_8x_path: Path = None,
    filter_mode=Image.Resampling.LANCZOS,
    alpha_threshold=110,
    sharpen_amount=0.35,
):
    """Downsamples a 48x48 supersampled image to 24x24 using True Surface Color Dilation:
    - Dilates genuine character surface colors (steel, gold, fabric, porcelain) into margin.
    - Preserves smooth internal normal/specular anti-aliasing.
    - Enforces binary Alpha threshold (100% solid inside, 0% outside - zero semi-transparent edge artifacts).
    - ZERO white halo, ZERO black halo on any background!
    """
    raw_img = Image.open(src_path).convert("RGBA")
    arr = np.array(raw_img)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]

    # Dilate true surface colors outward
    dilated_rgb = color_dilate(rgb, alpha, threshold=64)
    rgb_clean_img = Image.fromarray(dilated_rgb, mode="RGB")

    if sharpen_amount > 0:
        enhancer = ImageEnhance.Sharpness(rgb_clean_img)
        rgb_clean_img = enhancer.enhance(1.0 + sharpen_amount)

    # Downsample RGB cleanly (smooth interior AA)
    rgb_24 = rgb_clean_img.resize((24, 24), resample=filter_mode)

    # Downsample Alpha with Box/Area average to evaluate true coverage
    alpha_img = Image.fromarray(alpha, mode="L")
    alpha_24_soft = alpha_img.resize((24, 24), resample=Image.Resampling.BOX)

    # Apply clean binary alpha threshold
    alpha_24_arr = np.array(alpha_24_soft)
    alpha_24_bin = np.where(alpha_24_arr >= alpha_threshold, 255, 0).astype(np.uint8)
    alpha_final = Image.fromarray(alpha_24_bin, mode="L")

    img_24 = Image.merge("RGBA", (*rgb_24.split(), alpha_final))
    img_24.save(dst_24_path, format="PNG")

    if dst_8x_path:
        img_8x = img_24.resize((192, 192), resample=Image.Resampling.NEAREST)
        img_8x.save(dst_8x_path, format="PNG")

    return img_24


def process_all_raw_frames(filter_mode=Image.Resampling.LANCZOS):
    """Processes all raw rendered frames in raw_frames/ and creates 24x24 + 8x versions."""
    ensure_postprocess_directories()
    stats_by_char = {}

    for arch_id in ARCHETYPES:
        char_raw_dir = RAW_DIR / arch_id
        if not char_raw_dir.is_dir():
            continue

        char_24_dir = RENDERS_24_DIR / arch_id
        char_8x_dir = RENDERS_8X_DIR / arch_id
        char_24_dir.mkdir(parents=True, exist_ok=True)
        char_8x_dir.mkdir(parents=True, exist_ok=True)

        # Process directions
        for d in DIRECTIONS:
            raw_path = char_raw_dir / f"dir_{d}_raw.png"
            if raw_path.is_file():
                out_24 = char_24_dir / f"dir_{d}.png"
                out_8x = char_8x_dir / f"dir_{d}_8x.png"
                downsample_image(raw_path, out_24, out_8x, filter_mode=filter_mode)

        # Process animation frames
        for anim in ("idle", "walk", "gesture"):
            frames_24 = []
            frames_8x = []
            frame_num = 1
            while True:
                raw_path = char_raw_dir / f"{anim}_f{frame_num:02d}_raw.png"
                if not raw_path.is_file():
                    break
                out_24 = char_24_dir / f"{anim}_f{frame_num:02d}.png"
                out_8x = char_8x_dir / f"{anim}_f{frame_num:02d}_8x.png"
                img_24 = downsample_image(raw_path, out_24, out_8x, filter_mode=filter_mode)
                frames_24.append(img_24)
                frames_8x.append(Image.open(out_8x))
                frame_num += 1

            if frames_24:
                duration = 100 if anim != "walk" else 80
                gif_24 = ANIMATIONS_DIR / f"{arch_id}_{anim}_24x24.gif"
                frames_24[0].save(
                    gif_24,
                    save_all=True,
                    append_images=frames_24[1:],
                    duration=duration,
                    loop=0,
                    disposal=2,
                )
                gif_8x = ANIMATIONS_DIR / f"{arch_id}_{anim}_8x.gif"
                frames_8x[0].save(
                    gif_8x,
                    save_all=True,
                    append_images=frames_8x[1:],
                    duration=duration,
                    loop=0,
                    disposal=2,
                )

        # Compute pixel statistics for South (front) facing
        south_24 = char_24_dir / "dir_south.png"
        if south_24.is_file():
            stats = analyze_pixel_metrics(south_24)
            stats_by_char[arch_id] = stats

    return stats_by_char


def analyze_pixel_metrics(image_path: Path) -> dict:
    """Computes silhouette fill, non-zero pixel count, luminance dynamic range, and color statistics for a 24x24 image."""
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size
    total_pixels = w * h
    
    opaque_count = 0
    luminances = []
    unique_colors = set()

    for y in range(h):
        for x in range(w):
            r, g, b, a = img.getpixel((x, y))
            if a > 32:
                opaque_count += 1
                unique_colors.add((r, g, b))
                # Standard relative luminance (sRGB / Rec.709)
                lum = 0.2126 * (r / 255.0) + 0.7152 * (g / 255.0) + 0.0722 * (b / 255.0)
                luminances.append(lum)

    coverage_pct = round((opaque_count / total_pixels) * 100, 1)
    if luminances:
        min_lum = min(luminances)
        max_lum = max(luminances)
        mean_lum = sum(luminances) / len(luminances)
        variance = sum((x - mean_lum) ** 2 for x in luminances) / len(luminances)
        std_lum = math.sqrt(variance)
        contrast_ratio = (max_lum + 0.05) / (min_lum + 0.05)
    else:
        min_lum = max_lum = mean_lum = std_lum = contrast_ratio = 0.0

    return {
        "totalPixels": total_pixels,
        "occupiedPixels": opaque_count,
        "coveragePercent": coverage_pct,
        "uniqueColorCount": len(unique_colors),
        "minLuminance": round(min_lum, 3),
        "maxLuminance": round(max_lum, 3),
        "meanLuminance": round(mean_lum, 3),
        "contrastStandardDeviation": round(std_lum, 3),
        "contrastRatio": round(contrast_ratio, 2),
    }


def build_directional_contact_sheet() -> Path:
    """Builds side-by-side 8-direction comparison sheet for all 3 archetypes."""
    cell_w, cell_h = 192, 192
    pad = 16
    header_h = 48
    title_w = 260

    sheet_w = title_w + (len(DIRECTIONS) * (cell_w + pad)) + pad
    sheet_h = header_h + (len(ARCHETYPES) * (cell_h + pad)) + pad

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (22, 24, 30, 255))
    draw = ImageDraw.Draw(sheet)

    for col_idx, dir_name in enumerate(DIRECTIONS):
        x = title_w + col_idx * (cell_w + pad) + pad + (cell_w // 2)
        draw.text((x, 16), dir_name.upper().replace("_", "-"), fill=(210, 220, 235), anchor="mt")

    for row_idx, arch_id in enumerate(ARCHETYPES):
        y = header_h + row_idx * (cell_h + pad) + pad
        label = ARCHETYPE_LABELS.get(arch_id, arch_id)
        draw.text((pad, y + (cell_h // 2)), label, fill=(240, 240, 245), anchor="lm")

        for col_idx, dir_name in enumerate(DIRECTIONS):
            img_path = RENDERS_8X_DIR / arch_id / f"dir_{dir_name}_8x.png"
            cell_x = title_w + col_idx * (cell_w + pad) + pad
            draw.rectangle([cell_x - 1, y - 1, cell_x + cell_w, y + cell_h], outline=(42, 48, 62), fill=(16, 18, 22, 255))
            if img_path.is_file():
                cell_img = Image.open(img_path).convert("RGBA")
                sheet.paste(cell_img, (cell_x, y), mask=cell_img)

    out_sheet = CONTACT_DIR / "directional_comparison_8x.png"
    sheet.save(out_sheet)
    print(f"SAVED: {out_sheet}")
    return out_sheet


def build_walk_cycle_contact_sheet() -> Path:
    """Builds side-by-side walk cycle frame contact sheet."""
    cell_w, cell_h = 192, 192
    pad = 12
    header_h = 44
    title_w = 200
    frame_indices = list(range(1, 17, 2)) # 8 key steps

    sheet_w = title_w + (len(frame_indices) * (cell_w + pad)) + pad
    sheet_h = header_h + (len(ARCHETYPES) * (cell_h + pad)) + pad

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (20, 22, 28, 255))
    draw = ImageDraw.Draw(sheet)

    for col_idx, f_idx in enumerate(frame_indices):
        x = title_w + col_idx * (cell_w + pad) + pad + (cell_w // 2)
        draw.text((x, 14), f"Walk Step {f_idx}", fill=(185, 200, 220), anchor="mt")

    for row_idx, arch_id in enumerate(ARCHETYPES):
        y = header_h + row_idx * (cell_h + pad) + pad
        label = ARCHETYPE_LABELS.get(arch_id, arch_id)
        draw.text((pad, y + (cell_h // 2)), label, fill=(230, 235, 245), anchor="lm")

        for col_idx, f_idx in enumerate(frame_indices):
            img_path = RENDERS_8X_DIR / arch_id / f"walk_f{f_idx:02d}_8x.png"
            cell_x = title_w + col_idx * (cell_w + pad) + pad
            draw.rectangle([cell_x - 1, y - 1, cell_x + cell_w, y + cell_h], outline=(38, 44, 56), fill=(14, 16, 20, 255))
            if img_path.is_file():
                cell_img = Image.open(img_path).convert("RGBA")
                sheet.paste(cell_img, (cell_x, y), mask=cell_img)

    out_sheet = CONTACT_DIR / "walk_cycle_contact_sheet_8x.png"
    sheet.save(out_sheet)
    print(f"SAVED: {out_sheet}")
    return out_sheet


def archive_gauntlet_round(round_number: int, notes: str):
    """Archives the current renders into a gauntlet round folder and creates an evolutionary contact sheet."""
    r_dir = ROUNDS_DIR / f"round_{round_number:02d}"
    r_dir.mkdir(parents=True, exist_ok=True)

    round_manifest = {
        "round": round_number,
        "notes": notes,
        "characters": {},
    }

    for arch_id in ARCHETYPES:
        char_dst = r_dir / arch_id
        char_dst.mkdir(parents=True, exist_ok=True)
        # Copy key still (South), 45-deg (South-East), and high-res
        for src_name in ("dir_south.png", "dir_south_8x.png", "dir_south_east.png", "dir_south_east_8x.png"):
            src_p = (RENDERS_24_DIR if "8x" not in src_name else RENDERS_8X_DIR) / arch_id / src_name
            if src_p.is_file():
                img = Image.open(src_p)
                img.save(char_dst / src_name)

        south_p = RENDERS_24_DIR / arch_id / "dir_south.png"
        if south_p.is_file():
            round_manifest["characters"][arch_id] = analyze_pixel_metrics(south_p)

    with (r_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(round_manifest, f, indent=2)

    print(f"ARCHIVED GAUNTLET ROUND {round_number}: {notes}")
    return round_manifest


def build_gauntlet_evolution_sheet() -> Path:
    """Builds a comparison sheet tracking the visual evolution across all completed gauntlet rounds."""
    round_dirs = sorted([d for d in ROUNDS_DIR.glob("round_*") if d.is_dir()])
    if not round_dirs:
        return None

    cell_w, cell_h = 192, 192
    pad = 16
    header_h = 56
    title_w = 260

    sheet_w = title_w + (len(round_dirs) * (cell_w + pad)) + pad
    sheet_h = header_h + (len(ARCHETYPES) * (cell_h + pad)) + pad

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (24, 26, 32, 255))
    draw = ImageDraw.Draw(sheet)

    for col_idx, r_dir in enumerate(round_dirs):
        manifest_p = r_dir / "manifest.json"
        note = f"Round {col_idx + 1}"
        if manifest_p.is_file():
            try:
                data = json.loads(manifest_p.read_text(encoding="utf-8"))
                note = f"R{data.get('round', col_idx+1)}: {data.get('notes', '')[:18]}"
            except Exception:
                pass
        x = title_w + col_idx * (cell_w + pad) + pad + (cell_w // 2)
        draw.text((x, 18), note, fill=(220, 230, 245), anchor="mt")

    for row_idx, arch_id in enumerate(ARCHETYPES):
        y = header_h + row_idx * (cell_h + pad) + pad
        label = ARCHETYPE_LABELS.get(arch_id, arch_id)
        draw.text((pad, y + (cell_h // 2)), label, fill=(240, 240, 245), anchor="lm")

        for col_idx, r_dir in enumerate(round_dirs):
            img_path = r_dir / arch_id / "dir_south_8x.png"
            cell_x = title_w + col_idx * (cell_w + pad) + pad
            draw.rectangle([cell_x - 1, y - 1, cell_x + cell_w, y + cell_h], outline=(48, 54, 70), fill=(16, 18, 24, 255))
            if img_path.is_file():
                cell_img = Image.open(img_path).convert("RGBA")
                sheet.paste(cell_img, (cell_x, y), mask=cell_img)

    out_sheet = CONTACT_DIR / "gauntlet_evolution_8x.png"
    sheet.save(out_sheet)
    print(f"SAVED EVOLUTION CONTACT SHEET: {out_sheet}")
    return out_sheet


if __name__ == "__main__":
    stats = process_all_raw_frames()
    build_directional_contact_sheet()
    build_walk_cycle_contact_sheet()
    print("Post-processing complete. Stats:", json.dumps(stats, indent=2))
