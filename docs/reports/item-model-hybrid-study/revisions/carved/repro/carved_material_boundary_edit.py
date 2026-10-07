import bpy,json,hashlib
from pathlib import Path
p=Path('docs/reports/item-model-hybrid-study/revisions/carved/source-project/assets/authoring/items/carved_capsule_baked.blend').resolve();bpy.ops.wm.open_mainfile(filepath=str(p));root=bpy.data.objects['ITEM_carved_capsule_baked']
for mat in bpy.data.materials:
 if mat.name.startswith('hybrid_carved_hull_') or mat.name=='carved_revision_thread':mat.use_fake_user=True
for ob in root.children_recursive:
 if ob.hide_render and ob.type=='MESH':ob.data.materials.clear()
root['sr_control_material_boundary']='Nonrendering historical mask/cutter controls have no export material slots; procedural bake node graphs retained as fake-user material recipes.'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(p))
record=p.parents[4]/'surface-bake.json';d=json.loads(record.read_text());d['sourceSHA256']=hashlib.sha256(p.read_bytes()).hexdigest();record.write_text(json.dumps(d,indent=2)+'\n')
