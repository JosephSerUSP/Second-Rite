"""The worked exterior (tools/blender/recipes/examples/exterior_reference.py) builds and passes its
own checks, and those checks catch a broken composition (#1350).

One Blender run (``exterior_example_blender.py``) builds the example, measures it, injects a board
and measures again, and tries to save it into a Project. It runs the pinned Blender named by
``BLENDER_EXECUTABLE``.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator  # noqa: E402


class ExteriorExampleTests(unittest.TestCase):
    probe = None

    @classmethod
    def setUpClass(cls):
        script = ROOT / "tools" / "blender" / "tests" / "exterior_example_blender.py"
        result = subprocess.run(
            [blender_locator.blender_executable(), "-b", "-noaudio", "--factory-startup",
             "--python-exit-code", "1", "-P", str(script)],
            capture_output=True, text=True, timeout=600)
        marker = "EXTERIOR_EXAMPLE_PROBE "
        line = next((l for l in result.stdout.splitlines() if l.startswith(marker)), None)
        if line is None:
            raise AssertionError(f"probe produced no result:\n{result.stdout[-2000:]}\n{result.stderr[-1000:]}")
        cls.probe = json.loads(line[len(marker):])

    def test_the_example_passes_its_own_checks(self):
        self.assertEqual(self.probe["cleanProblems"], [])
        self.assertEqual(self.probe["clean"]["boards"], [])

    def test_the_near_stack_covers_the_menu_band_everywhere(self):
        self.assertGreaterEqual(self.probe["clean"]["dockCoverageMin"], 0.6)

    def test_an_injected_board_fails(self):
        self.assertTrue(any("tall-or-continuous" in p for p in self.probe["boardProblems"]),
                        self.probe["boardProblems"])

    def test_it_will_not_save_into_a_project(self):
        self.assertTrue(self.probe["projectSaveRefused"])

    def test_it_is_named_as_an_example(self):
        self.assertTrue(self.probe["clean"]["asset"].startswith("example_"))
        self.assertIn("EXAMPLE_EXTERIOR_REFERENCE", self.probe["rootNames"])


if __name__ == "__main__":
    unittest.main()
