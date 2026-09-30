"""The room exporter bakes its atlas with EEVEE when asked, and ships the same package contract.

A tiny synthetic room source (``eevee_backend_blender.py``) goes through the real
``export_room_environment.py`` twice, once per backend, at a 128 px atlas. It runs the pinned Blender
named by ``BLENDER_EXECUTABLE``. What is asserted is the contract (the files, the manifest, geometry that
does not depend on the backend, an atlas that holds light), not that the two backends agree: how close they
come is what ``docs/reports/eevee-*.md`` measure on the real rooms.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator  # noqa: E402

TOOLS = ROOT / "tools" / "blender"


def blender(*arguments, timeout=600):
    return subprocess.run([blender_locator.blender_executable(), "-b", "-noaudio", "--factory-startup",
                           "--python-exit-code", "1", *arguments], capture_output=True, text=True, timeout=timeout)


class EeveeBackendTests(unittest.TestCase):
    packages = {}

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        base = Path(cls.directory.name)
        source = base / "test_room.blend"
        made = blender("-P", str(TOOLS / "tests" / "eevee_backend_blender.py"), "--", str(source))
        if "EEVEE_BACKEND_ROOM" not in made.stdout:
            raise AssertionError(f"could not build the room:\n{made.stdout[-1500:]}\n{made.stderr[-800:]}")
        for backend in ("cycles", "eevee"):
            output = base / backend
            result = blender("-P", str(TOOLS / "export_room_environment.py"), "--",
                             "--blend", str(source), "--output", str(output), "--exit-y", "6.5",
                             "--atlas-size", "128", "--samples", "8", "--bake-backend", backend,
                             "--bake-supersample", "1")
            if "ROOM 3D EXPORT OK" not in result.stdout:
                raise AssertionError(f"{backend} export failed:\n{result.stdout[-2500:]}\n{result.stderr[-1000:]}")
            cls.packages[backend] = output

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def manifest(self, backend):
        return json.loads((self.packages[backend] / "environment.json").read_text(encoding="utf-8"))

    def atlas(self, backend):
        result = blender("-P", str(TOOLS / "tests" / "atlas_stats_blender.py"), "--",
                         str(self.packages[backend] / "environment.png"))
        line = next((l for l in result.stdout.splitlines() if l.startswith("ATLAS_STATS ")), None)
        if line is None:
            raise AssertionError(result.stdout[-1500:])
        return json.loads(line[len("ATLAS_STATS "):])

    def test_both_backends_ship_the_same_files(self):
        names = {backend: sorted(p.name for p in self.packages[backend].iterdir()) for backend in self.packages}
        self.assertEqual(names["cycles"], names["eevee"])
        self.assertIn("environment.png", names["eevee"])

    def test_the_geometry_does_not_depend_on_the_backend(self):
        cycles, eevee = self.manifest("cycles"), self.manifest("eevee")
        self.assertEqual(cycles["stats"]["triangleCount"], eevee["stats"]["triangleCount"])
        self.assertEqual(cycles["bounds"], eevee["bounds"])
        self.assertEqual((self.packages["cycles"] / "environment.obj").read_text(),
                         (self.packages["eevee"] / "environment.obj").read_text())

    def test_the_eevee_atlas_holds_light(self):
        atlas = self.atlas("eevee")
        self.assertEqual(atlas["size"], [128, 128])
        self.assertGreater(atlas["litFraction"], 0.15)           # the room's islands carry texels
        self.assertGreater(atlas["meanLit"], 10.0)

    def test_an_eevee_package_says_how_it_was_made(self):
        bake = self.manifest("eevee")["provenance"]["bake"]
        self.assertEqual(bake["backend"], "eevee")
        self.assertIn("exposureEV", bake)

    def test_a_cycles_package_keeps_the_manifest_it_always_had(self):
        self.assertNotIn("bake", self.manifest("cycles")["provenance"])


if __name__ == "__main__":
    unittest.main()
