"""Direct edits of six saved sources, not scaffold regeneration."""
import bpy,json,sys,hashlib
from pathlib import Path
sys.path.insert(0,'tools/blender');import item_kit as kit
source=Path('docs/reports/item-model-hybrid-study/source-project/assets/authoring/items').resolve()
colours=json.loads(Path('out/work/hybrid/plain-colours.json').read_text());records=[]
for path in sorted(source.glob('*.blend')):
 before=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path));root=bpy.data.objects['ITEM_'+path.stem];_,direction,route=path.stem.split('_');changes=[]
 for ob in root.children_recursive:
  if ob.type!='MESH':continue
  for mod in list(ob.modifiers):
   if mod.type=='NODES' and mod.node_group is None:ob.modifiers.remove(mod);changes.append(ob.name+': removed redundant empty projection modifier')
  if ob.name=='CORE_OrganicVolume' and route!='sdf':
   # Loft sides interpolate; authored top/bottom cap planes stay flat.
   for p in ob.data.polygons:p.use_smooth=len(p.vertices)==4
   changes.append(ob.name+': smooth loft walls, flat cap planes')
  if ob.name.startswith('PANEL_'):
   edge=kit.material(path.stem+'_edge',color=colours[direction+'_spine'],passes=[{'uvSource':'sphere','blend':'add','strength':.10,'texture':'assets/models/matcaps/steel.png'}] if direction=='salvage' else None)
   edge['sr_plain_region_colour']=direction+'_spine';ob.data.materials[1]=edge
   changes.append(ob.name+': plain back/rim colour from spine allocation mean times 1.16, no UV texture')
 root['sr_source_refinement']='Direct saved-source edits: smooth loft walls, plain conformed cut rims, redundant empty hull modifier removed'
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path))
 records.append({'item':path.stem,'beforeSHA256':before,'afterSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'changes':changes})
Path('out/work/hybrid-refinements.json').write_text(json.dumps(records,indent=2)+'\n');print('DIRECT HYBRID SOURCE REFINEMENTS OK')
