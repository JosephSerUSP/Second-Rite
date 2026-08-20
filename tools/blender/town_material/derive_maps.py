#!/usr/bin/env python3
"""Derive a registered PBR map set from ONE generated albedo image.

Why this exists
---------------
The brief's default was a 2x2 generated sheet (albedo/height/roughness/AO).
Measured on real output, current image models do NOT pixel-register the four
quadrants: structural alignment against the albedo scored r=0.06..0.42 where a
usable set needs ~0.9+. Both gpt-image-1-mini and gpt-image-2 instead returned
four tonal variants of a single lit render (tonal r up to +0.83), and the
"height" quadrant shaded flat faces with a 66-level gradient.

So we generate only the albedo -- the one thing the models do well -- and
derive every other map from it numerically. Registration is then exact by
construction, and the brief's preferred chain is preserved:

    generated height -> Blender bump/normal derivation -> optional displacement

Normals are never generated and never derived here; Blender derives them from
the height map at material-build time.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def _lum(rgb: np.ndarray) -> np.ndarray:
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def _norm(x: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(x, 1.0), np.percentile(x, 99.0)
    if hi - lo < 1e-6:
        return np.zeros_like(x)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def derive(albedo_path: Path, out_dir: Path, *, name: str,
           relief_sigma: float = 24.0, roughness_range=(0.45, 0.95),
           invert_height: bool = False) -> dict:
    """albedo PNG -> {albedo, height, roughness, ao} all pixel-registered."""
    out_dir.mkdir(parents=True, exist_ok=True)
    src = Image.open(albedo_path).convert("RGB")
    rgb = np.asarray(src, dtype=np.float64) / 255.0
    lum = _lum(rgb)

    # HEIGHT: local relief only. Subtracting a heavy blur removes large-scale
    # albedo/colour variation (a dark stone is not a deep stone) and keeps the
    # carving, mortar lines and chips that actually displace the surface.
    blur = np.asarray(
        Image.fromarray((lum * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(relief_sigma)),
        dtype=np.float64) / 255.0
    relief = _norm(lum - blur)
    if invert_height:
        relief = 1.0 - relief

    # AO: cavities are the low end of the relief, softened.
    ao = np.asarray(
        Image.fromarray(((relief ** 1.4) * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(3.0)),
        dtype=np.float64) / 255.0
    ao = np.clip(0.35 + 0.65 * ao, 0.0, 1.0)

    # ROUGHNESS: darker, more occluded, grimier areas read rougher; smooth,
    # exposed, brighter stone reads slightly polished by weather and traffic.
    lo, hi = roughness_range
    rough = np.clip(lo + (hi - lo) * (1.0 - 0.55 * _norm(lum) - 0.45 * (ao - 0.35) / 0.65), lo, hi)

    maps = {"albedo": rgb, "height": relief, "roughness": rough, "ao": ao}
    written = {}
    for key, data in maps.items():
        arr = (np.clip(data, 0, 1) * 255).astype(np.uint8)
        img = Image.fromarray(arr if arr.ndim == 3 else arr, "RGB" if arr.ndim == 3 else "L")
        target = out_dir / f"{name}_{key}.png"
        img.save(target)
        written[key] = {"file": target.name, "bytes": target.stat().st_size}

    # registration is exact by construction; assert it rather than assume it
    shapes = {k: (v.shape[0], v.shape[1]) for k, v in maps.items()}
    assert len(set(shapes.values())) == 1, f"maps not registered: {shapes}"
    return {"name": name, "maps": written, "resolution": list(shapes["albedo"]),
            "derivation": {
                "height": f"local relief = normalize(luminance - gaussian(luminance, sigma={relief_sigma}))",
                "ao": "gaussian(relief^1.4, 3.0) remapped to 0.35..1.0",
                "roughness": f"{lo}..{hi} driven by inverse luminance and cavity occlusion",
                "normal": "NOT derived here - Blender derives it from height",
            }}


if __name__ == "__main__":
    import sys
    ROOT = Path(__file__).resolve().parents[3]
    base = ROOT / "projects/hichaukitoden-game/assets/authoring/town/materials/generated"
    print(json.dumps(derive(Path(sys.argv[1]), base / "derived", name=sys.argv[2]), indent=2))
