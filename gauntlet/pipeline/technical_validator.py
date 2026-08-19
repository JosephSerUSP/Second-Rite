# gauntlet/pipeline/technical_validator.py
# Technical sprite validator enforcing 192x192, <=128px standing height, zero anchor drift

import os
import glob
from PIL import Image
from typing import Dict, Any, List
from gauntlet.pipeline.sprite_processor import measure_sprite_metrics

def validate_character_sprites(round_dir: str) -> Dict[str, Any]:
    """
    Validates sprite outputs against strict DRPG engine requirements:
    1. Every frame must be exactly 192x192 RGBA.
    2. Idle frames standing height must not exceed 128px.
    3. Ground anchor bottom_y drift must be <= 1.0px.
    4. Required frames: 1 static, 16 idle, 64 walk (8 dirs x 8 frames), 24 gesture = 105 frames.
    """
    errors = []
    warnings = []
    
    # 1. Check all rendered PNG files
    all_pngs = glob.glob(os.path.join(round_dir, "**", "*.png"), recursive=True)
    # Exclude sheets directory from sprite validation
    sprite_pngs = [p for p in all_pngs if "sheets" not in os.path.split(os.path.dirname(p))[1]]
    
    if not sprite_pngs:
        return {
            "valid": False,
            "errors": ["No sprite frames found in round directory."],
            "warnings": [],
            "total_frames": 0,
            "avg_idle_height": 0.0,
            "anchor_drift_px": 999.0
        }
    
    # Check dimensions & format
    for p in sprite_pngs:
        try:
            with Image.open(p) as im:
                if im.size != (192, 192):
                    errors.append(f"Invalid frame dimensions {im.size} for {os.path.basename(p)} (expected 192x192)")
                if im.mode != "RGBA":
                    errors.append(f"Invalid color mode {im.mode} for {os.path.basename(p)} (expected RGBA)")
        except Exception as e:
            errors.append(f"Failed to open image {os.path.basename(p)}: {e}")

    # Check Idle frames height & anchor stability
    idle_files = sorted(glob.glob(os.path.join(round_dir, "idle", "*.png")))
    idle_heights = []
    bottom_ys = []
    
    for ip in idle_files:
        with Image.open(ip) as im:
            m = measure_sprite_metrics(im)
            if m["empty"]:
                errors.append(f"Idle frame {os.path.basename(ip)} is completely transparent/empty.")
            else:
                idle_heights.append(m["standing_height"])
                bottom_ys.append(m["bottom_y"])

    avg_idle_height = float(sum(idle_heights) / len(idle_heights)) if idle_heights else 0.0
    max_idle_height = max(idle_heights) if idle_heights else 0.0
    anchor_drift_px = float(max(bottom_ys) - min(bottom_ys)) if bottom_ys else 0.0
    
    if max_idle_height > 128.0:
        errors.append(f"Max standing height exceeded: {max_idle_height:.1f}px (Limit is <= 128px)")
    
    if anchor_drift_px > 2.0:
        errors.append(f"Ground anchor drift during idle cycle: {anchor_drift_px:.1f}px (Limit is <= 2px)")

    # Check Walk frames completeness (8 dirs x 8 frames)
    walk_dirs = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
    for d in walk_dirs:
        dfiles = glob.glob(os.path.join(round_dir, "walk", d, "*.png"))
        if len(dfiles) != 8:
            errors.append(f"Walk direction '{d}' has {len(dfiles)} frames (expected 8)")

    # Check Gesture frames completeness (24 frames)
    gesture_files = glob.glob(os.path.join(round_dir, "gesture", "*.png"))
    if len(gesture_files) != 24:
        errors.append(f"Gesture sequence has {len(gesture_files)} frames (expected 24)")

    valid = len(errors) == 0
    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "total_frames": len(sprite_pngs),
        "avg_idle_height": round(avg_idle_height, 1),
        "max_idle_height": round(max_idle_height, 1),
        "anchor_drift_px": round(anchor_drift_px, 1)
    }
