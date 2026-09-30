"""The read-only remote asset library browser (tools/blender/asset_library.py).

No Blender and no network beyond loopback: a scratch library is written to disk and
served by a real HTTP server on 127.0.0.1, so the tests exercise the same protocol the
Online Essentials library uses. Every trust rule has a negative control.
"""
import contextlib
import hashlib
import http.server
import io
import json
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import asset_library as al  # noqa: E402


def _sha(data: bytes) -> str:
    return "SHA256:" + hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload).encode("utf-8")
    path.write_bytes(data)
    return _sha(data)


def _asset(name, kind, files, catalog, tags=(), license="CC0 - Public Domain",
           author="Ada", description="", versions=None):
    meta = {"catalog_id": catalog, "author": author, "tags": list(tags)}
    if license:
        meta["license"] = license
    if description:
        meta["description"] = description
    return {"name": name, "id_type": kind, "files": files, "bl_versions": versions or {"min": "5.2"},
            "thumbnail": {"url": f"thumbs/{name}.webp", "hash": "SHA256:" + "0" * 64}, "meta": meta}


def build_library(root: Path) -> dict:
    """Two pages, two catalogues, a licence-less asset and a per-Blender variant pair."""
    files = [{"path": "materials/wall.blend", "size_in_bytes": 1000, "hash": "SHA256:" + "a" * 64,
              "blender_version": "5.2"},
             {"path": "worlds/sky.blend", "size_in_bytes": 2000, "hash": "SHA256:" + "b" * 64,
              "blender_version": "5.2"},
             {"path": "tools/mask.blend", "size_in_bytes": 3000, "hash": "SHA256:" + "c" * 64,
              "blender_version": "5.2"},
             {"path": "tools/mask@b5_3.blend", "size_in_bytes": 3000, "hash": "SHA256:" + "d" * 64,
              "blender_version": "5.3", "url": "https://elsewhere.example/mask53.blend"}]
    page0 = {"asset_count": 3, "file_count": 2, "files": files[:2], "assets": [
        _asset("Brick Wall", "MATERIAL", ["materials/wall.blend"], "cat-mat", ["Building", "Stone"],
               description="Parametric brick", author="Grace"),
        _asset("Plaster", "MATERIAL", ["materials/wall.blend"], "cat-mat", ["Building"], license=""),
        _asset("Courtyard", "WORLD", ["worlds/sky.blend"], "cat-world", ["Outdoor"])]}
    page1 = {"asset_count": 2, "file_count": 2, "files": files[2:], "assets": [
        _asset("Mask", "NODETREE", ["tools/mask.blend"], "cat-fx",
               versions={"min": "5.2", "until": "5.3"}),
        _asset("Mask", "NODETREE", ["tools/mask@b5_3.blend"], "cat-fx", versions={"min": "5.3"})]}
    pages = [{"url": "_v1/assets-00000.json", "hash": _write_json(root / "_v1/assets-00000.json", page0)},
             {"url": "_v1/assets-00001.json", "hash": _write_json(root / "_v1/assets-00001.json", page1)}]
    index = {"schema_version": "1.0.0", "asset_size_bytes": 9000, "asset_count": 5, "file_count": 4,
             "pages": pages, "catalogs": [
                 {"path": "Materials", "uuids": ["cat-mat"], "simple_name": "Materials"},
                 {"path": "Worlds", "uuids": ["cat-world"], "simple_name": "Worlds"},
                 {"path": "Compositing/Effects", "uuids": ["cat-fx"], "simple_name": "fx"}]}
    index_hash = _write_json(root / "_v1/asset-index.json", index)
    meta = {"api_versions": {"v1": {"url": "_v1/asset-index.json", "hash": index_hash}},
            "name": "Test Library", "contact": {"name": "Tester"}}
    _write_json(root / al.META_NAME, meta)
    # Decoys the reader must never request.
    (root / "materials").mkdir(exist_ok=True)
    (root / "materials/wall.blend").write_bytes(b"BLENDER")
    (root / "thumbs").mkdir(exist_ok=True)
    return {"index": index, "pages": pages}


class _Handler(http.server.SimpleHTTPRequestHandler):
    log: list = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        type(self).log.append(self.path)
        super().do_GET()


