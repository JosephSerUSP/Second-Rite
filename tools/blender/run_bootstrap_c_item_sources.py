"""Run the one-shot C source bootstrap with repository Blender modules importable."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

runpy.run_path(str(SCRIPT_DIR / "bootstrap_c_item_sources.py"), run_name="__main__")
