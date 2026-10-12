"""Negative controls for the item-texture checker: each rule must fail when broken."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import item_textures  # noqa: E402


def make_project(tmp: Path, mtl: str, authored=None, promoted=None):
    authored_dir = tmp / item_textures.AUTHORED
    promoted_dir = tmp / item_textures.PROMOTED
    authored_dir.mkdir(parents=True)
    promoted_dir.mkdir(parents=True)
    (promoted_dir / "thing.mtl").write_text(mtl, encoding="utf-8")
    for name, data in (authored or {}).items():
        (authored_dir / name).write_bytes(data)
    for name, data in (promoted or {}).items():
        (promoted_dir / name).write_bytes(data)
    return tmp


class ItemTextureTests(unittest.TestCase):
    def check(self, mtl, authored=None, promoted=None):
        with tempfile.TemporaryDirectory() as tmp:
            return item_textures.check(make_project(Path(tmp), mtl, authored, promoted))

    def test_clean_project_passes(self):
        mtl = "newmtl a\nmap_Kd dial.png\npass uv multiply 0.8 assets/models/items/engrave.png\n"
        files = {"dial.png": b"1", "engrave.png": b"2"}
        self.assertEqual(self.check(mtl, authored=files, promoted=files), [])

    def test_pass_texture_that_does_not_exist_fails(self):
        problems = self.check("newmtl a\npass uv multiply 1 assets/models/items/missing.png\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("pass texture does not exist", problems[0])

    def test_map_kd_that_does_not_exist_fails(self):
        problems = self.check("newmtl a\nmap_Kd gone.png\n")
        self.assertIn("map_Kd texture does not exist", problems[0])

    def test_unpromoted_authored_texture_fails(self):
        problems = self.check("newmtl a\n", authored={"x.png": b"1"})
        self.assertIn("not promoted", problems[0])

    def test_stale_promoted_copy_fails(self):
        problems = self.check("newmtl a\nmap_Kd x.png\n", authored={"x.png": b"new"}, promoted={"x.png": b"old"})
        self.assertIn("differs from authored", problems[0])

    def test_refl_statement_counts_as_a_pass_reference(self):
        problems = self.check("newmtl a\nrefl -type sphere assets/models/matcaps/nope.png\n")
        self.assertIn("pass texture does not exist", problems[0])

    def test_sync_copies_authored_over_stale_promoted_and_never_deletes(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp), "newmtl a\n", authored={"x.png": b"new"}, promoted={"x.png": b"old", "keep.png": b"k"})
            self.assertEqual(item_textures.sync(project), ["x.png"])
            self.assertEqual((project / item_textures.PROMOTED / "x.png").read_bytes(), b"new")
            self.assertTrue((project / item_textures.PROMOTED / "keep.png").is_file())


if __name__ == "__main__":
    unittest.main()
