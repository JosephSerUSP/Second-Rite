"""Read-only saved source audit. --render adds actual cardinal Workbench views."""
import bpy,bmesh,json,hashlib,sys
from pathlib import Path
from mathutils import Vector
render='--render' in sys.argv
source=Path('docs/reports/item-model-hybrid-study/source-project/assets/authoring/items').resolve()
out=Path('out/work/hybrid-source-views').resolve();out.mkdir(exist_ok=True)
records=[]
for path in sorted(source.glob('*.blend')):
 before=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
 root=bpy.data.objects['ITEM_'+path.stem];points=[];objects=[]
 for ob in root.children_recursive:
  if ob.type not in ['MESH','CURVE'] or ob.hide_render:continue
  ev=ob.evaluated_get(dg);mesh=ev.to_mesh();bm=bmesh.new();bm.from_mesh(mesh)
  raw=sum(not e.is_manifold for e in bm.edges);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
  bad=sum(not e.is_manifold for e in bm.edges);volume=bm.calc_volume(signed=True)
  objects.append({'name':ob.name,'faces':len(mesh.polygons),'smoothFaces':sum(p.use_smooth for p in mesh.polygons),'rawNonmanifold':raw,'weldedNonmanifold':bad,'signedVolume':volume,'modifiers':[{'type':m.type,'name':m.name,'emptyGroup':m.type=='NODES' and m.node_group is None} for m in ob.modifiers]})
  points += [ev.matrix_world@v.co for v in mesh.vertices];bm.free();ev.to_mesh_clear()
 lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)]);dims=list(hi-lo)
 record={'item':path.stem,'sourceHash':before,'objects':objects,'boundsMin':list(lo),'boundsMax':list(hi),'dimensions':dims,'images':[i.filepath for i in bpy.data.images if i.source=='FILE'],'rootScale':list(root.scale),'metadata':{k:root[k] for k in root.keys()}}
 records.append(record);print('SOURCE AUDIT',path.stem,dims,[(o['name'],o['weldedNonmanifold'],round(o['signedVolume'],6)) for o in objects if o['weldedNonmanifold'] or o['signedVolume']<=0])
 if render:
  target=(hi+lo)/2;scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='TEXTURE';scene.display.shading.light='FLAT'
  scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.show_specular_highlight=False;scene.render.film_transparent=True
  for mat in bpy.data.materials:
   if mat.use_nodes:
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    if bsdf and not bsdf.inputs['Base Color'].is_linked:mat.diffuse_color=bsdf.inputs['Base Color'].default_value
  scene.render.resolution_x=scene.render.resolution_y=512;scene.render.resolution_percentage=100
  cam=bpy.data.objects.new('READ_ONLY_CAMERA',bpy.data.cameras.new('READ_ONLY_CAMERA'));scene.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.ortho_scale=max(dims)*1.12;scene.camera=cam
  for name,offset in [('front',(0,-8,0)),('right',(8,0,0)),('back',(0,8,0)),('top',(0,0,8))]:
   cam.location=target+Vector(offset);cam.rotation_euler=(-Vector(offset)).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/f'{path.stem}-{name}.png');bpy.ops.render.render(write_still=True)
 assert before==hashlib.sha256(path.read_bytes()).hexdigest()
Path('out/work/hybrid-source-evidence.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
