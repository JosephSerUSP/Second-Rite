#!/usr/bin/env python3
"""Generate the next-town-gauntlet camera calibration through LÖVE/Thestra."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = (
    ROOT
    / "projects"
    / "hichaukitoden-game"
    / "assets"
    / "authoring"
    / "town"
    / "town-camera-next.json"
)
RUNTIME_HARNESS = ROOT / "tools" / "blender" / "tests" / "runtime_town_camera"


def _first_file(candidates):
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    return None


def love_executable():
    direct = _first_file([
        os.environ.get("LOVE_PATH"),
        os.environ.get("LOVEC"),
        r"C:\Program Files\LOVE\lovec.exe",
        r"C:\Program Files\LOVE\love.exe",
        shutil.which("lovec"),
        shutil.which("love"),
    ])
    if direct:
        return direct
    raise RuntimeError("LÖVE not found; set LOVE_PATH or LOVEC")


def generate(output_path: Path, spec_path: Path = DEFAULT_SPEC) -> Path:
    output_path = Path(output_path).resolve()
    spec_path = Path(spec_path).resolve()
    if not spec_path.is_file():
        raise FileNotFoundError(f"town camera spec not found: {spec_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [love_executable(), str(RUNTIME_HARNESS), str(ROOT), str(spec_path), str(output_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode or "THESTRA_TOWN_CAMERA_CALIBRATION OK" not in result.stdout:
        raise RuntimeError(
            "town camera runtime calibration failed\n"
            + result.stdout[-4000:]
            + "\n"
            + result.stderr[-4000:]
        )
    print(result.stdout.strip())
    return output_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    args = parser.parse_args()
    generate(args.output, args.spec)


if __name__ == "__main__":
    main()
