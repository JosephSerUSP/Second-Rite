"""Procedural sheen maps ("matcaps") for the item shader's ``refl``/``pass sphere`` layer.

The item shader has no specular term (SPEC 1.25), so metal and glass read as
metal and glass only through a small image indexed by the screen-space normal.
Only gold and ruby existed. This writes more, from a tiny studio-lighting
model rather than by hand, so a new material is a recipe, not an afternoon:

    python tools/asset-production/make_matcap.py steel
    python tools/asset-production/make_matcap.py --list
    python tools/asset-production/make_matcap.py --preview out/matcaps.png

Orientation matches presentation/retro_mesh_shader.lua: u = N.x, v = -N.z
(top of the image faces up on screen). The shader ADDS this onto the already
lit base colour, so values are deliberately restrained: a full-white pixel
saturates whatever it lands on. Pass strength scales it further per material.

Deterministic: pure arithmetic, fixed size, no randomness.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = ROOT / "projects" / "hichaukitoden-game" / "assets" / "models" / "matcaps"
SIZE = 128


def _smooth(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _env(rx, ry, rz, recipe):
    """Radiance along reflection direction (rx right, ry toward viewer, rz up)."""
    up = rz  # -1..1 elevation
    sky = recipe["sky"]
    ground = recipe["ground"]
    horizon = recipe["horizon"]
    # vertical gradient: ground -> horizon band -> sky
    t_sky = _smooth(-0.05, 0.85, up)[..., None]
    t_gnd = _smooth(0.05, -0.85, up)[..., None]
    base = np.array(horizon)[None, None, :] * (1 - t_sky - t_gnd).clip(0, 1)
    col = base + np.array(sky)[None, None, :] * t_sky + np.array(ground)[None, None, :] * t_gnd
    # dark horizon line: the thing that makes polished steel look like steel
    line = np.exp(-((up - recipe.get("line_at", 0.02)) / recipe.get("line_w", 0.07)) ** 2)[..., None]
    col = col * (1 - recipe.get("line_dark", 0.0) * line)
    # softboxes: (azimuth_x, up, width, power)
    for bx, bz, bw, power in recipe["boxes"]:
        d2 = (rx - bx) ** 2 + (rz - bz) ** 2
        col = col + (power * np.exp(-d2 / (bw * bw)))[..., None] * np.array(recipe.get("box_tint", (1, 1, 1)))
    return col


RECIPES = {
    # cool polished steel: bright overhead, hard horizon, two strip lights
    "steel": dict(sky=(0.50, 0.55, 0.62), horizon=(0.16, 0.17, 0.20), ground=(0.06, 0.06, 0.07),
                  line_dark=0.85, boxes=[(-0.55, 0.45, 0.22, 0.55), (0.6, 0.15, 0.12, 0.45)],
                  box_tint=(0.95, 0.98, 1.0), gain=0.85),
    # bright, low-contrast silver
    "silver": dict(sky=(0.62, 0.64, 0.68), horizon=(0.30, 0.31, 0.34), ground=(0.14, 0.14, 0.16),
                   line_dark=0.45, boxes=[(-0.5, 0.5, 0.3, 0.45)], box_tint=(1, 1, 1), gain=0.8),
    # warm bronze, dim, broad
    "bronze": dict(sky=(0.52, 0.34, 0.16), horizon=(0.20, 0.12, 0.05), ground=(0.08, 0.05, 0.02),
                   line_dark=0.6, boxes=[(-0.5, 0.45, 0.25, 0.4)], box_tint=(1.0, 0.82, 0.55), gain=0.8),
    # glass: almost black body with hard white window reflections
    "glass": dict(sky=(0.10, 0.16, 0.18), horizon=(0.03, 0.05, 0.06), ground=(0.02, 0.03, 0.04),
                  line_dark=0.0, boxes=[(-0.45, 0.55, 0.20, 0.95), (0.55, 0.25, 0.10, 0.55)],
                  box_tint=(0.9, 1.0, 1.0), gain=1.0),
    # cold pewter-ish enamel for chrome-less "painted metal"
    "enamel": dict(sky=(0.30, 0.30, 0.32), horizon=(0.12, 0.12, 0.13), ground=(0.05, 0.05, 0.05),
                   line_dark=0.0, boxes=[(-0.5, 0.5, 0.3, 0.3)], box_tint=(1, 1, 1), gain=0.7),
}


def render(name: str) -> Image.Image:
    recipe = RECIPES[name]
    ys, xs = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    nx = (xs + 0.5) / SIZE * 2 - 1           # u -> N.x
    nz = -((ys + 0.5) / SIZE * 2 - 1)        # v -> -N.z, so row 0 faces up
    r2 = nx * nx + nz * nz
    inside = r2 <= 1.0
    ny = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))  # toward viewer
    # reflect a viewer looking along -y: r = 2(n.v)n - v, v = (0,1,0)
    rx, ry, rz = 2 * ny * nx, 2 * ny * ny - 1, 2 * ny * nz
    col = _env(rx, ry, rz, recipe) * recipe["gain"]
    # edges of the sphere (grazing) pick up the horizon, so the rim doesn't go black
    col = np.clip(col, 0.0, 1.0)
    col[~inside] = col[inside].mean(axis=0) if inside.any() else 0.0
    return Image.fromarray((col * 255 + 0.5).astype(np.uint8), "RGB")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("name", nargs="?")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--preview", type=Path, help="write a contact sheet of every recipe here, writing no matcap")
    args = parser.parse_args()
    if args.list:
        print("\n".join(sorted(RECIPES)))
        return
    if args.preview:
        names = sorted(RECIPES)
        sheet = Image.new("RGB", (SIZE * len(names), SIZE))
        for i, n in enumerate(names):
            sheet.paste(render(n), (i * SIZE, 0))
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(args.preview)
        print(f"PREVIEW {args.preview}: {', '.join(names)}")
        return
    if args.name not in RECIPES:
        parser.error(f"name must be one of {sorted(RECIPES)}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    target = args.out_dir / f"{args.name}.png"
    render(args.name).save(target, optimize=False)
    print(f"MATCAP {target}")


if __name__ == "__main__":
    main()
