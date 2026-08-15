from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_item_obj_runtime import validate


class RuntimeObjValidatorTests(unittest.TestCase):
    def write_obj(self, root: Path, body: str) -> Path:
        path = root / "model.obj"
        path.write_text(body, encoding="utf-8")
        return path

    def test_healthy_triangle(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_obj(Path(temp), "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
            self.assertEqual(validate(path)["triangles"], 1)

    def test_repeated_vertex_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_obj(Path(temp), "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 2\n")
            with self.assertRaisesRegex(ValueError, "repeats a vertex index"):
                validate(path)

    def test_collinear_triangle_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_obj(Path(temp), "v 0 0 0\nv 1 0 0\nv 2 0 0\nf 1 2 3\n")
            with self.assertRaisesRegex(ValueError, "degenerate face"):
                validate(path)

    def test_ngon_checks_each_fan_triangle(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_obj(
                Path(temp),
                "v 0 0 0\nv 1 0 0\nv 2 0 0\nv 0 1 0\nf 1 2 3 4\n",
            )
            with self.assertRaisesRegex(ValueError, "degenerate face"):
                validate(path)

    def test_missing_mtl_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_obj(
                Path(temp),
                "mtllib missing.mtl\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",
            )
            with self.assertRaisesRegex(ValueError, "referenced MTL does not exist"):
                validate(path)


if __name__ == "__main__":
    unittest.main()
