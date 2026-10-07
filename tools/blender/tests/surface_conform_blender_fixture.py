"""Real Blender: conformance responds to target edits and retains UVs/thickness."""
from pathlib import Path
import sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bpy,bmesh
import item_kit as kit
from surface_conform_blender import conform_panel
root=kit.begin('conform_fixture','test','surface conformance fixture')
mat=kit.material('face');edge=kit.material('edge')
v,f,uv=kit.loft([{'z':-1,'a':1.5,'b':.6},{'z':1,'a':1.5,'b':.6}],samples=32)
guide=kit.mesh_object('body_guide',v,f,root,mat);guide.hide_render=True
mesh={'vertices':[(-.7,-1,-.5),(.7,-1,-.5),(.7,-1,.5),(-.7,-1,.5)],
 'faces':[(0,1,2,3)],'uvs':[[(.1,.2),(.8,.2),(.8,.9),(.1,.9)]],
 'materials':[0],'report':{'fixture':True}}
panel=conform_panel('panel',mesh,root,guide,mat,edge,thickness=.12,offset=.02,boundary_iterations=1)
try:conform_panel('panel',mesh,root,guide,mat,edge)
except ValueError:pass
else:raise AssertionError('existing panel was overwritten or its live group cleared')
root.location=(2,3,4)
def evaluated():
 bpy.context.view_layer.update();ev=panel.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ev.to_mesh()
 bm=bmesh.new();bm.from_mesh(data);assert all(e.is_manifold for e in bm.edges)
 assert abs(bm.calc_volume(signed=True))>.01;bm.free()
 result=[tuple(v.co) for v in data.vertices]
 assert data.uv_layers.active is not None and len(data.polygons)==6
 assert all(p.use_smooth==(p.material_index==0) for p in data.polygons)
 ev.to_mesh_clear();return result
a=evaluated();assert max(p[1] for p in a)<-.4 and min(p[1] for p in a)>-.85,a
for vert in guide.data.vertices:vert.co.y*=.6
guide.data.update();guide.update_tag();b=evaluated()
assert all(abs(x-y)<1e-6 for pa,pb in zip(a,b) for x,y in ((pa[0],pb[0]),(pa[2],pb[2])))
assert all(pb[1]>pa[1]+.15 for pa,pb in zip(a,b)),(a,b)
assert [tuple(d.uv) for d in panel.data.uv_layers.active.data]==[(.1,.2),(.8,.2),(.8,.9),(.1,.9)] or all(abs(x-y)<1e-6 for pair,want in zip(panel.data.uv_layers.active.data,mesh['uvs'][0]) for x,y in zip(pair.uv,want))
from validate_item_obj_runtime import validate
pointer=panel.data.as_pointer()
with tempfile.TemporaryDirectory(prefix='conform-real-export-') as folder:
 output=Path(kit.core.export_asset_root(bpy.context,root,folder)[0]);validate(output)
 points=[tuple(map(float,l.split()[1:4])) for l in output.read_text().splitlines() if l.startswith('v ')]
 # Export maps Blender XYZ to XZ-Y. Root translation is removed; hidden
 # guide must follow the duplicate root so projection reaches the same surface.
 wanted=[(x,z,-y) for x,y,z in b]
 assert len(points)==len(wanted),(points,wanted)
 assert all(any(max(abs(x-y) for x,y in zip(p,w))<2e-6 for p in points) for w in wanted),(points,wanted)
assert panel.data.as_pointer()==pointer and next(m for m in panel.modifiers if m.type=='SHRINKWRAP').target==guide
assert panel.modifiers[0].type=='SMOOTH' and panel.modifiers[1].type=='SHRINKWRAP'
flat_panel=conform_panel('flat_panel',mesh,root,guide,mat,edge,smooth=False)
bpy.context.view_layer.update();ev=flat_panel.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ev.to_mesh()
assert all(not p.use_smooth for p in data.polygons);ev.to_mesh_clear()
for value in (-1,21,True,1.5):
 try:conform_panel('bad_boundary',mesh,root,guide,mat,edge,boundary_iterations=value)
 except ValueError:pass
 else:raise AssertionError('invalid boundary control accepted')
bad=kit.mesh_object('unowned',v,f,None,mat)
try:conform_panel('bad',mesh,root,bad,mat,edge)
except ValueError:pass
else:raise AssertionError('unowned target accepted')
edge['sr_runtime_passes_json']='[{"uvSource":"uv"}]'
try:conform_panel('bad_uv_edge',mesh,root,guide,mat,edge)
except ValueError:pass
else:raise AssertionError('UV-dependent cut rim accepted')
edge['sr_runtime_passes_json']='[]'
edge.node_tree.nodes.new('ShaderNodeTexImage')
try:conform_panel('bad_image_edge',mesh,root,guide,mat,edge)
except ValueError:pass
else:raise AssertionError('painted cut rim accepted')
print('SURFACE CONFORMANCE FIXTURE OK: target response, closed thickness, unchanged X/Z and source UVs')