class LibraryCase(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="test_asset_library_"))
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
        self.served = self.directory / "site"
        self.served.mkdir()
        self.parts = build_library(self.served)
        handler = type("Handler", (_Handler,), {"log": []})
        self.handler = handler
        handler_factory = lambda *a, **k: handler(*a, directory=str(self.served), **k)  # noqa: E731
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler_factory)
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02},
                         daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/"
        self.cache = self.directory / "cache"

    def open(self, **kwargs):
        return al.Library(self.url, cache=self.cache, **kwargs)

    def run_cli(self, *arguments):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            al.main(["--url", self.url, "--cache", str(self.cache), *arguments])
        return buffer.getvalue()


class ListingTests(LibraryCase):
    def test_pages_are_merged_and_counted(self):
        library = self.open()
        self.assertEqual(len(library.assets), 5)
        self.assertEqual(len(library.files), 4)
        self.assertEqual(library.meta["name"], "Test Library")

    def test_search_filters(self):
        library = self.open()
        names = lambda **kw: [a["name"] for a in library.search(**kw)]  # noqa: E731
        self.assertEqual(names(types=["material"]), ["Brick Wall", "Plaster"])
        self.assertEqual(names(query="parametric brick"), ["Brick Wall"])
        self.assertEqual(names(query="outdoor"), ["Courtyard"])            # tags are searched
        self.assertEqual(names(query="worlds"), ["Courtyard"])             # so is the catalogue
        self.assertEqual(names(license="cc0"), ["Brick Wall", "Mask", "Mask", "Courtyard"])   # sorted by type, then name
        self.assertEqual(names(author="grace"), ["Brick Wall"])
        self.assertEqual(names(tag="stone"), ["Brick Wall"])
        self.assertEqual(names(catalog="Compositing"), ["Mask", "Mask"])

    def test_a_licence_filter_excludes_unlicensed_assets(self):
        names = [a["name"] for a in self.open().search(license="CC0")]
        self.assertNotIn("Plaster", names)

    def test_blender_interval_is_half_open(self):
        library = self.open()
        variants = lambda v: [(a["bl_versions"]["min"]) for a in library.search(query="mask", blender=v)]  # noqa: E731
        self.assertEqual(variants("5.2"), ["5.2"])
        self.assertEqual(variants("5.2.2"), ["5.2"])
        self.assertEqual(variants("5.3"), ["5.3"])       # `until` 5.3 is the first NOT shown
        self.assertEqual(variants("5.1"), [])

    def test_record_resolves_relative_and_absolute_urls(self):
        library = self.open()
        wall = library.record(library.find("Brick Wall")[0])
        self.assertEqual(wall["files"][0]["url"], self.url + "materials/wall.blend")
        self.assertEqual(wall["catalog"], "Materials")
        self.assertEqual(wall["thumbnail"]["url"], self.url + "thumbs/Brick Wall.webp")
        variant = library.record(library.find("Mask", blender="5.3")[0])
        self.assertEqual(variant["files"][0]["url"], "https://elsewhere.example/mask53.blend")

    def test_provenance_names_the_source_and_how_to_verify_it(self):
        library = self.open()
        record = library.provenance(library.find("Brick Wall")[0])
        self.assertEqual(record["library"], "Test Library")
        self.assertEqual(record["license"], "CC0 - Public Domain")
        self.assertEqual(record["author"], "Grace")
        self.assertEqual(record["file"]["hash"], "SHA256:" + "a" * 64)
        self.assertEqual(record["listingIndexHash"], library.index_hash)
        self.assertEqual(record["requiresBlender"], "5.2")


class ReadOnlyTests(LibraryCase):
    def test_no_asset_file_or_thumbnail_is_ever_requested(self):
        library = self.open()
        for asset in library.assets:
            library.record(asset)
            library.provenance(asset)
        self.run_cli("info")
        self.run_cli("--any-blender", "search")
        self.run_cli("show", "Brick Wall")
        requested = self.handler.log
        self.assertTrue(requested)
        for path in requested:
            self.assertRegex(path, r"^/(_asset-library-meta|_v1/)", path)
            self.assertNotRegex(path, r"\.(blend|webp|png)")


