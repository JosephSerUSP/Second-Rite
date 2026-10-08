"""Edit the saved study to project mesh-conditioned paint in exact render framing."""
import bpy,json,hashlib,sys,shutil
from pathlib import Path
sys.path.insert(0,'tools/blender');import item_kit as kit
from view_projection import project_view,projection_material,visibility_tree
# HISTORICAL one-shot saved-source edit. Never rerun on the current source.
assert hashlib.sha256(Path('docs/reports/item-model-hybrid-study/revisions/view-projection/source-project/assets/authoring/items/carved_capsule_projected.blend').read_bytes()).hexdigest() == 'bade86208aab94ef2bc4e6a90761f27e33b150028056c2c2bee3b818b160508c', 'Historical input hash differs; edit the saved source directly instead of replaying surgery'
OUT=Path('docs/reports/item-model-hybrid-study/revisions/view-projection').resolve();SOURCE=OUT/'source-project/assets/authoring/items';TEX=SOURCE/'_textures';path=SOURCE/'carved_capsule_projected.blend';record=json.loads((OUT/'projection.json').read_text());shutil.copy2(path,Path('out/work/projection-original-rejected.blend'))
for name in ['mesh-paint-v2.png','fixed-mesh-support.png']:shutil.copy2(OUT/name,TEX/name)
bpy.ops.wm.open_mainfile(filepath=str(path));root=bpy.data.objects['ITEM_carved_capsule_projected'];ob=bpy.data.objects['BakedAssembly'];scene=bpy.context.scene;scene.render.resolution_x=scene.render.resolution_y=512;scene.render.resolution_percentage=100;scene.render.pixel_aspect_x=scene.render.pixel_aspect_y=1
paint=bpy.data.images.load(str(TEX/'mesh-paint-v2.png'));mask=bpy.data.images.load(str(TEX/'fixed-mesh-support.png'));fallback=bpy.data.images.load(str(TEX/'hybrid_surface_atlas.png'));paint.use_fake_user=True;mask.use_fake_user=True;fallback.use_fake_user=True
size=tuple(paint.size);w,h=size;tree=visibility_tree(ob);views=[]
for i,old in enumerate(record['views']):
 camera=bpy.data.objects['PROJECTION_'+old['name']];camera.data.ortho_scale=4.0;x=(i%2)*w/2;y=(i//2)*h/2;panel=(x,y,x+w/2,y+h/2)
 view=project_view(ob,scene,camera,name=old['name'],image_size=size,rectangle=panel,clip=panel,tree=tree,update=True,fit_bounds=False);views.append(view)
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.device='CPU';scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=True;scene.render.bake.margin=4;scene.render.bake.margin_type='EXTEND';scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;ob.data.uv_layers.active=ob.data.uv_layers['BakedUV'];ob.data.uv_layers['BakedUV'].active_render=True
bakes=[]
for stem,selection in [('mesh_projection_single',views[:1]),('mesh_projection_multi',views)]:
 recipe,control=projection_material(stem+'_recipe',paint,selection,fallback,power=6,mask_image=mask);ob.data.materials.clear();ob.data.materials.append(recipe)
 for poly in ob.data.polygons:poly.material_index=0
 for coverage in [False,True]:
  name=stem+('_coverage' if coverage else '');image=bpy.data.images.new(name,width=1536,height=1536,alpha=False);image.colorspace_settings.name='sRGB';image.filepath_raw=str(TEX/(name+'.png'));image.file_format='PNG';control.inputs[0].default_value=float(coverage)
  nodes=recipe.node_tree.nodes
  for n in nodes:n.select=False
  target=nodes.new('ShaderNodeTexImage');target.image=image;target.select=True;nodes.active=target
  bpy.ops.object.bake(type='EMIT');image.save();bakes.append({'name':name,'sha256':hashlib.sha256(Path(image.filepath_raw).read_bytes()).hexdigest()});print('BAKED',name,flush=True)
 control.inputs[0].default_value=0
final=kit.material('carved_capsule_mesh_projected_surface',image=TEX/'mesh_projection_multi.png',passes=[{'uvSource':'uv','blend':'add','strength':.16,'texture':'assets/models/items/mesh_projection_multi.png'}]);ob.data.materials.clear();ob.data.materials.append(final)
for p in ob.data.polygons:p.material_index=0
for old in ['projection_single_recipe','projection_multi_recipe','carved_capsule_projected_surface']:
 mat=bpy.data.materials.get(old)
 if mat:bpy.data.materials.remove(mat)
for image in bpy.data.images:
 if image.source=='FILE':image.filepath='//_textures/'+Path(image.filepath).name
root['sr_projection_views']=json.dumps(views);root['sr_projection_boundary']='Paintovers of actual saved-mesh renders; fixed camera framing, no silhouette fitting. First transparent paintover rejected for drift. Second opaque plate has estimated silhouette overlap 96-98 percent; internal semantic correspondence still requires visual review.';root['sr_reference_role']='Original different-shape concept is art direction only; never final projection paint.'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path))
record['rejectedOriginalReferenceProjection']={'sourceSHA256':record['sourceSHA256'],'views':record['views'],'bakes':record['bakes'],'boundary':'Rejected by owner: source topology/shape does not correspond to the original image.'};record.update(views=views,bakes=bakes,sourceSHA256=hashlib.sha256(path.read_bytes()).hexdigest(),paintFile='mesh-paint-v2.png',paintSHA256=hashlib.sha256((TEX/'mesh-paint-v2.png').read_bytes()).hexdigest(),boundary=root['sr_projection_boundary']);(OUT/'projection.json').write_text(json.dumps(record,indent=2)+'\n');print('MESH-CONDITIONED PROJECTION SAVED')
