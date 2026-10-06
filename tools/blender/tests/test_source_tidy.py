import unittest
from tools.blender.tests.test_eevee_backend import blender, TOOLS


class SourceTidyTests(unittest.TestCase):
    def test_consolidation_joins_repeats_and_preserves_geometry(self):
        result = blender('--disable-autoexec', '-P', str(TOOLS / 'offline_blender.py'),
                         '--', str(TOOLS / 'tests/source_tidy_blender.py'))
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-1000:])
        self.assertIn('SOURCE TIDY OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
