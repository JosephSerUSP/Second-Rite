import unittest
from tools.blender.tests.test_eevee_backend import blender,TOOLS

class BakeReceiverTests(unittest.TestCase):
    def test_sources_remain_in_beauty_and_receivers_remain_in_export(self):
        result=blender('--disable-autoexec','-P',str(TOOLS/'tests/bake_receivers_blender.py'))
        self.assertEqual(result.returncode,0,result.stdout[-2000:]+result.stderr[-1000:])
        self.assertIn('BAKE_RECEIVER_PROOF',result.stdout)

if __name__=='__main__':unittest.main()
