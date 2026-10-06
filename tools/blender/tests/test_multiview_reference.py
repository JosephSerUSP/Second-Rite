import sys
import unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from multiview_reference import measure_profile, interpolate, atlas_uv, combine_profiles


class MultiviewReferenceTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.new('RGBA', (80, 70))
        # Three real widths with an attached right-side occluder on one row.
        for y in range(10, 61):
            radius = 10 + (y - 10) // 5
            for x in range(35 - radius, 36 + radius):
                self.image.putpixel((x, y), (170, 100, 40, 253))
        for x in range(45, 79):
            self.image.putpixel((x, 35), (170, 100, 40, 253))

    def test_unoccluded_edge_preserves_body_and_uses_alpha(self):
        before = self.image.tobytes()
        p = measure_profile(self.image, center=35, top=10, bottom=60,
                            clip=(0, 80), edge='left', samples=3)
        self.assertEqual(p, [[0, .4], [.5, .3], [1, .2]])
        self.assertEqual(self.image.tobytes(), before)
        self.assertAlmostEqual(interpolate(p, .25), .35)

    def test_occlusion_clip_and_missing_body_fail(self):
        with self.assertRaisesRegex(ValueError, 'clip'):
            measure_profile(self.image, center=35, top=10, bottom=60,
                            clip=(0, 79), edge='both', samples=3)
        self.image.putpixel((35, 60), (0, 0, 0, 0))
        with self.assertRaisesRegex(ValueError, 'empty body'):
            measure_profile(self.image, center=35, top=10, bottom=60,
                            clip=(0, 80), edge='left')

    def test_original_atlas_coordinates_and_reversed_back(self):
        panel = {'axes': [0, 2], 'center': [300, 200], 'scale': [-40, -50]}
        self.assertEqual(atlas_uv((2, 99, 1), panel, (800, 400)), (.275, .625))
        with self.assertRaisesRegex(ValueError, 'leaves'):
            atlas_uv((100, 0, 0), panel, (800, 400))
        panel['scale'][0] = float('nan')
        with self.assertRaises(ValueError):
            atlas_uv((0, 0, 0), panel, (800, 400))

    def test_invalid_calibration(self):
        for kwargs in ({'samples': 1}, {'edge': 'invent'}, {'alpha': 0}, {'top': 65}):
            args = dict(center=35, top=10, bottom=60, clip=(0, 80), edge='left')
            args.update(kwargs)
            with self.assertRaises(ValueError):
                measure_profile(self.image, **args)

    def test_side_controls_depth_independently_of_front_width(self):
        front = [[0, .3], [1, .4]]
        side = [[0, .2], [1, .3]]
        back = [[0, .4], [1, .5]]
        rows = combine_profiles(front, side, back, height=2, top_ratio=1, top_weight=0)
        changed = combine_profiles(front, [[f, r*1.5] for f, r in side], back,
                                   height=2, top_ratio=1, top_weight=0)
        self.assertEqual([v[0] for v in rows], [v[0] for v in changed])
        self.assertEqual([v[2] for v in rows], [-1, 1])
        for a, b in zip(rows, changed):self.assertAlmostEqual(b[1], a[1]*1.5)
        reconciled = combine_profiles(front, side, back, height=2, top_ratio=1.1, top_weight=1)
        self.assertAlmostEqual(reconciled[-1][1]/reconciled[-1][0], 1.1)

    def test_disagreeing_profile_levels_and_invalid_radii_fail(self):
        p = [[0, .3], [1, .4]]
        for side in ([[0, .3], [.8, .4]], [[0, 0], [1, .4]], [[0, .3], [1, float('nan')]]):
            with self.assertRaises(ValueError):combine_profiles(p, side, p, height=2, top_ratio=1)
