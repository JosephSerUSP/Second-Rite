import bpy, math, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'gauntlet'
CON=json.loads((ROOT/'contract.json').read_text())
PAL={
 'celina':{'skin':'C98D78','main':'273853','accent':'D9B55A','dark':'171827'},
 'agnes': {'skin':'925E4C','main':'A14A35','accent':'D5B25B','dark':'262432'},
 'gambler':{'skin':'D39A78','main':'4B2B63','accent':'2BA69A','dark':'201822'}}
def mat(n,h):
 m=bpy.data.materials.new(n); m.diffuse_color=tuple(int(h[i:i+2],16)/255 for i in (0,2,4))+(1,); m.use_nodes=True; m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=m.diffuse_color; m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.58; return m
def add(n,typ,loc,scale,ma,bevel=.08):
 getattr(bpy.ops.mesh,'primitive_'+typ+'_add')(location=loc); o=bpy.context.object; o.name=n; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(ma)
 if bevel and typ in ('cube','cylinder','uv_sphere'): mod=o.modifiers.new('soft','BEVEL');mod.width=bevel;mod.segments=3
 return o
def cone(n,loc,r1,r2,d,ma):
 bpy.ops.mesh.primitive_cone_add(vertices=12,radius1=r1,radius2=r2,depth=d,location=loc);o=bpy.context.object;o.name=n;o.data.materials.append(ma);return o
def character(kind):
 bpy.ops.object.empty_add(type='PLAIN_AXES',location=(0,0,0)); root=bpy.context.object;root.name=kind+'_RIG_ROOT'
 p=PAL[kind]; skin,main,acc,dark=[mat(kind+'_'+x,p[x]) for x in ('skin','main','accent','dark')]
 objs=[]
 def a(*x): objs.append(add(*x)); return objs[-1]
 # all forms intentionally designed as clean large sprite masses
 if kind=='celina':
  a('long_coat','cube',(0,.04,2.2),(.65,.32,1.55),main,.14); cone('skirt',(0,.02,.82),.88,.48,1.15,main); objs.append(bpy.context.object)
  a('collar','uv_sphere',(0,-.03,3.25),(.72,.34,.34),acc,.05); a('head','uv_sphere',(0,-.03,3.82),(.52,.42,.58),skin,.04)
  a('hair_cap','uv_sphere',(0,.02,4.1),(.58,.45,.48),dark,.05); a('eye_l','uv_sphere',(-.17,-.43,3.85),(.06,.025,.07),dark,.01);a('eye_r','uv_sphere',(.17,-.43,3.85),(.06,.025,.07),dark,.01);a('braid','cylinder',(.52,.08,3.48),(.12,.12,.78),dark,.05).rotation_euler[1]=-.28
  # restrained contained hands, vertical cane
  a('arm_l','cylinder',(-.67,-.04,2.42),(.16,.16,.78),main,.07).rotation_euler[1]=-.12; a('arm_r','cylinder',(.67,-.04,2.34),(.16,.16,.70),main,.07).rotation_euler[1]=.15
  a('hand_l','uv_sphere',(-.76,-.18,1.75),(.18,.13,.22),skin,.03); a('cane','cylinder',(.76,.08,1.5),(.06,.06,1.55),acc,.03)
  a('boot_l','cube',(-.28,.05,.27),(.25,.32,.25),dark,.06);a('boot_r','cube',(.29,.05,.27),(.25,.32,.25),dark,.06)
 elif kind=='agnes':
  cone('broad_torso',(0,.05,2.3),1.03,.72,1.55,main); a('apron','cube',(0,-.39,1.88),(.82,.10,.9),acc,.08);a('head','uv_sphere',(-.08,-.08,3.62),(.62,.46,.54),skin,.04)
  a('swept_hair','uv_sphere',(-.18,.02,3.93),(.78,.48,.38),dark,.06);a('eye_l','uv_sphere',(-.26,-.46,3.65),(.07,.025,.07),dark,.01);a('eye_r','uv_sphere',(.10,-.46,3.65),(.07,.025,.07),dark,.01);a('shoulder_l','uv_sphere',(-.92,.02,2.75),(.42,.38,.42),main,.08);a('shoulder_r','uv_sphere',(.92,.02,2.63),(.42,.38,.42),main,.08)
  a('leg_l','cylinder',(-.42,.05,.82),(.30,.30,.62),dark,.07);a('leg_r','cylinder',(.45,.05,.82),(.30,.30,.62),dark,.07)
  a('arm_l','cylinder',(-1.03,-.05,2.05),(.22,.22,.78),skin,.07).rotation_euler[1]=-.26;a('arm_r','cylinder',(1.08,-.08,2.15),(.22,.22,.68),skin,.07).rotation_euler[1]=.33
  a('bracelet','torus',(1.28,-.18,1.67),(.17,.17,.17),acc,0);a('boot_l','cube',(-.44,.05,.42),(.38,.40,.36),dark,.08);a('boot_r','cube',(.47,.05,.42),(.38,.40,.36),dark,.08)
 else:
  cone('crooked_coat',(0,.08,2.18),.82,.46,1.9,main); a('waist_sash','torus',(0,-.02,1.68),(.58,.58,.18),acc,0);a('head','uv_sphere',(.12,-.08,3.72),(.54,.45,.57),skin,.04)
  a('tilt_hat','cone',(.02,.04,4.34),(.86,.86,.58),main,.08).rotation_euler[1]=.23;a('eye_l','uv_sphere',(-.08,-.46,3.75),(.06,.025,.07),dark,.01);a('eye_r','uv_sphere',(.28,-.46,3.75),(.06,.025,.07),dark,.01);a('hat_band','torus',(.02,.04,4.05),(.7,.7,.12),acc,0)
  a('arm_l','cylinder',(-.8,-.08,2.42),(.15,.15,.93),main,.06).rotation_euler[1]=-.62;a('arm_r','cylinder',(.82,-.25,2.72),(.15,.15,.98),main,.06).rotation_euler[1]=.86
  a('hand_l','uv_sphere',(-1.38,-.35,1.82),(.22,.15,.22),skin,.03);a('hand_r','uv_sphere',(1.48,-.42,3.3),(.22,.15,.22),skin,.03);a('cape_tail','cube',(-.58,.12,1.2),(.35,.18,1.15),dark,.08).rotation_euler[1]=-.28
  a('boot_l','cube',(-.34,.05,.25),(.28,.34,.24),dark,.06);a('boot_r','cube',(.38,.05,.25),(.28,.34,.24),dark,.06)
 for o in objs:
  o.parent=root
 # informative reusable armature, kept separate from presentation root
 bpy.ops.object.armature_add(enter_editmode=True,location=(0,0,.35)); rig=bpy.context.object;rig.name=kind+'_armature'; rig.data.edit_bones[0].name='root'; b=rig.data.edit_bones.new('spine');b.head=(0,0,1.1);b.tail=(0,0,3.6);b.parent=rig.data.edit_bones['root']; bpy.ops.object.mode_set(mode='OBJECT'); rig.parent=root
 return root
