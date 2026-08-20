"""Numerically solve the fixed-eye distance for a native 24x48 actor.

Each candidate is resolved by the LÖVE runtime harness, then measured by the
Blender adapter.  The resulting record is therefore a checked boundary
artifact, not a hand-derived camera duplicate.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "town-camera-next.json"
DEFAULT_BLEND = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "town-next-level-winner.blend"
MEASURE = ROOT / "tools" / "blender" / "measure_town_camera_actor.py"
GENERATE = ROOT / "tools" / "blender" / "generate_town_camera_calibration.py"
MEASURE_RE = re.compile(
    r"THESTRA_TOWN_ACTOR_MEASURE OK heightPx=([0-9.eE+-]+) "
    r"feet=\(([0-9.eE+-]+),([0-9.eE+-]+)\) "
    r"top=\(([0-9.eE+-]+),([0-9.eE+-]+)\) lens=([0-9.eE+-]+)"
)


def blender_executable() -> str:
    for candidate in (
        os.environ.get("BLENDER_PATH"),
        r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
        shutil.which("blender"),
    ):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise RuntimeError("Blender not found; set BLENDER_PATH")


def parse_measure(output: str) -> dict:
    match = MEASURE_RE.search(output)
    if not match:
        raise RuntimeError("Blender actor measurement marker missing\n" + output[-4000:])
    values = [float(v) for v in match.groups()]
    return {
        "heightPx": values[0],
        "feet": {"x": values[1], "y": values[2]},
        "top": {"x": values[3], "y": values[4]},
        "lensMm": values[5],
    }


def measure(calibration: Path, blend: Path, actor: str, height: float) -> dict:
    result = subprocess.run(
        [blender_executable(), "--background", str(blend), "--python", str(MEASURE), "--",
         "--camera", str(calibration), "--actor", actor, "--height", str(height)],
        cwd=ROOT, text=True, capture_output=True,
    )
    if result.returncode:
        raise RuntimeError("Blender camera measurement failed\n" + result.stdout[-4000:] + result.stderr[-4000:])
    return parse_measure(result.stdout + result.stderr)


def write_spec(source: dict, distance: float, output: Path) -> None:
    spec = json.loads(json.dumps(source))
    spec["camera"]["distance"] = distance
    output.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")


def solve(args: argparse.Namespace) -> dict:
    source = json.loads(args.spec.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="thestra-town-camera-") as temp:
        temp_dir = Path(temp)

        def evaluate(distance: float) -> dict:
            spec_path = temp_dir / "candidate.json"
            calibration_path = temp_dir / "candidate-calibration.json"
            write_spec(source, distance, spec_path)
            generated = subprocess.run(
                [sys.executable, str(GENERATE), str(calibration_path), "--spec", str(spec_path)],
                cwd=ROOT, text=True, capture_output=True,
            )
            if generated.returncode:
                raise RuntimeError("runtime camera calibration failed\n" + generated.stdout[-4000:] + generated.stderr[-4000:])
            result = measure(calibration_path, args.blend, args.actor, args.height)
            result["distance"] = distance
            result["calibration"] = json.loads(calibration_path.read_text(encoding="utf-8"))
            return result

        low = evaluate(args.minimum)
        high = evaluate(args.maximum)
        if not (low["heightPx"] > args.target and high["heightPx"] < args.target):
            raise RuntimeError(
                f"distance bracket does not contain {args.target}px: "
                f"{args.minimum}=>{low['heightPx']}, {args.maximum}=>{high['heightPx']}"
            )
        best = high
        for _ in range(args.iterations):
            mid = (low["distance"] + high["distance"]) * 0.5
            candidate = evaluate(mid)
            if abs(candidate["heightPx"] - args.target) < abs(best["heightPx"] - args.target):
                best = candidate
            if candidate["heightPx"] > args.target:
                low = candidate
            else:
                high = candidate

        if abs(best["heightPx"] - args.target) > args.tolerance:
            raise RuntimeError(f"camera solve missed target: {best['heightPx']}px")
        record = best["calibration"]
        record["townActorSolve"] = {
            "targetHeightPixels": args.target,
            "measuredHeightPixels": best["heightPx"],
            "actorWorldAnchor": [float(v) for v in args.actor.split(",")],
            "actorWorldHeight": args.height,
            "distance": best["distance"],
            "method": "runtime-lovec-calibration -> Blender world_to_camera_view binary search",
        }
        record["sourceCameraSpec"] = str(args.spec.relative_to(ROOT)).replace("\\", "/")
        return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--blend", type=Path, default=DEFAULT_BLEND)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--actor", default="5.35,5.5,-1.5")
    parser.add_argument("--height", type=float, default=1.75)
    parser.add_argument("--target", type=float, default=48.0)
    parser.add_argument("--minimum", type=float, default=1.0)
    parser.add_argument("--maximum", type=float, default=128.0)
    parser.add_argument("--iterations", type=int, default=16)
    parser.add_argument("--tolerance", type=float, default=0.001)
    args = parser.parse_args()
    args.spec = args.spec.resolve()
    args.blend = args.blend.resolve()
    args.output = args.output.resolve()
    record = solve(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(
        "THESTRA_TOWN_CAMERA_DISTANCE_SOLVE OK "
        f"distance={record['townActorSolve']['distance']:.9f} "
        f"heightPx={record['townActorSolve']['measuredHeightPixels']:.9f} "
        f"lensMm={record['lensMm'] if 'lensMm' in record else 'derived'}"
    )


if __name__ == "__main__":
    main()
