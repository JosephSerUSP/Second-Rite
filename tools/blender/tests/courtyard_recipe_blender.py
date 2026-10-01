"""Prove the advertised fresh-build command reproduces the registered scaffold."""
import json
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
            'vertices':[[round(float(c),5) for c in vertex.co] for vertex in obj.data.vertices],
            'faces':sorted(tuple(face.vertices) for face in obj.data.polygons),
            'transform':[[round(float(c),5) for c in row] for row in obj.matrix_world],
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
assert actual==expected, f'Recipe/source disagree: {set(actual)^set(expected)}; changed {[name for name in actual.keys()&expected.keys() if actual[name]!=expected[name]][:10]}'
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
