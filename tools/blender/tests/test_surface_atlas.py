import unittest,sys
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from surface_atlas import path_parameters, rectangle_uv, cyclic_face_parameters, seam_color_report, pixel_rectangle_uv


class SurfaceAtlasTests(unittest.TestCase):
    def test_pixel_allocation_preserves_orientation_and_sampling_clearance(self):
        bounds = pixel_rectangle_uv((20, 10, 100, 50), (200, 100), inset=2)
        self.assertEqual(bounds, (.11, .52, .49, .88))
        self.assertEqual(rectangle_uv(0, 1, bounds), (.11, .88))
        for box, size, inset in [((0, 0, 10, 10), (20, 20), 5),
                                 ((0, 0, 21, 10), (20, 20), 0),
                                 ((0, 0, 10, 10), (0, 20), 0),
                                 ((0, 0, 10, 10), (20, 20), -1)]:
            with self.assertRaises(ValueError):pixel_rectangle_uv(box, size, inset=inset)

    def test_distance_controls_uv_density_and_shared_join(self):
        p=path_parameters([(0,0),(3,0),(3,1),(6,1)])
        self.assertEqual(p,[0,3/7,4/7,1])
        a=rectangle_uv(p[1],.2,(.02,.1,.98,.8));b=rectangle_uv(p[1],.2,(.02,.1,.98,.8))
        self.assertEqual(a,b)
        with self.assertRaises(ValueError):path_parameters([(0,0),(0,0)])

    def test_one_cyclic_seam_and_noncollapsed_pole(self):
        self.assertEqual(cyclic_face_parameters([.875,0,None]),[.875,1,.9375])
        self.assertEqual(cyclic_face_parameters([.125,.25,None]),[.125,.25,.1875])
        with self.assertRaises(ValueError):cyclic_face_parameters([.1,.4,.7])

    def test_normalized_bounds_fail_loud(self):
        self.assertEqual(rectangle_uv(1,0,(.1,.2,.9,.8)),(.9,.2))
        self.assertEqual(rectangle_uv(1+1e-8,0,(.1,.2,.9,.8)),(.9,.2))
        for u,v,box in [(1.01,0,(0,0,1,1)),(0,0,(0,0,0,1)),(0,float('nan'),(0,0,1,1))]:
            with self.assertRaises(ValueError):rectangle_uv(u,v,box)

    def test_seam_report_reads_without_modifying_pixels(self):
        image=Image.new('RGB',(5,5),(50,90,130));before=image.tobytes()
        report=seam_color_report(image,(0,0,1,1),samples=5)
        self.assertEqual(report['meanAbsoluteRGBDelta'],0)
        image.putpixel((4,2),(80,120,160))
        self.assertEqual(seam_color_report(image,(0,0,1,1),samples=5)['meanAbsoluteRGBDelta'],6)
        self.assertNotEqual(before,image.tobytes())
        changed=image.tobytes();seam_color_report(image,(0,0,1,1));self.assertEqual(changed,image.tobytes())
