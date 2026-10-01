"""The exterior bake must carry Geometry Nodes output into the render mesh (#1257).

Before this, ``rebuild_render_mesh`` copied each object's *base* mesh and chose
objects by name prefix, so a ground-cover host (an empty base mesh) baked to
nothing and nothing said so.  One Blender run measures every scenario (see
``exterior_bake_source_blender.py``); it runs the pinned Blender named by
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


class ExteriorBakeSourceTests(unittest.TestCase):
    probe = None

    @classmethod
    def setUpClass(cls):
        blender = blender_locator.blender_executable()
        script = ROOT / "tools" / "blender" / "tests" / "exterior_bake_source_blender.py"
        result = subprocess.run(
            [blender, "-b", "-noaudio", "--factory-startup", "-P", str(script)],
            capture_output=True, text=True, timeout=600)
        marker = "EXTERIOR_BAKE_PROBE "
        line = next((l for l in result.stdout.splitlines() if l.startswith(marker)), None)
        if line is None:
            raise AssertionError(f"probe produced no result:\n{result.stdout[-2000:]}")
        cls.probe = json.loads(line[len(marker):])
        if not cls.probe.get("ok"):
            raise AssertionError(cls.probe.get("error", "probe failed"))

    def test_the_scene_has_a_body_and_a_cover_to_measure(self):
        self.assertGreater(self.probe["base"], 100)
        self.assertGreater(self.probe["tufts"], 0)

    def test_ground_cover_reaches_the_render_mesh_exactly(self):
        # Every tuft is 4 triangles and none may be lost, merged or culled.
        self.assertEqual(self.probe["with_cover"] - self.probe["base"],
                         self.probe["tufts"] * self.probe["tris_per_tuft"])

    def test_an_unmarked_modifier_host_is_left_out_loudly(self):
        self.assertEqual(self.probe["unmarked"], self.probe["base"])
        self.assertTrue(self.probe["unmarked_warned"])

    def test_untagged_open_tufts_are_also_protected(self):
        # Boundary/zero-volume detection protects sheets even when authored tags
        # are missing. Tagged and untagged crossed cards must retain equal geometry.
        self.assertEqual(self.probe["closed_as_solid"], self.probe["with_cover"])

    # -- the ground: #1287 ---------------------------------------------------------------------
    def test_the_ground_sheet_keeps_its_top_and_faces_up(self):
        ground = self.probe["ground"]["whole"]
        self.assertEqual(ground["faces"], 1)
        self.assertEqual(ground["normalsZ"], [1.0])
        self.assertAlmostEqual(ground["area"], 40000.0, delta=1.0)

    def test_without_the_sheet_handling_the_cull_keeps_the_underside(self):
        """The negative control: the shipped Praca ground kept one face, pointing down (#1287).

        In this small scene the cull takes both faces; either way no face looks up, which is the defect.
        """
        ground = self.probe["ground"]["unflattened"]
        self.assertNotIn(1.0, ground["normalsZ"])
        self.assertLessEqual(ground["faces"], 1)

    def test_the_ground_is_cut_down_to_what_the_camera_sees(self):
        clipped = self.probe["ground"]["clipped"]
        self.assertEqual(clipped["normalsZ"], [1.0])
        self.assertGreater(clipped["area"], 100.0)            # the street is seen
        self.assertLess(clipped["area"], 0.5 * self.probe["ground"]["whole"]["area"])
        xmin, xmax, ymin, ymax = clipped["bounds"]
        self.assertLess(xmax - xmin, 200.0)
        self.assertLess(ymax - ymin, 200.0)

    def test_the_view_layout_gives_the_ground_more_than_the_fixed_three_per_cent(self):
        legacy, view = self.probe["ground"]["legacyLayout"], self.probe["ground"]["viewLayout"]
        self.assertLess(legacy["uvShare"], 0.05)
        self.assertGreater(view["uvShare"], 2.0 * legacy["uvShare"])

    def test_the_cycles_bake_reaches_the_ground(self):
        """Not only the geometry: the baked atlas holds light where the ground island is."""
        baked = self.probe["ground"]["bakedWhole"]
        self.assertEqual(baked["faces"], 1)
        self.assertGreater(baked["litFraction"], 0.9)
        self.assertGreater(baked["mean"], 0.05)

    def test_source_winding_repair_prevents_black_copy_only_bake(self):
        """Batch preparation repairs inverted closed-source winding before baking."""
        baked = self.probe["ground"]["bakedCopyOnly"]
        self.assertEqual(baked["faces"], 1)
        self.assertGreater(baked["litFraction"], 0.8)

    def test_a_marked_host_that_realises_nothing_refuses_to_bake(self):
        self.assertIn("refusing to bake", self.probe["refused"])
        self.assertIn("GROUND_COVER", self.probe["refused"])


if __name__ == "__main__":
    unittest.main()
