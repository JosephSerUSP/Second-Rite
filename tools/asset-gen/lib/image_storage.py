"""Small, provably lossless image files for durable repository storage."""

from __future__ import annotations

import io
import os

from PIL import Image


def _rgba_pixels(image):
    rgba = image.convert("RGBA")
    return rgba.size, rgba.tobytes()


def _exact_palette(image):
    """Return an indexed copy when the source has at most 256 RGBA colours."""
    rgba = image.convert("RGBA")
    colours = rgba.getcolors(maxcolors=257)
    if not colours:
        return None
    values = [colour for _, colour in colours]
    indexes = {colour: index for index, colour in enumerate(values)}
    result = Image.new("P", rgba.size)
    result.putdata([indexes[pixel] for pixel in rgba.getdata()])
    palette = []
    for red, green, blue, _alpha in values:
        palette.extend((red, green, blue))
    result.putpalette(palette + [0] * (768 - len(palette)))
    if any(alpha != 255 for _red, _green, _blue, alpha in values):
        result.info["transparency"] = bytes(colour[3] for colour in values)
    return result


def _verified_bytes(source, encoded, fmt):
    with Image.open(io.BytesIO(encoded)) as decoded:
        if _rgba_pixels(decoded) != _rgba_pixels(source):
            raise RuntimeError(f"{fmt} encoder changed decoded RGBA pixels")
    return encoded


def png_bytes(image, original=None):
    """Return the smaller of optimized true-colour and exact indexed PNG."""
    candidates = []
    if original is not None:
        candidates.append(_verified_bytes(image, original, "original PNG"))
    for candidate in (image, _exact_palette(image)):
        if candidate is None:
            continue
        output = io.BytesIO()
        candidate.save(output, format="PNG", optimize=True, compress_level=9)
        candidates.append(_verified_bytes(image, output.getvalue(), "PNG"))
    return min(candidates, key=len)


def webp_bytes(image):
    """Encode lossless WebP and prove its decoded pixels match the source."""
    output = io.BytesIO()
    image.save(output, format="WEBP", lossless=True, quality=100, method=6, exact=True)
    return _verified_bytes(image, output.getvalue(), "lossless WebP")


def write_png(source_path, destination):
    with open(source_path, "rb") as handle:
        original = handle.read()
    with Image.open(source_path) as image:
        data = png_bytes(image, original)
    with open(destination, "wb") as handle:
        handle.write(data)
    return destination


def write_webp(source_path, destination):
    with Image.open(source_path) as image:
        data = webp_bytes(image)
    with open(destination, "wb") as handle:
        handle.write(data)
    return destination


def audit(path):
    """Return byte savings available without changing a decoded pixel."""
    with open(path, "rb") as handle:
        original = handle.read()
    old = len(original)
    with Image.open(path) as image:
        new = len(png_bytes(image, original))
        colours = image.convert("RGBA").getcolors(maxcolors=257)
    return {"path": path, "old": old, "new": new, "saving": old - new,
            "indexed": colours is not None}
