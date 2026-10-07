from pathlib import Path
import sys,subprocess,unittest
TOOLS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TOOLS));sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_test_support import blender_executable
class SurfaceConformTests(unittest.TestCase):
    def test_live_target_edit_changes_closed_panel_without_losing_uvs(self):
        blender_executable()
        result=subprocess.run([sys.executable,str(TOOLS/'run.py'),str(TOOLS/'tests/surface_conform_blender_fixture.py')],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
        self.assertEqual(result.returncode,0,result.stdout[-3000:]+result.stderr[-1000:])
        self.assertIn('SURFACE CONFORMANCE FIXTURE OK',result.stdout)
if __name__=='__main__':unittest.main()
