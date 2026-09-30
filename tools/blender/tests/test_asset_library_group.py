"""The SR_GroundCover in our asset library is the group ground_cover.build_group() builds now.

One Blender run describes the committed library file and a fresh build, and this compares
them: interface sockets (name, type, default, range), node types and link count. It runs
the pinned Blender named by ``BLENDER_EXECUTABLE``. The library `.blend` is not
byte-reproducible, so identity is judged by structure, not by hash.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator  # noqa: E402
import build_asset_library as lib  # noqa: E402

MARKER = "ASSET_LIBRARY_DESCRIPTION "


def describe(*extra):
    script = ROOT / "tools" / "blender" / "asset_library_source.py"
    result = subprocess.run(
        [blender_locator.blender_executable(), "--background", "--factory-startup", "-noaudio",
         "--python-exit-code", "1", "--python", str(script), "--", "describe", *extra],
        capture_output=True, text=True, timeout=300)
    line = next((l for l in result.stdout.splitlines() if l.startswith(MARKER)), None)
    if line is None:
        raise AssertionError(f"no description produced:\n{result.stdout[-2000:]}\n{result.stderr[-1000:]}")
    return json.loads(line[len(MARKER):])


class LibraryGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.committed = describe(str(lib.LIBRARY / lib.BLEND_NAME))
        cls.fresh = describe()

    def test_the_committed_group_is_the_one_built_now(self):
        self.assertEqual(self.committed["sockets"], self.fresh["sockets"])
        self.assertEqual(self.committed["nodes"], self.fresh["nodes"])
        self.assertEqual(self.committed["links"], self.fresh["links"])

    def test_every_input_the_builder_declares_is_on_the_asset(self):
        names = sorted(s["name"] for s in self.committed["sockets"] if s["in_out"] == "INPUT")
        self.assertEqual(names, self.committed["declaredInputs"])

    def test_the_asset_carries_the_declared_metadata(self):
        _, description, tags = lib.ASSETS["SR_GroundCover"]
        asset = self.committed["asset"]
        self.assertEqual(asset["license"], lib.LICENSE)
        self.assertEqual(asset["author"], lib.AUTHOR)
        self.assertEqual(asset["copyright"], lib.COPYRIGHT)
        self.assertEqual(asset["description"], description)
        self.assertEqual(asset["tags"], sorted(tags))
        self.assertEqual(asset["catalog_id"], lib.CATALOG_ID)

    def test_a_group_that_has_drifted_would_be_caught(self):
        drifted = json.loads(json.dumps(self.committed))
        drifted["sockets"][0]["name"] = "Renamed"
        self.assertNotEqual(drifted["sockets"], self.fresh["sockets"])


if __name__ == "__main__":
    unittest.main()
