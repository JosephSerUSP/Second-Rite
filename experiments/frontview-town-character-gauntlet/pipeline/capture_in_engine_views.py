"""Capture real in-engine first-person viewport views of St. Maria world events using lovec.
"""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
RUNTIME_CAP_DIR = ROOT / "experiments" / "frontview-town-character-gauntlet" / "renders" / "runtime_captures"
LOVEC_PATH = r"C:\Program Files\LOVE\lovec.exe"


def capture_map_preview(map_id: int, x: int, y: int, dir_str: str) -> Image.Image:
    """Run lovec . preview-map <map_id> <x> <y> <dir> and return decoded PIL Image."""
    cmd = [LOVEC_PATH, ".", "preview-map", str(map_id), str(x), str(y), dir_str]
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)

    stdout = result.stdout
    if "PREVIEW BEGIN" not in stdout or "PREVIEW END" not in stdout:
        raise RuntimeError(f"lovec preview-map failed:\nSTDOUT:\n{stdout}\nSTDERR:\n{result.stderr}")

    json_text = stdout.split("PREVIEW BEGIN")[1].split("PREVIEW END")[0].strip()
    data = json.loads(json_text)
    if "error" in data:
        raise RuntimeError(f"preview-map error payload: {data['error']}")

    img_b64 = data["image"]
    img_bytes = base64.b64decode(img_b64)
    import io
    return Image.open(io.BytesIO(img_bytes))


def run_captures():
    RUNTIME_CAP_DIR.mkdir(parents=True, exist_ok=True)
    print("=== CAPTURING IN-ENGINE FIRST-PERSON VIEWPORT FRAMES ===")

    # Scenarios in St. Maria (Map 1):
    # Sister Agnes is at x=9, y=6 (0-indexed)
    # Registrar Celina is at x=11, y=6 (0-indexed)
    scenarios = [
        ("agnes_1step_near", 1, 9, 7, "N", "Sister Agnes -- 1 tile distance (near encounter)"),
        ("agnes_2steps_mid", 1, 9, 8, "N", "Sister Agnes -- 2 tiles distance (mid encounter)"),
        ("agnes_4steps_far", 1, 9, 10, "N", "Sister Agnes -- 4 tiles distance (far encounter)"),
        ("celina_1step_near", 1, 11, 7, "N", "Registrar Celina -- 1 tile distance (near encounter)"),
        ("celina_2steps_mid", 1, 11, 8, "N", "Registrar Celina -- 2 tiles distance (mid encounter)"),
        ("celina_4steps_far", 1, 11, 10, "N", "Registrar Celina -- 4 tiles distance (far encounter)"),
    ]

    for name, m_id, x, y, d, desc in scenarios:
        try:
            print(f"Capturing: {desc}...")
            img = capture_map_preview(m_id, x, y, d)
            out_p = RUNTIME_CAP_DIR / f"{name}.png"
            img.save(out_p)
            print(f"Saved: {out_p}")
        except Exception as exc:
            print(f"Failed {name}: {exc}")

    print("=== IN-ENGINE CAPTURES FINISHED ===")


if __name__ == "__main__":
    run_captures()
