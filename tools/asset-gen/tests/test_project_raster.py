from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import raster


class ProjectRasterTests(unittest.TestCase):
    def make_project(self):
        root = Path(tempfile.mkdtemp(prefix="asset-gen-project-"))
        (root / "data").mkdir()
        (root / "assets").mkdir()
        spec = {
            "version": 1,
            "palette": {"clear": "transparent", "ink": "#102030", "hot": "#e0a040"},
            "assets": [
                {
                    "id": "fixture",
                    "path": "assets/fixture.png",
                    "size": [7, 5],
                    "background": "clear",
                    "draw": [
                        {"op": "rect", "box": [1, 1, 5, 3], "fill": "ink"},
                        {"op": "point", "at": [3, 2], "fill": "hot"},
                    ],
                },
                {
                    "id": "mask",
                    "path": "assets/mask.png",
                    "size": [4, 3],
                    "mode": "L",
                    "background": 0,
                    "draw": [{"op": "rect", "box": [1, 1, 2, 1], "fill": 255}],
                },
            ],
        }
        source = root / "art" / "source.json"
        source.parent.mkdir()
        source.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        return root, source

    def test_rerun_is_byte_identical_and_check_is_read_only(self):
        root, source = self.make_project()
        raster.generate(source, root)
        first = {path: path.read_bytes() for path in (root / "assets").glob("*.png")}
        manifest = root / "art" / "provenance" / "raster-manifest.json"
        contact = root / "art" / "review" / "visual-contact-sheet.png"
        first_evidence = (manifest.read_bytes(), contact.read_bytes())

        result = raster.generate(source, root, check=True)

        self.assertEqual(set(result["outputs"]), {str(root / "assets/fixture.png"), str(root / "assets/mask.png")})
        self.assertEqual(first, {path: path.read_bytes() for path in (root / "assets").glob("*.png")})
        self.assertEqual(first_evidence, (manifest.read_bytes(), contact.read_bytes()))

    def test_output_cannot_escape_project_assets(self):
        root, source = self.make_project()
        spec = json.loads(source.read_text(encoding="utf-8"))
        spec["assets"][0]["path"] = "../outside.png"
        source.write_text(json.dumps(spec), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inside Project root"):
            raster.generate(source, root)


if __name__ == "__main__":
    unittest.main()
