"""Image-alpha meshing preserves pixels and has explicit geometric limits."""
from pathlib import Path
import hashlib,sys,tempfile,unittest
from collections import Counter
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import painted_relief as relief


class PaintedReliefTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'image.png'
        image=Image.new('RGBA',(33,33),(160,80,40,0));ImageDraw.Draw(image).rectangle((4,4,28,28),fill=(160,80,40,252));image.save(self.path)
    def tearDown(self):self.tmp.cleanup()
    def mesh(self,**kwargs):return relief.build_mesh(self.path,grid=16,**kwargs)
    def test_source_pixels_and_file_bytes_are_unchanged(self):
        before=self.path.read_bytes();mesh=self.mesh()
        self.assertEqual(before,self.path.read_bytes());self.assertEqual(mesh['report']['imageHash'],hashlib.sha256(before).hexdigest())
    def test_width_height_and_parallel_thickness_are_authored(self):
        mesh=self.mesh(width=2,height=3,depth=.3,bow=.2,relief=.04);v=mesh['vertices'];n=len(v)//2
        self.assertAlmostEqual(max(p[0] for p in v)-min(p[0] for p in v),2)
        self.assertAlmostEqual(max(p[2] for p in v)-min(p[2] for p in v),3)
        for a,b in zip(v[:n],v[n:]):self.assertAlmostEqual(b[1]-a[1],.32)
    def test_mesh_is_closed_and_front_uvs_match_original_image_positions(self):
        mesh=self.mesh(width=2,height=2);edges=Counter()
        for face in mesh['faces']:
            for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted((a,b)))]+=1
        self.assertTrue(all(n==2 for n in edges.values()))
        for face,uvs,material in zip(mesh['faces'],mesh['uvs'],mesh['materials']):
            if material:continue
            for index,(u,v) in zip(face,uvs):
                x,y,z=mesh['vertices'][index]
                self.assertAlmostEqual(u,(4+(x/2+.5)*24)/32)
                self.assertAlmostEqual(v,(4+(z/2+.5)*24)/32)
    def test_hole_remains_a_physical_opening(self):
        image=Image.open(self.path);ImageDraw.Draw(image).rectangle((13,13,19,19),fill=(0,0,0,0));image.save(self.path)
        mesh=self.mesh(width=2,height=2)
        self.assertLess(mesh['report']['acceptedCells'],256)
        self.assertFalse(any(all(abs(mesh['vertices'][v][0])<.1 and abs(mesh['vertices'][v][2])<.1 for v in face) for face in mesh['faces']))
    def test_disconnected_marks_are_reported_and_excluded(self):
        image=Image.new('RGBA',(49,33),(0,0,0,0));d=ImageDraw.Draw(image);d.rectangle((4,4,28,28),fill=(160,80,40,252));d.rectangle((36,12,44,20),fill=(160,80,40,252));image.save(self.path)
        mesh=self.mesh();self.assertGreater(mesh['report']['discardedDetachedCells'],0)
    def test_rgb_opaque_and_empty_images_fail(self):
        for mode,color in [('RGB',(1,2,3)),('RGBA',(1,2,3,255)),('RGBA',(1,2,3,0))]:
            Image.new(mode,(33,33),color).save(self.path)
            with self.subTest(mode=mode,color=color),self.assertRaises(ValueError):self.mesh()
    def test_bad_controls_fail(self):
        for kwargs in [{'width':0},{'width':float('nan')},{'depth':-1},{'bow':-.1},{'relief':True},{'alpha':256},{'height':float('inf')}]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.mesh(**kwargs)
    def test_existing_outputs_are_not_overwritten(self):
        output=Path(self.tmp.name)/'mesh.json';output.write_bytes(b'owner')
        self.assertEqual(relief.main([str(self.path),'--mesh-output',str(output)]),1)
        self.assertEqual(output.read_bytes(),b'owner')


if __name__=='__main__':unittest.main()
