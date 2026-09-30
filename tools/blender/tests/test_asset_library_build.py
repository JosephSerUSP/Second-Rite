"""Our own asset library describes what it holds (tools/blender/build_asset_library.py --check).

Pure Python: the committed listing is read the way Blender reads a remote library, so this
runs in the required gate without Blender. Each rule has a negative control against a copy.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import build_asset_library as lib  # noqa: E402


class CommittedLibraryTests(unittest.TestCase):
    def test_the_committed_library_verifies(self):
        self.assertEqual(lib.check(lib.LIBRARY), [])

    def test_it_holds_exactly_the_declared_assets_under_one_licence(self):
        import asset_library
        with tempfile.TemporaryDirectory() as cache:
            listing = asset_library.Library(lib.LIBRARY.resolve().as_uri(), cache=Path(cache))
        self.assertEqual({a["name"] for a in listing.assets}, set(lib.ASSETS))
        self.assertEqual({a["meta"]["license"] for a in listing.assets}, {lib.LICENSE})

    def test_the_catalogue_file_declares_the_catalogue_the_asset_uses(self):
        text = (lib.LIBRARY / "blender_assets.cats.txt").read_text(encoding="utf-8")
        self.assertIn(f"{lib.CATALOG_ID}:{lib.CATALOG_PATH}:", text)

    def test_nothing_stray_sits_in_the_library(self):
        names = {p.name for p in lib.LIBRARY.iterdir()}
        self.assertLessEqual(names, {lib.BLEND_NAME, "blender_assets.cats.txt", "_asset-library-meta.json",
                                     "_v1", "second_rite_nodes_thumbnails", ".gitignore"})
        self.assertFalse(list(lib.LIBRARY.rglob("*.blend1")))


class NegativeControlTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="test_asset_library_build_"))
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
        self.copy = self.directory / "library"
        shutil.copytree(lib.LIBRARY, self.copy)

    def problems(self):
        return lib.check(self.copy)

    def test_the_copy_starts_green(self):
        self.assertEqual(self.problems(), [])

    def test_a_blend_changed_since_the_listing_is_refused(self):
        with open(self.copy / lib.BLEND_NAME, "ab") as handle:
            handle.write(b"\0")
        self.assertTrue(any("has changed since the listing" in p for p in self.problems()))

    def test_a_missing_blend_is_refused(self):
        (self.copy / lib.BLEND_NAME).unlink()
        self.assertEqual(self.problems(), [f"{lib.BLEND_NAME} is missing"])

    def test_a_tampered_page_is_refused(self):
        page = self.copy / "_v1" / "assets-00000.json"
        page.write_text(page.read_text(encoding="utf-8").replace("CC0 - Public Domain", "MIT"),
                        encoding="utf-8")
        self.assertTrue(any("listing is not valid" in p for p in self.problems()))

    def test_a_wrong_library_name_is_refused(self):
        meta = self.copy / "_asset-library-meta.json"
        data = json.loads(meta.read_text(encoding="utf-8"))
        data["name"] = "Someone Else"
        meta.write_text(json.dumps(data), encoding="utf-8")
        self.assertTrue(any("library name" in p for p in self.problems()))

    def test_an_asset_the_spec_promises_but_the_listing_lacks_is_refused(self):
        assets = dict(lib.ASSETS, Ghost=("NODETREE", "x", ["y"]))
        with mock.patch.object(lib, "ASSETS", assets):
            self.assertTrue(any("no NODETREE asset 'Ghost'" in p for p in self.problems()))

    def test_an_asset_the_spec_does_not_declare_is_refused(self):
        with mock.patch.object(lib, "ASSETS", {}):
            self.assertTrue(any("not declared in ASSETS" in p for p in self.problems()))

    def test_a_licence_that_differs_from_the_spec_is_refused(self):
        with mock.patch.object(lib, "LICENSE", "MIT"):
            self.assertTrue(any("licence is" in p for p in self.problems()))


if __name__ == "__main__":
    unittest.main()
