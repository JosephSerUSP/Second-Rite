"""Environment source authority is a record, not a guess (#1269).

Pure Python: the manifest and the packages are read as JSON, so this runs
without Blender. Each rule has a negative control against a scratch project.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import environment_sources as sources  # noqa: E402

GAME = ROOT / "projects" / "hichaukitoden-game"
FIXTURE = ROOT / "projects" / "editor-fixture"

# Every tool that writes an environment .blend must ask before it does.
WRITERS = (
    "tools/blender/recipes/interior.py",
    "tools/blender/recipes/st_maria_praca.py",
    "tools/blender/recipes/refine_st_maria_praca.py",
    "tools/blender/recipes/replace_st_maria_tree.py",
    "tools/blender/recipes/mark_st_maria_exits.py",
    "tools/blender/reauthor_praca_spiral.py",
)


def _scratch_project(directory):
    """A minimal project: two .blend files, one package citing the adopted one."""
    root = Path(directory) / "proj"
    authoring = root / "assets" / "authoring" / "environments"
    authoring.mkdir(parents=True)
    for name in ("old.blend", "new.blend"):
        (authoring / name).write_bytes(b"BLENDER")
    manifest = {"schemaVersion": 1, "sources": {
        "new.blend": {"status": "adopted", "basis": "test"},
        "old.blend": {"status": "superseded", "supersededBy": "new.blend", "basis": "test"},
    }}
    (authoring / sources.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    package = root / "assets" / "environments" / "town" / "hall"
    package.mkdir(parents=True)
    (package / "environment.json").write_text(json.dumps(
        {"provenance": {"sourceBlend": "new.blend"}}), encoding="utf-8")
    return root


def _rewrite(path, mutate):
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data), encoding="utf-8")


class RepositoryTests(unittest.TestCase):
    def test_shipped_projects_pass(self):
        for project in (GAME, FIXTURE):
            self.assertEqual(sources.check_project(project), [], project.name)

    def test_the_adopted_praca_is_the_modelled_file(self):
        entries = sources.load_sources(sources.authoring_dir(GAME))
        self.assertEqual(entries["st_maria_praca_modelled.blend"]["status"], "adopted")
        self.assertEqual(entries["st_maria_praca.blend"]["status"], "scaffold")
        package = json.loads((GAME / "assets/environments/st_maria_town/praca/environment.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual(package["provenance"]["sourceBlend"], "st_maria_praca_modelled.blend")

    def test_every_writer_asks_before_it_writes(self):
        for relative in WRITERS:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("environment_sources.refuse_superseded(", text, relative)

    def test_the_room_installer_carries_the_source_into_the_package(self):
        import install_room_3d
        with tempfile.TemporaryDirectory() as directory:
            export = Path(directory) / "export"
            export.mkdir()
            (export / "environment.json").write_text(json.dumps({
                "bounds": [0, 0, 0, 1, 1, 1],
                "anchors": {"spawn_player": {"position": [0, 0, 0]}},
                "provenance": {"generator": "x", "sourceBlend": "room.blend"},
            }), encoding="utf-8")
            with mock.patch.object(install_room_3d, "ENV_ROOT", Path(directory) / "env"), \
                    mock.patch.object(sys, "argv", ["install_room_3d", "--export", str(export),
                                                    "--name", "room_3d"]):
                install_room_3d.main()
            package = json.loads((Path(directory) / "env" / "room_3d" / "environment.json")
                                 .read_text(encoding="utf-8"))
        self.assertEqual(package["provenance"], {"sourceBlend": "room.blend"})


class NegativeControlTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="test_env_sources_")
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
        self.root = _scratch_project(self.directory)
        self.authoring = sources.authoring_dir(self.root)
        self.package = self.root / "assets/environments/town/hall/environment.json"

    def test_the_scratch_project_starts_green(self):
        self.assertEqual(sources.check_project(self.root), [])

    def test_a_missing_sourceBlend_record_fails(self):
        _rewrite(self.package, lambda d: d["provenance"].pop("sourceBlend"))
        self.assertTrue(any("records no provenance.sourceBlend" in e
                            for e in sources.check_project(self.root)))

    def test_a_package_with_no_provenance_at_all_fails(self):
        _rewrite(self.package, lambda d: d.pop("provenance"))
        self.assertTrue(sources.check_project(self.root))

    def test_a_sourceBlend_that_does_not_exist_fails(self):
        _rewrite(self.package, lambda d: d["provenance"].update(sourceBlend="ghost.blend"))
        self.assertTrue(any("does not exist" in e for e in sources.check_project(self.root)))

    def test_null_needs_a_reason(self):
        _rewrite(self.package, lambda d: d["provenance"].update(sourceBlend=None))
        self.assertTrue(any("sourceBlendNote" in e for e in sources.check_project(self.root)))
        _rewrite(self.package, lambda d: d["provenance"].update(sourceBlendNote="2D plate"))
        self.assertEqual(sources.check_project(self.root), [])

    def test_a_package_baked_from_a_superseded_file_fails(self):
        _rewrite(self.package, lambda d: d["provenance"].update(sourceBlend="old.blend"))
        self.assertTrue(any("superseded" in e for e in sources.check_project(self.root)))

    def test_a_blend_with_no_entry_fails(self):
        (self.authoring / "stray.blend").write_bytes(b"BLENDER")
        self.assertTrue(any("stray.blend has no entry" in e
                            for e in sources.check_project(self.root)))

    def test_an_entry_for_a_missing_file_fails(self):
        (self.authoring / "old.blend").unlink()
        self.assertTrue(any("does not exist" in e for e in sources.check_project(self.root)))

    def test_a_missing_manifest_fails(self):
        (self.authoring / sources.MANIFEST_NAME).unlink()
        self.assertTrue(any("is missing" in e for e in sources.check_project(self.root)))

    def test_a_dangling_supersededBy_fails(self):
        _rewrite(self.authoring / sources.MANIFEST_NAME,
                 lambda d: d["sources"]["old.blend"].update(supersededBy="nowhere.blend"))
        self.assertTrue(any("superseded by" in e for e in sources.check_project(self.root)))

    def test_an_unknown_status_fails(self):
        _rewrite(self.authoring / sources.MANIFEST_NAME,
                 lambda d: d["sources"]["new.blend"].update(status="final"))
        self.assertTrue(any("status" in e for e in sources.check_project(self.root)))


class RefusalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="test_env_refusal_")
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
        self.authoring = sources.authoring_dir(_scratch_project(self.directory))

    def test_a_superseded_file_is_refused(self):
        with self.assertRaises(SystemExit) as raised:
            sources.refuse_superseded(self.authoring / "old.blend")
        self.assertIn("new.blend", str(raised.exception))

    def test_adopted_and_unlisted_files_pass(self):
        sources.refuse_superseded(self.authoring / "new.blend")
        sources.refuse_superseded(self.authoring / "brand_new.blend")

    def test_the_override_is_explicit(self):
        with mock.patch.dict(os.environ, {sources.OVERRIDE_ENV: "1"}):
            sources.refuse_superseded(self.authoring / "old.blend")


if __name__ == "__main__":
    unittest.main()
