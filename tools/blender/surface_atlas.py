"""Continuous UV coordinates for unchanged generated surface atlases.

No pixel editing or reconstruction. Path distance distributes a single cover
wrap; local cyclic faces isolate one deliberate sleeve seam. Pillow is optional
and supplied by callers only when measuring the original texture seam.
"""
import math


def path_parameters(points):
    if len(points) < 2 or any(any(not math.isfinite(c) for c in p) for p in points):
        raise ValueError('finite path with at least two points required')
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    if any(d <= 1e-9 for d in lengths):
        raise ValueError('coincident path points collapse UV faces')
    total = sum(lengths)
    values = [0.]
    for d in lengths:values.append(values[-1] + d / total)
    values[-1] = 1.
    return values


def rectangle_uv(u, v, bounds):
    a, b, c, d = bounds
    if any(not math.isfinite(x) for x in (u, v, a, b, c, d)) or not (0 <= a < c <= 1 and 0 <= b < d <= 1):
        raise ValueError('finite bounded atlas rectangle required')
    # Evaluated Blender coordinates are float32: accept only endpoint roundoff.
    if not (-1e-7 <= u <= 1+1e-7 and -1e-7 <= v <= 1+1e-7):
        raise ValueError('normalized coordinates must stay inside rectangle')
    u, v = min(1, max(0, u)), min(1, max(0, v))
    return a + u * (c - a), b + v * (d - b)


def cyclic_face_parameters(values):
    """0..1 turns on a local face; None is a pole receiving mean angular U."""
    finite = [v for v in values if v is not None]
    if not finite or any(not math.isfinite(v) or not 0 <= v < 1 for v in finite):
        raise ValueError('bounded turns and at least one non-pole required')
    crosses = max(finite) - min(finite) > .5
    wrapped = [None if v is None else v + (1 if crosses and v < .5 else 0) for v in values]
    known = [v for v in wrapped if v is not None]
    if max(known)-min(known) > .5 or max(known) > 1:
        raise ValueError('face spans more than one local sleeve interval')
    mean = sum(known)/len(known)
    return [mean if v is None else v for v in wrapped]


def seam_color_report(image, bounds, samples=96):
    """Read original strip end colours; diagnostics, not a seamlessness verdict."""
    if samples < 2:raise ValueError('at least two seam samples required')
    rectangle_uv(0, 0, bounds)
    rgb = image.convert('RGB')
    pairs = []
    for i in range(samples):
        v=i/(samples-1)
        pixels=[]
        for u in (0,1):
            x,y=rectangle_uv(u,v,bounds)
            pixels.append(rgb.getpixel((round(x*(rgb.width-1)),round((1-y)*(rgb.height-1)))))
        pairs.append(tuple(abs(a-b) for a,b in zip(*pixels)))
    return {'samples':samples,'meanAbsoluteRGBDelta':sum(sum(p) for p in pairs)/(samples*3),
            'maxChannelDelta':max(max(p) for p in pairs),
            'boundary':'Raw original strip end colours; grain can differ. Not a visual acceptance claim.'}
