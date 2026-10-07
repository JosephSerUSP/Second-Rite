"""Directly author and bake the saved carved study. Refuses repeating finalization."""
import bpy,bmesh,json,sys,hashlib,math
from pathlib import Path
sys.path.insert(0,'tools/blender')
import item_kit as kit
from atlas_allocation import pack,uv_islands
from surface_finishes import linear
BASE=Path('docs/reports/item-model-hybrid-study').resolve();OUT=BASE/'revisions/carved';SOURCE=OUT/'source-project/assets/authoring/items';path=SOURCE/'carved_capsule_baked.blend'
bpy.ops.wm.open_mainfile(filepath=str(path));root=bpy.data.objects['ITEM_carved_capsule_baked'];assert not root.get('sr_baked_surface_revision'),'Edit existing finalized source explicitly'
geometry=SOURCE/'carved_capsule_geometry.blend';geometry_hash=hashlib.sha256(geometry.read_bytes()).hexdigest()
# Resolve only the saved source, with every visible member retained.
visible=[o for o in root.children_recursive if o.type=='MESH' and not o.hide_render]
bpy.ops.object.select_all(action='DESELECT')
for ob in visible:
 ob.select_set(True);bpy.context.view_layer.objects.active=ob
 if ob.data.users>1:ob.data=ob.data.copy()
 for mod in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
 ob.data.uv_layers.active.name='OriginalUV'
bpy.context.view_layer.objects.active=visible[0];bpy.ops.object.join();assembly=bpy.context.object;assembly.name='BakedAssembly'
mesh=assembly.data;original=mesh.uv_layers.get('OriginalUV');assert original
# Original bitmap charts remain explicit shader inputs. New bake UVs are unique.
layer=mesh.uv_layers.new(name='BakedUV');mesh.uv_layers.active=layer;layer.active_render=True
pack(assembly,1536,gutter_texels=8)
mesh=assembly.data;layer=mesh.uv_layers.active
for p in mesh.polygons:
 coords=[tuple(layer.data[i].uv) for i in p.loop_indices]
 area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(coords,coords[1:]+coords[:1])))*.5
 assert area>1e-12,(p.index,area)
 assert all(-1e-5<=v<=1.00001 for uv in coords for v in uv)
