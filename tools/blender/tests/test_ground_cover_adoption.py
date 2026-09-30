"""The Praca ground-cover adoption is surgical, idempotent and inside its budget (#1270).

It works on a COPY of the adopted `st_maria_praca_modelled.blend` and never on the document itself,
and checks the document's hash before and after to prove it. Every step is a fresh run of the pinned
Blender named by ``BLENDER_EXECUTABLE``.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator  # noqa: E402

DOCUMENT = ROOT / "projects/hichaukitoden-game/assets/authoring/environments/st_maria_praca_modelled.blend"
RECIPE = ROOT / "tools/blender/recipes/adopt_praca_ground_cover.py"
PROBE = ROOT / "tools/blender/tests/adoption_blender.py"
BUDGET = 375
#: Name prefixes of the datablocks the adoption is allowed to add; anything else is a stray edit.
ALLOWED = ("GROUND_COVER", "SR_GroundCover", "CARD_", "sr_grass_kenney_atlas", "kenney_grass_atlas")


def blender(*arguments):
    result = subprocess.run([blender_locator.blender_executable(), "--background", "--factory-startup",
                             "-noaudio", "--python-exit-code", "1", *arguments],
                            capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise AssertionError(f"Blender failed ({result.returncode}):\n{result.stdout[-2500:]}\n{result.stderr[-1000:]}")
    return result.stdout


def probe(document):
    out = blender("-P", str(PROBE), "--", str(document))
    line = next(l for l in out.splitlines() if l.startswith("ADOPTION_PROBE "))
    return json.loads(line[len("ADOPTION_PROBE "):])


def adopt(document, *extra):
    return blender("-P", str(RECIPE), "--", "--document", str(document), *extra)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class AdoptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = Path(tempfile.mkdtemp(prefix="test_cover_adoption_"))
        cls.copy = cls.directory / DOCUMENT.name
        shutil.copy2(DOCUMENT, cls.copy)
        cls.source_hash = sha(DOCUMENT)
        cls.before = probe(cls.copy)
        cls.dry = adopt(cls.copy, "--dry-run")
        cls.after_dry_hash = sha(cls.copy)
        cls.first = adopt(cls.copy)
        cls.after_first_hash = sha(cls.copy)
        cls.after = probe(cls.copy)
        cls.second = adopt(cls.copy)
        cls.after_second_hash = sha(cls.copy)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def test_the_real_document_is_never_touched(self):
        self.assertEqual(sha(DOCUMENT), self.source_hash)

    def test_a_dry_run_writes_nothing(self):
        self.assertIn("DRY RUN", self.dry)
        self.assertEqual(self.after_dry_hash, self.source_hash)

    def test_nothing_that_existed_is_changed(self):
        before, after = self.before["census"], self.after["census"]
        self.assertEqual(after["scene"], before["scene"])
        for name, value in before["meshes"].items():
            self.assertEqual(after["meshes"].get(name), value, f"mesh {name} changed")
        for name, value in before["cameras"].items():
            self.assertEqual(after["cameras"].get(name), value, f"camera {name} changed")
        for name, value in before["objects"].items():
            self.assertEqual(after["objects"][name], value, f"object {name} changed or moved")
        for name, members in before["collections"].items():
            self.assertEqual(after["collections"][name], members, f"collection {name} changed")
        for kind in ("materials", "node_groups", "images", "lights", "worlds"):
            self.assertTrue(set(before[kind]) <= set(after[kind]), f"{kind} lost something")

    def test_only_the_cover_is_added(self):
        before, after = self.before["census"], self.after["census"]
        for kind in ("objects", "meshes", "materials", "node_groups", "collections", "images"):
            for name in set(after[kind]) - set(before[kind]):
                self.assertTrue(name.startswith(ALLOWED), f"unexpected {kind} added: {name}")
        self.assertIn("GROUND_COVER_SET", after["collections"])

    def test_it_is_idempotent(self):
        self.assertIn("ALREADY ADOPTED", self.second)
        self.assertEqual(self.after_second_hash, self.after_first_hash)          # not even a resave

    def test_the_cover_is_inside_its_budget_and_its_rules(self):
        cover = self.after["realised"]
        self.assertGreater(cover["tufts"], 0.8 * BUDGET)          # scaled to the ceiling, not far under
        self.assertLessEqual(cover["tufts"], BUDGET)
        self.assertEqual(cover["maxTufts"], BUDGET)
        self.assertEqual(cover["underBuilding"], 0)
        self.assertEqual(cover["inLane"], 0)
        self.assertEqual(cover["outOfFrame"], 0)
        self.assertTrue(cover["bake"])
        self.assertTrue(cover["inSource"])          # what the exterior exporter walks
        self.assertEqual(cover["properties"], {"sr_cover_layout": "E_mixed", "sr_cover_budget": BUDGET,
                                               "sr_cover_seed": 1})

    def test_the_document_had_no_cover_before(self):
        self.assertIsNone(self.before["realised"])


if __name__ == "__main__":
    unittest.main()
