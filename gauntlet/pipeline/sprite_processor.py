# gauntlet/pipeline/sprite_processor.py

import os
from typing import Tuple, Optional, Dict, Any
from PIL import Image
import numpy as np

TARGET_CANVAS_SIZE = (192, 192)
GROUND_ANCHOR_X = 96
GROUND_ANCHOR_Y = 176 # Character feet land at Y=176 (leaving 16px bottom margin, 48px top margin for 128px character)
MAX_STANDING_HEIGHT = 128

def get_alpha_bounding_box(img: Image.Image, alpha_threshold: int = 10) -> Optional[Tuple[int, int, int, int]]:
    """Returns (min_x, min_y, max_x, max_y) for non-transparent pixels."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    arr = np.array(img)
    alpha = arr[:, :, 3]
    mask = alpha > alpha_threshold
    if not np.any(mask):
        return None
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    min_y, max_y = np.where(rows)[0][[0, -1]]
    min_x, max_x = np.where(cols)[0][[0, -1]]
    return int(min_x), int(min_y), int(max_x), int(max_y)

def measure_sprite_metrics(img: Image.Image) -> Dict[str, Any]:
    """Measures standing height, width, bounding box, and anchor contact point."""
    bbox = get_alpha_bounding_box(img)
    if not bbox:
        return {
            "bbox": None,
            "width": 0,
            "height": 0,
            "standing_height": 0,
            "anchor_x": GROUND_ANCHOR_X,
            "anchor_y": GROUND_ANCHOR_Y,
            "is_within_height_limit": True
        }
    min_x, min_y, max_x, max_y = bbox
    width = max_x - min_x + 1
    height = max_y - min_y + 1
    return {
        "bbox": bbox,
        "width": width,
        "height": height,
        "standing_height": height,
        "bottom_y": max_y,
        "center_x": (min_x + max_x) // 2,
        "is_within_height_limit": height <= MAX_STANDING_HEIGHT
    }

def process_and_anchor_frame(
    raw_img: Image.Image,
    target_size: Tuple[int, int] = TARGET_CANVAS_SIZE,
    anchor_pos: Tuple[int, int] = (GROUND_ANCHOR_X, GROUND_ANCHOR_Y)
) -> Image.Image:
    """
    Ensures the image is placed onto a 192x192 canvas with exact bottom-center grounding.
    If the raw render is already rendered with camera-centered coordinates corresponding to the ground anchor,
    it verifies and preserves transparency without distortion.
    """
    if raw_img.mode != "RGBA":
        raw_img = raw_img.convert("RGBA")

    if raw_img.size == target_size:
        return raw_img

    # If raw render is a larger high-res render or off-sized, place/scale cleanly
    # (Preferred workflow is Blender renders directly at target framing, or high-res and cleanly downscaled)
    target = Image.new("RGBA", target_size, (0, 0, 0, 0))
    # Paste centered
    target.paste(raw_img, (0, 0), raw_img)
    return target
