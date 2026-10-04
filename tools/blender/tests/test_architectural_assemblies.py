import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'recipes'))
from architectural_assemblies import Window

class ArchitecturalAssemblyTests(unittest.TestCase):
    def test_stock_is_dimensioned_and_has_explicit_hinge_poses(self):
        spec=Window('example',4.5,3.5,1.2,width=1.6,height=2.0,shutter_angles=(95,140))
        self.assertEqual(spec.rows*spec.columns,6)
        self.assertEqual(spec.shutter_angles,(95,140))
    def test_invalid_apertures_and_pose_fail_before_blender_work(self):
        for values in [{'width':0},{'reveal':-1},{'height':float('nan')},{'rows':0},{'columns':1.5},{'shutter_angles':(181,90)},{'shutter_angles':(90,)}]:
            with self.subTest(values=values),self.assertRaises(ValueError):Window('example',4.5,3.5,1.2,**values)

if __name__=='__main__':unittest.main()
