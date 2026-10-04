"""Real Blender check: broken relocation fails; packed relocation succeeds."""
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_test_support
from blender_test_support import blender_executable


class SourceDependencyTests(unittest.TestCase):
    def test_relative_and_packed_source_relocation(self):
        result=subprocess.run([blender_executable(),'--background','--factory-startup',
            '--disable-autoexec','--python-exit-code','1','--python',
            str(TOOLS/'tests/source_dependencies_blender.py')],capture_output=True,text=True,
            encoding='utf-8',errors='replace',timeout=120)
        self.assertEqual(result.returncode,0,result.stdout[-3000:]+result.stderr[-1000:])
        self.assertIn('SOURCE DEPENDENCY REGRESSION OK',result.stdout)


if __name__=='__main__':unittest.main()
