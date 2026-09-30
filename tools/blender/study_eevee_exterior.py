"""The Praça exterior: its atlas as Cycles bakes it today, and as EEVEE would by projection.

The interiors needed a light probe volume, a solved exposure and two lighting shims to stand beside
Cycles. The exterior is lit differently: one sample, no bounces, a sun and a world fill (the exporter's
`flat_bake` profile). This drives `study_eevee_exterior_blender.py`, which bakes both atlases on the same
rebuilt mesh, then lays the views from lane positions the EEVEE bake did not use side by side:

  * the EEVEE beauty of the source meshes, against the EEVEE atlas on the joined mesh;
  * the Cycles atlas (what ships) against the EEVEE atlas, unlit and nearest-sampled at native size.

Nothing here writes an asset, and the source document is never saved.

    python tools/blender/study_eevee_exterior.py --out out/eevee-exterior/praca
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator  # noqa: E402

BLENDER_SIDE = ROOT / "tools" / "blender" / "study_eevee_exterior_blender.py"
SHEET = ROOT / "tools" / "blender" / "preview_diff_sheet.py"


def main() -> int:
    parser = argparse.ArgumentParser(prog="study_eevee_exterior")
    parser.add_argument("--out", type=Path, required=True)
    args, passthrough = parser.parse_known_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([blender_locator.blender_executable(), "--background", "--factory-startup",
                             "-noaudio", "--python-exit-code", "1", "--python", str(BLENDER_SIDE), "--",
                             "--out", str(out), *passthrough], capture_output=True, text=True)
    (out / "blender.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode != 0:
        sys.stdout.write(result.stdout[-3000:])
        sys.stderr.write(result.stderr[-1500:])
        raise SystemExit("Blender failed; see " + str(out / "blender.log"))
    for line in result.stdout.splitlines():
        if line.startswith(("lights", "beauty frame", "EEVEE atlas", "texels per", "probe volume", "eevee options")):
            print(line, flush=True)
    cycles = "--no-cycles" not in passthrough
    for number in (1, 3):
        pairs = [f"EEVEE beauty vs EEVEE atlas (how well the projection reproduces its own lighting)="
                 f"{out / f'target_eevee_{number}.png'}|{out / f'atlas_eevee_{number}.png'}"]
        if cycles:
            pairs += [f"Cycles atlas (shipped approach) vs EEVEE atlas (what the player would see)="
                      f"{out / f'atlas_cycles_{number}.png'}|{out / f'atlas_eevee_{number}.png'}",
                      f"EEVEE beauty vs Cycles atlas="
                      f"{out / f'target_eevee_{number}.png'}|{out / f'atlas_cycles_{number}.png'}"]
        sheet = subprocess.run([sys.executable, str(SHEET), "--out", str(out / f"sheet_{number}.png"), *pairs],
                               capture_output=True, text=True)
        if sheet.returncode != 0:
            raise SystemExit(sheet.stderr[-1500:])
        print(sheet.stdout, flush=True)
    print((out / "result.json").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
