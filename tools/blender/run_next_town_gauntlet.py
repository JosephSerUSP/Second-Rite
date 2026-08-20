#!/usr/bin/env python3
"""Run #856's gauntlet machinery with the owner-selected next camera baseline."""
from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTHORING_DIR = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town"
NEXT_BUILDER = ROOT / "tools" / "blender" / "town_gauntlet_next.py"
CAMERA_ENV = "THESTRA_TOWN_CAMERA_CALIBRATION"


def _lens_mm(record):
    ax = (
        float(record["projectionScale"]["x"])
        / float(record["fovHalfX"])
        * (float(record["baseViewportWidth"]) / float(record["targetWidth"]))
    )
    return 36.0 * ax * 0.5


def _rewrite_report_camera(record):
    path = AUTHORING_DIR / "town-gauntlet-report.md"
    if not path.is_file():
        return
    fov_degrees = math.degrees(2 * math.atan(float(record["fovHalfX"])))
    lens = _lens_mm(record)
    replacement = (
        "**Camera Authority:** generated Thestra town-gauntlet calibration "
        f"(426x240 Wide native, 256x144 base projection, level 0 deg pitch, "
        f"{fov_degrees:.2f} deg horizontal FOV, ~{lens:.1f} mm Blender equivalent)  "
    )
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith("**Camera Authority:**"):
            lines[index] = replacement
            lines.insert(
                index + 1,
                "**Camera Source:** `town-camera-next.json` -> LÖVE/Thestra calibration -> Blender preview  ",
            )
            break
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    from generate_town_camera_calibration import generate
    from check_next_town_camera import blender_executable, validate_blender
    import run_full_town_gauntlet as gauntlet

    with tempfile.TemporaryDirectory(prefix="thestra-next-town-gauntlet-") as tmp:
        calibration = generate(Path(tmp) / "town-camera-calibration.json")
        validate_blender(calibration)
        record = json.loads(calibration.read_text(encoding="utf-8"))

        previous = os.environ.get(CAMERA_ENV)
        os.environ[CAMERA_ENV] = str(calibration)
        try:
            gauntlet.BLENDER_EXE = blender_executable()
            gauntlet.BUILDER_SCRIPT = NEXT_BUILDER
            gauntlet.main()
        finally:
            if previous is None:
                os.environ.pop(CAMERA_ENV, None)
            else:
                os.environ[CAMERA_ENV] = previous

        _rewrite_report_camera(record)


if __name__ == "__main__":
    main()
