"""Render the same Blender town scene through two runtime calibration records."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))


def main() -> None:
    import bpy
    import thestra_camera

    parser = argparse.ArgumentParser()
    parser.add_argument("--camera-a", required=True, type=Path)
    parser.add_argument("--camera-b", required=True, type=Path)
    parser.add_argument("--out-a", required=True, type=Path)
    parser.add_argument("--out-b", required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)

    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    for record_path, output in ((args.camera_a, args.out_a), (args.camera_b, args.out_b)):
        record = json.loads(record_path.read_text(encoding="utf-8"))
        camera = thestra_camera.create_or_update_camera(record, scene=scene, make_active=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        print(f"THESTRA_TOWN_CAMERA_PAIR OK output={output} lens={float(camera.data.lens):.6f}")


if __name__ == "__main__":
    main()
