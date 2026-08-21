"""Focused Blender proof for authoritative camera and Walker preview facts."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXTURE = HERE / "tests" / "fixtures" / "thestra_camera_calibration.json"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def blender_executable() -> str:
    candidates = [
        os.environ.get("BLENDER_PATH"),
        os.environ.get("BLENDER"),
        r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        shutil.which("blender"),
    ]
    for candidate in candidates:
        if candidate and (candidate == "blender" or Path(candidate).is_file()):
            return str(candidate)
    raise SystemExit("Blender not found; set BLENDER_PATH or BLENDER")


def run_inside_blender(root: Path) -> None:
    import bpy
    import thestra_camera

    record = thestra_camera.load_calibration(FIXTURE)
    scene = bpy.context.scene
    camera = thestra_camera.create_or_update_camera(record, scene=scene)
    expected = {
        row["name"]: row["screenAtZero"]
        for row in record["samples"]
    }
    points = {
        row["name"]: row["world"]
        for row in record["samples"]
    }
    for name, point in points.items():
        actual = thestra_camera.project_world_point(scene, camera, point)
        wanted = expected[name]
        if max(abs(actual[index] - wanted[index]) for index in (0, 1)) > 1e-4:
            raise AssertionError(f"camera parity failed for {name}: {actual} != {wanted}")

    transform = tuple(round(value, 9) for row in camera.matrix_world for value in row)
    base_shift = float(camera.data.shift_x)
    movement = []
    for offset in (-96.0, 0.0, 96.0):
        camera.data.shift_x = base_shift - offset / float(record["targetWidth"])
        current = thestra_camera.project_world_point(scene, camera, points["optical_center"])
        movement.append({"offset": offset, "screen": list(current)})
        current_transform = tuple(round(value, 9) for row in camera.matrix_world for value in row)
        if current_transform != transform:
            raise AssertionError("projection-window movement translated or rotated the eye")
    if abs(movement[0]["screen"][0] - movement[2]["screen"][0]) < 100.0:
        raise AssertionError("projection-window movement did not move the frame")

    walker_path = root / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
    walker = thestra_camera.create_actor_preview(
        walker_path, camera, anchor=(1.0, 2.0, 0.0), frame_width=24, frame_height=48
    )
    if tuple(round(value, 6) for value in walker.location) != (1.0, 2.0, 0.0):
        raise AssertionError("Walker preview lost its feet anchor")
    if abs(float(walker.dimensions.z) - 1.75) > 1e-4:
        raise AssertionError(f"Walker preview height is {walker.dimensions.z}, not 1.75")

    print("THESTRA_CAMERA_CALIBRATION OK")
    print(json.dumps({"transform": transform, "projectionWindow": movement}, indent=2))


def main() -> None:
    try:
        import bpy  # noqa: F401
        in_blender = True
    except ImportError:
        in_blender = False
    if in_blender:
        run_inside_blender(ROOT)
        return
    command = [
        blender_executable(), "--background", "--factory-startup",
        "--python", str(Path(__file__).resolve()), "--",
        "--root", str(ROOT),
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    print(result.stdout)


if __name__ == "__main__":
    main()
