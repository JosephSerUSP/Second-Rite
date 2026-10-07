"""Read-only evaluated geometry/UV continuity and actual orthographic source captures."""
import bpy,bmesh,json,hashlib,sys,math
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
source=Path('projects/hichaukitoden-game/assets/authoring/items').resolve();out=Path('out/work/staves-source-views').resolve();out.mkdir(exist_ok=True)
records=[]
for stem in ('silver_rod', 'mage_staff', 'sage_staff', 'ether_staff', 'war_staff', 'healing_staff'):
 path=source/f'{stem}.blend';before=hashlib.sha256(path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
 root=bpy.data.objects['ITEM_'+stem];objects=[];points=[]
 for ob in root.children_recursive:
  if ob.type not in ('MESH','CURVE') or ob.hide_render:continue
  ev=ob.evaluated_get(dg);mesh=ev.to_mesh();bm=bmesh.new();bm.from_mesh(mesh)
  raw_bad=sum(not e.is_manifold for e in bm.edges)
  # Curve conversion duplicates cap vertices for normals. Weld this AUDIT COPY
  # by position before diagnosing an actual geometric opening; never save it.
  bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
  bad=sum(not e.is_manifold for e in bm.edges);volume=bm.calc_volume(signed=True)
  assert bad==0 and abs(volume)>1e-8,(stem,ob.name,bad,volume)
  objects.append({'name':ob.name,'type':ob.type,'modifiers':[m.type for m in ob.modifiers],
   'faces':len(mesh.polygons),'smoothFaces':sum(p.use_smooth for p in mesh.polygons),'rawNonmanifoldEdges':raw_bad,
   'positionWeldedAuditNonmanifoldEdges':bad,'signedVolume':volume})
  points += [ob.matrix_world@v.co for v in mesh.vertices];bm.free();ev.to_mesh_clear()
 lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)]);target=(lo+hi)/2;scale=max(hi-lo)*1.12
 scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='TEXTURE';scene.display.shading.light='FLAT'
 scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
 # Workbench ignores BSDF for untextured materials; mirror authored Base Color
 # into its display colour in memory ONLY. Runtime captures remain separate.
 for material in bpy.data.materials:
  if material.use_nodes:
   bsdf=material.node_tree.nodes.get('Principled BSDF')
   if bsdf and not bsdf.inputs['Base Color'].is_linked:material.diffuse_color=bsdf.inputs['Base Color'].default_value
 scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.show_specular_highlight=False;scene.render.film_transparent=True
 scene.render.resolution_x=scene.render.resolution_y=512;scene.render.resolution_percentage=100
 cam=bpy.data.objects.new('READ_ONLY_PROOF_CAMERA',bpy.data.cameras.new('READ_ONLY_PROOF_CAMERA'));scene.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.ortho_scale=scale;scene.camera=cam
 for name,offset in [('front',(0,-8,0)),('right',(8,0,0)),('back',(0,8,0)),('top',(0,0,8))]:
  cam.location=target+Vector(offset);cam.rotation_euler=(-Vector(offset)).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/f'{stem}-{name}.png');bpy.ops.render.render(write_still=True)
 assert before==hashlib.sha256(path.read_bytes()).hexdigest()
 records.append({'item':stem,'sourceHash':before,'objects':objects,'boundsMin':list(lo),'boundsMax':list(hi),
  'metadata':{k:root[k] for k in root.keys()}})
Path('out/work/staves-source-evidence.json').write_text(json.dumps(records,indent=2)+'\n')
print('ACTUAL SOURCE PROOF OK: evaluated components closed; source hashes unchanged; Workbench not runtime')
