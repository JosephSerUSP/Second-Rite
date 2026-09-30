"""The room atlas is packed tight and, optionally, spent where the camera looks (#877).

One Blender run (see ``atlas_allocation_blender.py``) lays out a three-quad scene four ways:
the original loose layout, packed, allocated by view, and allocated by view with the bias at 0.
It runs the pinned Blender named by ``BLENDER_EXECUTABLE``.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator  # noqa: E402


class AtlasAllocationTests(unittest.TestCase):
    probe = None

    @classmethod
    def setUpClass(cls):
        script = ROOT / "tools" / "blender" / "tests" / "atlas_allocation_blender.py"
        result = subprocess.run(
            [blender_locator.blender_executable(), "-b", "-noaudio", "--factory-startup",
             "--python-exit-code", "1", "-P", str(script)],
            capture_output=True, text=True, timeout=300)
        marker = "ATLAS_ALLOCATION_PROBE "
        line = next((l for l in result.stdout.splitlines() if l.startswith(marker)), None)
        if line is None:
            raise AssertionError(f"probe produced no result:\n{result.stdout[-2000:]}\n{result.stderr[-1000:]}")
        cls.probe = json.loads(line[len(marker):])

    def test_packing_is_never_looser_than_the_original_layout(self):
        # Three big quads pack well either way; the real rooms have ~1,000 small islands, where the
        # loose layout covers 10.9% (Padaria) and 15.4% (smith) of the atlas and packing 73% and 80%
        # (docs/reports/eevee-atlas-and-grass-placement-2026-09-30.md).
        self.assertGreater(self.probe["packed"]["coverage"], 0.5)
        self.assertGreaterEqual(self.probe["packed"]["coverage"], self.probe["loose"]["coverage"])

    def test_the_view_layout_is_about_as_full_as_packed(self):
        self.assertGreater(self.probe["view"]["coverage"], 0.4)

    def test_a_face_no_camera_sees_is_shrunk_but_kept(self):
        parts = self.probe["view"]["parts"]
        self.assertLess(parts["C"]["density"], 0.5 * parts["A"]["density"])
        self.assertGreater(parts["C"]["uvArea"], 0.0)                 # the floor keeps it

    def test_seen_faces_are_not_starved(self):
        parts = self.probe["view"]["parts"]
        self.assertGreater(parts["A"]["density"], 0.0)
        self.assertGreater(parts["B"]["density"], 0.5 * parts["A"]["density"])

    def test_the_measurement_saw_what_it_should(self):
        report = self.probe["view"]["report"]
        self.assertEqual(report["polygons"], 3)
        self.assertEqual(report["visiblePolygons"], 2)                # A and B; C is behind the wall

    def test_with_the_bias_at_zero_every_surface_is_equal(self):
        """The negative control: without view bias the hidden face is not shrunk."""
        parts = self.probe["worldBias"]["parts"]
        for part in ("B", "C"):
            self.assertAlmostEqual(parts[part]["density"] / parts["A"]["density"], 1.0, delta=0.15)


if __name__ == "__main__":
    unittest.main()
