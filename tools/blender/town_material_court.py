"""Render the level-camera material micro-gauntlet at native town scale."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; PROJECT=ROOT/'projects'/'hichaukitoden-game'; sys.path.insert(0,str(ROOT/'tools'/'blender'))
def main():
 import bpy; import thestra_camera
 bpy.ops.wm.read_factory_settings(use_empty=True); s=bpy.context.scene; s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True;s.render.resolution_x=426;s.render.resolution_y=240;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('court');s.world.color=(.02,.025,.04)
 def m(n,c,rough=.8):
  x=bpy.data.materials.new(n);x.use_nodes=True;b=x.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*c,1);b.inputs['Roughness'].default_value=rough;noise=x.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=8;noise.inputs['Detail'].default_value=5;bump=x.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.25;x.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);x.node_tree.links.new(bump.outputs['Normal'],b.inputs['Normal']);return x
 def pbr(n,base,rough,height):
  x=m(n,(.45,.32,.2));nd=x.node_tree.nodes;lk=x.node_tree.links; b=nd['Principled BSDF'];co=nd.new('ShaderNodeTexCoord')
  for label,path,slot,cs in [('albedo',base,'Base Color','sRGB'),('roughness',rough,'Roughness','Non-Color')]:
   im=bpy.data.images.load(str(path));im.colorspace_settings.name=cs;z=nd.new('ShaderNodeTexImage');z.label=label;z.image=im;lk.new(co.outputs['Generated'],z.inputs['Vector']);lk.new(z.outputs['Color'],b.inputs[slot])
  im=bpy.data.images.load(str(height));im.colorspace_settings.name='Non-Color';z=nd.new('ShaderNodeTexImage');z.image=im;bu=nd.new('ShaderNodeBump');bu.inputs['Strength'].default_value=.18;lk.new(co.outputs['Generated'],z.inputs['Vector']);lk.new(z.outputs['Color'],bu.inputs['Height']);lk.new(bu.outputs['Normal'],b.inputs['Normal']);return x
 def box(n,p,size,mat):
  bpy.ops.mesh.primitive_cube_add(location=p);o=bpy.context.object;o.name=n;o.scale=tuple(q/2 for q in size);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);return o
 src=PROJECT/'assets'/'authoring'/'town'/'material-sources'; proc=m('A procedural limestone',(.44,.26,.14)); pub=pbr('B PolyHaven Cobblestone',src/'polyhaven-cobblestone-01/cobblestone_01_diff_1k.jpg',src/'polyhaven-cobblestone-01/cobblestone_01_rough_1k.jpg',src/'polyhaven-cobblestone-01/cobblestone_01_disp_1k.jpg'); gen=pbr('C OpenAI limestone',src/'generated-limestone-albedo.png',src/'generated-limestone-roughness.png',src/'generated-limestone-height.png')
 mats=[proc,pub,gen];ys=(4.05,5.5,6.95)
 for i,(mat,y) in enumerate(zip(mats,ys)):
  box(('A procedural','B PolyHaven CC0','C OpenAI source')[i],(8.5,y,.25),(.5,1.12,3.5),mat);box('plinth',(7.55,y,-1.25),(1.8,1.16,.35),mat)
 # remaining representative source surfaces; their node recipes use the same procedural family.
 for i,(name,c) in enumerate([('stucco',(.5,.30,.2)),('aged wood',(.12,.045,.015)),('roof tile',(.28,.05,.02)),('metal fixture',(.06,.09,.1))]):
  box(name,(6.1,4.15+i*.9,-.4),(.42,.58,1.45),m(name,c,.45 if name=='metal fixture' else .82))
 bpy.ops.object.light_add(type='AREA',location=(4.0,5.5,4));l=bpy.context.object;l.data.energy=900;l.data.size=5;l.data.color=(1,.42,.18)
 bpy.ops.object.light_add(type='AREA',location=(6,8,2));l=bpy.context.object;l.data.energy=260;l.data.size=3;l.data.color=(.2,.35,1)
 cal=json.loads(Path(os.environ['THESTRA_TOWN_CAMERA_CALIBRATION']).read_text()); thestra_camera.create_or_update_camera(cal,scene=s,make_active=True)
 out=PROJECT/'assets'/'authoring'/'town'/'town-material-gauntlet-contact-sheet.png';s.render.filepath=str(out);s.render.image_settings.file_format='PNG';bpy.ops.render.render(write_still=True);print(out)
if __name__=='__main__':main()
