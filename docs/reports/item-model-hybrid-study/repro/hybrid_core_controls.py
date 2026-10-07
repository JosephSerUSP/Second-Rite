"""Disposable SDF-core ablation: keep exact assembly, return core to its saved loft."""
import bpy,json,hashlib,shutil
from pathlib import Path
source=Path('docs/reports/item-model-hybrid-study/source-project/assets/authoring/items').resolve();dest=Path('out/work/hybrid-core-control/assets/authoring/items').resolve();(dest/'_textures').mkdir(parents=True,exist_ok=True);shutil.copy2(source/'_textures/hybrid_surface_atlas.png',dest/'_textures/hybrid_surface_atlas.png');records=[]
def other_geometry(root):
 bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();result=[]
 for ob in root.children_recursive:
  if ob.hide_render or ob.type!='MESH' or ob.name=='CORE_OrganicVolume':continue
  ev=ob.evaluated_get(dg);m=ev.to_mesh();result.append((ob.name,[list(ev.matrix_world@v.co) for v in m.vertices],[list(p.vertices) for p in m.polygons],[p.use_smooth for p in m.polygons]));ev.to_mesh_clear()
 return result
for path in sorted(source.glob('*_sdf.blend')):
 before=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path));root=bpy.data.objects['ITEM_'+path.stem];assembly=other_geometry(root);core=bpy.data.objects['CORE_OrganicVolume']
 for m in list(core.modifiers):core.modifiers.remove(m)
 for p in core.data.polygons:p.use_smooth=len(p.vertices)==4
 assert assembly==other_geometry(root)
 root['sr_study_control']='Disposable SDF-core ablation: original saved loft + side smoothing, same assembly/root/palette; other evaluated geometry exactly unchanged'
 target=dest/path.name;assert not target.exists();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(target))
 assert before==hashlib.sha256(path.read_bytes()).hexdigest()
 records.append({'item':path.stem,'originalSHA256':before,'controlSHA256':hashlib.sha256(target.read_bytes()).hexdigest(),'otherEvaluatedGeometryIdentical':True,'boundary':'Core changes include geometry and its UV chart, not only triangle count. Source loft side normals deliberately smooth.'})
Path('out/work/hybrid-core-controls.json').write_text(json.dumps(records,indent=2)+'\n')
