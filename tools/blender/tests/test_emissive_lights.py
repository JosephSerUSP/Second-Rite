"""EEVEE draws emission but does not cast it, so emissive patches get companion area lights.

One Blender run (see ``emissive_lights_blender.py``) builds a white room with a glowing slab and a
glowing panel on two walls, plus an ember too small to matter, and adds the companions four ways.
It runs the pinned Blender named by ``BLENDER_EXECUTABLE``. The power law (watts = pi x strength x
area) was measured against Cycles in ``docs/reports/eevee-emissive-lights-2026-09-30.md``; this
file guards that the lights land where and as that law says.
"""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator  # noqa: E402


class EmissiveLightsTests(unittest.TestCase):
    probe = None

    @classmethod
    def setUpClass(cls):
        script = ROOT / "tools" / "blender" / "tests" / "emissive_lights_blender.py"
        result = subprocess.run(
            [blender_locator.blender_executable(), "-b", "-noaudio", "--factory-startup",
             "--python-exit-code", "1", "-P", str(script)],
            capture_output=True, text=True, timeout=300)
        marker = "EMISSIVE_LIGHTS_PROBE "
        line = next((l for l in result.stdout.splitlines() if l.startswith(marker)), None)
        if line is None:
            raise AssertionError(f"probe produced no result:\n{result.stdout[-2000:]}\n{result.stderr[-1000:]}")
        cls.probe = json.loads(line[len(marker):])

    def lights(self, key="default"):
        data = self.probe[key]
        return data["lights"] if isinstance(data, dict) else data

    def by_source(self, key="default"):
        return {l["of"]: l for l in self.lights(key)}

    def test_each_room_facing_glow_gets_one_light_and_nothing_else_does(self):
        # the slab's five other faces look sideways or into the wall; the ember is under the watt floor
        self.assertEqual(sorted(self.by_source()), ["panel", "slab"])

    def test_watts_are_pi_times_strength_times_area(self):
        lights = self.by_source()
        self.assertAlmostEqual(lights["slab"]["watts"], math.pi * 2.0 * 1.0, places=3)
        self.assertAlmostEqual(lights["panel"]["watts"], math.pi * 3.0 * 1.0, places=3)

    def test_the_light_follows_the_material_strength(self):
        """Scaling a window's emission at render time must scale its companion."""
        doubled = self.by_source("doubled")["slab"]["watts"]
        self.assertAlmostEqual(doubled, 2.0 * self.by_source()["slab"]["watts"], places=3)

    def test_colour_is_the_emission_colour(self):
        self.assertEqual([round(c, 3) for c in self.by_source()["slab"]["colour"]], [1.0, 0.5, 0.2])
        self.assertEqual([round(c, 3) for c in self.by_source()["panel"]["colour"]], [0.2, 0.6, 1.0])

    def test_the_light_shines_out_of_the_face_into_the_room(self):
        slab = self.by_source()["slab"]
        for got, want in zip(slab["shines"], (-1.0, 0.0, 0.0)):
            self.assertAlmostEqual(got, want, places=4)
        # on the face (x = 2.9), a centimetre out toward the room
        self.assertAlmostEqual(slab["position"][0], 2.89, places=3)
        self.assertAlmostEqual(slab["position"][1], 0.0, places=3)
        self.assertAlmostEqual(slab["position"][2], 1.5, places=3)

    def test_the_rectangle_is_the_glowing_face(self):
        sizes = sorted(self.by_source()["slab"]["size"])
        self.assertAlmostEqual(sizes[0], 1.0, places=3)
        self.assertAlmostEqual(sizes[1], 1.0, places=3)

    def test_the_light_is_a_rotation_not_a_mirror(self):
        for light in self.lights():
            self.assertAlmostEqual(light["determinant"], 1.0, places=4)

    def test_every_companion_has_a_reach(self):
        """EEVEE's light_threshold gives a dim light a short reach; measured, it darkens the far floor."""
        for light in self.lights():
            self.assertEqual(light["type"], "AREA")
            self.assertEqual(light["shape"], "RECTANGLE")
            self.assertGreaterEqual(light["cutoff"], 20.0)

    def test_the_ember_is_reported_as_skipped(self):
        skipped = self.probe["default"]["report"]["skipped"]
        self.assertTrue(any(s["object"] == "ember" and "under" in s["why"] for s in skipped), skipped)

    def test_an_excluded_material_gets_no_light(self):
        self.assertEqual(sorted(self.by_source("excluded")), ["panel"])
        self.assertTrue(any(s["why"] == "excluded" for s in self.probe["excluded"]["report"]["skipped"]))

    def test_an_ignored_object_is_not_lit_twice(self):
        """The atlas study's joined mesh carries the source meshes' emissive faces as well."""
        self.assertEqual(sorted(self.by_source("ignored")), ["panel"])

    def test_a_face_looking_into_the_wall_gets_no_light(self):
        """The negative control: a glowing quad facing away from the room adds nothing."""
        self.assertEqual(sorted(self.by_source("backwards")), ["panel", "slab"])


if __name__ == "__main__":
    unittest.main()
