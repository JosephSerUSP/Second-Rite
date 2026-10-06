"""Read calibrated multiview silhouettes and project onto an unchanged image atlas.

This is an import library, not automatic 3D reconstruction. Calibration, view
correspondence, occlusion masks and unseen surfaces are explicit author choices.
Pillow stays on the host; atlas_uv is also usable inside Blender without Pillow.
"""
import math


def measure_profile(image, *, center, top, bottom, clip, edge, samples=25, alpha=240):
    """Measure the body run containing center, using a declared unoccluded edge.

    Returns bottom-to-top (height fraction, radius/height) samples. The chosen
    left/right edge avoids an attached handle contaminating the body profile.
    A clipped edge or empty center fails rather than inventing a radius.
    """
    if edge not in ('left', 'right', 'both'):
        raise ValueError('edge must be left, right or both')
    if samples < 2 or not (0 <= top < bottom < image.height):
        raise ValueError('invalid sampling height/count')
    if not (0 <= clip[0] < center < clip[1] <= image.width) or not 1 <= alpha <= 255:
        raise ValueError('invalid horizontal calibration/alpha')
    result = []
    for i in range(samples):
        fraction = i / (samples - 1)
        y = round(bottom - fraction * (bottom - top))
        x = round(center)
        if image.getpixel((x, y))[3] < alpha:
            raise ValueError(f'empty body center at row {y}')
        lo = hi = x
        while lo > clip[0] and image.getpixel((lo - 1, y))[3] >= alpha:
            lo -= 1
        while hi < clip[1] - 1 and image.getpixel((hi + 1, y))[3] >= alpha:
            hi += 1
        if (edge != 'right' and lo == clip[0]) or (edge != 'left' and hi == clip[1] - 1):
            raise ValueError(f'body hits clip at row {y}; select an unoccluded edge')
        radius = {'left': center - lo, 'right': hi - center,
                  'both': (hi - lo) / 2}[edge]
        if radius <= 0:
            raise ValueError('empty radius')
        result.append([fraction, radius / (bottom - top)])
    return result


def interpolate(profile, fraction):
    if not profile or not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError('profile fraction must be finite and bounded')
    for (a, r), (b, s) in zip(profile, profile[1:]):
        if a <= fraction <= b:
            return r + (s - r) * (fraction - a) / (b - a)
    raise ValueError('profile does not cover fraction')


def atlas_uv(point, panel, image_size):
    """Affine world-plane to full original atlas UV, never silently clamping.

    panel: axes (two xyz indices), center in original pixels, scale (signed
    pixels/world-unit). Explicit per-surface calibration also supports an
    independently sized top view. Pixel Y runs down; OBJ V runs up.
    """
    axes, center, scale = panel['axes'], panel['center'], panel['scale']
    if len(set(axes)) != 2 or any(a not in (0, 1, 2) for a in axes):
        raise ValueError('projection needs two distinct world axes')
    if any(not math.isfinite(v) for v in (*point, *center, *scale)) or any(s == 0 for s in scale):
        raise ValueError('finite nonzero calibration required')
    w, h = image_size
    if w <= 0 or h <= 0:
        raise ValueError('invalid image size')
    px, py = (center[i] + point[axes[i]] * scale[i] for i in range(2))
    u, v = px / w, 1 - py / h
    if not (0 <= u <= 1 and 0 <= v <= 1):
        raise ValueError('projection leaves original atlas')
    return u, v


def combine_profiles(front, side, back, *, height, top_ratio, top_weight=.25):
    """Elliptical scaffold rows (rx, ry, z) from independent measured views.

    Front/back determine width, side determines depth. A declared top correction
    reconciles disagreement rather than claiming exact photogrammetric recovery.
    This returns scaffold data only; a saved .blend is subsequently authoritative.
    """
    if not all(math.isfinite(x) and x > 0 for x in (height, top_ratio)):
        raise ValueError('finite positive height/top ratio required')
    if not math.isfinite(top_weight) or not 0 <= top_weight <= 1:
        raise ValueError('top weight must be between zero and one')
    fractions = [f for f, r in front]
    if len(front) < 2 or fractions != [f for f, r in side] or fractions != [f for f, r in back]:
        raise ValueError('all profiles must have matching sampled heights')
    if any(not math.isfinite(f) for f in fractions) or fractions[0] != 0 or fractions[-1] != 1 or any(a >= b for a, b in zip(fractions, fractions[1:])):
        raise ValueError('profiles must increase from zero to one')
    if any(not math.isfinite(r) or r <= 0 for p in (front, side, back) for f, r in p):
        raise ValueError('finite positive radii required')
    widths = [height * (a[1] + b[1]) / 2 for a, b in zip(front, back)]
    depths = [height * s[1] for s in side]
    correction = (1 - top_weight) + top_weight * (widths[-1] * top_ratio / depths[-1])
    return [(a, b * correction, height * (f - .5)) for a, b, f in zip(widths, depths, fractions)]
