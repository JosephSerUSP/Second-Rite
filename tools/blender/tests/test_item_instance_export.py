"""Pinned-Blender host regression for collection-instance item export."""
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_test_support import blender_executable


class ItemInstanceExportTests(unittest.TestCase):
    def test_collection_instance_is_realized_only_in_export_scratch_graph(self):
        result = subprocess.run(
            [
                blender_executable(), "--background", "--factory-startup",
                "--disable-autoexec", "--python-exit-code", "1", "--python",
                str(TOOLS / "tests/item_instance_export_blender.py"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout[-6000:] + result.stderr[-2000:])
        self.assertIn("ITEM COLLECTION INSTANCE EXPORT STRESS OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
