"""Compute edge and alpha transparency metrics comparing Old 192px Soft vs New 48px Crisp."""

from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = ROOT / "experiments" / "tiny-character-pipeline"
STUDY_DIR = EXPERIMENT_DIR / "renders" / "resolution_study"

for arch in ["knight_volumetric", "rogue_faceted", "mage_planar"]:
    old_p = STUDY_DIR / f"{arch}_old_baseline_192px_soft_24.png"
    new_p = STUDY_DIR / f"{arch}_48px_crisp_plus_sharpen_24.png"

    if not old_p.is_file() or not new_p.is_file():
        continue

    img_old = Image.open(old_p).convert("RGBA")
    img_new = Image.open(new_p).convert("RGBA")

    a_old = np.array(img_old)[:, :, 3]
    a_new = np.array(img_new)[:, :, 3]

    # Count semi-transparent pixels (0 < alpha < 255)
    semi_old = np.count_nonzero((a_old > 0) & (a_old < 255))
    semi_new = np.count_nonzero((a_new > 0) & (a_new < 255))

    solid_old = np.count_nonzero(a_old == 255)
    solid_new = np.count_nonzero(a_new == 255)

    print(f"=== {arch} ===")
    print(f"  Old Baseline (192px soft): Semi-transparent edge pixels = {semi_old} ({semi_old/576*100:.1f}%), Solid pixels = {solid_old}")
    print(f"  New 48px Crisp:            Semi-transparent edge pixels = {semi_new} (0.0%), Solid pixels = {solid_new}")
