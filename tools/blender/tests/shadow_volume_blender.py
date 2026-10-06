"""Real Blender probes: known hull/cut volume, live editing, UVs and duplicate dependencies."""
import sys,math,tempfile,hashlib
from pathlib import Path
import bpy,bmesh
from mathutils import Vector

TOOLS=Path(__file__).resolve().parents[1];sys.path.insert(0,str(TOOLS))
import item_kit as kit
from shadow_volume import validate
from shadow_volume_blender import build_volume,inspect_body
from validate_item_obj_runtime import validate as validate_obj


def spec(cuts=None):
    return {'version':1,'id':'shadow_test','front':[[-1,-3],[1,-3],[1,3],[-1,3]],
      'side':[[-2,-3],[2,-3],[2,3],[-2,3]],'top':[[-1,-2],[1,-2],[1,2],[-1,2]],'cuts':cuts or []}


def measured(ob):
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg);data=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
    try:
        bm=bmesh.new();bm.from_mesh(data);volume=abs(bm.calc_volume(signed=True));bm.free()
        low=tuple(min(v.co[i] for v in data.vertices) for i in range(3));high=tuple(max(v.co[i] for v in data.vertices) for i in range(3))
        layer=data.uv_layers.get('UVMap');assert layer is not None,'generated mesh lacks UVs'
        for poly in data.polygons:
            coords=[tuple(layer.data[li].uv) for li in poly.loop_indices]
            area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(coords,coords[1:]+coords[:1])))/2
            assert area>1e-10,('collapsed generated-face UV',poly.index)
            assert all(-1e-5<=c<=1+1e-5 for uv in coords for c in uv),('unbounded UV',poly.index)
        return volume,low,high
    finally:ev.to_mesh_clear()


root=kit.begin('shadow_test','test','known box from three shadows');material=kit.material('shadow_test_surface',color=(.6,.7,.8))
body,masks=build_volume('Hull',spec(),root,material)
volume,lo,hi=measured(body);assert abs(volume-48)<1e-6,(volume,lo,hi)
assert lo==(-1,-2,-3) and hi==(1,2,3),(lo,hi)
assert body.data==masks['front'].data,'front control must drive source body'
# Edit a hidden side silhouette, not the scaffold inputs. The saved graph updates.
for vertex in masks['side'].data.vertices:
    if vertex.co.y>0:vertex.co.y=1.5
volume,lo,hi=measured(body);assert abs(volume-42)<1e-6,(volume,lo,hi)
print('LIVE SHADOW EDIT OK: volume 48 -> 42 via one saved silhouette')

# A stencil is a real through opening, with the analytically expected volume.
root=kit.begin('shadow_test','test','known pierced box');material=kit.material('shadow_test_surface',color=(.6,.7,.8))
body,masks=build_volume('Hull',spec([{'plane':'front','outline':[[-.2,-.3],[.2,-.3],[.2,.3],[-.2,.3]]}]),root,material)
volume,lo,hi=measured(body);assert abs(volume-47.04)<1e-5,volume
assert len([m for m in body.modifiers if m.type=='BOOLEAN'])==3
print('THROUGH STENCIL OK: known 0.96 volume removed; generated-face UVs valid')

# Source projection bounds can overlap even when the actual intersection is empty.
empty=spec();empty['front']=[[0,1],[1,0],[1,1]];empty['side']=[[0,0],[1,0],[0,1]];empty['top']=[[0,.2],[.8,1],[0,1]]
validate(empty)  # All projection bounds overlap, yet y<=x and y>=x+.2 conflict.
try:build_volume('Empty',empty,root,material)
except ValueError:pass
else:raise AssertionError('empty/disjoint shadow body silently accepted')

# Compiler temporary duplicates shift the root; modifier dependencies must shift too.
root.location=(5,7,11);bpy.context.view_layer.update()
collection,duplicate,copies=kit.core.duplicate_hierarchy(bpy.context,root)
duplicate_body=next(ob for ob in copies if ob.name.startswith('Hull'))
booleans=[m for m in duplicate_body.modifiers if m.type=='BOOLEAN']
assert all(m.object in copies for m in booleans),'export duplicate still points at source masks'
volume,lo,hi=measured(duplicate_body);assert abs(volume-47.04)<1e-5,(volume,lo,hi)
assert tuple(duplicate.matrix_world.translation)==(0,0,0)
kit.core.delete_collection(collection.name)
print('ROOT TRANSLATION OK: duplicate dependencies belong to temporary export graph')

# An asymmetric intersection bevel used to export a triangle whose rounded
# endpoints coincide. The live cleanup must survive the actual OBJ boundary.
root=kit.begin('shadow_test','test','asymmetric bevel precision fixture');material=kit.material('shadow_test_surface')
asymmetric={'version':1,'id':'shadow_test',
 'front':[[-.55,-.89],[.23,-.79],[.56,-.19],[.24,.98],[-.11,.72],[-.43,.06],[-.63,-.16]],
 'side':[[-.22,-.89],[.23,-.67],[.27,.08],[.02,.98],[-.30,.02]],
 'top':[[-.63,-.07],[-.40,-.30],[.42,-.26],[.56,.04],[.17,.23],[-.47,.19]],'bevel':.008}
body,masks=build_volume('AsymmetricHull',asymmetric,root,material)
report=inspect_body(body);assert report['uvFindings']==0 and len(report['controls'])==3
with tempfile.TemporaryDirectory(prefix='shadow-precision-') as folder:
    output=kit.core.export_asset_root(bpy.context,root,folder)[0];validate_obj(Path(output))
print('EXPORT PRECISION OK: asymmetric live bevel exports without degenerate faces')
print('SHADOW VOLUME BLENDER OK')
