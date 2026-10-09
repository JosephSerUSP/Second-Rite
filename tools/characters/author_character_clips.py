"""Author additive FK clips on a compiler-built rig. Run with tools/blender/run.py.
Input/output are generated compiler intermediates; the JSON recipe is authority.
"""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Euler

def main():
 p=argparse.ArgumentParser();p.add_argument('--recipe',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);recipe=json.loads(args.recipe.read_text(encoding='utf-8'))
 rig=bpy.data.objects['Rig'];rig['ik_fk']=0
 for bone in rig.pose.bones:
  for constraint in bone.constraints:constraint.mute=True
 idle=next(a for a in bpy.data.actions if a.name.lower()=='idle')
 rig.animation_data.action=idle
 bpy.context.scene.frame_set(int(idle.frame_range[0]));bpy.context.view_layer.update()
 base={b.name:(b.location.copy(),b.rotation_quaternion.copy(),b.scale.copy()) for b in rig.pose.bones if b.bone.use_deform}
 for name,frames in recipe['clips'].items():
  assert isinstance(name,str) and len(frames)>=2,'clip requires two keyed poses'
  times=[f['frame'] for f in frames]
  assert all(isinstance(t,int) and t>=1 for t in times) and all(a<b for a,b in zip(times,times[1:])),'invalid keyed frames'
  for frame in frames:
   for rotation in frame['rotations'].values():
    assert len(rotation)==3 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in rotation),'invalid local rotation'
  assert not bpy.data.actions.get(name),'clip already exists'
  action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
  for frame in frames:
   for key in frame['rotations']:assert key in base,'unknown deform bone '+key
   for key,(loc,rot,scale) in base.items():
    b=rig.pose.bones[key];b.rotation_mode='QUATERNION';b.location=loc;b.scale=scale
    b.rotation_quaternion=rot@Euler(tuple(math.radians(v) for v in frame['rotations'].get(key,[0,0,0])),'XYZ').to_quaternion()
    b.keyframe_insert('rotation_quaternion',frame=frame['frame'],group=key)
    b.keyframe_insert('location',frame=frame['frame'],group=key)
   for layer in action.layers:
    for strip in layer.strips:
     for slot in action.slots:
      bag=strip.channelbag(slot)
      if bag:
       for fc in bag.fcurves:
        for k in fc.keyframe_points:k.interpolation='LINEAR'
 rig.animation_data.action=None
 args.out.parent.mkdir(parents=True,exist_ok=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(args.out.resolve()))
 print('AUTHORED CLIPS OK '+','.join(recipe['clips']))
if __name__=='__main__':main()
