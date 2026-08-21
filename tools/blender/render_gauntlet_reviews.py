"""Render review frames and tracking strips for Second Gate town gauntlet environments."""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLENDER_SEARCH = [
    os.environ.get("BLENDER"),
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    "blender",
]


def blender_executable():
    for candidate in BLENDER_SEARCH:
        if candidate and (candidate == "blender" or Path(candidate).is_file()):
            return candidate
    raise SystemExit("Blender not found; set BLENDER or install Blender")


def render_scene_in_blender(
    blend_path: Path,
    out_dir: Path,
    profile_name: str = "clay",
    prefix: str = "clay",
    hide_actors: bool = False,
):
    import bpy
    import second_gate_render

    blend_path = Path(blend_path).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    second_gate_render.apply(scene, profile_name)

    # Actor visibility
    actors_col = bpy.data.collections.get("TH_PREVIEW_ACTORS")
    if actors_col:
        actors_col.hide_render = hide_actors

    # Ensure source collection is visible in render
    source_col = bpy.data.collections.get("TH_SOURCE")
    if source_col:
        source_col.hide_render = False

    render_col = bpy.data.collections.get("TH_RENDER")
    if render_col:
        render_col.hide_render = True  # In review renders, show TH_SOURCE

    cam = scene.camera
    if not cam:
        raise RuntimeError("No scene camera found")

    target_w = float(scene.render.resolution_x)  # 426
    shifts = [
        ("m96", -96.0),
        ("zero", 0.0),
        ("p96", 96.0),
    ]

    base_shift_x = 0.0  # Camera principal point shift
    # Check if camera has base principal point
    if hasattr(cam.data, "shift_x"):
        base_shift_x = float(cam.data.shift_x)

    rendered_files = []
    for label, offset_px in shifts:
        cam.data.shift_x = base_shift_x - (offset_px / target_w)
        out_path = out_dir / f"{prefix}_{label}.png"
        scene.render.filepath = str(out_path)
        bpy.ops.render.render(write_still=True)
        rendered_files.append(out_path)
        print(f"[render] Saved {out_path}")

    # Reset shift
    cam.data.shift_x = base_shift_x

    # Also render single center frame at beauty if candidate
    print("[render] Review render complete.")


def create_strip(images: list[Path], output_path: Path):
    """Combine 3 426x240 frames into a 1278x240 continuous panoramic review strip."""
    from PIL import Image
    imgs = [Image.open(p) for p in images]
    w, h = imgs[0].size
    strip = Image.new("RGBA", (w * len(imgs), h))
    for i, img in enumerate(imgs):
        strip.paste(img, (i * w, 0))
    strip.save(output_path)
    print(f"[strip] Saved combined review strip to {output_path}")


def run_render(blend_path: Path, out_dir: Path, profile_name: str = "clay", prefix: str = "clay", hide_actors: bool = False):
    blender = blender_executable()
    script_path = Path(__file__).resolve()
    temp_runner = tempfile.NamedTemporaryFile(prefix="th_review_render_", suffix=".py", delete=False, mode="w", encoding="utf-8")
    temp_runner.write(
        f"import sys\n"
        f"sys.path.insert(0, {repr(str(script_path.parent))})\n"
        f"from render_gauntlet_reviews import render_scene_in_blender\n"
        f"from pathlib import Path\n"
        f"render_scene_in_blender(Path({repr(str(blend_path))}), Path({repr(str(out_dir))}), "
        f"profile_name={repr(profile_name)}, prefix={repr(prefix)}, hide_actors={repr(hide_actors)})\n"
    )
    temp_runner.close()

    try:
        cmd = [blender, "--background", "--factory-startup", str(blend_path), "--python", temp_runner.name]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.stdout:
            print(res.stdout)
        if res.stderr:
            print(res.stderr, file=sys.stderr)
        if res.returncode != 0:
            raise SystemExit(f"Render failed with code {res.returncode}")
    finally:
        Path(temp_runner.name).unlink(missing_ok=True)

    # Make strip
    files = [
        out_dir / f"{prefix}_m96.png",
        out_dir / f"{prefix}_zero.png",
        out_dir / f"{prefix}_p96.png",
    ]
    if all(f.exists() for f in files):
        create_strip(files, out_dir / f"{prefix}_strip.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--profile", default="clay")
    parser.add_argument("--prefix", default="clay")
    parser.add_argument("--hide-actors", action="store_true")
    args = parser.parse_args()

    run_render(args.blend, args.outdir, args.profile, args.prefix, args.hide_actors)


if __name__ == "__main__":
    main()
