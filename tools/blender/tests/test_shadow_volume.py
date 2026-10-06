"""Malformed controls must fail before Blender; previews describe the input only."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TOOLS))
import shadow_volume as shadow


def box():
    return {'version':1,'id':'test_hull','front':[[-1,-3],[1,-3],[1,3],[-1,3]],
            'side':[[-2,-3],[2,-3],[2,3],[-2,3]],'top':[[-1,-2],[1,-2],[1,2],[-1,2]]}


class ShadowControls(unittest.TestCase):
    def test_axis_pairs_have_expected_intersected_bounds(self):
        self.assertEqual(shadow.validate(box())['projectionBounds'],[(-1,1),(-2,2),(-3,3)])

    def test_clockwise_outline_normalized_without_mutating_input(self):
        spec=box();spec['front'].reverse();before=copy.deepcopy(spec)
        result=shadow.validate(spec);self.assertEqual(spec,before)
        self.assertGreater(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(result['front'],result['front'][1:]+result['front'][:1])),0)

    def test_crossed_or_touching_edges_rejected(self):
        spec=box();spec['front']=[[-1,-1],[1,1],[-1,1],[1,-1]]
        with self.assertRaisesRegex(ValueError,'self-intersect'):shadow.validate(spec)

    def test_duplicate_collinear_nonfinite_and_boolean_coordinates_rejected(self):
        for points in ([[-1,-1],[1,-1],[1,1],[-1,1],[-1,-1]], [[0,0],[1,0],[2,0],[1,1]], [[0,0],[1,0],[0,float('nan')]], [[0,0],[True,0],[0,1]]):
            spec=box();spec['front']=points
            with self.subTest(points=points),self.assertRaises(ValueError):shadow.validate(spec)

    def test_disjoint_projection_bounds_rejected(self):
        spec=box();spec['side']=[[y,z+10] for y,z in spec['side']]
        with self.assertRaisesRegex(ValueError,'overlapping Z'):shadow.validate(spec)

    def test_invalid_cut_unknown_field_and_settings_rejected(self):
        for change in ({'cuts':[{'plane':'camera','outline':[[0,0],[1,0],[0,1]]}]},
                       {'cuts':[{'plane':['front'],'outline':[[0,0],[1,0],[0,1]]}]},
                       {'bevel':-1},{'smooth':1},{'color':[2,0,0]},{'density':10}):
            spec=box();spec.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):shadow.validate(spec)

    def test_concave_outline_and_cut_survive_preflight(self):
        spec=box();spec['front']=[[-1,-1],[1,-1],[1,1],[0,.1],[-1,1]]
        spec['cuts']=[{'plane':'side','outline':[[0,0],[.2,0],[0,.3]]}]
        result=shadow.validate(spec);self.assertEqual(len(result['front']),5);self.assertEqual(len(result['cuts']),1)

    def test_preview_names_axes_and_does_not_claim_evaluation(self):
        svg=shadow.preview_svg(box())
        for text in ('front: X / Z','side: Y / Z','top: X / Y','final hull must be evaluated'):self.assertIn(text,svg)

    def test_build_and_preview_refuse_existing_output_before_blender(self):
        with tempfile.TemporaryDirectory() as folder:
            spec=Path(folder)/'spec.json';spec.write_text(json.dumps(box()))
            for action,suffix in (('build','.blend'),('preview','.svg')):
                target=Path(folder)/('test_hull'+suffix);target.write_bytes(b'owner-edited')
                self.assertEqual(shadow.main([action,str(spec),'--output',str(target)]),1)
                self.assertEqual(target.read_bytes(),b'owner-edited')


if __name__=='__main__':unittest.main()
