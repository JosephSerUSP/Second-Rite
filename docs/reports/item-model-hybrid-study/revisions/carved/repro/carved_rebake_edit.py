"""Rebake the edited saved UV mesh using its retained material recipes."""
import bpy,json,sys,hashlib,collections
from pathlib import Path
BASE=Path('docs/reports/item-model-hybrid-study').resolve();OUT=BASE/'revisions/carved';SOURCE=OUT/'source-project/assets/authoring/items';p=SOURCE/'carved_capsule_baked.blend'
bpy.ops.wm.open_mainfile(filepath=str(p));root=bpy.data.objects['ITEM_carved_capsule_baked'];ob=bpy.data.objects['BakedAssembly'];mesh=ob.data;uv=mesh.uv_layers['OriginalUV']
layout=json.loads((BASE/'actual-layout.json').read_text());W,H=layout['imageSize'];rects={k.removeprefix('carved_'):(v['pixels'][0]/W,1-v['pixels'][3]/H,v['pixels'][2]/W,1-v['pixels'][1]/H) for k,v in layout['regions'].items() if k.startswith('carved_')}
# Vertex-connected components retain each physical material; tiny 12-vertex
# tubes are the stitched threads. Other components vote using original UVs.
adj=[[] for v in mesh.vertices]
for edge in mesh.edges:
 a,b=edge.vertices;adj[a].append(b);adj[b].append(a)
unseen=set(range(len(mesh.vertices)));vertex_role={};components=[]
while unseen:
 start=unseen.pop();group=[start];queue=[start]
 while queue:
  v=queue.pop()
  for j in adj[v]:
   if j in unseen:unseen.remove(j);group.append(j);queue.append(j)
 polys=[poly for poly in mesh.polygons if poly.vertices[0] in group];votes=collections.Counter()
 for poly in polys:
  u=sum(uv.data[li].uv.x for li in poly.loop_indices)/len(poly.loop_indices);v=sum(uv.data[li].uv.y for li in poly.loop_indices)/len(poly.loop_indices)
  for role,(u0,v0,u1,v1) in rects.items():
   if u0<=u<=u1 and v0<=v<=v1:votes[role]+=1
 role='thread' if len(group)==12 else votes.most_common(1)[0][0]
 components.append({'vertices':len(group),'faces':len(polys),'role':role,'votes':dict(votes)})
 for i in group:vertex_role[i]=role
roles=['outer','core','binding','spine','thread'];recipes=[bpy.data.materials['carved_revision_thread' if r=='thread' else 'hybrid_carved_hull_'+r] for r in roles];final=mesh.materials[0];mesh.materials.clear()
for mat in recipes:mesh.materials.append(mat)
for poly in mesh.polygons:poly.material_index=roles.index(vertex_role[poly.vertices[0]])
controls=[]
for mat in recipes:
 emission=next(n for n in mat.node_tree.nodes if n.type=='EMISSION');controls.append(emission.inputs['Color'].links[0].from_node)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.device='CPU';scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=4;scene.render.bake.margin_type='EXTEND';scene.render.bake.use_clear=True
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;mesh.uv_layers.active=mesh.uv_layers['BakedUV'];mesh.uv_layers['BakedUV'].active_render=True
results=[]
for name,strength in [('carved_features',0),('carved_baked',1)]:
 for c in controls:c.inputs[0].default_value=strength
 filepath=SOURCE/'_textures'/(name+'.png');image=bpy.data.images.load(str(filepath),check_existing=True);image.filepath_raw=str(filepath);image.file_format='PNG'
 for mat in recipes:
  nodes=mat.node_tree.nodes
  for n in nodes:n.select=False
  target=nodes.new('ShaderNodeTexImage');target.image=image;target.select=True;nodes.active=target
 bpy.ops.object.bake(type='EMIT');image.save();results.append({'name':name,'sha256':hashlib.sha256(filepath.read_bytes()).hexdigest()});print('REBAKED',name,flush=True)
mesh.materials.clear();mesh.materials.append(final)
for poly in mesh.polygons:poly.material_index=0
for image in bpy.data.images:
 if image.source=='FILE':image.filepath='//_textures/'+Path(image.filepath).name
root['sr_geometry_control_sha256']=hashlib.sha256((SOURCE/'carved_capsule_geometry.blend').read_bytes()).hexdigest();root['sr_bake_recipe_components']=json.dumps(components)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(p))
record=OUT/'surface-bake.json';d=json.loads(record.read_text());d.update(sourceSHA256=hashlib.sha256(p.read_bytes()).hexdigest(),geometrySourceSHA256=root['sr_geometry_control_sha256'],bakes=results,components=components);record.write_text(json.dumps(d,indent=2)+'\n')
print('EDITED SOURCE REBAKED')
