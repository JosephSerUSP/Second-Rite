"""Real scaffold construction and negative controls, run inside pinned Blender."""
from copy import deepcopy
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import compile_room_spec as compiler
import furnishing_geometry as geometry
from placement_rules import assert_keep_clear

spec=json.loads((HERE/'recipes/examples/serving_corner.json').read_text(encoding='utf-8'))
room,bounds=compiler.compile_spec(spec)
counter=[o for o in room.parts if o.name=='counter']
surface=geometry.rectangular_top(counter,'counter')
assert abs(bounds['bread'][0][2]-surface[1][2])<1e-5
assert abs(bounds['counter'][0][0]-bounds['water'][1][0]-.16)<1e-5
for name,box in bounds.items(): assert_keep_clear(box,spec['keepClear'],name)
for key,alter,expected in [
    ('on',lambda s:s['furnishings'][1]['place'].update(offset=[.5,0]),'beyond support'),
    ('exit',lambda s:s['furnishings'][3].update(place={'at':[-.85,-3.15]}),'exit_sightline'),
    ('param',lambda s:s['furnishings'][0]['params'].update(lenght=3.6),'lenght'),
    ('forward',lambda s:s['furnishings'][1]['place'].update(on='unknown'),'unknown/forward'),
]:
    candidate=deepcopy(spec); alter(candidate)
    try: compiler.compile_spec(candidate)
    except ValueError as error:
        assert expected in str(error),(key,str(error))
        assert 'furnishings[' in str(error),(key,str(error))
    else: raise AssertionError(key+' negative control unexpectedly succeeded')
print('ROOM SPEC PROBE OK')
