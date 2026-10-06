"""Real export of alpha-bound geometry after live boundary finishing."""
from pathlib import Path
import sys,json,tempfile
import bpy,bmesh
TOOLS=Path(__file__).resolve().parents[1];sys.path.insert(0,str(TOOLS))
import item_kit as kit
from painted_relief_blender import create_relief,add_boundary_finish
from validate_item_obj_runtime import validate

args=sys.argv[sys.argv.index('--')+1:];mesh=json.loads(Path(args[0]).read_text());image=Path(args[1])
root=kit.begin('painted_test','test','known alpha silhouette export')
paint=kit.material('painted_test_face',image=image);edge=kit.material('painted_test_edge',color=(.6,.4,.2))
body=create_relief('PaintedBody',mesh,root,paint,edge)
add_boundary_finish(body,iterations=3,ratio=.45)
before=body.data.as_pointer();bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(dg)
data=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
try:
    bm=bmesh.new();bm.from_mesh(data);assert all(e.is_manifold for e in bm.edges)
    assert abs(bm.calc_volume(signed=True))>.01;bm.free()
    uv=data.uv_layers.get('UVMap');assert uv is not None
    painted=0
    for p in data.polygons:
        if p.material_index!=0:continue
        painted+=1;coords=[tuple(uv.data[i].uv) for i in p.loop_indices]
        area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(coords,coords[1:]+coords[:1])))/2
        assert area>1e-10
        assert all(0<=x<=1 for pair in coords for x in pair)
    assert painted>10
finally:ev.to_mesh_clear()
with tempfile.TemporaryDirectory(prefix='painted-real-export-') as folder:
    output=kit.core.export_asset_root(bpy.context,root,folder)[0];validate(Path(output))
assert body.data.as_pointer()==before and len(body.modifiers)==2
print('PAINTED RELIEF BLENDER OK: manifold finish, positive volume, generated UVs, runtime OBJ, source mesh preserved')
