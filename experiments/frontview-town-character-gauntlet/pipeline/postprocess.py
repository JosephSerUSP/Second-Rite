"""Image post-processing, alpha dilation, multi-scale downsampling, contact sheet generation,
and metrics computation for Second Gate 128x128 front-view character sprites.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Tuple, Dict, Any

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import numpy as np


# Palette constants for backgrounds
BG_CHECKER_LIGHT = (200, 200, 200, 255)
BG_CHECKER_DARK = (150, 150, 150, 255)
BG_DUNGEON_SLATE = (27, 30, 38, 255)       # #1b1e26
BG_ST_MARIA_MASONRY = (90, 83, 72, 255)    # #5a5348
BG_PITCH_BLACK = (0, 0, 0, 255)            # #000000
BG_PARCHMENT = (216, 210, 196, 255)        # #d8d2c4


def dilate_rgb_into_alpha(img: Image.Image, max_dilation_passes: int = 16) -> Image.Image:
    """Dilate genuine surface RGB colors into 0-alpha border pixels using nearest non-zero color.
    Prevents background bleed or white/black fringes during downsampling.
    """
    img_rgba = img.convert("RGBA")
    arr = np.array(img_rgba)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]

    solid_mask = alpha > 10
    if not np.any(solid_mask) or np.all(solid_mask):
        return img_rgba

    try:
        from scipy.ndimage import distance_transform_edt
        # Use exact Euclidean distance transform for nearest color lookup
        indices = distance_transform_edt(~solid_mask, return_distances=False, return_indices=True)
        dilated_rgb = rgb[indices[0], indices[1]]
        result_arr = np.dstack((dilated_rgb, alpha))
        return Image.fromarray(result_arr, "RGBA")
    except ImportError:
        # Fallback pure-NumPy / iterative dilation if scipy is not installed
        padded_rgb = rgb.copy()
        current_mask = solid_mask.copy()
        h, w = alpha.shape
        for _ in range(max_dilation_passes):
            if np.all(current_mask):
                break
            new_mask = current_mask.copy()
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                sy = np.clip(np.arange(h) + dy, 0, h - 1)
                sx = np.clip(np.arange(w) + dx, 0, w - 1)
                neighbor_mask = current_mask[sy[:, None], sx]
                eligible = (~current_mask) & neighbor_mask
                if np.any(eligible):
                    padded_rgb[eligible] = padded_rgb[sy[:, None], sx][eligible]
                    new_mask[eligible] = True
            current_mask = new_mask
        result_arr = np.dstack((padded_rgb, alpha))
        return Image.fromarray(result_arr, "RGBA")


def process_rendered_sprite(
    raw_img: Image.Image,
    target_size: int = 128,
    alpha_mode: str = "steep",  # "steep", "binary", or "smooth"
    threshold: int = 128
) -> Image.Image:
    """Process high-res/raw render (e.g. 256x256) into final clean sprite (e.g. 128x128)."""
    # 1. Dilate RGB into alpha margin to eliminate edge bleed
    dilated = dilate_rgb_into_alpha(raw_img)

    # 2. High-quality resampling to target resolution
    if dilated.size != (target_size, target_size):
        downscaled = dilated.resize((target_size, target_size), Image.Resampling.LANCZOS)
    else:
        downscaled = dilated

    arr = np.array(downscaled)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3].astype(np.float32)

    # 3. Alpha curve application
    if alpha_mode == "binary":
        alpha_out = np.where(alpha >= threshold, 255, 0).astype(np.uint8)
    elif alpha_mode == "steep":
        # Steep smoothstep curve: preserves slight anti-aliasing on subpixel diagonals
        # while keeping the core silhouette 100% solid and removing faint halo edges
        norm_a = alpha / 255.0
        clamped = np.clip((norm_a - 0.2) / 0.6, 0.0, 1.0)
        smooth = clamped * clamped * (3.0 - 2.0 * clamped)
        alpha_out = (smooth * 255.0).astype(np.uint8)
    else: # smooth
        alpha_out = alpha.astype(np.uint8)

    result_arr = np.dstack((rgb, alpha_out))
    return Image.fromarray(result_arr, "RGBA")


def create_checkerboard(width: int, height: int, cell_size: int = 8) -> Image.Image:
    """Create checkerboard background for transparency diagnostics."""
    bg = Image.new("RGBA", (width, height), BG_CHECKER_LIGHT)
    draw = ImageDraw.Draw(bg)
    for y in range(0, height, cell_size):
        for x in range(0, width, cell_size):
            if (x // cell_size + y // cell_size) % 2 == 1:
                draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=BG_CHECKER_DARK)
    return bg


def composite_on_background(img: Image.Image, bg_type: str = "checker") -> Image.Image:
    """Composite RGBA sprite onto specified background type."""
    img_rgba = img.convert("RGBA")
    w, h = img_rgba.size
    if bg_type == "none":
        return img_rgba
    if bg_type == "checker":
        bg = create_checkerboard(w, h, cell_size=max(4, w // 16))
    elif bg_type == "slate":
        bg = Image.new("RGBA", (w, h), BG_DUNGEON_SLATE)
    elif bg_type == "masonry":
        bg = Image.new("RGBA", (w, h), BG_ST_MARIA_MASONRY)
    elif bg_type == "black":
        bg = Image.new("RGBA", (w, h), BG_PITCH_BLACK)
    elif bg_type == "parchment":
        bg = Image.new("RGBA", (w, h), BG_PARCHMENT)
    else:
        bg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg.alpha_composite(img_rgba)
    return bg


def compute_sprite_metrics(img: Image.Image) -> Dict[str, Any]:
    """Compute informative diagnostic metrics for a sprite."""
    arr = np.array(img.convert("RGBA"))
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3]

    solid_mask = alpha > 32
    solid_count = int(np.sum(solid_mask))
    total_pixels = img.size[0] * img.size[1]
    coverage_pct = round((solid_count / total_pixels) * 100.0, 2)

    if solid_count == 0:
        return {
            "width": img.size[0],
            "height": img.size[1],
            "bbox": [0, 0, 0, 0],
            "occupied_height_px": 0,
            "occupied_width_px": 0,
            "coverage_pct": 0.0,
            "solid_pixels": 0,
            "mean_luminance": 0.0,
            "std_luminance": 0.0,
        }

    # Bounding box of non-transparent content
    rows = np.any(solid_mask, axis=1)
    cols = np.any(solid_mask, axis=0)
    ymin, ymax = int(np.where(rows)[0][0]), int(np.where(rows)[0][-1])
    xmin, xmax = int(np.where(cols)[0][0]), int(np.where(cols)[0][-1])

    occ_h = ymax - ymin + 1
    occ_w = xmax - xmin + 1

    # Luminance / value metrics
    solid_rgb = rgb[solid_mask].astype(np.float32)
    luminance = 0.299 * solid_rgb[:, 0] + 0.587 * solid_rgb[:, 1] + 0.114 * solid_rgb[:, 2]
    mean_lum = round(float(np.mean(luminance)), 2)
    std_lum = round(float(np.std(luminance)), 2)

    return {
        "width": img.size[0],
        "height": img.size[1],
        "bbox": [xmin, ymin, xmax, ymax],
        "occupied_height_px": occ_h,
        "occupied_width_px": occ_w,
        "coverage_pct": coverage_pct,
        "solid_pixels": solid_count,
        "mean_luminance": mean_lum,
        "std_luminance": std_lum,
    }


def build_solid_silhouette(img: Image.Image, color: Tuple[int, int, int, int] = (15, 15, 20, 255)) -> Image.Image:
    """Produce pure solid silhouette with preserved alpha for shape inspection."""
    arr = np.array(img.convert("RGBA"))
    alpha = arr[:, :, 3]
    sil_arr = np.zeros_like(arr)
    sil_arr[:, :, 0] = color[0]
    sil_arr[:, :, 1] = color[1]
    sil_arr[:, :, 2] = color[2]
    sil_arr[:, :, 3] = alpha
    return Image.fromarray(sil_arr, "RGBA")


def build_grayscale_view(img: Image.Image) -> Image.Image:
    """Produce grayscale value view with preserved alpha."""
    arr = np.array(img.convert("RGBA"))
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3].astype(np.float32)
    lum = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]).astype(np.uint8)
    gray_arr = np.dstack((lum, lum, lum, alpha))
    return Image.fromarray(gray_arr, "RGBA")


def _get_font(size: int = 14) -> ImageFont.ImageFont:
    """Get system TrueType font or fallback."""
    for font_path in [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _clean_str(text: str) -> str:
    """Sanitize text for cross-platform raster rendering."""
    return text.replace("—", "--").replace("–", "-").replace("×", "x").replace("•", "*")


def create_contact_sheet(
    entries: List[Dict[str, Any]],
    output_path: Path,
    title: str,
    subtitle: str = "",
    columns: int = 4,
    cell_size: Tuple[int, int] = (180, 240),
    scale: int = 1,
    bg_type: str = "checker"
) -> Image.Image:
    """Generate high-contrast, informative contact sheet."""
    num_items = len(entries)
    rows = math.ceil(num_items / columns)

    header_height = 80 if subtitle else 60
    sheet_w = columns * cell_size[0] + 40
    sheet_h = rows * cell_size[1] + header_height + 30

    sheet = Image.new("RGB", (sheet_w, sheet_h), (20, 22, 28))
    draw = ImageDraw.Draw(sheet)

    font_title = _get_font(18)
    font_sub = _get_font(12)
    font_body = _get_font(12)
    font_tiny = _get_font(10)

    # Header
    draw.text((20, 16), _clean_str(title), fill=(240, 235, 220), font=font_title)
    if subtitle:
        draw.text((20, 44), _clean_str(subtitle), fill=(160, 155, 140), font=font_sub)

    draw.line([(20, header_height - 10), (sheet_w - 20, header_height - 10)], fill=(50, 55, 65), width=1)

    # Grid items
    for idx, entry in enumerate(entries):
        r = idx // columns
        c = idx % columns
        cell_x = 20 + c * cell_size[0]
        cell_y = header_height + r * cell_size[1]

        # Inner card box
        card_w = cell_size[0] - 10
        card_h = cell_size[1] - 10
        draw.rectangle([cell_x, cell_y, cell_x + card_w, cell_y + card_h], fill=(30, 34, 42), outline=(50, 56, 68))

        # Render preview image
        sprite = entry.get("image")
        if sprite:
            if scale > 1:
                display_img = sprite.resize((sprite.size[0] * scale, sprite.size[1] * scale), Image.Resampling.NEAREST)
            else:
                display_img = sprite

            comp_bg = entry.get("bg_type", bg_type)
            comp_img = composite_on_background(display_img, bg_type=comp_bg)

            # Center image in upper portion of card
            preview_max_h = card_h - 60
            img_x = cell_x + (card_w - comp_img.size[0]) // 2
            img_y = cell_y + 12 + max(0, (preview_max_h - comp_img.size[1]) // 2)

            sheet.paste(comp_img.convert("RGB"), (img_x, img_y))

        # Labels
        label = entry.get("label", f"Item #{idx+1}")
        sublabel = entry.get("sublabel", "")
        metrics_text = entry.get("metrics_text", "")

        text_y = cell_y + card_h - 54
        draw.text((cell_x + 8, text_y), _clean_str(label), fill=(225, 220, 205), font=font_body)
        if sublabel:
            draw.text((cell_x + 8, text_y + 16), _clean_str(sublabel), fill=(150, 165, 185), font=font_tiny)
        if metrics_text:
            draw.text((cell_x + 8, text_y + 30), _clean_str(metrics_text), fill=(120, 135, 145), font=font_tiny)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)
    return sheet


def create_animated_gif(
    frames: List[Image.Image],
    output_path: Path,
    duration_ms: int = 150,
    scale: int = 1,
    loop: int = 0
) -> None:
    """Save sequence of frames as clean animated GIF with optional integer scaling."""
    if not frames:
        return

    processed_frames = []
    for f in frames:
        rgba = f.convert("RGBA")
        if scale > 1:
            scaled = rgba.resize((rgba.size[0] * scale, rgba.size[1] * scale), Image.Resampling.NEAREST)
        else:
            scaled = rgba
        # Convert to palette image with preserved transparency
        # Pillow handles transparency in GIFs via 'transparency' parameter
        alpha = scaled.split()[3]
        mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
        p_frame = scaled.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=255)
        p_frame.paste(255, mask)
        p_frame.info["transparency"] = 255
        processed_frames.append(p_frame)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed_frames[0].save(
        output_path,
        save_all=True,
        append_images=processed_frames[1:],
        duration=duration_ms,
        loop=loop,
        disposal=2
    )
