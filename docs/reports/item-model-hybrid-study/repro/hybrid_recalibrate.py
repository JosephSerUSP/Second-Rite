"""Direct root-scale correction after live perimeter relaxation."""
import bpy,json,hashlib
from pathlib import Path
source=Path('docs/reports/item-model-hybrid-study/source-project/assets/authoring/items').resolve();cal=json.loads(Path('out/work/hybrid/calibration.json').read_text());records=[]
for path in sorted(source.glob('*_conform.blend')):
 before=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path));root=bpy.data.objects['ITEM_'+path.stem];bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();pts=[]
 for ob in root.children_recursive:
  if ob.hide_render or ob.type!='MESH':continue
  ev=ob.evaluated_get(dg);data=ev.to_mesh();pts.extend(ev.matrix_world@v.co for v in data.vertices);ev.to_mesh_clear()
 spans=[max(p[i] for p in pts)-min(p[i] for p in pts) for i in range(3)];direction=path.stem.split('_')[1];target=cal[direction]['targetDimensions'];old=list(root.scale)
 root.scale=tuple(root.scale[i]*target[i]/spans[i] for i in range(3));root['sr_final_dimension_fit']='Direct root adjustment after perimeter smoothing to match shared front/right bounding dimensions; no per-vertex reconstruction.'
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path));records.append({'item':path.stem,'beforeSHA256':before,'afterSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'oldRootScale':old,'newRootScale':list(root.scale),'beforeDimensions':spans,'targetDimensions':target})
Path('out/work/hybrid-dimension-refinements.json').write_text(json.dumps(records,indent=2)+'\n')
