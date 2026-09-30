"""A lamp inside its own small fixture must be able to light the wall beside it (see light_fixtures.py).

One Blender run (see ``light_fixtures_blender.py``) puts a point light inside a 0.16 m box, one beside
a 2 m table, and one in open air, renders the wall beside the first in EEVEE, releases the fixtures,
and renders it again. It runs the pinned Blender named by ``BLENDER_EXECUTABLE``.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator  # noqa: E402


class LightFixtureTests(unittest.TestCase):
    probe = None

    @classmethod
    def setUpClass(cls):
        script = ROOT / "tools" / "blender" / "tests" / "light_fixtures_blender.py"
        result = subprocess.run(
            [blender_locator.blender_executable(), "-b", "-noaudio", "--factory-startup",
             "--python-exit-code", "1", "-P", str(script)],
            capture_output=True, text=True, timeout=300)
        marker = "LIGHT_FIXTURES_PROBE "
        line = next((l for l in result.stdout.splitlines() if l.startswith(marker)), None)
        if line is None:
            raise AssertionError(f"probe produced no result:\n{result.stdout[-2000:]}\n{result.stderr[-1000:]}")
        cls.probe = json.loads(line[len(marker):])

    def test_the_box_around_a_lamp_stops_shadowing_it(self):
        self.assertEqual(self.probe["report"]["released"], {"lantern_light": ["lantern_box"]})
        self.assertFalse(self.probe["visibleShadowAfter"]["lantern_box"])

    def test_a_housing_bigger_than_its_light_keeps_its_shadow(self):
        """Cycles shades a light inside a 0.3 m lantern too, so the EEVEE plate must agree."""
        self.assertTrue(self.probe["visibleShadowAfter"]["big_lantern"])
        self.assertNotIn("lamp_in_big_lantern", self.probe["report"]["released"])

    def test_everything_else_keeps_its_shadow(self):
        """The wall, the table and the far box are not fixtures of any lamp."""
        for name in ("wall", "table", "far_box"):
            self.assertTrue(self.probe["visibleShadowAfter"][name], name)
        self.assertTrue(all(self.probe["visibleShadowBefore"].values()))

    def test_the_light_actually_gets_out(self):
        """Not just a flag: the wall beside the lantern is lit by the lantern once its box lets go."""
        before, after = self.probe["wallBefore"], self.probe["wallAfter"]
        self.assertGreater(after, 2.0 * before, (before, after))


if __name__ == "__main__":
    unittest.main()
