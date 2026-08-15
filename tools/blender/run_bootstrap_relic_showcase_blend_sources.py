"""Run the one-shot relic migration with tools/blender importable in Blender Python.

Fresh-run marker: runner retry after hosted package setup stalled before Blender.
"""

from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

runpy.run_path(str(HERE / "bootstrap_relic_showcase_blend_sources.py"), run_name="__main__")
