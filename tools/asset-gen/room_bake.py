"""Capture real-engine room guides and deproject a generated room into tiles."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
LOVE = Path(r"C:\Program Files\LOVE\lovec.exe")
SURFACES = {"wall": 0.2, "floor": 0.5, "ceiling": 0.8}


def capture(out: Path, layout: str) -> None:
    proc = subprocess.run([str(LOVE), ".", "room-bake-guides", layout], cwd=ROOT,
                          capture_output=True, text=True, timeout=120)
    begin = proc.stdout.find("ROOM BAKE BEGIN")
    end = proc.stdout.find("ROOM BAKE END")
    if proc.returncode or begin < 0 or end < 0:
        raise SystemExit((proc.stderr or proc.stdout or "room guide capture failed").strip())
    payload = json.loads(proc.stdout[begin + len("ROOM BAKE BEGIN"):end].strip())
    if payload.get("error"):
        raise SystemExit(payload["error"])
    out.mkdir(parents=True, exist_ok=True)
    for key in ("depth", "uv"):
        (out / f"{key}.png").write_bytes(base64.b64decode(payload[key]))
    (out / "manifest.json").write_text(json.dumps({
        "kind": "room_bake_guides", "width": payload["width"],
        "height": payload["height"], "far": payload["far"],
        "layout": payload["layout"], "corridorWidth": payload["corridorWidth"],
        "surfaces": payload["surfaces"],
    }, indent=2) + "\n", encoding="utf-8")


def extract(generated: Path, guides: Path, out: Path, inset: float = 0.08) -> None:
    rgb = np.asarray(Image.open(generated).convert("RGB"), dtype=np.float32)
    uv = np.asarray(Image.open(guides / "uv.png").convert("RGB"), dtype=np.float32) / 255.0
    if rgb.shape[:2] != uv.shape[:2]:
        raise SystemExit(f"generated image is {rgb.shape[1]}x{rgb.shape[0]}, "
                         f"guides are {uv.shape[1]}x{uv.shape[0]}")
    out.mkdir(parents=True, exist_ok=True)
    yy, xx = np.mgrid[0:rgb.shape[0], 0:rgb.shape[1]]
    centre = 1.0 - np.maximum(abs(xx - rgb.shape[1] / 2) / (rgb.shape[1] / 2),
                            abs(yy - rgb.shape[0] / 2) / (rgb.shape[0] / 2))
    for name, code in SURFACES.items():
        u, v, surface = uv[..., 0], uv[..., 1], uv[..., 2]
        mask = ((abs(surface - code) < 0.08) & (u >= inset) & (u <= 1 - inset)
                & (v >= inset) & (v <= 1 - inset))
        accum = np.zeros((64, 64, 3), dtype=np.float64)
        weights = np.zeros((64, 64), dtype=np.float64)
        tx = np.clip((u[mask] * 64).astype(int), 0, 63)
        ty = np.clip((v[mask] * 64).astype(int), 0, 63)
        w = np.maximum(centre[mask], 0.05) ** 2
        np.add.at(accum, (ty, tx), rgb[mask] * w[:, None])
        np.add.at(weights, (ty, tx), w)
        known = weights > 0
        tile = np.zeros((64, 64, 3), dtype=np.uint8)
        tile[known] = np.clip(accum[known] / weights[known, None], 0, 255).astype(np.uint8)
        # Coverage repair only. Seam construction remains gen.py's real path.
        for _ in range(64):
            if known.all():
                break
            changed = False
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                source = np.roll(tile, (dy, dx), axis=(0, 1))
                source_known = np.roll(known, (dy, dx), axis=(0, 1))
                take = ~known & source_known
                if take.any():
                    tile[take], known[take], changed = source[take], True, True
            if not changed:
                break
        Image.fromarray(tile).save(out / f"{name}.png")
        Image.fromarray((mask * 255).astype(np.uint8)).save(out / f"{name}-coverage.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    cap = sub.add_parser("capture")
    cap.add_argument("--out", type=Path, required=True)
    cap.add_argument("--layout", choices=("one", "two", "three",
                     "three-block-left", "three-block-right"), default="three")
    ext = sub.add_parser("extract")
    ext.add_argument("image", type=Path)
    ext.add_argument("--guides", type=Path, required=True)
    ext.add_argument("--out", type=Path, required=True)
    ext.add_argument("--inset", type=float, default=0.08)
    args = parser.parse_args()
    if args.command == "capture":
        capture(args.out, args.layout)
    else:
        extract(args.image, args.guides, args.out, args.inset)


if __name__ == "__main__":
    main()
