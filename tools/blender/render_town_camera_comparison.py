"""Create the preferred-vs-control native-resolution camera comparison."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BLEND_SCRIPT = ROOT / "tools" / "blender" / "render_town_camera_pair.py"
DEFAULT_BLEND = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "town-next-level-winner.blend"
DEFAULT_A = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "town-camera-preferred-calibration.json"
DEFAULT_B = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "town-camera-pixel-lock-control-calibration.json"
DEFAULT_OUT = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "town-camera-distance-solve-comparison.png"


def blender_executable() -> str:
    import os
    candidates = (os.environ.get("BLENDER_PATH"), r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe", shutil.which("blender"))
    for value in candidates:
        if value and Path(value).is_file():
            return str(value)
    raise RuntimeError("Blender not found; set BLENDER_PATH")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, default=DEFAULT_BLEND)
    parser.add_argument("--camera-a", type=Path, default=DEFAULT_A)
    parser.add_argument("--camera-b", type=Path, default=DEFAULT_B)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="thestra-town-camera-pair-") as temp:
        temp_path = Path(temp)
        out_a, out_b = temp_path / "preferred.png", temp_path / "control.png"
        result = subprocess.run(
            [blender_executable(), "--background", str(args.blend), "--python", str(BLEND_SCRIPT), "--",
             "--camera-a", str(args.camera_a), "--camera-b", str(args.camera_b),
             "--out-a", str(out_a), "--out-b", str(out_b)],
            cwd=ROOT, text=True, capture_output=True,
        )
        if result.returncode:
            raise RuntimeError(result.stdout[-4000:] + result.stderr[-4000:])
        preferred, control = Image.open(out_a).convert("RGBA"), Image.open(out_b).convert("RGBA")
        canvas = Image.new("RGBA", (preferred.width * 2, preferred.height + 22), (20, 18, 24, 255))
        canvas.paste(preferred, (0, 22))
        canvas.paste(control, (preferred.width, 22))
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 5), "preferred ~43 mm / distance solved", fill=(255, 240, 210, 255))
        draw.text((preferred.width + 8, 5), "control ~16 mm / 68.1432 deg", fill=(255, 240, 210, 255))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(args.output)
        print(f"THESTRA_TOWN_CAMERA_COMPARISON OK output={args.output}")


if __name__ == "__main__":
    main()