def setup():
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 world=bpy.context.scene.world or bpy.data.worlds.new('World');bpy.context.scene.world=world;world.color=(.05,.05,.05)
 bpy.ops.object.camera_add(location=CON['camera']['location'],rotation=(math.radians(78),0,0)); cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=CON['camera']['ortho_scale']; bpy.context.scene.camera=cam
 # point toward z 2.3
 q=(mathutils.Vector(CON['camera']['target'])-cam.location).to_track_quat('-Z','Y');cam.rotation_euler=q.to_euler()
 for loc,pow,size in [((-4,-5,7),850,4),((4,-3,5),450,3),((0,2,6),500,3)]:
  bpy.ops.object.light_add(type='AREA',location=loc);L=bpy.context.object;L.data.energy=pow;L.data.shape='DISK';L.data.size=size;L.rotation_euler=(0,0,0)
 s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=192;s.render.resolution_y=192;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.film_transparent=True
def render_frames(kind,root):
 base=OUT/kind; (base/'final').mkdir(parents=True,exist_ok=True)
 parts=[o for o in bpy.context.scene.objects if o.parent==root and o.type=='MESH']
 rest={o.name:(o.location.copy(),o.rotation_euler.copy()) for o in parts}
 def frame(path,rot=0,phase=0,gesture=0,mode='idle'):
  for o in parts:o.location,o.rotation_euler=rest[o.name][0].copy(),rest[o.name][1].copy()
  s=math.sin(phase*2*math.pi); c=math.cos(phase*2*math.pi)
  def shift(n,x=0,z=0,ry=0,rz=0):
   o=bpy.data.objects.get(n)
   if o:o.location.x+=x;o.location.z+=z;o.rotation_euler[1]+=ry;o.rotation_euler[2]+=rz
  # deliberate motion language; the root remains immovable at the ground anchor.
  if kind=='celina':
   shift('head',z=.075*s,ry=.07*c);shift('braid',z=.16*s,ry=.22*s);shift('arm_l',ry=.11*s);shift('arm_r',ry=-.16*s);shift('cane',ry=-.16*s)
   if mode=='walk':shift('boot_l',z=.17*max(0,s),ry=.32*s);shift('boot_r',z=.17*max(0,-s),ry=-.32*s);shift('arm_l',ry=.25*s);shift('arm_r',ry=-.25*s)
   if mode=='gesture':shift('arm_r',z=.38*math.sin(math.pi*phase),ry=-.85*math.sin(math.pi*phase));shift('cane',z=.36*math.sin(math.pi*phase),ry=-.8*math.sin(math.pi*phase));shift('head',x=-.12*math.sin(math.pi*phase))
  elif kind=='agnes':
   shift('head',x=.12*s,z=-.07*max(0,s));shift('shoulder_l',z=-.14*max(0,s));shift('shoulder_r',z=-.10*max(0,s));shift('arm_l',ry=.25*s);shift('arm_r',ry=-.22*s)
   if mode=='walk': shift('boot_l',z=.24*max(0,s),ry=.42*s);shift('boot_r',z=.24*max(0,-s),ry=-.42*s);shift('leg_l',z=.13*max(0,s),ry=.28*s);shift('leg_r',z=.13*max(0,-s),ry=-.28*s)
   if mode=='gesture':shift('arm_r',z=.5*math.sin(math.pi*phase),ry=-1.0*math.sin(math.pi*phase));shift('head',x=.28*math.sin(math.pi*phase));shift('shoulder_l',z=-.18*math.sin(math.pi*phase))
  else:
   shift('head',x=.10*s,ry=.11*s);shift('tilt_hat',x=.18*s,ry=.28*s);shift('cape_tail',x=-.28*s,ry=-.34*s);shift('arm_l',ry=.32*s);shift('arm_r',ry=-.28*s)
   if mode=='walk':shift('boot_l',z=.24*max(0,s),ry=.48*s);shift('boot_r',z=.24*max(0,-s),ry=-.48*s);shift('arm_l',ry=.5*s);shift('arm_r',ry=-.5*s)
   if mode=='gesture':shift('arm_r',z=.55*math.sin(math.pi*phase),ry=.9*math.sin(math.pi*phase));shift('hand_r',z=.58*math.sin(math.pi*phase),x=.38*math.sin(math.pi*phase));shift('tilt_hat',ry=.6*math.sin(math.pi*phase));shift('cape_tail',x=-.35*math.sin(math.pi*phase))
  # Root stays at its fixed world contact point: never fake movement by recentering frames.
  root.rotation_euler[2]=rot;root.location=(0,0,0);root.rotation_euler[0]=.05*math.sin(phase*2*math.pi)+gesture; bpy.context.scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
 for i in range(16):frame(base/'final'/f'idle_{i:02}.png',phase=i/16,mode='idle')
 dirs=['N','NE','E','SE','S','SW','W','NW']
 for d,ang in enumerate([math.pi,2.36,1.57,.78,0,-.78,-1.57,-2.36]):
  for i in range(8):frame(base/'final'/f'walk_{dirs[d]}_{i:02}.png',ang,i/8,mode='walk')
 for i in range(20):frame(base/'final'/f'gesture_{i:02}.png',phase=i/19,gesture=.18*math.sin(math.pi*i/19),mode='gesture')
def main():
 import mathutils
 global mathutils
 for k in PAL:
  setup()
  (OUT/k).mkdir(parents=True,exist_ok=True)
  root=character(k); bpy.ops.wm.save_as_mainfile(filepath=str((OUT/k/'source').with_suffix('.blend')));render_frames(k,root); bpy.data.objects.remove(root,do_unlink=True)
if __name__=='__main__':main()
