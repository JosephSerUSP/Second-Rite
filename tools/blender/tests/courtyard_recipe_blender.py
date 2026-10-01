"""Prove the advertised fresh-build command reproduces the registered scaffold."""
import json
import math
import copy
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/blender/recipes'))
import passage_house_courtyard as recipe

def snapshot():
    bpy.context.view_layer.update()
    rows={}
    for obj in bpy.data.collections['TH_SOURCE'].all_objects:
        if obj.type!='MESH':continue
        rows[obj.name]={
            'vertices':[[float(c) for c in vertex.co] for vertex in obj.data.vertices],
            'faces':sorted(tuple(face.vertices) for face in obj.data.polygons),
            'transform':[[float(c) for c in row] for row in obj.matrix_world],
            'materials':[mat.name for mat in obj.data.materials],
            'role':obj.get('sr_bake_role','both'),
            'hidden':obj.hide_render,
            'modifiers':[(mod.name,mod.type) for mod in obj.modifiers],
        }
    return rows

output=Path(sys.argv[sys.argv.index('--')+1])/'fresh.blend'
source=ROOT/'projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
expected=snapshot()
source_before=source.read_bytes()
recipe.build(output)
actual=snapshot()
def equivalent(a,b):
    if a.keys()!=b.keys():return False
    for name,row in a.items():
        other=b[name]
        for field in row:
            if field in ['vertices','transform']:
                if len(row[field])!=len(other[field]):return False
                for left,right in zip(row[field],other[field]):
                    if len(left)!=len(right) or any(not math.isclose(x,y,rel_tol=0,abs_tol=1e-5) for x,y in zip(left,right)):return False
            elif row[field]!=other[field]:return False
    return True
assert equivalent(actual,expected), f'Recipe/source disagree: {set(actual)^set(expected)}'
# Ten micrometres tolerates cross-platform floating-point rotations without
# rounding-bin discontinuities. Real geometry drift still fails this gate.
changed=copy.deepcopy(actual)
name=next(name for name,row in changed.items() if row['vertices'])
changed[name]['vertices'][0][0]+=.001
assert not equivalent(changed,expected),'Parity gate missed a planted millimetre displacement'
assert source.read_bytes()==source_before,'Fresh build modified its registered source'
assert bpy.context.scene['courtyard_revision']==11
# The posed leaves are separate proxies: their detailed source has no opaque
# backing that would hide the louvres in oblique/rear views.
for tag in ['left','right']:
    target=bpy.data.objects['Court casement 1 '+tag+' shutter target']
    pivot=bpy.data.objects['Court casement 1 '+tag+' shutter hinge']
    assert target['sr_bake_role']=='receiver' and target.hide_render
    assert target.parent==pivot and 0<pivot['opening_degrees']<180
for name in ['Sleeping wing','Arrival hall','Service wing']:
    owner=bpy.data.objects[name+' volume']
    spec=json.loads(owner['building_volume'])
    assert spec['start_portal'] or spec['end_portal']
    assert any(obj.name.endswith('continuous footing') for obj in owner.children)
from mathutils import Vector
graph=bpy.context.evaluated_depsgraph_get()
for y in [7.5,13.5]:
    hit,*_=bpy.context.scene.ray_cast(graph,Vector((7.1,y,1.5)),Vector((0,1,0)),distance=1.8)
    assert not hit,'Authored room connection is blocked at '+str(y)
hit,*_=bpy.context.scene.ray_cast(graph,Vector((0,.5,1)),Vector((0,-1,0)),distance=3)
assert not hit,'The Cortico lane exit is blocked by courtyard geometry'
print('COURTYARD RECIPE PARITY OK',len(actual))
