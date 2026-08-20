#!/usr/bin/env python3
"""Fail-fast runtime + Blender check for the next town-gauntlet camera."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLENDER_TEST = ROOT / "tools" / "blender" / "tests" / "town_camera_blender.py"


def _first_file(candidates):
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    return None


def blender_executable():
    direct = _first_file([
        os.environ.get("BLENDER_PATH"),
        os.environ.get("BLENDER"),
        r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
        shutil.which("blender"),
    ])
    if direct:
        return direct
    raise RuntimeError("Blender not found; set BLENDER_PATH or BLENDER")


def validate_blender(calibration_path: Path):
    result = subprocess.run(
        [
            blender_executable(),
            "--background",
            "--factory-startup",
            "--python",
            str(BLENDER_TEST),
            "--",
            "--camera",
            str(Path(calibration_path).resolve()),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode or "THESTRA_TOWN_CAMERA_BLENDER OK" not in result.stdout:
        raise RuntimeError(
            "town camera Blender validation failed\n"
            + result.stdout[-4000:]
            + "\n"
            + result.stderr[-4000:]
        )
    print(result.stdout.strip().splitlines()[-1])


def main():
    from generate_town_camera_calibration import generate

    with tempfile.TemporaryDirectory(prefix="thestra-town-camera-") as tmp:
        calibration = generate(Path(tmp) / "town-camera-calibration.json")
        validate_blender(calibration)


if __name__ == "__main__":
    main()
