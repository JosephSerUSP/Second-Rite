"""Run the one-shot C source bootstrap with the legacy C coordinate adapter.

Batch C wrote its authored coordinates directly to OBJ, where +Y is up. The
production Blender source contract is +Z-up and the shared exporter converts
Blender -> OBJ as ``(x, y, z) -> (x, z, -y)``. Therefore bootstrap points must
be mapped from the preserved C/OBJ frame into Blender as ``(x, -z, y)``.

This adapter exists only while materializing the initial editable source files;
the resulting .blend documents store ordinary Blender-space coordinates and
become the authority after visual review.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

source_path = SCRIPT_DIR / "bootstrap_c_item_sources.py"
source = source_path.read_text(encoding="utf-8")
needle = "        point.co = (*co, 1.0)\n"
replacement = (
    "        x, y, z = co\n"
    "        point.co = (x, -z, y, 1.0)  # legacy C/OBJ -> Blender +Z-up\n"
)
if source.count(needle) != 1:
    raise RuntimeError("C bootstrap coordinate assignment changed; review migration adapter")
source = source.replace(needle, replacement)
exec(compile(source, str(source_path), "exec"), {"__name__": "__main__", "__file__": str(source_path)})
