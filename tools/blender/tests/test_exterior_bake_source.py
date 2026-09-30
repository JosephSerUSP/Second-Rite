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

    def test_the_open_surface_mark_is_what_protects_the_tufts(self):
        # Control: without it the parity cull treats crossed cards as solids and
        # deletes some, so the exact-count test above is not passing by accident.
        self.assertLess(self.probe["closed_as_solid"], self.probe["with_cover"])

    def test_a_marked_host_that_realises_nothing_refuses_to_bake(self):
        self.assertIn("refusing to bake", self.probe["refused"])
        self.assertIn("GROUND_COVER", self.probe["refused"])


if __name__ == "__main__":
    unittest.main()
