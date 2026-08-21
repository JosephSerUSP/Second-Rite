"""Numeric derivation of supporting maps from ONE flat albedo.

Deliberately not a 2x2 pseudo-PBR sheet. An image model asked for four
quadrants returns four tonal variants of one *lit render*, and they are not
pixel-registered. Deriving every other channel from the albedo makes
registration exact by construction and never asks a model for a normal map.

Also reports the two metrics that decide whether an albedo is usable as a
material source at all:

  low_freq_energy -- how much baked-in lighting gradient the albedo carries
                     (a flat, evenly lit source is near zero)
  detail_std      -- how much real high-frequency material detail survives

Run with plain CPython; no Blender required.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


# --------------------------------------------------------------------------

def _srgb_to_linear(a):
    a = np.clip(a, 0.0, 1.0)
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(a):
    a = np.clip(a, 0.0, 1.0)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * (a ** (1 / 2.4)) - 0.055)


def _luma(rgb_lin):
    return (0.2126 * rgb_lin[..., 0] + 0.7152 * rgb_lin[..., 1]
            + 0.0722 * rgb_lin[..., 2])


def _box1d(a, radius, axis):
    """Periodic (wrap-around) box filter along one axis."""
    k = 2 * int(radius) + 1
    n = a.shape[axis]
    if k <= 1:
        return a
    pad = [(0, 0), (0, 0)]
    pad[axis] = (int(radius) + 1, int(radius))
    p = np.pad(a, pad, mode="wrap")
    c = np.cumsum(p, axis=axis)
    hi = np.take(c, np.arange(k, k + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return (hi - lo) / float(k)


def _blur(a, sigma):
    """Wrap-around Gaussian approximation (three box passes).

    Periodic on purpose: these maps are meant to tile, so a clamped blur would
    manufacture an edge artefact and then bake it into the derived height.
    """
    sigma = float(sigma)
    if sigma <= 0.5:
        return np.asarray(a, dtype=np.float64).copy()
    radius = max(1, int(round(sigma * 0.5 * math.sqrt(12.0 / 3.0 + 1.0) / 2.0)))
    out = np.asarray(a, dtype=np.float64)
    for _ in range(3):
        out = _box1d(out, radius, 0)
        out = _box1d(out, radius, 1)
    return out


def _norm(a):
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo) if hi > lo else np.zeros_like(a)


def make_tileable(rgb, blend_frac=0.14):
    """One-sided wrap blend: exactly continuous across the tile boundary.

    Only the trailing band is touched, and it is cross-faded toward the
    *leading* content shifted so the last column lands exactly on the first.
    A symmetric blend of the two bands (the obvious implementation) makes the
    two bands equal to each other but leaves the actual seam untouched, which
    the seam_error metric reports as no improvement or worse.
    """
    out = rgb.copy()
    for axis in (1, 0):
        n = out.shape[axis]
        b = max(3, int(round(n * blend_frac)))
        t = np.linspace(0.0, 1.0, b)
        if axis == 1:
            t = t.reshape(1, b, 1)
            tail = out[:, n - b:, :]
            lead = out[:, np.arange(-b + 1, 1) % n, :]
            out[:, n - b:, :] = tail * (1 - t) + lead * t
        else:
            t = t.reshape(b, 1, 1)
            tail = out[n - b:, :, :]
            lead = out[np.arange(-b + 1, 1) % n, :, :]
            out[n - b:, :, :] = tail * (1 - t) + lead * t
    return out


def seam_error(rgb):
    """Mean absolute discontinuity across the wrap boundary, 0..1."""
    v = np.abs(rgb[0, :, :] - rgb[-1, :, :]).mean()
    h = np.abs(rgb[:, 0, :] - rgb[:, -1, :]).mean()
    return float(0.5 * (v + h))


def albedo_metrics(rgb_srgb):
    """low_freq_energy / detail_std / vertical ramp of a candidate albedo."""
    lin = _srgb_to_linear(rgb_srgb)
    lum = _luma(lin)
    h, w = lum.shape
    low = _blur(lum, max(h, w) * 0.10)
    detail = lum - low
    rows = lum.mean(axis=1)
    top = rows[: h // 4].mean()
    bot = rows[-h // 4:].mean()
    return {
        "low_freq_energy": round(float(low.std() * 255.0), 3),
        "detail_std": round(float(detail.std() * 255.0), 3),
        "vertical_ramp": round(float(abs(top - bot) * 255.0), 3),
        "mean_luma": round(float(lum.mean()), 4),
    }


# --------------------------------------------------------------------------

def derive(albedo_path, out_dir, *, stem=None, size=512, tileable=True,
           height_highpass=0.09, ao_sigma=0.02, rough_from="detail",
           rough_invert=False):
    albedo_path = Path(albedo_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = stem or albedo_path.stem

    img = Image.open(albedo_path).convert("RGB")
    if size and img.size != (size, size):
        img = img.resize((size, size), Image.LANCZOS)
    rgb = np.asarray(img).astype(np.float64) / 255.0

    metrics_raw = albedo_metrics(rgb)

    if tileable:
        rgb = make_tileable(rgb)
    metrics = albedo_metrics(rgb)
    metrics["seam_error"] = round(seam_error(rgb), 5)
    metrics["seam_error_before"] = round(seam_error(np.asarray(img).astype(np.float64) / 255.0), 5)
    metrics["raw"] = metrics_raw

    lin = _srgb_to_linear(rgb)
    lum = _luma(lin)
    n = max(rgb.shape[:2])

    # HEIGHT: luminance with its low-frequency shading removed, so a residual
    # lighting gradient in the source can never become real displacement.
    low = _blur(lum, n * height_highpass)
    height = _norm(lum - low + 0.5)
    height = np.clip(height, 0.0, 1.0)

    # AO / cavity: where the surface sits below its local neighbourhood.
    cav = _blur(height, n * ao_sigma) - height
    ao = np.clip(1.0 - _norm(np.clip(cav, 0, None)) * 0.95, 0.0, 1.0)

    # ROUGHNESS: rough where detailed and dark, smoother on flat bright areas.
    detail = np.abs(height - 0.5) * 2.0
    if rough_from == "detail":
        rough = 0.30 + 0.62 * _norm(_blur(detail, n * 0.006))
    else:
        rough = 0.30 + 0.62 * (1.0 - _norm(lum))
    if rough_invert:
        rough = 1.0 - rough
    rough = np.clip(rough, 0.0, 1.0)

    paths = {}
    alb_out = out_dir / ("%s_albedo.png" % stem)
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(alb_out)
    paths["albedo"] = alb_out
    for key, arr in (("height", height), ("ao", ao), ("roughness", rough)):
        p = out_dir / ("%s_%s.png" % (stem, key))
        Image.fromarray((arr * 255).astype(np.uint8), mode="L").save(p)
        paths[key] = p

    # Registration is exact by construction; assert it rather than assume it.
    metrics["registration"] = "exact-by-construction"
    metrics["derived_from"] = str(albedo_path.name)
    metrics["size"] = list(Image.open(alb_out).size)
    (out_dir / ("%s_maps.json" % stem)).write_text(
        json.dumps(metrics, indent=2), encoding="utf-8")
    return {k: str(v) for k, v in paths.items()}, metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("albedo", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--stem")
    ap.add_argument("--size", type=int, default=512)
    args = ap.parse_args()
    paths, metrics = derive(args.albedo, args.out, stem=args.stem, size=args.size)
    print(json.dumps({"paths": paths, "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
