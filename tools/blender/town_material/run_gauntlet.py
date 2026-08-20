"""Drive the town gauntlet: generate the calibration, render attempts, collect census."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "projects/hichaukitoden-game/assets/authoring/town/attempts_next"


def blender():
    for c in (os.environ.get("BLENDER_PATH"),
              r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
              shutil.which("blender")):
        if c and Path(c).is_file():
            return c
    raise RuntimeError("Blender not found")


def calibration(dest: Path) -> Path:
    sys.path.insert(0, str(ROOT / "tools" / "blender"))
    from generate_town_camera_calibration import generate
    return Path(generate(dest))


def render(attempt, cal, samples, offset=0.0, out=None, blend=None, census=None):
    cmd = [blender(), "--background", "--factory-startup", "--python",
           str(HERE / "render_attempt.py"), "--",
           "--attempt", attempt, "--calibration", str(cal),
           "--samples", str(samples), "--offset", str(offset)]
    if out:
        cmd += ["--out", str(out)]
    if blend:
        cmd += ["--blend", str(blend)]
    if census:
        cmd += ["--census", str(census)]
    r = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("ATTEMPT_OK")]
    if not line:
        raise RuntimeError("attempt %s failed\n%s\n%s"
                           % (attempt, r.stdout[-3000:], r.stderr[-2000:]))
    return json.loads(line[0][len("ATTEMPT_OK "):])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attempts", nargs="*", default=None)
    ap.add_argument("--samples", type=int, default=160)
    args = ap.parse_args()

    from town_attempts import ATTEMPTS
    sys.path.insert(0, str(HERE))

    OUT.mkdir(parents=True, exist_ok=True)
    cal = calibration(OUT / "town-camera-calibration.json")
    names = args.attempts or sorted(ATTEMPTS)
    census = {}
    for a in names:
        rec = render(a, cal, args.samples, census=OUT / ("census_%s.json" % a))
        census[a] = rec
        print("  %s  %-42s src=%7d rnd=%5d  %.0f:1  lens=%.4f"
              % (a, rec["title"][:42], rec["sourceTris"], rec["renderTris"],
                 rec["reductionRatio"], rec["cameraLensMm"]))
    (OUT / "census.json").write_text(json.dumps(census, indent=2), encoding="utf-8")
    print("GAUNTLET_OK %d attempts" % len(census))


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    main()
