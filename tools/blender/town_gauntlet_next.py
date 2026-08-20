"""Next-gauntlet entrypoint: inject a generated Thestra camera into #856 tooling.

The historical #856 builder intentionally remains unchanged as evidence of the
first gauntlet. This wrapper replaces only its in-process calibration record.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
CALIBRATION_ENV = "THESTRA_TOWN_CAMERA_CALIBRATION"


def _load_record():
    raw = os.environ.get(CALIBRATION_ENV)
    if not raw:
        raise SystemExit(
            f"{CALIBRATION_ENV} is not set; run tools/blender/run_next_town_gauntlet.py "
            "or generate a calibration first"
        )
    path = Path(raw).resolve()
    if not path.is_file():
        raise SystemExit(f"town camera calibration not found: {path}")
    record = json.loads(path.read_text(encoding="utf-8"))

    import thestra_camera

    thestra_camera.validate_calibration(record)
    if abs(float(record["orientation"]["pitchRadians"])) > 1e-10:
        raise SystemExit("next town gauntlet calibration is not level sideview")
    return record


def main():
    record = _load_record()
    import town_gauntlet_builder as builder

    # Compatibility adapter only: all scene construction/rendering stays in the
    # existing #856 builder, but its parity-test fixture can no longer become
    # accidental art direction for the next gauntlet.
    builder.CALIBRATION_RECORD = record
    builder.main()


if __name__ == "__main__":
    main()
