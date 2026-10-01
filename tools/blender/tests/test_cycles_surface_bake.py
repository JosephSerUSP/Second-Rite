import unittest
from tools.blender.tests.test_eevee_backend import blender,TOOLS
class CyclesSurfaceBakeTests(unittest.TestCase):
    def test_export_preserves_open_sheets_and_repairs_closed_winding(self):
        result=blender('-P',str(TOOLS/'tests/export_geometry_blender.py'))
        self.assertEqual(result.returncode,0,result.stdout[-2000:]+result.stderr[-1000:])
        self.assertIn('EXPORT GEOMETRY OK',result.stdout)

    def test_only_the_receiver_image_is_baked_and_proxies_are_not_sources(self):
        result=blender('--disable-autoexec','-P',str(TOOLS/'offline_blender.py'),'--',str(TOOLS/'tests/cycles_surface_bake_blender.py'))
        self.assertEqual(result.returncode,0,result.stdout[-3000:]+result.stderr[-1000:])
        self.assertIn('CYCLES SURFACE BAKE OK',result.stdout)
if __name__=='__main__':unittest.main()
