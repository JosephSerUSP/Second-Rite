"""Exercise Project selection across Python, Node and production adapters."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools/asset-production'))
from tools.shared.project_paths import project_root, within, ProjectPathError
import asset_set


class ProjectSelectionTests(unittest.TestCase):
    def test_explicit_root_wins_over_environment_and_matches_node(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / 'external projeto praça'
            (project / 'data').mkdir(parents=True)
            with patch.dict(os.environ, {'SECOND_RITE_PROJECT': str(ROOT)}):
                actual = project_root(project)
                result = subprocess.run(['node', str(ROOT / 'tools/semantic-roots.js')], input=json.dumps({'projectRoot': str(project)}), text=True, encoding='utf-8', capture_output=True, check=True)
                self.assertEqual(actual, Path(json.loads(result.stdout)['projectRoot']))
                self.assertEqual(actual, project.resolve())

    def test_environment_selects_an_external_project(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / 'data').mkdir()
            self.assertEqual(project_root(env={'SECOND_RITE_PROJECT': directory}), project.resolve())

    def test_installation_root_is_rejected_without_fallback(self):
        with self.assertRaisesRegex(ProjectPathError, 'no data/'):
            project_root(ROOT)

    def test_relative_selection_resolves_from_callers_working_directory(self):
        relative = Path('projects/editor-fixture')
        self.assertEqual(project_root(relative), (ROOT / relative).resolve())

    def test_product_path_cannot_escape_owner(self):
        with self.assertRaisesRegex(ProjectPathError, 'outside'):
            within(ROOT, '../escape')

    def test_asset_contract_stays_in_installation_for_external_project(self):
        default = asset_set.load_asset_set()
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / 'data').mkdir()
            record = project / 'asset-set.json'
            serializable = {key: value for key, value in default.items() if not key.startswith('_')}
            record.write_text(json.dumps(serializable))
            selected = asset_set.load_asset_set(record, root=project, check_files=False)
            surface = next(row for row in selected['assets'] if row['kind'] == 'surface')
            command = asset_set.surface_generate_command(surface, root=project)
            height = Path(command[command.index('--height') + 1])
            self.assertTrue(height.is_relative_to(project))
            self.assertEqual(command[1], 'tools/asset-gen/gen.py')
