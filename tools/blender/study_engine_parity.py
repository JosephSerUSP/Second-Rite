"""Can EEVEE stand in for Cycles on the interior plates? A measurement, not a switch.

`stage_room_model.py` renders the St. Maria interiors with Cycles, for a
recorded reason (docs/design/st-maria-interior-authoring.md): the rooms are
sealed boxes, and EEVEE without an occlusion term let the world fill light them
as if the walls were absent (38% of the Padaria, against Cycles' 3.4%). Blender
5.2 reworked EEVEE's raytracing and Fast GI, so the answer may have moved.

For each room and each engine configuration this renders the plate twice, with
the world fill on (`--ambient 0.13`) and off (`--ambient 0`), and reports:

  * the fill's share of the median luminance, the measure the design doc uses
    (lower is better; Cycles is the reference);
  * the mean and 95th-percentile per-pixel difference from the Cycles plate,
    and the fraction of pixels more than 8/255 away;
  * the plate's median luminance.

It also writes a contact sheet per room: every configuration beside the Cycles
control, with a 4x amplified difference strip. Numbers rank; the contact sheet
decides, because this project's plates are judged by eye at 256 px.

    python tools/blender/study_engine_parity.py --out out/engine-parity

Nothing here writes an asset. The `.blend` sources are opened and never saved.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator  # noqa: E402

ENVIRONMENTS = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "environments"
ROOMS = ("alicias_padaria", "lauras_smith")
STAGER = ROOT / "tools" / "blender" / "stage_room_model.py"
COMMON = ["--lamp-scale", "0.3", "--accent-scale", "0.4",
          "--window-emission-scale", "1.0", "--no-walker"]

# name -> stager arguments. `cycles` is the control every other row is judged against.
CONFIGS = {
    "cycles": ["--engine", "cycles"],
    "eevee_no_rt": ["--engine", "eevee", "--no-raytracing"],
    "eevee_ao": ["--engine", "eevee"],
    "eevee_ao_nobackface": ["--engine", "eevee", "--eevee-option",
                            "ray_tracing_options.use_backface_hit=false"],
    "eevee_gi": ["--engine", "eevee", "--eevee-option",
                 "fast_gi_method=GLOBAL_ILLUMINATION"],
    "eevee_probe": ["--engine", "eevee", "--probe-volume", "2"],
    "eevee_probe_dense": ["--engine", "eevee", "--probe-volume", "4", "--probe-samples", "512"],
    "eevee_probe_no_rt": ["--engine", "eevee", "--no-raytracing", "--probe-volume", "2"],
    "eevee_gi_full": ["--engine", "eevee",
                      "--eevee-option", "fast_gi_method=GLOBAL_ILLUMINATION",
                      "--eevee-option", "ray_tracing_options.resolution_scale=1",
                      "--eevee-option", "ray_tracing_options.screen_trace_quality=1.0",
                      "--eevee-option", "fast_gi_resolution=1"],
}


def render(room: str, name: str, ambient: float, out: Path, reuse: bool = False) -> Path:
    target = out / room / f"{name}_a{ambient:g}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    if reuse and target.is_file():
        return target
    command = [blender_locator.blender_executable(), "--background", "--factory-startup",
               "-noaudio", "--python", str(STAGER), "--", "--model",
               str(ENVIRONMENTS / f"{room}.blend"), "--ambient", f"{ambient:g}",
               *COMMON, *CONFIGS[name], "--render", str(target)]
    started = time.time()
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not target.is_file():
        sys.stdout.write(result.stdout[-2000:])
        sys.stderr.write(result.stderr[-2000:])
        raise SystemExit(f"render failed: {room} {name} ambient {ambient:g}")
    print(f"  {room:16s} {name:22s} ambient {ambient:<5g} {time.time() - started:5.1f}s", flush=True)
    return target


def luminance(path: Path) -> np.ndarray:
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def _to_linear(srgb: np.ndarray) -> np.ndarray:
    c = srgb / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _to_srgb(linear: np.ndarray) -> np.ndarray:
    c = np.clip(linear, 0.0, 1.0)
    return 255.0 * np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def compare(control: Path, other: Path) -> dict:
    a = np.asarray(Image.open(control).convert("RGB"), dtype=np.float64)
    b = np.asarray(Image.open(other).convert("RGB"), dtype=np.float64)
    if a.shape != b.shape:
        raise SystemExit(f"shape mismatch {a.shape} vs {b.shape}")
    delta = np.abs(a - b).max(axis=2)
    # Exposure is one dial (--lamp-scale) and is tuned per engine, so a plate can
    # be uniformly darker without being structurally wrong. Fit one linear-light
    # gain to the plate and report the difference that remains: that is the part
    # exposure cannot fix (bounce, occlusion, colour).
    la, lb = _to_linear(a), _to_linear(b)
    gain = float(la.sum() / lb.sum()) if lb.sum() else 1.0
    fitted = np.abs(a - _to_srgb(lb * gain)).max(axis=2)
    return {"meanAbsDiff": round(float(delta.mean()), 3),
            "p95AbsDiff": round(float(np.percentile(delta, 95)), 3),
            "fractionOver8": round(float((delta > 8).mean()), 4),
            "exposureGain": round(gain, 3),
            "fittedMeanAbsDiff": round(float(fitted.mean()), 3),
            "fittedFractionOver8": round(float((fitted > 8).mean()), 4)}


def contact_sheet(room: str, names: list[str], out: Path) -> Path:
    control = Image.open(out / room / "cycles_a0.13.png").convert("RGB")
    width, height = control.size
    label = 14
    sheet = Image.new("RGB", (width * len(names), (height + label) * 2), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    base = np.asarray(control, dtype=np.float64)
    for column, name in enumerate(names):
        image = Image.open(out / room / f"{name}_a0.13.png").convert("RGB")
        diff = np.clip(np.abs(np.asarray(image, dtype=np.float64) - base) * 4, 0, 255)
        sheet.paste(image, (column * width, label))
        sheet.paste(Image.fromarray(diff.astype(np.uint8)), (column * width, height + 2 * label))
        draw.text((column * width + 3, 1), name, fill=(230, 230, 230))
        draw.text((column * width + 3, height + label + 1), "diff x4 vs cycles", fill=(160, 160, 160))
    path = out / f"{room}_contact.png"
    sheet.save(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(prog="study_engine_parity")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rooms", nargs="*", default=list(ROOMS))
    parser.add_argument("--configs", nargs="*", default=list(CONFIGS))
    parser.add_argument("--reuse", action="store_true",
                        help="keep renders already in --out and only re-analyse them")
    args = parser.parse_args()
    out = args.out.resolve()
    configs = ["cycles"] + [c for c in args.configs if c != "cycles"]
    print("Blender " + blender_locator.reported_version(blender_locator.blender_executable()))

    results = {}
    for room in args.rooms:
        renders = {}
        for name in configs:
            renders[name] = (render(room, name, 0.13, out, args.reuse), render(room, name, 0.0, out, args.reuse))
        # The plate is 256x240 with black dead rows above and below the room;
        # a whole-frame median would measure the black. Take the median over
        # the rows any render lit, the same rows for every configuration.
        lit = {n: (luminance(a), luminance(b)) for n, (a, b) in renders.items()}
        rows_lit = np.zeros(next(iter(lit.values()))[0].shape[0], dtype=bool)
        for pair in lit.values():
            for frame in pair:
                rows_lit |= frame.max(axis=1) > 0
        rows = {}
        for name, (bright, dark) in lit.items():
            median_lit = float(np.median(bright[rows_lit]))
            median_dark = float(np.median(dark[rows_lit]))
            rows[name] = {"medianLit": round(median_lit, 2), "medianDark": round(median_dark, 2),
                          "fillShare": round(1 - median_dark / median_lit, 4) if median_lit else None}
        control = out / room / "cycles_a0.13.png"
        for name in configs:
            rows[name].update(compare(control, out / room / f"{name}_a0.13.png"))
        results[room] = rows
        print("sheet", contact_sheet(room, configs, out))

    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    for room, rows in results.items():
        print(f"\n{room}")
        print(f"  {'config':22s} {'fill%':>6s} {'median':>7s} {'mean|d|':>8s} {'p95|d|':>7s} {'>8/255':>7s} {'gain':>6s} {'fit|d|':>7s} {'fit>8':>6s}")
        for name, row in rows.items():
            print(f"  {name:22s} {row['fillShare'] * 100:6.1f} {row['medianLit']:7.1f} "
                  f"{row['meanAbsDiff']:8.2f} {row['p95AbsDiff']:7.1f} {row['fractionOver8'] * 100:6.1f}% "
                  f"{row['exposureGain']:6.2f} {row['fittedMeanAbsDiff']:7.2f} {row['fittedFractionOver8'] * 100:5.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
