"""Render a source assembly independently from its scene, without saving changes."""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_profiles

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--assembly',required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    root=bpy.data.objects.get(args.assembly)
    if root is None or not any(key in root for key in ['architectural_spec','building_volume']):raise ValueError('No architectural assembly '+args.assembly)
    is_window='architectural_spec' in root
    spec=json.loads(root['architectural_spec' if is_window else 'building_volume']);members=set(root.children_recursive)
    scene=bpy.context.scene
    for obj in bpy.data.objects:
        if obj.type=='MESH':obj.hide_render=obj not in members or obj.get('sr_bake_role')=='receiver'
    for obj in list(bpy.data.objects):
        if obj.type=='LIGHT':bpy.data.objects.remove(obj,do_unlink=True)
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.25,.27,.30,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4
    center=Vector((spec['x']+.10,spec['y'],spec['sill']+spec['height']/2)) if is_window else Vector(((spec['front']+spec['back'])/2,(spec['start']+spec['end'])/2,(spec['floor']+spec['eave'])/2))
    extent=3.60 if is_window else max(spec['back']-spec['front'],spec['end']-spec['start'],spec['ridge']-spec['floor'])*1.45
    for tag,offset,power,size in [('key',(-3,-4,5),600,4),('fill',(-2,4,2),250,3),('rim',(3,1,4),450,3)]:
        data=bpy.data.lights.new('Assembly '+tag,'AREA');data.energy=power;data.size=size
        obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj);obj.location=center+Vector(offset)
        obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('Assembly inspection camera');camera=bpy.data.objects.new(data.name,data)
    scene.collection.objects.link(camera);scene.camera=camera;data.type='ORTHO';data.ortho_scale=extent
    scene.render.resolution_x=640;scene.render.resolution_y=640
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    render_profiles.apply(scene,render_profiles.resolve('review'));scene.view_settings.view_transform='AgX'
    args.out.mkdir(parents=True,exist_ok=True)
    for tag,angle in [('front',0),('oblique',40),('side',75),('rear',180)]:
        rad=math.radians(angle)
        radius=extent*2
        camera.location=center+Vector((-radius*math.cos(rad),radius*math.sin(rad),extent*.35))
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str((args.out/(tag+'.png')).resolve())
        bpy.ops.render.render(write_still=True)
    if not is_window:
        for obj in members:
            if obj.get('construction_layer')=='roof':obj.hide_render=True
        camera.location=center+Vector((0,0,extent*2));camera.rotation_euler=(0,0,0)
        scene.render.filepath=str((args.out/'roof-cut-plan.png').resolve());bpy.ops.render.render(write_still=True)
    (args.out/'assembly.json').write_text(json.dumps({'spec':spec,'views':['front','oblique','side','rear'],'sourceMeshObjects':sum(o.type=='MESH' for o in members),'source':str(args.source)},indent=2),encoding='utf-8')
    print('ASSEMBLY INSPECTION OK')

if __name__=='__main__':main()
