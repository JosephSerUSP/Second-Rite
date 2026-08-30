import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import build_synthetic_environment


class TerrainSurfaceTests(unittest.TestCase):
    """The adapter exists to read real scene geometry, so it is tested in Blender.

    One headless run produces every measurement; splitting it into a test per
    assertion would pay Blender's startup each time for no extra coverage.
    """

    probe = None

    @classmethod
    def setUpClass(cls):
        blender = build_synthetic_environment.blender_executable()
        script = ROOT / "tools" / "blender" / "tests" / "terrain_surface_blender.py"
        result = subprocess.run(
            [blender, "-b", "-noaudio", "--factory-startup", "-P", str(script)],
            capture_output=True, text=True, timeout=300)
        marker = "TERRAIN_PROBE "
        line = next((l for l in result.stdout.splitlines() if l.startswith(marker)), None)
        if line is None:
            raise AssertionError(f"probe produced no result:\n{result.stdout[-2000:]}")
        cls.probe = json.loads(line[len(marker):])
        if not cls.probe.get("ok"):
            raise AssertionError(cls.probe.get("error", "probe failed"))

    def test_height_follows_the_mesh(self):
        self.assertAlmostEqual(self.probe["flat_height"], 0.0, places=3)
        # The ridge climbs at 0.6 per metre, so x=3 sits at 1.8.
        self.assertAlmostEqual(self.probe["ramp_height"], 1.8, places=3)

    def test_normals_report_real_slope(self):
        self.assertAlmostEqual(self.probe["flat_normal_z"], 1.0, places=3)
        self.assertLess(self.probe["ramp_normal_z"], 0.95)
        self.assertGreater(self.probe["ramp_normal_z"], 0.5)

    def test_a_miss_falls_back_instead_of_raising(self):
        # A patch overhanging its ground should thin out, not fail the scatter.
        self.assertEqual(self.probe["miss_height"], 0.0)

    def test_painted_weight_becomes_density(self):
        self.assertAlmostEqual(self.probe["weight_painted"], 1.0, places=2)
        self.assertAlmostEqual(self.probe["weight_bare"], 0.0, places=2)

    def test_keep_out_clears_a_footprint(self):
        self.assertEqual(self.probe["mask_on_lane"], 0.0)
        self.assertEqual(self.probe["mask_off_lane"], 1.0)

    def test_patch_bounds_cover_the_ground(self):
        centre_x, centre_y, width, depth = self.probe["patch"]
        self.assertAlmostEqual(centre_x, 0.0, places=3)
        self.assertAlmostEqual(centre_y, 0.0, places=3)
        self.assertAlmostEqual(width, 10.0, places=3)
        self.assertAlmostEqual(depth, 10.0, places=3)

    def test_the_scatter_obeys_paint_and_keep_out_together(self):
        self.assertGreater(self.probe["tufts"], 0)
        self.assertGreater(self.probe["roots_on_painted_side"], 0)
        self.assertEqual(self.probe["roots_on_bare_side"], 0)
        self.assertEqual(self.probe["roots_inside_lane"], 0)

    def test_every_tuft_sits_on_the_terrain(self):
        # The whole point of the adapter: without it a patch is flat at z=0
        # regardless of the ground under it.
        self.assertLess(self.probe["max_height_error"], 1e-4)


if __name__ == "__main__":
    unittest.main()
