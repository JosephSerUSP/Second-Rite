from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from item_mtl_runtime import RuntimePassError, inject_runtime_passes, normalize_passes


class RuntimePassTests(unittest.TestCase):
    def test_injects_pass_into_matching_material_section(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "model.mtl"
            path.write_text(
                "newmtl bone\nKd 0.7 0.7 0.5\n\n"
                "newmtl ritual_gold\nKd 0.5 0.4 0.2\n",
                encoding="utf-8",
            )
            inject_runtime_passes(path, {
                "ritual_gold": [{
                    "uvSource": "sphere",
                    "blend": "add",
                    "strength": 1.0,
                    "texture": "assets/models/matcaps/gold.png",
                }]
            })
            text = path.read_text(encoding="utf-8")
            self.assertIn(
                "newmtl ritual_gold\nKd 0.5 0.4 0.2\n"
                "pass sphere add 1 assets/models/matcaps/gold.png\n",
                text,
            )
            self.assertNotIn("newmtl bone\npass", text)

    def test_rejects_more_than_shader_maximum(self):
        with self.assertRaises(RuntimePassError):
            normalize_passes([
                {"uvSource": "uv", "blend": "mix", "strength": 1, "texture": "a.png"},
                {"uvSource": "uv", "blend": "mix", "strength": 1, "texture": "b.png"},
                {"uvSource": "uv", "blend": "mix", "strength": 1, "texture": "c.png"},
            ])

    def test_rejects_unknown_runtime_vocabulary(self):
        with self.assertRaises(RuntimePassError):
            normalize_passes([
                {"uvSource": "cube", "blend": "add", "strength": 1, "texture": "x.png"}
            ])
        with self.assertRaises(RuntimePassError):
            normalize_passes([
                {"uvSource": "sphere", "blend": "overlay", "strength": 1, "texture": "x.png"}
            ])

    def test_rejects_material_missing_from_export(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "model.mtl"
            path.write_text("newmtl bone\nKd 1 1 1\n", encoding="utf-8")
            with self.assertRaises(RuntimePassError):
                inject_runtime_passes(path, {
                    "crystal": [{
                        "uvSource": "sphere", "blend": "add", "strength": 1,
                        "texture": "assets/models/matcaps/ruby.png",
                    }]
                })


if __name__ == "__main__":
    unittest.main()
