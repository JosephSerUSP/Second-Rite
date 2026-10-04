import tempfile
import unittest
from tools.blender.tests.test_eevee_backend import blender,TOOLS

class CourtyardRecipeTests(unittest.TestCase):
    def test_fresh_build_matches_registered_scaffold_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            result=blender('--disable-autoexec','-P',str(TOOLS/'offline_blender.py'),
                '--',str(TOOLS/'tests/courtyard_recipe_blender.py'),'--',directory)
        self.assertEqual(result.returncode,0,result.stdout[-3000:]+result.stderr[-1000:])
        self.assertIn('COURTYARD RECIPE PARITY OK',result.stdout)

if __name__=='__main__':unittest.main()
