#!/usr/bin/env python3
"""Run the #837 runtime->Blender WorldCamera numerical parity fixture."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tools" / "blender" / "tests" / "fixtures" / "thestra_camera_parity.json"
RUNTIME_HARNESS = ROOT / "tools" / "blender" / "tests" / "runtime_camera_parity"
BLENDER_TEST = ROOT / "tools" / "blender" / "tests" / "thestra_camera_parity_blender.py"


def _first_file(candidates):
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    return None


def love_executable():
    direct = _first_file([
        os.environ.get("LOVE_PATH"),
        r"C:\Program Files\LOVE\lovec.exe",
        r"C:\Program Files\LOVE\love.exe",
        shutil.which("lovec"),
        shutil.which("love"),
    ])
    if direct:
        return direct
    raise SystemExit("LÖVE not found; set LOVE_PATH")


def blender_executable():
    direct = _first_file([
        os.environ.get("BLENDER_PATH"), os.environ.get("BLENDER"),
        r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        shutil.which("blender"),
    ])
    if direct:
        return direct
    raise SystemExit("Blender not found; set BLENDER_PATH (or BLENDER)")


# A failing LOVE script does not exit: it raises into LOVE's error screen and
# waits for a keypress a CI runner will never send. Without a timeout the job
# sits until GitHub cancels it. This step normally finishes in well under a
# minute, and a broken require once burned the full 30-minute ceiling before
# anyone could see the error text.
RUNTIME_TIMEOUT_SECONDS = 120


def _tail(stream):
    if not stream:
        return ""
    text = stream if isinstance(stream, str) else stream.decode("utf-8", "replace")
    return text[-4000:]


def run_runtime_half():
    command = [love_executable(), str(RUNTIME_HARNESS), str(ROOT), str(FIXTURE)]
    try:
        result = subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True,
            timeout=RUNTIME_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as expired:
        raise SystemExit(
            "runtime calibration parity hung for %ds and was killed.\n"
            "LOVE almost certainly raised into its error screen, which never exits on its own.\n"
            % RUNTIME_TIMEOUT_SECONDS
            + _tail(expired.stdout) + "\n" + _tail(expired.stderr)
        )
    if result.returncode or "THESTRA_CAMERA_RUNTIME_PARITY OK" not in result.stdout:
        raise SystemExit(
            "runtime calibration parity failed\n"
            + result.stdout[-4000:] + "\n" + result.stderr[-4000:]
        )
    print("runtime WorldCamera calibration fixture: passed")


def run_blender_half():
    command = [
        blender_executable(), "--background", "--factory-startup",
        "--python", str(BLENDER_TEST), "--",
        "--root", str(ROOT), "--fixture", str(FIXTURE),
    ]
    result = subprocess.run(command, cwd=ROOT, text=True)
    if result.returncode:
        raise SystemExit(result.returncode)


def main():
    run_runtime_half()
    run_blender_half()


if __name__ == "__main__":
    main()
