"""Phase 7: projection-window proof strip.

Renders the winner at three projection-window offsets and asserts that the eye
transform and lens are IDENTICAL across all three -- only the window moves.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TOWN = ROOT / "projects/hichaukitoden-game/assets/authoring/town"
OUT = TOWN / "town-final-projection-window-strip.png"


def _f(sz, bold=False):
    for n in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(n, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attempt", required=True)
    ap.add_argument("--calibration", required=True, type=Path)
    ap.add_argument("--offsets", nargs="*", type=float, default=[-96.0, 0.0, 96.0])
    ap.add_argument("--samples", type=int, default=180)
    ap.add_argument("--blender", default=r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
    args = ap.parse_args()

    frames, census = [], []
    for off in args.offsets:
        tag = "center" if off == 0 else ("left" if off < 0 else "right")
        png = TOWN / "attempts_next" / ("attempt_%s_pan_%s.png" % (args.attempt, tag))
        cmd = [args.blender, "--background", "--factory-startup", "--python",
               str(HERE / "render_attempt.py"), "--",
               "--attempt", args.attempt, "--calibration", str(args.calibration),
               "--samples", str(args.samples), "--offset", str(off),
               "--out", str(png)]
        r = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        line = [ln for ln in r.stdout.splitlines() if ln.startswith("ATTEMPT_OK")]
        if not line:
            raise RuntimeError("offset %s failed\n%s" % (off, r.stdout[-2500:]))
        rec = json.loads(line[0][len("ATTEMPT_OK "):])
        census.append(rec)
        frames.append((tag, off, png))
        print("  offset %+7.1f  lens=%.4f  eye=%s" % (off, rec["cameraLensMm"], rec["cameraEye"]))

    # the invariant this strip exists to prove
    lenses = {round(c["cameraLensMm"], 6) for c in census}
    eyes = {tuple(round(v, 6) for v in c["cameraEye"]) for c in census}
    if len(lenses) != 1 or len(eyes) != 1:
        raise RuntimeError("projection-window movement changed the camera! "
                           "lenses=%s eyes=%s" % (lenses, eyes))
    print("INVARIANT OK  single lens %s  single eye %s" % (lenses, eyes))

    S = 2
    W, H = 426 * S, 240 * S
    PAD, HDR, LAB = 14, 66, 34
    sheet = Image.new("RGB", (PAD + 3 * (W + PAD), HDR + H + LAB + PAD), (18, 19, 23))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 12), "PROJECTION-WINDOW PAN  -  fixed eye, fixed lens, moving window",
           fill=(238, 238, 244), font=_f(26, True))
    d.text((PAD, 44), "attempt %s   lens %.4f mm (identical in all three)   eye %s (identical in all three)"
           % (args.attempt, census[0]["cameraLensMm"], census[0]["cameraEye"]),
           fill=(150, 154, 168), font=_f(14))
    for i, (tag, off, png) in enumerate(frames):
        x = PAD + i * (W + PAD)
        sheet.paste(Image.open(png).convert("RGB").resize((W, H), Image.NEAREST), (x, HDR))
        d.rectangle([x, HDR, x + W - 1, HDR + H - 1], outline=(62, 64, 74))
        d.text((x, HDR + H + 7), "projectionWindowOffsetX = %+g px  (%s)" % (off, tag),
               fill=(240, 205, 90), font=_f(17, True))
    sheet.save(OUT)
    print("wrote %s %s" % (OUT, sheet.size))


if __name__ == "__main__":
    main()
