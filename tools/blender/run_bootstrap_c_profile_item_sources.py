"""Run the one-shot C profile bootstrap with the Batch-C roll-frame adapter.

Batch C's transported sweep frame and Blender Curve's minimum-twist bevel frame
use perpendicular zero-roll bases after the C/Y-up -> Blender/Z-up coordinate
conversion. The visual A/B showed an exact broad/edge-on swap for anisotropic
profiles, so source creation applies one uniform +90 degree tilt calibration.

This adapter exists only while creating the initial source documents. The saved
.blend files contain ordinary Blender tilt values and become authoritative after
review; this script is deleted before the migration PR is finalized.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

source_path = SCRIPT_DIR / "bootstrap_c_profile_item_sources.py"
source = source_path.read_text(encoding="utf-8")
needle = "        point.tilt = math.radians(float(roll))\n"
replacement = "        point.tilt = math.radians(float(roll) + 90.0)  # Batch-C frame -> Blender bevel frame\n"
if source.count(needle) != 1:
    raise RuntimeError("C profile bootstrap tilt assignment changed; review frame adapter")
source = source.replace(needle, replacement)
exec(compile(source, str(source_path), "exec"), {"__name__": "__main__", "__file__": str(source_path)})
