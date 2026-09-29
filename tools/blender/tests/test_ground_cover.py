"""Headless check for the Geometry Nodes ground cover (#1257).

One Blender run produces every measurement (see ``ground_cover_blender.py``);
splitting it into a run per assertion would pay Blender's startup each time for
no extra coverage.  It runs the pinned Blender named by ``BLENDER_EXECUTABLE``.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator  # noqa: E402


class GroundCoverTests(unittest.TestCase):
    probe = None

    @classmethod
    def setUpClass(cls):
        blender = blender_locator.blender_executable()
        script = ROOT / "tools" / "blender" / "tests" / "ground_cover_blender.py"
        result = subprocess.run(
            [blender, "-b", "-noaudio", "--factory-startup", "-P", str(script)],
            capture_output=True, text=True, timeout=300)
        marker = "GROUND_COVER_PROBE "
        line = next((l for l in result.stdout.splitlines() if l.startswith(marker)), None)
        if line is None:
            raise AssertionError(f"probe produced no result:\n{result.stdout[-2000:]}")
        cls.probe = json.loads(line[len(marker):])
        if not cls.probe.get("ok"):
            raise AssertionError(cls.probe.get("error", "probe failed"))

    def test_it_scatters_something_realised_as_plain_mesh(self):
        self.assertGreater(self.probe["tufts"], 0)
        # Two crossed quads per tuft, realised: nothing but vertices remains.
        self.assertEqual(self.probe["vertices"], self.probe["tufts"] * 8)

    def test_no_instance_stands_above_the_slope_limit(self):
        self.assertGreaterEqual(self.probe["min_normal_z"], self.probe["slope_floor"] - 1e-3)
        # The control: lifting the limit is what lets the ridge root.
        self.assertEqual(self.probe["roots_on_ridge"], 0)
        self.assertGreater(self.probe["ridge_roots_without_limit"], 0)

    def test_nothing_is_inside_a_keep_out_footprint(self):
        self.assertEqual(self.probe["roots_inside_lane"], 0)
        # ...and the lane is what did it: an empty keep-out gains tufts back.
        self.assertGreater(self.probe["empty_keep_out_gains"], 0)

    def test_painted_density_gates_the_scatter(self):
        self.assertGreater(self.probe["roots_painted_side"], 0)
        self.assertEqual(self.probe["roots_bare_side"], 0)
        # Controls: with the slope limit lifted the bare side is still bare, and
        # only clearing the group name makes it root there.
        self.assertEqual(self.probe["bare_side_with_paint_without_limit"], 0)
        self.assertGreater(self.probe["unpainted_bare_side"], 0)

    def test_every_tuft_sits_on_the_terrain(self):
        self.assertLess(self.probe["max_height_error"], 1e-3)

    def test_the_vertex_budget_is_honoured_exactly(self):
        self.assertEqual(self.probe["budgeted_vertices"], 10 * 8)

    def test_seeded_and_deterministic(self):
        self.assertTrue(self.probe["repeatable"])
        self.assertTrue(self.probe["seed_changes_layout"])
        self.assertTrue(self.probe["seed_restores_layout"])


if __name__ == "__main__":
    unittest.main()