class TrustTests(LibraryCase):
    def test_a_tampered_page_is_refused(self):
        page = self.served / "_v1" / "assets-00000.json"
        page.write_bytes(page.read_bytes().replace(b"Grace", b"Mallory"))
        with self.assertRaises(al.LibraryError) as raised:
            self.open()
        self.assertIn("hash mismatch", str(raised.exception))

    def test_a_tampered_index_is_refused(self):
        index = self.served / "_v1" / "asset-index.json"
        index.write_bytes(index.read_bytes().replace(b'"asset_count": 5', b'"asset_count": 6'))
        with self.assertRaises(al.LibraryError) as raised:
            self.open()
        self.assertIn("hash mismatch", str(raised.exception))

    def test_a_count_that_disagrees_with_the_pages_is_refused(self):
        parts = self.parts
        index = dict(parts["index"], asset_count=99)
        index_hash = _write_json(self.served / "_v1/asset-index.json", index)
        meta = json.loads((self.served / al.META_NAME).read_text())
        meta["api_versions"]["v1"]["hash"] = index_hash
        _write_json(self.served / al.META_NAME, meta)
        with self.assertRaises(al.LibraryError) as raised:
            self.open()
        self.assertIn("declares 99 assets", str(raised.exception))

    def test_an_unsupported_api_version_is_refused(self):
        meta = json.loads((self.served / al.META_NAME).read_text())
        meta["api_versions"] = {"v9": meta["api_versions"]["v1"]}
        _write_json(self.served / al.META_NAME, meta)
        with self.assertRaises(al.LibraryError) as raised:
            self.open()
        self.assertIn("v9", str(raised.exception))

    def test_an_unsupported_scheme_is_refused(self):
        with self.assertRaises(al.LibraryError):
            al.Library("ftp://example.org/lib/", cache=self.cache)


class CacheTests(LibraryCase):
    def test_a_second_open_fetches_only_the_meta_file(self):
        self.open()
        self.handler.log.clear()
        library = self.open()
        self.assertEqual(len(library.assets), 5)
        self.assertEqual(self.handler.log, ["/" + al.META_NAME])

    def test_refresh_refetches_every_listing_file(self):
        self.open()
        self.handler.log.clear()
        self.open(refresh=True)
        self.assertEqual(len(self.handler.log), 4)     # meta, index, two pages

    def test_offline_uses_the_cache(self):
        self.open()
        self.handler.log.clear()
        self.assertEqual(len(self.open(offline=True).assets), 5)
        self.assertEqual(self.handler.log, [])

    def test_offline_without_a_cache_fails(self):
        with self.assertRaises(al.LibraryError):
            self.open(offline=True)

    def test_a_dead_server_falls_back_to_the_cache(self):
        self.open()
        self.server.shutdown()
        self.server.server_close()
        self.assertEqual(len(self.open().assets), 5)

    def test_a_corrupt_cache_file_is_refetched_not_trusted(self):
        self.open()
        for cached in self.cache.rglob("*.json"):
            if cached.name != "meta.json":
                cached.write_bytes(b"{}")
        self.assertEqual(len(self.open().assets), 5)


class CommandLineTests(LibraryCase):
    def test_search_json(self):
        rows = json.loads(self.run_cli("--json", "search", "--type", "MATERIAL", "--license", "CC0"))
        self.assertEqual([r["name"] for r in rows], ["Brick Wall"])
        self.assertEqual(rows[0]["catalog"], "Materials")

    def test_info_reports_types_and_licences(self):
        info = json.loads(self.run_cli("--json", "info"))
        self.assertEqual(info["assets"], 5)
        self.assertEqual(info["byType"]["NODETREE"], 2)
        self.assertEqual(info["byLicense"]["(none)"], 1)

    def test_catalogs_count_descendants(self):
        rows = {r["path"]: r["assets"] for r in json.loads(self.run_cli("--json", "catalogs"))}
        self.assertEqual(rows["Materials"], 2)
        self.assertEqual(rows["Compositing/Effects"], 2)

    def test_an_ambiguous_name_asks_for_a_type_or_blender(self):
        with self.assertRaises(al.LibraryError) as raised:
            self.run_cli("--any-blender", "show", "Mask")
        self.assertIn("ambiguous", str(raised.exception))
        self.assertEqual(json.loads(self.run_cli("--json", "--blender", "5.3", "show", "Mask"))["blenderVersions"],
                         {"min": "5.3"})

    def test_an_unknown_name_suggests_neighbours(self):
        with self.assertRaises(al.LibraryError) as raised:
            self.run_cli("show", "Brick")
        self.assertIn("Brick Wall", str(raised.exception))

    def test_the_default_blender_is_the_repository_pin(self):
        self.assertRegex(al.pinned_blender(), r"^\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
