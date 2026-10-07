import subprocess
import sys
import unittest
from pathlib import Path
TOOLS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TOOLS))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_test_support import blender_executable


class ItemKitReportTests(unittest.TestCase):
    def test_bounds_include_current_child_and_parent_transforms(self):
        blender_executable()
        result=subprocess.run([sys.executable,str(TOOLS/'run.py'),
            str(TOOLS/'tests/item_kit_report_blender.py')],capture_output=True,text=True,
            encoding='utf-8',errors='replace',timeout=120)
        # Explicitly select/check configured pinned Blender, consistent with the
        # optional integration policy used by the other host-discovery suites.
        self.assertEqual(result.returncode,0,result.stdout[-3000:]+result.stderr[-1000:])
        self.assertIn('ITEM KIT CURRENT TRANSFORM BOUNDS OK',result.stdout)


if __name__=='__main__':unittest.main()
