import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'recipes'))
from shell_geometry import ceiling_members

class ShellGeometryTests(unittest.TestCase):
    def test_ceiling_covers_outer_wall_tops_at_different_dimensions(self):
        for front,back,width,wall,z,thick in [(-2.13,4.67,4.65,.5,3.65,.3),(-1,3,2,.3,2.7,.2)]:
            members=ceiling_members(front,back,width,wall,z,thick)
            _,size,center=members[0]
            self.assertAlmostEqual(center[0]-size[0]/2,front)
            self.assertAlmostEqual(center[0]+size[0]/2,back+wall)
            self.assertAlmostEqual(size[1]/2,width+wall)
            self.assertAlmostEqual(center[2]-size[2]/2,z)
            for _,size,center in members[1:]:
                self.assertAlmostEqual(center[2]+size[2]/2,z)
            # Plates embed into masonry rather than leave an air seam.
            rear=members[1]
            self.assertGreater(rear[2][0]+rear[1][0]/2,back)
            for _,size,center in members[2:]:
                self.assertGreater(abs(center[1])+size[1]/2,width)

if __name__=='__main__': unittest.main()
