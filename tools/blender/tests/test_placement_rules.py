import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import placement_rules as rules


class PlacementTests(unittest.TestCase):
    def test_on_uses_support_height_and_rejects_overhang(self):
        surface=[[.16,-2.3,.96],[.84,1.3,.96]]
        child=[[-.2,-.2,0],[.2,.2,.5]]
        delta=rules.on_surface(child,surface,[0,0],'basket.place.on')
        self.assertAlmostEqual(delta[2],.96)
        with self.assertRaisesRegex(ValueError,'basket.place.on.*beyond support'):
            rules.on_surface(child,surface,[.3,0],'basket.place.on')

    def test_beside_tracks_changed_target_dimensions(self):
        child=[[-.3,-.3,0],[.3,.3,1.2]]
        short=[[-.34,-.9,0],[.34,.9,.96]]
        long=[[-.34,-1.8,0],[.34,1.8,.96]]
        for target in (short,long):
            offset=rules.beside(child,target,'y',1,.16,'water.place.beside')
            bounds=rules.translated(child,offset)
            self.assertAlmostEqual(bounds[0][1]-target[1][1],.16)

    def test_bakery_exit_sightline_rejects_old_water_stand(self):
        protected={'exit_sightline':[[-1.6,-3.9,.05],[.1,-2.4,1.8]]}
        old=[[-1.167,-3.4163,0],[-.570,-2.8,1.238976]]
        with self.assertRaisesRegex(ValueError,'water.*keepClear.exit_sightline'):
            rules.assert_keep_clear(old,protected,'water')
        rules.assert_keep_clear([[.18,1.46,0],[.78,2.08,1.24]],protected,'water')

    def test_nonfinite_or_reversed_bounds_fail(self):
        for bounds in ([[0,0,0],[-1,1,1]],[[0,0,0],[1,1,float('nan')]]):
            with self.assertRaisesRegex(ValueError,'ordered XYZ bounds'):
                rules.checked_bounds(bounds,'part')


if __name__=='__main__': unittest.main()
