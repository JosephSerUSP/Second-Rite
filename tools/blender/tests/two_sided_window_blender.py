"""Check actual window swing geometry in both wall orientations."""
from pathlib import Path
import sys
from types import SimpleNamespace
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'recipes'))
from opening_families import two_sided_window

class Part(dict):
    def __init__(self,name,location):
        super().__init__();self.name=name;self.location=Vector(location)
        self.rotation_euler=SimpleNamespace(z=0)

class Host:
    wood='wood';whitewash='lime';stone='stone';glass='glass';iron='iron';panel='paint'
    def part(self,name,size,location,material):return Part(name,location)

center=Vector((3,7,2))
for normal in (Vector((1,0,0)),Vector((0,1,0))):
    parts=two_sided_window(Host(),'test',center,normal)
    shutters=[p for p in parts if p.name=='test_shutter']
    casements=[p for p in parts if p.name=='test_casement_glass']
    grille=[p for p in parts if p.name=='test_outer_grille']
    assert len(shutters)==2 and len(casements)==2 and len(grille)==5
    assert all((p.location-center).dot(normal)>.5 for p in shutters), 'Shutters intrude indoors'
    assert all((p.location-center).dot(normal)<0 for p in casements), 'Casements cross exterior grille'
    assert all(abs((p.location-center).dot(normal)-.445)<1e-5 for p in grille)
    assert all(p['sr_shutters_open']=='outward' and p['sr_casements_open']=='inward' for p in parts)
try:two_sided_window(Host(),'bad',center,(0,0,0))
except ValueError:pass
else:raise AssertionError('Degenerate window basis accepted')
print('TWO-SIDED WINDOW GEOMETRY OK')
