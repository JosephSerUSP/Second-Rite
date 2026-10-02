"""Counter carcasses must support the underside of their slabs."""
from contextlib import nullcontext
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'recipes'))
from furnishings import counter,service_screen

class Host:
    wood='wood'
    def __init__(self):self.parts={};self.records=[]
    def piece(self,name):return nullcontext()
    def part(self,name,size,location,material):
        self.parts[name]=(size,location);self.records.append((name,size,location))

class CounterSupportTests(unittest.TestCase):
    def test_slab_is_supported_at_multiple_authored_heights(self):
        for height in (.6,.92,1.2):
            host=Host();counter(host,'counter',(0,0),height=height)
            body,center=host.parts['counter_carcass'];slab,slab_center=host.parts['counter_top']
            self.assertAlmostEqual(center[2]+body[2]/2,slab_center[2]-slab[2]/2)
            self.assertGreater(slab[0],body[0]);self.assertGreater(slab[1],body[1])

    def test_ceiling_head_reaches_ceiling_without_filling_beam_pockets(self):
        host=Host();pockets=[(-1.62,-1.38),(-.12,.12)]
        service_screen(host,'screen',front=.89,rear=4.66,left=1.245,right=-2.645,
                       height=3.65,transom_top=3.33,beam_spans=pockets)
        fills=[(size,location) for name,size,location in host.records if name=='notched_front_head_infill']
        self.assertEqual(len(fills),3)
        for size,location in fills:
            self.assertAlmostEqual(location[2]+size[2]/2,3.65)
            low=location[1]-size[1]/2;high=location[1]+size[1]/2
            for begin,end in pockets:self.assertTrue(high<=begin+1e-6 or low>=end-1e-6)
        rails=[(size,location) for name,size,location in host.records if name=='service_transom_rail']
        self.assertAlmostEqual(max(location[2]+size[2]/2 for size,location in rails),3.37)

if __name__=='__main__':unittest.main()
