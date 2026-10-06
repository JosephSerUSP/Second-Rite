"""Integration remains an explicit skip without pinned Blender; required CI fails loud."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]


class ShadowBlenderIntegration(unittest.TestCase):
    def test_live_masks_cuts_uvs_and_export_dependencies(self):
        if not os.environ.get('BLENDER_EXECUTABLE'):
            if os.environ.get('BLENDER_TESTS_REQUIRED')=='1':self.fail('pinned Blender is required')
            self.skipTest('BLENDER_EXECUTABLE not configured')
        result=subprocess.run([sys.executable,'tools/blender/run.py','tools/blender/tests/shadow_volume_blender.py'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        self.assertIn('SHADOW VOLUME BLENDER OK',result.stdout)


if __name__=='__main__':unittest.main()
