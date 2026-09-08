import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
import sys
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import build_synthetic_environment


class CorticoFloorExportTests(unittest.TestCase):
    def test_source_grid_exports_and_missing_grid_fails(self):
        blender = build_synthetic_environment.blender_executable()
        script = ROOT / "tools" / "blender" / "tests" / "cortico_floor_export_blender.py"
        blend = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "environments" / "st_maria_cortico.blend"
        with tempfile.TemporaryDirectory(prefix="cortico-floor-export-") as directory:
            env = os.environ.copy()
            env["CORTICO_FLOOR_TEST_BLEND"] = str(blend)
            env["CORTICO_FLOOR_TEST_OUTPUT"] = directory
            result = subprocess.run(
                [blender, "-b", "-noaudio", "--factory-startup", "-P", str(script)],
                capture_output=True, text=True, timeout=300, env=env)
        marker = "CORTICO_FLOOR_EXPORT_TEST "
        line = next((item for item in result.stdout.splitlines() if item.startswith(marker)), None)
        self.assertIsNotNone(line, f"probe produced no result:\n{result.stdout[-4000:]}")
        probe = json.loads(line[len(marker):])
        self.assertTrue(probe.get("ok"), probe.get("error", "probe failed"))
        self.assertEqual(probe["report"]["sourceObject"], "CORTICO_floor_grid")
        self.assertEqual(probe["report"]["gridSpacingWorld"], 1.0)
        self.assertEqual(probe["report"]["vertexCount"], 1548)
        self.assertEqual(probe["report"]["faceCount"], 1470)
        self.assertEqual(sorted(["floor.obj", "floor.mtl", "floor.png"]), probe["files"])
        self.assertEqual([layer["id"] for layer in probe["background"]],
                         ["centre", "east", "laundry_quad", "west"])
        self.assertEqual(sorted([
            "background_centre.obj", "background_centre.mtl",
            "cortico_background_centre.png", "background_east.obj",
            "background_east.mtl", "cortico_background_east.png",
            "background_laundry_quad.obj", "background_laundry_quad.mtl",
            "cortico_background_laundry_quad.png",
            "background_west.obj", "background_west.mtl",
            "cortico_background_west.png",
        ]), probe["backgroundFiles"])
        self.assertTrue(all(layer["provenance"]["cameraSpace"] is False
                            and layer["provenance"]["reactsToPitch"] is True
                            for layer in probe["background"]))
        self.assertIn("exactly one sr_floor_mesh", probe["negativeError"])


if __name__ == "__main__":
    unittest.main()
