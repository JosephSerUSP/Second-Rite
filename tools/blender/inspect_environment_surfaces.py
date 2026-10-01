"""Read-only source/package geometry and atlas inspection from independent cameras."""
import argparse,json,sys,hashlib
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_profiles

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--modes',nargs='+',choices=('source-clay','source-beauty','runtime-clay','runtime-atlas'),
                        default=['source-clay','source-beauty','runtime-clay','runtime-atlas'])
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.out.mkdir(parents=True,exist_ok=True);source=args.source.resolve();package=args.package.resolve()
    before=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source))
    scene=bpy.context.scene
    meshes=[o for o in bpy.data.collections['TH_SOURCE'].all_objects if o.type=='MESH']
    source_meshes=[o for o in meshes if o.get('sr_bake_role')!='receiver' and not o.hide_render]
    for name in ['TH_RENDER','TH_COLLISION','TH_ANCHORS','TH_PREVIEW_ACTORS']:bpy.data.collections[name].hide_render=True
    bpy.ops.wm.obj_import(filepath=str(package/'environment.obj'))
    runtime=[o for o in bpy.context.selected_objects if o.type=='MESH']
    # The package OBJ uses Blender's default Y-up export; default import restores
    # Blender coordinates. Verify against the authoritative package bounds.
    coordinates=[obj.matrix_world@vertex.co for obj in runtime for vertex in obj.data.vertices]
    bounds=[min(p[i] for p in coordinates) for i in range(3)]+[max(p[i] for p in coordinates) for i in range(3)]
    declared=json.loads((package/'environment.json').read_text(encoding='utf-8'))['bounds']
    assert all(abs(a-b)<1e-4 for a,b in zip(bounds,declared)), f'Imported coordinate mismatch: {bounds} != {declared}'
    for obj in runtime:obj.hide_render=True
    data=bpy.data.cameras.new('Surface inspection');camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera);scene.camera=camera
    data.type='ORTHO';scene.render.resolution_x=800;scene.render.resolution_y=600;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    views=[('court-oblique',(4,6,2.8),(-32,-10,12),21),('rear-houses',(14,6,5),(-28,-14,16),27),('window',(4.5,3.5,2.1),(-6,-2.6,2.3),4.8),('window-reverse',(4.5,3.5,2.1),(-5,3.2,1.8),4.8),('portal',(4.5,11.5,2),(-8,-4,3),6)]
    rows=[]
    for mode in args.modes:
        for obj in source_meshes:obj.hide_render=not mode.startswith('source')
        for obj in runtime:obj.hide_render=mode.startswith('source')
        if mode.endswith('clay'):
            scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='SINGLE'
            scene.display.shading.single_color=(.65,.65,.65);scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
            scene.display.shading.show_backface_culling=True;scene.display.shading.background_type='WORLD';scene.world.color=(.12,.12,.12)
        elif mode=='source-beauty':
            render_profiles.apply(scene,render_profiles.resolve('draft'),device='AUTO');scene.view_settings.view_transform='AgX'
        else:
            render_profiles.apply(scene,render_profiles.resolve('draft'),device='AUTO');scene.view_settings.view_transform='Standard'
            atlas=bpy.data.images.load(str(package/'environment.png'),check_existing=True)
            mat=bpy.data.materials.new('Atlas inspection emission');mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear()
            texture=nodes.new('ShaderNodeTexImage');texture.image=atlas;texture.interpolation='Closest';emission=nodes.new('ShaderNodeEmission');output=nodes.new('ShaderNodeOutputMaterial')
            mat.node_tree.links.new(texture.outputs['Color'],emission.inputs['Color']);mat.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
            for obj in runtime:obj.data.materials.clear();obj.data.materials.append(mat)
        for tag,center,offset,scale in views:
            data.ortho_scale=scale;camera.location=Vector(center)+Vector(offset);camera.rotation_euler=(Vector(center)-camera.location).to_track_quat('-Z','Y').to_euler()
            scene.render.filepath=str((args.out/(mode+'-'+tag+'.png')).resolve());bpy.ops.render.render(write_still=True)
        rows.append({'mode':mode,'views':[v[0] for v in views]})
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    (args.out/'inspection.json').write_text(json.dumps({'sourceSHA256':before,'sourceMeshes':len(source_meshes),'runtimeMeshes':len(runtime),'renderProfile':render_profiles.resolve('draft').record(),'views':rows,'interpretation':'Workbench clay with backface culling is geometry evidence. Emission atlas views remove additional scene lighting; baked shading remains in the texture. Source file unchanged.'},indent=2)+'\n',encoding='utf-8')
    print('SURFACE INSPECTION OK')
if __name__=='__main__':main()
