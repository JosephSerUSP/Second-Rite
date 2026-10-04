from pathlib import Path
import subprocess
import sys
import unittest

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from blender_test_support import blender_executable


class RoomSpecIntegrationTests(unittest.TestCase):
    def test_real_builders_support_and_exit_constraints(self):
        result=subprocess.run([blender_executable(),'--background','--factory-startup',
            '--python-exit-code','1','--python',str(HERE/'tests/room_spec_probe.py')],
            capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('ROOM SPEC PROBE OK',result.stdout)


if __name__=='__main__': unittest.main()
