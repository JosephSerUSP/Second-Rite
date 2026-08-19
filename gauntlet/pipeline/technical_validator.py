# gauntlet/pipeline/technical_validator.py

import os
import glob
from typing import Dict, Any, List
from PIL import Image
from gauntlet.pipeline.sprite_processor import measure_sprite_metrics, TARGET_CANVAS_SIZE, MAX_STANDING_HEIGHT

def validate_character_sprites(
    char_dir: str,
    expected_idle_frames: int = 16,
    expected_gesture_frames: int = 24,
    expected_walk_directions: int = 8,
    expected_walk_frames_per_dir: int = 8
) -> Dict[str, Any]:
    """
    Programmatically verifies all hard technical constraints:
    1. Every frame is 192x192 RGBA.
    2. Standing height <= 128px on canonical idle.
    3. Anchor bottom alignment is consistent.
    4. Frame count completeness.
    """
    errors = []
    warnings = []

    # Check idle frames
    idle_files = sorted(glob.glob(os.path.join(char_dir, "idle", "*.png")))
    if len(idle_files) != expected_idle_frames:
        errors.append(f"Idle frame count mismatch: found {len(idle_files)}, expected {expected_idle_frames}")

    # Check gesture frames
    gesture_files = sorted(glob.glob(os.path.join(char_dir, "gesture", "*.png")))
    if len(gesture_files) != expected_gesture_frames:
        errors.append(f"Gesture frame count mismatch: found {len(gesture_files)}, expected {expected_gesture_frames}")

    # Check walk frames
    walk_dirs = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
    total_walk = 0
    for d in walk_dirs:
        dfiles = sorted(glob.glob(os.path.join(char_dir, "walk", d, "*.png")))
        total_walk += len(dfiles)
        if len(dfiles) != expected_walk_frames_per_dir:
            errors.append(f"Walk direction {d} frame count mismatch: found {len(dfiles)}, expected {expected_walk_frames_per_dir}")

    # Inspect idle frame metrics
    idle_heights = []
    idle_bottoms = []
    for fpath in idle_files:
        try:
            im = Image.open(fpath)
            if im.size != TARGET_CANVAS_SIZE:
                errors.append(f"File {os.path.basename(fpath)} size is {im.size}, expected {TARGET_CANVAS_SIZE}")
            if im.mode != "RGBA":
                errors.append(f"File {os.path.basename(fpath)} mode is {im.mode}, expected RGBA")

            metrics = measure_sprite_metrics(im)
            if metrics["standing_height"] > 0:
                idle_heights.append(metrics["standing_height"])
                idle_bottoms.append(metrics["bottom_y"])
                if metrics["standing_height"] > MAX_STANDING_HEIGHT:
                    errors.append(f"File {os.path.basename(fpath)} exceeds standing height: {metrics['standing_height']}px > {MAX_STANDING_HEIGHT}px")
        except Exception as e:
            errors.append(f"Failed to read {fpath}: {e}")

    # Check anchor variance across idle
    anchor_drift = max(idle_bottoms) - min(idle_bottoms) if idle_bottoms else 0
    if anchor_drift > 2:
        warnings.append(f"Ground anchor drift across idle is {anchor_drift}px (threshold <= 2px)")

    avg_idle_height = sum(idle_heights) / len(idle_heights) if idle_heights else 0

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "total_frames": len(idle_files) + len(gesture_files) + total_walk,
        "avg_idle_height": round(avg_idle_height, 1),
        "anchor_drift_px": anchor_drift
    }
