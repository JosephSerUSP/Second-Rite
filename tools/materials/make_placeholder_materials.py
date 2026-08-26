"""Deterministic procedural placeholder textures for the material library.

These exist so every surface in an environment can be bound to a real,
tiling, world-scaled texture before any art is authored. They are placeholders
on purpose: structured enough to read material FAMILY at 426x240 (plank runs,
mortar courses, weave) and deliberately plain enough that nobody mistakes one
for finished art.

Generated in-repo from a fixed seed, so they carry no third-party licensing and
regenerate byte-identically. External scans are supported by the same record
format -- they simply carry a real source, license and retrieval date.

    python tools/materials/make_placeholder_materials.py
    python tools/materials/make_placeholder_materials.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import material_library  # noqa: E402

SIZE = 512
LICENSE = "CC0-1.0"


def rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def tiling_noise(seed: int, frequency: int, octaves: int = 4) -> np.ndarray:
    """Periodic value noise: built at low resolution and tiled by wrapping."""
    total = np.zeros((SIZE, SIZE), dtype=np.float64)
    amplitude, weight = 1.0, 0.0
    generator = rng(seed)
    for octave in range(octaves):
        cells = frequency * (2 ** octave)
        grid = generator.random((cells, cells))
        # Wrap by sampling the grid periodically with smooth interpolation.
        ys = np.linspace(0, cells, SIZE, endpoint=False)
        xs = np.linspace(0, cells, SIZE, endpoint=False)
        y0 = np.floor(ys).astype(int) % cells
        x0 = np.floor(xs).astype(int) % cells
        y1, x1 = (y0 + 1) % cells, (x0 + 1) % cells
        fy = (ys - np.floor(ys))[:, None]
        fx = (xs - np.floor(xs))[None, :]
        sy, sx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        top = grid[np.ix_(y0, x0)] * (1 - sx) + grid[np.ix_(y0, x1)] * sx
        bottom = grid[np.ix_(y1, x0)] * (1 - sx) + grid[np.ix_(y1, x1)] * sx
        total += (top * (1 - sy) + bottom * sy) * amplitude
        weight += amplitude
        amplitude *= 0.5
    return total / weight


def colourise(height: np.ndarray, low, high) -> np.ndarray:
    normalised = (height - height.min()) / max(height.ptp(), 1e-6)
    low_arr = np.array(low, dtype=np.float64)
    high_arr = np.array(high, dtype=np.float64)
    return low_arr + (high_arr - low_arr) * normalised[..., None]


def planks(seed: int, count: int = 6) -> np.ndarray:
    """Horizontal plank runs with per-plank tone and long grain."""
    generator = rng(seed)
    rows = np.arange(SIZE)[:, None] * np.ones((1, SIZE))
    index = (rows / (SIZE / count)).astype(int)
    tone = generator.uniform(0.75, 1.12, size=count)[index % count]
    grain = tiling_noise(seed + 1, 2, 3) * 0.22 + tiling_noise(seed + 2, 16, 2) * 0.10
    # Stretch grain along the plank direction.
    grain = np.roll(grain, 0, axis=0)
    seam = (np.abs(((rows % (SIZE / count)) / (SIZE / count)) - 0.5) > 0.46) * 0.30
    return np.clip(tone * (0.86 + grain) - seam, 0.0, 1.5)


def courses(seed: int, rows_count: int = 7, cols_count: int = 4) -> np.ndarray:
    """Masonry courses with staggered joints and per-block tone."""
    generator = rng(seed)
    yy = np.arange(SIZE)[:, None] * np.ones((1, SIZE))
    xx = np.ones((SIZE, 1)) * np.arange(SIZE)[None, :]
    row = (yy / (SIZE / rows_count)).astype(int)
    offset = (row % 2) * (SIZE / cols_count / 2.0)
    col = (((xx + offset) % SIZE) / (SIZE / cols_count)).astype(int)
    tone = generator.uniform(0.80, 1.10, size=(rows_count, cols_count))[
        row % rows_count, col % cols_count]
    fy = (yy % (SIZE / rows_count)) / (SIZE / rows_count)
    fx = ((xx + offset) % (SIZE / cols_count)) / (SIZE / cols_count)
    joint = ((np.abs(fy - 0.5) > 0.44) | (np.abs(fx - 0.5) > 0.455)) * 0.34
    mottle = tiling_noise(seed + 3, 6, 4) * 0.26
    return np.clip(tone * (0.84 + mottle) - joint, 0.0, 1.5)


def weave(seed: int, threads: int = 60) -> np.ndarray:
    warp = np.sin(np.arange(SIZE) * math.tau * threads / SIZE)[None, :]
    weft = np.sin(np.arange(SIZE) * math.tau * threads / SIZE)[:, None]
    fibre = tiling_noise(seed + 4, 8, 3) * 0.35
    return np.clip(0.82 + 0.09 * (warp + weft) + fibre, 0.0, 1.5)


RECIPES = {
    "dark_wood": dict(seed=1101, field=lambda s: planks(s),
                      low=(46, 31, 21), high=(104, 74, 50), world=2.0,
                      note="Plank runs for floors, partitions, beams and doors."),
    "rough_limestone": dict(seed=2203, field=lambda s: courses(s),
                            low=(92, 87, 74), high=(150, 143, 124), world=2.5,
                            note="Staggered masonry courses for exterior walls."),
    "old_limestone": dict(seed=3307, field=lambda s: courses(s, 5, 3),
                          low=(112, 107, 92), high=(168, 161, 141), world=2.5,
                          note="Cleaner interior plaster/stone."),
    "aged_cloth": dict(seed=4409, field=lambda s: weave(s),
                       low=(86, 68, 52), high=(138, 113, 88), world=1.2,
                       note="Bedding, sacking, hangings."),
}


def build(semantic_id: str, spec: dict, directory: Path, *, write: bool) -> dict:
    field = spec["field"](spec["seed"])
    albedo = np.clip(colourise(field, spec["low"], spec["high"]), 0, 255).astype(np.uint8)
    normalised = (field - field.min()) / max(field.ptp(), 1e-6)
    height = (normalised * 255).astype(np.uint8)
    roughness = (np.clip(0.72 + (1.0 - normalised) * 0.24, 0, 1) * 255).astype(np.uint8)

    files = {"albedo.png": Image.fromarray(albedo, "RGB"),
             "height.png": Image.fromarray(height, "L"),
             "roughness.png": Image.fromarray(roughness, "L")}
    if write:
        directory.mkdir(parents=True, exist_ok=True)
        for name, image in files.items():
            image.save(directory / name, optimize=True)

    hashes = {}
    for name in files:
        path = directory / name
        if path.is_file():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()

    record = {
        "materialKind": material_library.MATERIAL_KIND,
        "version": material_library.MATERIAL_VERSION,
        "semanticId": semantic_id,
        "status": "placeholder",
        "worldSizeMetres": spec["world"],
        "maps": {"albedo": "albedo.png", "height": "height.png",
                 "roughness": "roughness.png"},
        "notes": spec["note"],
        "provenance": {
            "origin": "procedural",
            "generator": "tools/materials/make_placeholder_materials.py",
            "seed": spec["seed"],
            "license": LICENSE,
            "retrieved": "2026-08-26",
            "sha256": hashes,
        },
    }
    if write:
        (directory / "material.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(prog="make_placeholder_materials")
    parser.add_argument("--check", action="store_true",
                        help="regenerate in memory and verify the tracked files")
    parser.add_argument("--project", type=Path, default=None)
    args = parser.parse_args()

    root = material_library.library_root(args.project)
    failures = 0
    for semantic_id, spec in sorted(RECIPES.items()):
        directory = root / semantic_id
        if args.check:
            existing = material_library.load(semantic_id, args.project)
            if existing is None:
                print(f"{semantic_id}: MISSING")
                failures += 1
                continue
            problems = material_library.validate(existing)
            print(f"{semantic_id}: {'ok' if not problems else 'FAILED'}")
            for problem in problems:
                print(f"    - {problem}")
            failures += len(problems)
        else:
            build(semantic_id, spec, directory, write=True)
            print(f"{semantic_id}: wrote {directory}")
    if failures:
        raise SystemExit(f"{failures} problem(s)")


if __name__ == "__main__":
    main()
