"""Direct saved-source edits: exported-precision tip weld and measured Y depth."""
import bpy,bmesh,json,hashlib,shutil
from pathlib import Path
from mathutils import Vector
p=Path('out/work/staves');source=Path('projects/hichaukitoden-game/assets/authoring/items');cal=json.loads((p/'calibration.json').read_text());evidence=json.loads(Path('out/work/staves-source-evidence.json').read_text())
records=[]
for r in evidence:
 stem=r['item'];path=(source/(stem+'.blend')).resolve();backup=p/(stem+'-before-depth-edit.blend');assert not backup.exists();shutil.copy2(path,backup)
 before=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path));root=bpy.data.objects['ITEM_'+stem];repairs=[]
 if stem=='ether_staff':
  for name in ('E_OuterCrescentWithBrassDepth','F_InnerOpposingCrescent'):
   ob=bpy.data.objects[name];count=len(ob.data.vertices);old=[v.co.copy() for v in ob.data.vertices]
   bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
   assert all(e.is_manifold for e in bm.edges);bm.to_mesh(ob.data);bm.free();ob.data.update()
   delta=max(min((v.co-v0).length for v0 in old) for v in ob.data.vertices);assert delta<1e-6
   ob.data.calc_loop_triangles()
   for t in ob.data.loop_triangles:
    a,b,c=[Vector(tuple(round(v,6) for v in ob.data.vertices[i].co)) for i in t.vertices];assert (b-a).cross(c-a).length>1e-9,(name,t.vertices)
   for uv in ob.data.uv_layers.active.data:uv.uv=tuple(round(c,6) for c in uv.uv)
   repairs.append({'object':name,'verticesBefore':count,'verticesAfter':len(ob.data.vertices),'maxRemainingVertexDisplacement':delta})
 height=r['boundsMax'][2]-r['boundsMin'][2];depth=r['boundsMax'][1]-r['boundsMin'][1];target=height*cal['items'][stem]['sideWidthHeightRatio'];factor=target/depth
 assert .7<factor<1.7,(stem,factor)
 root.scale.y=factor
 root['sr_saved_depth_adjustment']=json.dumps({'method':'World-Y root scale toward independently measured right-view main-body bounds; front X/Z preserved','factor':factor,'initialDepth':depth,'targetDepth':target,'height':height,'boundary':'Right silhouette includes attachments and generated views differ; this is a proportion target, not a depth scan. Initial profiles/path metadata are provenance; source geometry and transform remain authority.'})
 if repairs:root['sr_precision_repair']=json.dumps(repairs)
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path))
 records.append({'item':stem,'beforeSHA256':before,'afterSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'worldYFactor':factor,'targetDepth':target,'height':height,'frontXZPreserved':True,'tipRepairs':repairs})
Path('out/work/staves-source-refinements.json').write_text(json.dumps(records,indent=2)+'\n');print('SAVED SOURCE DEPTH/EXPORTED-PRECISION EDITS OK',json.dumps(records))
