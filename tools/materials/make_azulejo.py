"""Author the azulejo dado tile: blue-and-white tin glaze, painted in-repo.

This one material is deliberately NOT sourced from a CC0 photo library, and the
reason is worth keeping. Every blue tile such a library offers is modern
bathroom or pool tile -- flat glaze, machine edges, subway bond. Azulejo is
tin-glazed earthenware with a cobalt motif PAINTED on a white ground, and it is
the single most identifying surface in a colonial Portuguese room. A generic
blue tile there does not read as "close enough"; it reads as a bathroom, which
is worse than the placeholder it replaced.

## What it has to do at 256x240

The dado is a waist-high band on a wall eighteen metres from a level lens. On
screen it is about **five pixels tall**. That fact decides the whole design:

- The motif will never be resolved, so drawing a finer one is wasted. What
  survives to five pixels is the BAND'S AVERAGE COLOUR and its contrast
  against the limewash above it.
- The old placeholder averaged (199, 210, 217) -- a hair off white. Against a
  whitewashed wall it disappeared completely, which is why no render in this
  pass showed a dado at all despite every room having one.
- So the cobalt is laid down at real strength and real coverage. The band's
  mean lands in the blues, and it reads as a blue-and-white band the moment it
  appears, at any distance.

The motif is a four-petal corner figure repeated across a 6x6 grid -- the most
common Portuguese repeating field pattern, and one that stays coherent when it
is smaller than a pixel because its coverage is even.

    python tools/materials/make_azulejo.py
    python tools/materials/make_azulejo.py --check
"""

from __future__ import annotations

import argparse
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
TILES = 6                 # 6 x 6 tiles across 0.9 m -> 15 cm tiles
WORLD_SIZE_M = 0.9
LICENSE = "CC0-1.0"

GLAZE = np.array([242, 241, 232], dtype=np.float64)   # tin-glaze white ground
COBALT = np.array([38, 70, 138], dtype=np.float64)    # painted cobalt motif
GROUT = np.array([196, 188, 170], dtype=np.float64)   # lime mortar joint


def tile_fields():
    """Per-pixel tile coordinates, joint mask and motif coverage."""
    axis = (np.arange(SIZE) + 0.5) / SIZE * TILES
    tx, ty = np.meshgrid(axis, axis, indexing="xy")
    # Position WITHIN the tile, 0..1.
    u, v = tx % 1.0, ty % 1.0

    # The joint: a narrow band at each tile edge, softened so it survives the
    # downsample to a few pixels instead of aliasing into a hard grid.
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    joint = np.clip(1.0 - edge / 0.055, 0.0, 1.0)

    # The motif: four petals meeting at the tile corners, plus a small centre
    # boss. Coverage is even across the tile, which is what keeps the average
    # stable when the whole thing is smaller than one screen pixel.
    cu, cv = u - 0.5, v - 0.5
    radius = np.hypot(cu, cv)
    angle = np.arctan2(cv, cu)
    petal = 0.30 + 0.085 * np.cos(4.0 * angle)
    motif = np.clip((petal - radius) / 0.05, 0.0, 1.0)

    corner = np.hypot(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    motif = np.maximum(motif, np.clip((0.17 - corner) / 0.045, 0.0, 1.0))

    boss = np.clip((0.075 - radius) / 0.03, 0.0, 1.0)
    motif = np.clip(motif - boss * 0.85, 0.0, 1.0)
    return joint, motif


def build(directory: Path, write: bool = True) -> dict:
    joint, motif = tile_fields()

    # A hand-painted glaze is never flat: a slow wobble across the field makes
    # the cobalt pool and thin the way a brushed tile does.
    ys, xs = np.mgrid[0:SIZE, 0:SIZE] / SIZE * math.tau
    wobble = (np.sin(xs * 3.0) * np.cos(ys * 2.0)
              + np.sin(ys * 5.0 + 1.1) * 0.5) * 0.5
    ink = np.clip(motif * (0.86 + 0.14 * wobble), 0.0, 1.0)

    colour = (GLAZE[None, None, :] * (1.0 - ink[..., None])
              + COBALT[None, None, :] * ink[..., None])
    colour = (colour * (1.0 - joint[..., None])
              + GROUT[None, None, :] * joint[..., None])
    # Tin glaze is uneven across the tile face; a touch of shading keeps a big
    # run of dado from reading as printed vinyl.
    colour *= (0.955 + 0.045 * np.cos(xs * 6.0) * np.cos(ys * 6.0))[..., None]
    albedo = Image.fromarray(np.clip(colour, 0, 255).astype(np.uint8), "RGB")

    # Height: the joint is recessed, the tile face stands slightly proud and
    # domes a little toward its centre, the way a fired glaze does.
    dome = (1.0 - joint) * 0.12
    height = np.clip(0.72 + dome - joint * 0.68, 0.0, 1.0)
    height_img = Image.fromarray((height * 255).astype(np.uint8), "L")

    # Cavity/AO: the joint is the only thing that occludes.
    ao = np.clip(1.0 - joint * 0.55, 0.0, 1.0)
    ao_img = Image.fromarray((ao * 255).astype(np.uint8), "L")

    # Glaze is glossy; the lime joint is not. That difference is most of what
    # says "glazed ceramic" rather than "painted plaster".
    rough = 0.19 + joint * 0.62 + ink * 0.04
    rough_img = Image.fromarray((np.clip(rough, 0, 1) * 255).astype(np.uint8), "L")

    if not write:
        return {}

    directory.mkdir(parents=True, exist_ok=True)
    files = {"albedo.png": albedo, "height.png": height_img,
             "ao.png": ao_img, "roughness.png": rough_img}
    for name, image in files.items():
        image.save(directory / name, optimize=True)

    mean = tuple(int(v) for v in np.array(albedo).reshape(-1, 3).mean(axis=0))
    record = {
        "materialKind": material_library.MATERIAL_KIND,
        "version": material_library.MATERIAL_VERSION,
        "semanticId": "azulejo",
        "status": "authored",
        "worldSizeMetres": WORLD_SIZE_M,
        "maps": {"albedo": "albedo.png", "height": "height.png",
                 "ao": "ao.png", "roughness": "roughness.png"},
        "notes": f"Tin-glazed blue-and-white azulejo, {TILES}x{TILES} tiles per "
                 f"{WORLD_SIZE_M}m ({WORLD_SIZE_M / TILES * 100:.0f}cm tiles). "
                 f"Mean {mean}: cobalt at real strength so the band still reads "
                 "as blue-and-white at the five pixels it gets on screen. Use "
                 "as a dado band, never as a whole wall.",
        "provenance": {
            "origin": "procedural",
            "generator": "tools/materials/make_azulejo.py",
            "license": LICENSE,
            "retrieved": "2026-08-26",
            "sha256": {name: material_library.sha256(directory / name)
                       for name in files},
        },
    }
    (directory / "material.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(prog="make_azulejo")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--project", type=Path, default=None)
    args = parser.parse_args()

    directory = material_library.library_root(args.project) / "azulejo"
    if args.check:
        existing = material_library.load("azulejo", args.project)
        problems = material_library.validate(existing) if existing else ["MISSING"]
        print(f"azulejo: {'ok' if not problems else 'FAILED'}")
        for problem in problems:
            print(f"    - {problem}")
        raise SystemExit(1 if problems else 0)

    record = build(directory)
    print(f"azulejo: wrote {directory}")
    print(f"    {record['notes']}")


if __name__ == "__main__":
    main()
