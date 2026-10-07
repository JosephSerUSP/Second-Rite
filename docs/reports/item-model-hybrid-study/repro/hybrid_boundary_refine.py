"""Direct saved-source perimeter relaxation before surface projection."""
import bpy,json,hashlib
from pathlib import Path
source=Path('docs/reports/item-model-hybrid-study/source-project/assets/authoring/items').resolve();records=[]
for path in sorted(source.glob('*_conform.blend')):
 before=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path));root=bpy.data.objects['ITEM_'+path.stem]
 for ob in root.children_recursive:
  if not ob.name.startswith('PANEL_'):continue
  assert not ob.vertex_groups.get('Conformed silhouette boundary')
  edges={}
  for p in ob.data.polygons:
   ids=tuple(p.vertices)
   for a,b in zip(ids,ids[1:]+ids[:1]):key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
  group=ob.vertex_groups.new(name='Conformed silhouette boundary');group.add(sorted({v for e,c in edges.items() if c==1 for v in e}),1,'REPLACE')
  mod=ob.modifiers.new('Relax sampled panel boundary','SMOOTH');mod.vertex_group=group.name;mod.factor=.5;mod.iterations=3;ob.modifiers.move(len(ob.modifiers)-1,0)
 root['sr_panel_perimeter_edit']='Direct source: 3 iterations of live boundary-only relaxation before projection. Shape may shrink; native review and final UV/topology audit required.'
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path));records.append({'item':path.stem,'beforeSHA256':before,'afterSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'change':'live boundary-only relaxation before Shrinkwrap; no source mesh or PNG replacement'})
Path('out/work/hybrid-boundary-refinements.json').write_text(json.dumps(records,indent=2)+'\n')
