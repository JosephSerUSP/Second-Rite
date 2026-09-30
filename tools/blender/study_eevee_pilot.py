"""One room, plate and atlas both on EEVEE, judged next to Cycles: the Padaria pilot.

The interior plates stay on Cycles because EEVEE lets the world fill leak into a sealed room (the
design doc measured 38% of the Padaria; `study_engine_parity.py` finds 74-80% under 5.2.2 even with
raytracing and Fast GI). A baked light probe volume with `capture_world` is the EEVEE answer, but it
darkens the room, so the pilot also solves the exposure: it scales `--lamp-scale` until the EEVEE
plate's mean linear luminance over the lit rows equals the Cycles plate's, in three steps.

It renders, for one room:

  * the Cycles plate (production settings: supersampled 3x and box-averaged, the stager's default);
  * the EEVEE plate as `stage_room_model.py --engine eevee` renders it today (AO raytracing);
  * the EEVEE plate with a light probe volume and matched exposure;
  * the fill's share of each plate's median (world fill on against off), the design doc's measure;
  * the 3D room drawn from an EEVEE projection atlas baked with the same probe volume and exposure,
    beside the Cycles atlas (`study_eevee_atlas.py`), nearest-sampled at native size, no film filter.

Then a contact sheet per comparison. Nothing here writes an asset.

    python tools/blender/study_eevee_pilot.py --out out/eevee-pilot/padaria \
        --cycles-atlas path/to/environment.png
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator  # noqa: E402

ENVIRONMENTS = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "environments"
STAGER = ROOT / "tools" / "blender" / "stage_room_model.py"
ATLAS_STUDY = ROOT / "tools" / "blender" / "study_eevee_atlas.py"
BASE_LAMP_SCALE = 0.3
PROBE_CELLS = 2
FIXED = ["--accent-scale", "0.4", "--window-emission-scale", "1.0", "--no-walker"]


def blender(*arguments: str) -> None:
    result = subprocess.run([blender_locator.blender_executable(), "--background", "--factory-startup",
                             "-noaudio", "--python-exit-code", "1", *arguments],
                            capture_output=True, text=True)
    if result.returncode != 0:
        sys.stdout.write(result.stdout[-2500:])
        sys.stderr.write(result.stderr[-1000:])
        raise SystemExit("Blender failed: " + " ".join(arguments[:6]))


def plate(room: str, path: Path, ambient: float, lamp_scale: float, *engine: str) -> Path:
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        blender("--python", str(STAGER), "--", "--model", str(ENVIRONMENTS / f"{room}.blend"),
                "--ambient", f"{ambient:g}", "--lamp-scale", f"{lamp_scale:.5f}", *FIXED, *engine,
                "--render", str(path))
    return path


def exposed_plate(room: str, path: Path, ambient: float, ev: float, *engine: str) -> Path:
    return plate(room, path, ambient, BASE_LAMP_SCALE, "--exposure", f"{ev:.4f}", *engine)


def linear(path: Path) -> np.ndarray:
    c = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def lit_rows(*images: np.ndarray) -> np.ndarray:
    rows = np.zeros(images[0].shape[0], dtype=bool)
    for image in images:
        rows |= image.max(axis=1) > 0
    return rows


def fill_share(lit: Path, dark: Path) -> float:
    a, b = linear(lit), linear(dark)
    rows = lit_rows(a, b)
    return float(1.0 - np.median(b[rows]) / np.median(a[rows]))


def diff_sheet(path: Path, pairs: list[str]) -> None:
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "blender" / "preview_diff_sheet.py"),
                             "--out", str(path), *pairs], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr[-1500:])
    print(result.stdout, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(prog="study_eevee_pilot")
    parser.add_argument("--room", default="alicias_padaria")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cycles-atlas", type=Path, default=None,
                        help="a Cycles atlas baked on the same layout (--atlas-layout packed)")
    parser.add_argument("--layout", default="packed")
    parser.add_argument("--span", type=float, default=7.7667, help="walkable lane length; 23 for the corridor")
    parser.add_argument("--atlas-size", type=int, default=1024)
    parser.add_argument("--probe-cells", type=float, default=PROBE_CELLS, help="light probe volume cells per metre")
    parser.add_argument("--eevee-option", action="append", default=[], metavar="NAME=VALUE",
                        help="scene.eevee override for every EEVEE render (plates and atlas)")
    parser.add_argument("--emissive-lights", action="store_true",
                        help="companion area lights on emissive patches for the probe plate and the atlas")
    parser.add_argument("--emissive-exclude", action="append", default=[], metavar="MATERIAL")
    parser.add_argument("--fixture-lights", action="store_true",
                        help="a small mesh around a lamp stops shadowing it (the lantern in its cage)")
    args = parser.parse_args()
    out = args.out.resolve()
    room = args.room
    options = [x for o in args.eevee_option for x in ("--eevee-option", o)]
    emissive = (["--emissive-lights"] + [x for m in args.emissive_exclude for x in ("--emissive-exclude", m)]
                if args.emissive_lights else [])
    emissive += ["--fixture-lights"] if args.fixture_lights else []
    probe = ["--engine", "eevee", "--probe-volume", str(args.probe_cells), *options, *emissive]

    cycles = plate(room, out / "plate_cycles.png", 0.13, BASE_LAMP_SCALE, "--engine", "cycles")
    cycles_dark = plate(room, out / "plate_cycles_dark.png", 0.0, BASE_LAMP_SCALE, "--engine", "cycles")
    ao = plate(room, out / "plate_eevee_ao.png", 0.13, BASE_LAMP_SCALE, "--engine", "eevee", *options)
    ao_dark = plate(room, out / "plate_eevee_ao_dark.png", 0.0, BASE_LAMP_SCALE, "--engine", "eevee", *options)

    target = linear(cycles)
    rows = lit_rows(target)
    goal = float(target[rows].mean())
    # Exposure is a camera setting, not a lighting one. Scaling the lamps barely moves a room whose
    # light is mostly world fill and window emission (measured: doubling --lamp-scale changed the mean
    # by 5%), and it would change the balance the recipe struck. A film exposure in EV multiplies the
    # whole frame, which is what "the probe volume made the room darker" needs.
    import math
    scale, ev = BASE_LAMP_SCALE, 0.0
    history = []
    for step in range(4):
        candidate = exposed_plate(room, out / f"probe_step{step}.png", 0.13, ev, *probe)
        cand = linear(candidate)
        measured = float(cand[lit_rows(cand)].mean())
        history.append({"exposureEV": round(ev, 4), "meanLinear": round(measured, 5)})
        print(f"exposure step {step}: {ev:+.3f} EV, mean linear {measured:.5f} (goal {goal:.5f})", flush=True)
        if abs(measured / goal - 1.0) < 0.03:
            break
        ev += math.log2(goal / measured)
    matched = out / "plate_eevee_probe.png"
    if not matched.is_file():
        exposed_plate(room, matched, 0.13, ev, *probe)
    matched_dark = exposed_plate(room, out / "plate_eevee_probe_dark.png", 0.0, ev, *probe)

    report = {"room": room, "goalMeanLinear": round(goal, 5), "exposureSteps": history,
              "matchedExposureEV": round(ev, 4),
              "fillShare": {"cycles": round(fill_share(cycles, cycles_dark), 4),
                            "eevee_ao": round(fill_share(ao, ao_dark), 4),
                            "eevee_probe_matched": round(fill_share(matched, matched_dark), 4)}}
    print("fill share:", json.dumps(report["fillShare"]), flush=True)

    diff_sheet(out / "plates_sheet.png", [
        f"cycles plate vs eevee AO plate (today's --engine eevee)={cycles}|{ao}",
        f"cycles plate vs eevee probe plate, exposure matched={cycles}|{matched}"])
    atlas_args = ["--blend", str(ENVIRONMENTS / f"{room}.blend"), "--layout", args.layout,
                  "--probe-volume", str(args.probe_cells), *options, *emissive, "--lamp-scale", f"{scale:.5f}", "--exposure", f"{ev:.4f}",
                  "--span", str(args.span), "--atlas-size", str(args.atlas_size), "--out", str(out / "atlas")]
    atlas_args += ["--cycles-atlas", str(args.cycles_atlas)] if args.cycles_atlas else ["--cycles-target"]
    blender("--python", str(ATLAS_STUDY), "--", *atlas_args)
    report["atlasStudy"] = json.loads((out / "atlas" / "result.json").read_text(encoding="utf-8"))
    a = out / "atlas"
    pairs = [f"3D room, eevee+probe beauty vs eevee projected atlas={a / 'target_eevee_1.png'}|{a / 'atlas_eevee_1.png'}",
             f"3D room, cycles beauty vs eevee+probe beauty (the engine gap)={a / 'target_cycles_1.png'}|{a / 'target_eevee_1.png'}",
             f"3D room, cycles beauty vs eevee projected atlas={a / 'target_cycles_1.png'}|{a / 'atlas_eevee_1.png'}"]
    if args.cycles_atlas:
        pairs = [f"3D room, cycles beauty vs cycles atlas (as baked today)={a / 'target_cycles_1.png'}|{a / 'atlas_cycles_1.png'}"] + pairs
    diff_sheet(out / "rooms_sheet.png", pairs)
    (out / "pilot.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
