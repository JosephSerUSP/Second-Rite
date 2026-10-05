"""build_layered_package.py: a plate pair becomes a loadable layered_2d package."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

TOOL = Path(__file__).resolve().parents[1] / "build_layered_package.py"

# A level, un-yawed camera: lane Y runs along screen X, so the projection is
# easy to reason about without importing the engine's resolver.
RECORD = {
    "eye": {"x": -10.0, "y": 8.0, "z": 2.0},
    "orientation": {"forwardX": 1.0, "forwardY": 0.0, "rightX": 0.0, "rightY": 1.0,
                    "pitchRadians": 0.0},
    "projectionScale": {"x": 1.0, "y": 1.0},
    "fovHalfX": 0.4, "fovHalfY": 0.2,
    "targetWidth": 200, "targetHeight": 100,
    "baseViewportWidth": 200, "baseViewportHeight": 100,
    "viewportCenterX": 100.0, "viewportCenterY": 50.0,
}
ANCHORS = {"anchors": {"spawn_player": {"position": [0, 4, 0]}}}


def run(args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)],
                          capture_output=True, text=True)


class LayeredPackageTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        Image.new("RGBA", (200, 100), (10, 20, 30, 255)).save(self.root / "bg.png")
        Image.new("RGBA", (200, 100), (0, 0, 0, 0)).save(self.root / "fg.png")
        (self.root / "record.json").write_text(json.dumps(RECORD))
        (self.root / "anchors.json").write_text(json.dumps(ANCHORS))

    def tearDown(self):
        self.dir.cleanup()

    def args(self, out="pkg", fg="fg.png"):
        r = self.root
        return ["--background", r / "bg.png", "--foreground", r / fg,
                "--record", r / "record.json", "--anchors", r / "anchors.json",
                "--source-blend", "x.blend", "--lane", "0", "16", "--slice-y", "8",
                "--output", r / out]

    def test_writes_a_package_the_runtime_contract_accepts(self):
        result = run(self.args())
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.root / "pkg" / "environment.json").read_text())
        pre = manifest["preRendered"]
        self.assertEqual(pre["mode"], "layered_2d")
        self.assertEqual(pre["imageSize"], [200, 100])
        self.assertEqual(pre["slicePositions"], [8.0])
        self.assertEqual(len(pre["backgrounds"]), len(pre["foregrounds"]))
        self.assertEqual(manifest["provenance"]["sourceBlend"], "x.blend")
        self.assertIn("spawn_player", manifest["anchors"])
        # Lane Y 8 is the eye's own Y, so it sits on the plate's centre column,
        # and a metre of lane is 1 / (fovHalfX * depth) of the half-width.
        projection = pre["playerProjection"]
        self.assertAlmostEqual(projection["centerX"], 100.0, places=3)
        self.assertAlmostEqual(projection["pixelsPerRuntimeY"], 100.0 / (0.4 * 10.0), places=2)
        for name in ("background.png", "foreground.png", "stub.obj", "stub.mtl", "atlas.png"):
            self.assertTrue((self.root / "pkg" / name).exists(), name)

    def test_refuses_a_plate_that_does_not_match_its_record(self):
        Image.new("RGBA", (180, 100), (0, 0, 0, 0)).save(self.root / "fg_small.png")
        result = run(self.args(fg="fg_small.png"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("foreground", result.stderr + result.stdout)

    def test_refuses_an_opaque_foreground(self):
        Image.new("RGB", (200, 100), (0, 0, 0)).save(self.root / "fg_rgb.png")
        result = run(self.args(fg="fg_rgb.png"))
        self.assertNotEqual(result.returncode, 0)

    def test_never_writes_over_an_existing_package(self):
        self.assertEqual(run(self.args()).returncode, 0)
        self.assertNotEqual(run(self.args()).returncode, 0)


if __name__ == "__main__":
    unittest.main()
