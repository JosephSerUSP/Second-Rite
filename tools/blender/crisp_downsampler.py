"""Test script to evaluate 48x48 vs 72x72 vs 96x96 vs 192x192 and Crisp-Alpha / Matte Downsampling."""

import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageEnhance

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = ROOT / "experiments" / "tiny-character-pipeline"
RAW_DIR = EXPERIMENT_DIR / "raw_frames"


def process_crisp_sprite(raw_img: Image.Image, target_size=(24, 24), alpha_threshold=128, sharpen=True):
    """Processes a high-res render to a crisp 24x24 sprite:
    1. Unpremultiplies color by alpha so edge pixels don't have black fringe.
    2. Applies subtle crisp edge enhancement on high-res input if sharpen=True.
    3. Downsamples RGB smoothly (preserving interior normal/specular AA).
    4. Applies binary thresholding to Alpha (no semi-transparent halo, 100% solid or transparent).
    """
    img = raw_img.convert("RGBA")
    
    if sharpen:
        # Subtle unsharp mask to crisp up high-frequency specular and facet boundaries
        # Radius 1.0, percent 130
        rgb = img.convert("RGB")
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.0, percent=130, threshold=2))
        img.paste(rgb, (0, 0), mask=img.split()[3])

    arr = np.array(img, dtype=np.float32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]

    # Unpremultiply RGB to avoid dark halo bleeding at transparent boundary
    alpha_norm = np.maximum(a / 255.0, 1e-6)
    r_unpre = np.clip(r / alpha_norm, 0, 255)
    g_unpre = np.clip(g / alpha_norm, 0, 255)
    b_unpre = np.clip(b / alpha_norm, 0, 255)

    # For pixels with 0 alpha, fill with neighboring color or keep
    # Reconstruct RGB image
    unpre_rgb = np.stack([r_unpre, g_unpre, b_unpre], axis=2).astype(np.uint8)
    rgb_img = Image.fromarray(unpre_rgb, mode="RGB")
    alpha_img = Image.fromarray(a.astype(np.uint8), mode="L")

    # Downsample RGB with Box / Area averaging or Lanczos for clean interior AA
    rgb_24 = rgb_img.resize(target_size, resample=Image.Resampling.LANCZOS)
    
    # Downsample Alpha with Box / Area averaging to measure subpixel coverage
    alpha_24_soft = alpha_img.resize(target_size, resample=Image.Resampling.BOX)
    
    # Threshold Alpha: strictly binary (0 or 255) - ZERO semi-transparent alpha fringes
    alpha_arr = np.array(alpha_24_soft)
    alpha_arr_bin = np.where(alpha_arr >= alpha_threshold, 255, 0).astype(np.uint8)
    alpha_24_bin = Image.fromarray(alpha_arr_bin, mode="L")

    # Merge crisp RGB and Binary Alpha
    result = Image.merge("RGBA", (*rgb_24.split(), alpha_24_bin))
    return result


if __name__ == "__main__":
    print("Crisp sprite processing module ready.")
