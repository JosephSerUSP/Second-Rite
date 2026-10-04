"""Public coverage, stale-artifact controls and real-builder measurement evidence."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import furnishings_catalogue as catalogue
import script_index
from blender_test_support import blender_executable


class CatalogueTests(unittest.TestCase):
    def test_committed_catalogue_covers_public_api(self):
        rows = catalogue.check()
        self.assertEqual({r['id'] for r in rows}, {r['id'] for r in catalogue.inventory()})

    def test_new_required_parameter_needs_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'furnishings.py'
            fixtures = Path(temp)/'fixtures.json'
            source.write_text('def new_builder(room, name, at, *, wall):\n    """Needs a wall."""\n', encoding='utf-8')
            fixtures.write_text('{"overrides":{},"placement":{}}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'missing preview inputs'):
                catalogue.inventory(source, fixtures)

    def test_missing_documentation_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'furnishings.py'
            source.write_text('def undocumented(room):\n    pass\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'docstring'):
                catalogue.inventory(source)

    def test_changed_or_orphaned_thumbnail_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'catalogue'
            shutil.copytree(catalogue.OUTPUT, output)
            (output/'water_stand.png').write_bytes(b'not the rendered preview')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                catalogue.check(output)
            shutil.copy2(catalogue.OUTPUT/'water_stand.png', output/'water_stand.png')
            (output/'retired.png').write_bytes(b'orphan')
            with self.assertRaisesRegex(ValueError, 'orphaned'):
                catalogue.check(output)

    def test_measurement_is_not_nominal_height(self):
        row = next(r for r in catalogue.check() if r['id']=='water_stand')
        # The public height=.55 is the stand, not the crock/dipper assembly.
        self.assertGreater(row['dimensions'][2], 1.2)

    def test_search_finds_customer_water_and_prioritizes_named_builder(self):
        rows=catalogue.check()
        self.assertEqual(catalogue.search(rows,'water')[0]['id'],'water_stand')
        self.assertEqual(catalogue.search(rows,'customer water')[0]['id'],'water_stand')
        self.assertEqual(catalogue.search(rows,'unicorn'),[])


class ScriptIndexTests(unittest.TestCase):
    def test_manifest_and_generated_index(self):
        script_index.check()

    def test_unclassified_or_duplicate_file_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'new.py').write_text('pass', encoding='utf-8')
            manifest=root/'manifest.json'
            manifest.write_text('{"scripts":[]}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'unclassified'):
                script_index.entries(manifest, root)
            rows=[dict(path='new.py',role='production',purpose='Example.')]*2
            manifest.write_text(json.dumps(dict(scripts=rows)), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                script_index.entries(manifest, root)


class CatalogueIntegrationTests(unittest.TestCase):
    def test_every_builder_rebuilds_and_preserves_measurements(self):
        blender_executable()  # configured/required prerequisites never silently skip
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            catalogue.build(root/'catalogue', root/'FURNISHINGS.md')
            fresh=json.loads((root/'catalogue/index.json').read_text(encoding='utf-8'))['entries']
            committed=catalogue.check()
            for actual, expected in zip(fresh, committed):
                self.assertEqual(actual['id'], expected['id'])
                for field in ('bounds','dimensions','materials','meshCount','lightCount'):
                    self.assertEqual(actual[field],expected[field],f"{actual['id']}: {field}")
            # Pixel hashes validate each committed artefact, but are not compared
            # between GPU/driver hosts. This is construction, not native visual proof.


if __name__=='__main__':
    unittest.main()
