from pathlib import Path
import subprocess
import sys
import unittest

TOOLS = Path(__file__).resolve().parents[1]


class ViewProjectionTests(unittest.TestCase):
    def test_real_bake_rejects_occlusion_and_preserves_unseen_fallback(self):
        result = subprocess.run([sys.executable, str(TOOLS/'run.py'),
                                 str(TOOLS/'tests/view_projection_blender_fixture.py')],
                                capture_output=True, text=True, encoding='utf-8',
                                errors='replace', timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout[-4000:]+result.stderr[-1000:])
        self.assertIn('VIEW PROJECTION FIXTURE OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