# Procedural albedo has role-specific features, rather than a uniform grain.
AO_CONTROLS=[];surface_roles=[]
for mat in assembly.data.materials:
 role=mat.name.rsplit('_',1)[-1];surface_roles.append(role)
 mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links
 tex=next((n for n in nodes if n.type=='TEX_IMAGE'),None)
 uv=nodes.new('ShaderNodeUVMap');uv.uv_map='OriginalUV'
 if tex:links.new(uv.outputs['UV'],tex.inputs['Vector'])
 pos=nodes.new('ShaderNodeNewGeometry')
 def scale(vector,factors):
  n=nodes.new('ShaderNodeVectorMath');n.operation='MULTIPLY';n.inputs[1].default_value=factors;links.new(vector,n.inputs[0]);return n.outputs['Vector']
 def noise(vector,amount):
  n=nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=amount;n.inputs['Detail'].default_value=3;links.new(vector,n.inputs['Vector']);return n.outputs['Fac']
 def mathnode(op,a,b):
  n=nodes.new('ShaderNodeMath');n.operation=op
  for i,v in enumerate([a,b]):
   if isinstance(v,(int,float)):n.inputs[i].default_value=v
   else:links.new(v,n.inputs[i])
  return n.outputs[0]
 def ramp(value,stops):
  n=nodes.new('ShaderNodeValToRGB');r=n.color_ramp;r.elements.remove(r.elements[1])
  for i,(at,col) in enumerate(stops):
   e=r.elements[0] if i==0 else r.elements.new(at);e.position=at;e.color=(*linear(col),1)
  links.new(value,n.inputs[0]);return n.outputs['Color']
 def multiply(a,b):
  n=nodes.new('ShaderNodeMixRGB');n.blend_type='MULTIPLY';n.inputs[0].default_value=1
  for i,v in enumerate([a,b]):
   if isinstance(v,tuple):n.inputs[i+1].default_value=(*v,1)
   else:links.new(v,n.inputs[i+1])
  return n.outputs[0]
 if role=='outer':
  pores=nodes.new('ShaderNodeTexVoronoi');pores.feature='F1';pores.distance='EUCLIDEAN';pores.inputs['Scale'].default_value=18;links.new(pos.outputs['Position'],pores.inputs['Vector'])
  colour=ramp(pores.outputs['Distance'],[(0,(.28,.16,.07)),(.10,(.52,.34,.16)),(.21,(.92,.82,.61)),(.6,(1,.92,.75))])
  mineral=ramp(noise(pos.outputs['Position'],5),[(.25,(.54,.40,.25)),(.48,(.93,.82,.61)),(.7,(1,1,.9))]);colour=multiply(colour,mineral)
 elif role=='core':
  veins=nodes.new('ShaderNodeTexVoronoi');veins.feature='DISTANCE_TO_EDGE';veins.inputs['Scale'].default_value=6;links.new(pos.outputs['Position'],veins.inputs['Vector'])
  colour=ramp(veins.outputs['Distance'],[(0,(.20,.044,.025)),(.027,(.46,.12,.055)),(.08,(.83,.34,.17)),(.2,(1,.53,.29))])
  flesh=ramp(noise(pos.outputs['Position'],14),[(.25,(.60,.31,.21)),(.52,(1,.93,.84)),(.75,(1,1,.9))]);colour=multiply(colour,flesh)
 elif role=='spine':
  grain=noise(scale(pos.outputs['Position'],(2,12,.4)),5)
  colour=ramp(grain,[(.23,(.10,.05,.025)),(.42,(.32,.17,.072)),(.6,(.62,.40,.19)),(.8,(.78,.59,.33))])
 elif role=='binding':
  grain=noise(pos.outputs['Position'],18)
  colour=ramp(grain,[(.18,(.045,.11,.18)),(.43,(.10,.23,.37)),(.65,(.26,.40,.56)),(.85,(.41,.56,.67))])
  # Subtle original woven variation survives alongside deliberate broad dye structure.
  if tex:colour=multiply(colour,ramp(noise(pos.outputs['Position'],55),[(.25,(.7,.7,.7)),(.7,(1,1,1))]))
 else:
  rgb=mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value[:3];colour=tuple(rgb)
 ao=nodes.new('ShaderNodeAmbientOcclusion');ao.samples=32;ao.inputs['Distance'].default_value=.34;ao.inside=False;ao.only_local=False
 shadow=mathnode('ADD',mathnode('MULTIPLY',ao.outputs['AO'],.68),.32)
 control=nodes.new('ShaderNodeMixRGB');control.blend_type='MULTIPLY';control.inputs[0].default_value=0
 if isinstance(colour,tuple):control.inputs[1].default_value=(*colour,1)
 else:links.new(colour,control.inputs[1])
 links.new(shadow,control.inputs[2]);AO_CONTROLS.append(control)
 emission=nodes.new('ShaderNodeEmission');links.new(control.outputs[0],emission.inputs['Color']);emission.inputs['Strength'].default_value=1
 output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');links.new(emission.outputs[0],output.inputs['Surface'])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.device='CPU';scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=4;scene.render.bake.margin_type='EXTEND';scene.render.bake.use_clear=True
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
textures=SOURCE/'_textures';textures.mkdir(exist_ok=True);results=[]
for name,ao_strength in [('carved_features',0),('carved_baked',1)]:
 for c in AO_CONTROLS:c.inputs[0].default_value=ao_strength
 image=bpy.data.images.new(name,width=1536,height=1536,alpha=False);image.colorspace_settings.name='sRGB';image.filepath_raw=str(textures/(name+'.png'));image.file_format='PNG'
 for mat in assembly.data.materials:
  nodes=mat.node_tree.nodes
  for n in nodes:n.select=False
  target=nodes.new('ShaderNodeTexImage');target.image=image;target.select=True;nodes.active=target
 bpy.ops.object.select_all(action='DESELECT');assembly.select_set(True);bpy.context.view_layer.objects.active=assembly
 bpy.ops.object.bake(type='EMIT');image.save();results.append({'name':name,'sha256':hashlib.sha256(Path(image.filepath_raw).read_bytes()).hexdigest()});print('BAKED',name,flush=True)
# Exportable material reads only the finalized RGB bitmap and unique UV map.
final=kit.material('carved_capsule_baked_surface',image=textures/'carved_baked.png',passes=[{'uvSource':'uv','blend':'add','strength':.16,'texture':'assets/models/items/carved_baked.png'}])
assembly.data.materials.clear();assembly.data.materials.append(final)
for p in assembly.data.polygons:p.material_index=0
for image in bpy.data.images:
 if image.source=='FILE' and Path(image.filepath).name in ['hybrid_surface_atlas.png','carved_baked.png','carved_features.png']:image.filepath='//_textures/'+Path(image.filepath).name
root['sr_baked_surface_revision']='1536 unique UVs, material-specific pores/veins/grain/dye; Cycles EMIT albedo plus directionless contact AO. Final mesh editable; old graphs retained in original study.'
root['sr_geometry_control_sha256']=geometry_hash;root['sr_bake_distance']=.34;root['sr_bake_occlusion_floor']=.32
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path))
assert geometry_hash==hashlib.sha256(geometry.read_bytes()).hexdigest()
(OUT/'surface-bake.json').write_text(json.dumps({'geometrySourceSHA256':geometry_hash,'sourceSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'atlasSize':1536,'packingGutterTexels':8,'dilationTexels':4,'faces':len(mesh.polygons),'vertices':len(mesh.vertices),'uvCharts':len(set(uv_islands(mesh))),'surfaceRoles':surface_roles,'bakes':results,'method':'Cycles EMIT, CPU, 32 samples. Feature albedo and feature albedo multiplied by 0.32+0.68*AO(distance 0.34). No directional key light baked.'},indent=2)+'\n')
print('SURFACE REVISION SAVED')
