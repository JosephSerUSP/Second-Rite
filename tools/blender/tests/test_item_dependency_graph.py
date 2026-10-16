"""Pinned-Blender regression for the item export scratch dependency graph."""
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_test_support import blender_executable


class ItemDependencyGraphTests(unittest.TestCase):
    def test_internal_object_dependencies_follow_scratch_duplicates(self):
        result = subprocess.run(
            [
                blender_executable(), "--background", "--factory-startup",
                "--disable-autoexec", "--python-exit-code", "1", "--python",
                str(TOOLS / "tests/item_dependency_graph_blender.py"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout[-5000:] + result.stderr[-2000:])
        self.assertIn("ITEM DEPENDENCY GRAPH STRESS OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
