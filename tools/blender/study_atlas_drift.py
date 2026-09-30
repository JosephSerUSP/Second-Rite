"""What does Blender 5.2.2 change in the baked atlases we already ship? A measurement.

Re-bakes the two shop 3D packages with the shipped arguments into a scratch
directory and compares each result with the committed package:

  * the atlas PNG: mean and 95th-percentile per-pixel difference, the fraction of
    pixels more than 8/255 away, and a sharpness ratio (variance of a Laplacian,
    new over shipped; above 1 means the new bake is crisper, which is what the
    5.2 Cycles aliasing fix should do);
  * the OBJ: vertex, UV and face counts, and the largest position and UV
    difference over the shared vertex range, so a moved vertex or a reordered UV
    table is visible rather than assumed absent.

The shipped atlases were baked by an earlier Blender (5.0.x or 5.1.x); which one
is not recorded, so this reports "5.2.2 against what is committed", and cannot
separate the version from later edits to the source `.blend`.

    python tools/blender/study_atlas_drift.py --out out/atlas-drift

Nothing here writes an asset: the bake goes to `--out`, and the `.blend` sources
are opened, never saved. A rebake of a shipped package is an owner-signed step.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator  # noqa: E402

PROJECT = ROOT / "projects" / "hichaukitoden-game" / "assets"
SOURCES = PROJECT / "authoring" / "environments"
PACKAGES = PROJECT / "environments" / "st_maria_town"

# package -> (source .blend, exporter arguments recorded in the shipped anchors)
ROOMS = {
    "alicias_padaria_3d": ("alicias_padaria.blend", ["--exit-y", "7.0333", "--npc", "npc_alicia=2.3333"]),
    "lauras_smith_3d": ("lauras_smith.blend", ["--exit-y", "4.2833", "--npc", "npc_smith=2.7333"]),
}


def bake(package: str, out: Path) -> tuple[Path, float]:
    blend, extra = ROOMS[package]
    target = out / package
    target.mkdir(parents=True, exist_ok=True)
    command = [blender_locator.blender_executable(), "--background", "--factory-startup",
               "-noaudio", "--python", str(ROOT / "tools" / "blender" / "export_room_environment.py"),
               "--", "--blend", str(SOURCES / blend), "--output", str(target), *extra]
    started = time.time()
    result = subprocess.run(command, capture_output=True, text=True)
    elapsed = time.time() - started
    if result.returncode != 0 or not (target / "environment.png").is_file():
        sys.stdout.write(result.stdout[-3000:])
        sys.stderr.write(result.stderr[-3000:])
        raise SystemExit(f"bake failed: {package}")
    return target, elapsed


def sharpness(rgb: np.ndarray) -> float:
    grey = rgb @ np.array([0.2126, 0.7152, 0.0722])
    laplacian = (-4 * grey[1:-1, 1:-1] + grey[:-2, 1:-1] + grey[2:, 1:-1]
                 + grey[1:-1, :-2] + grey[1:-1, 2:])
    return float(laplacian.var())


def compare_atlas(shipped: Path, fresh: Path) -> dict:
    a = np.asarray(Image.open(shipped).convert("RGB"), dtype=np.float64)
    b = np.asarray(Image.open(fresh).convert("RGB"), dtype=np.float64)
    if a.shape != b.shape:
        return {"shapeMismatch": [list(a.shape), list(b.shape)]}
    delta = np.abs(a - b).max(axis=2)
    return {"meanAbsDiff": round(float(delta.mean()), 3),
            "p95AbsDiff": round(float(np.percentile(delta, 95)), 3),
            "fractionOver8": round(float((delta > 8).mean()), 4),
            "sharpnessShipped": round(sharpness(a), 2), "sharpnessFresh": round(sharpness(b), 2),
            "sharpnessRatio": round(sharpness(b) / sharpness(a), 3)}


def read_obj(path: Path) -> dict:
    vertices, uvs, faces = [], [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            vertices.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("vt "):
            uvs.append([float(x) for x in line.split()[1:3]])
        elif line.startswith("f "):
            faces += 1
    return {"v": np.array(vertices), "vt": np.array(uvs), "f": faces}


def compare_obj(shipped: Path, fresh: Path) -> dict:
    a, b = read_obj(shipped), read_obj(fresh)
    row = {"vertices": [len(a["v"]), len(b["v"])], "uvs": [len(a["vt"]), len(b["vt"])],
           "faces": [a["f"], b["f"]], "byteIdentical": shipped.read_bytes() == fresh.read_bytes()}
    for key in ("v", "vt"):
        shared = min(len(a[key]), len(b[key]))
        row["max" + key.upper() + "Diff"] = (
            round(float(np.abs(a[key][:shared] - b[key][:shared]).max()), 6) if shared else None)
    return row


def sheet(package: str, shipped: Path, fresh: Path, out: Path) -> Path:
    a = Image.open(shipped).convert("RGB")
    b = Image.open(fresh).convert("RGB")
    diff = np.clip(np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)) * 4, 0, 255)
    width, height = a.size
    label = 14
    image = Image.new("RGB", (width * 3, height + label), (24, 24, 24))
    draw = ImageDraw.Draw(image)
    for column, (name, tile) in enumerate((("shipped", a), ("5.2.2 fresh bake", b),
                                            ("diff x4", Image.fromarray(diff.astype(np.uint8))))):
        image.paste(tile, (column * width, label))
        draw.text((column * width + 3, 1), name, fill=(230, 230, 230))
    path = out / f"{package}_atlas_sheet.png"
    image.save(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(prog="study_atlas_drift")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--packages", nargs="*", default=list(ROOMS))
    args = parser.parse_args()
    out = args.out.resolve()
    print("Blender " + blender_locator.reported_version(blender_locator.blender_executable()))
    results = {}
    for package in args.packages:
        fresh, seconds = bake(package, out)
        shipped = PACKAGES / package
        results[package] = {"bakeSeconds": round(seconds, 1),
                            "atlas": compare_atlas(shipped / "environment.png", fresh / "environment.png"),
                            "obj": compare_obj(shipped / "environment.obj", fresh / "environment.obj")}
        print("sheet", sheet(package, shipped / "environment.png", fresh / "environment.png", out))
    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
