import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from path_sweep import transported_frames, sweep_tube


class PathSweepTests(unittest.TestCase):
    def test_frames_through_world_axis_turns(self):
        points=[(0,0,0),(0,0,1),(0,1,2),(1,2,2),(2,2,1)]
        frames=transported_frames(points)
        for t,n,b in frames:
            for v in (t,n,b):self.assertAlmostEqual(sum(x*x for x in v),1)
            for a,c in ((t,n),(t,b),(n,b)):self.assertAlmostEqual(sum(x*y for x,y in zip(a,c)),0)
        for (_,a,_),(_,b,_) in zip(frames,frames[1:]):self.assertGreater(sum(x*y for x,y in zip(a,b)),0)

    def test_tube_topology_and_distance_uv(self):
        verts,faces,uvs,smooth=sweep_tube([(0,0,0),(0,0,1),(0,0,3)],[(.2,.1)]*3,segments=8)
        edges={}
        for face in faces:
            for a,b in zip(face,face[1:]+face[:1]):
                key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
        self.assertTrue(all(count==2 for count in edges.values()))
        self.assertEqual(len(verts)-len(edges)+len(faces),2)
        self.assertAlmostEqual(uvs[0][2][1],1/3)
        self.assertEqual(uvs[7][1][0],1)
        for face in uvs:
            area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(face,face[1:]+face[:1])))/2
            self.assertGreater(area,0)
        self.assertEqual(sum(smooth),16)

    def test_invalid_geometry_fails(self):
        for points in ([(0,0,0)]*2,[(0,0,0),(1,0,0),(0,0,0)],[(0,0,0),(0,0,float('nan'))]):
            with self.assertRaises(ValueError):transported_frames(points)
        with self.assertRaises(ValueError):sweep_tube([(0,0,0),(0,0,1)],[(0,1)]*2)


if __name__=='__main__':unittest.main()
