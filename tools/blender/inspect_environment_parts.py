"""Inspect named source furnishings individually without saving the document.

Neutral studio views diagnose shape and material, not the environment's lighting.
Optional native camera records measure projected bounds, not visible pixel area.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_profiles
import thestra_camera
import source_dependencies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--parts', nargs='+', required=True)
    parser.add_argument('--companions', nargs='*', default=[],
                        help='Context meshes retained around each inspected part, e.g. ceiling beams')
    parser.add_argument('--frames', type=Path)
    parser.add_argument('--centre', type=float, default=3.8833)
    parser.add_argument('--view-directions', nargs='+',
                        help='Named inspection offsets, e.g. inside=0,-3,1 outside=0,3,1')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    directions=[('front',(-3,0,.8)),('oblique',(-3,-2.5,2.8)),('top',(-.15,0,4))]
    if args.view_directions:
        directions=[]
        for item in args.view_directions:
            tag,raw=item.split('=',1);offset=tuple(float(v) for v in raw.split(','))
            if len(offset)!=3 or not tag.replace('_','').isalnum() or sum(v*v for v in offset)<.01:
                parser.error('Use a safe view name and three nonzero direction components')
            directions.append((tag,offset))
    if args.output.exists():
        parser.error('Use a new inspection directory')
    before = hashlib.sha256(args.source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    dependencies=source_dependencies.assert_available()
    missing = [name for name in args.parts+args.companions if bpy.data.objects.get(name) is None]
    if missing: raise ValueError(f'Missing source parts: {missing}')
    scene = bpy.context.scene
    for obj in scene.objects: obj.hide_render = True
    for name in args.companions:
        if bpy.data.objects[name].type!='MESH':raise ValueError('Inspection companions must be meshes')
        bpy.data.objects[name].hide_render=False
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.08,.08,.08,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .25
    data = bpy.data.cameras.new('Part inspection')
    camera = bpy.data.objects.new(data.name, data); scene.collection.objects.link(camera)
    camera.hide_render = False; data.type = 'ORTHO'; scene.camera = camera
    lights=[]
    for name, energy in [('key',450),('fill',160),('rim',240)]:
        light_data=bpy.data.lights.new(f'Inspection {name}','AREA'); light_data.energy=energy
        light=bpy.data.objects.new(light_data.name,light_data); scene.collection.objects.link(light)
        lights.append(light)
    args.output.mkdir(parents=True)
    profile=render_profiles.resolve('draft'); rows=[]
    native = None
    if args.frames:
        frames=json.loads(args.frames.read_text(encoding='utf-8'))['frames']
        native=copy.deepcopy(next(f['cameraRecord'] for f in frames if abs(f['y']-args.centre)<1e-7))
        native['eye']['y']=args.centre-native['eye']['y']
        native['orientation']['forwardY']*=-1
        native['orientation']['rightY']*=-1
    for name in args.parts:
        obj=bpy.data.objects[name]
        if obj.type!='MESH': raise ValueError(f'{name} is not a mesh')
        obj.hide_render=False; bpy.context.view_layer.update()
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        points=[evaluated.matrix_world @ Vector(c) for c in evaluated.bound_box]
        low=Vector(tuple(min(p[i] for p in points) for i in range(3)))
        high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
        center=(low+high)/2; extent=high-low; span=max(extent)
        for light,offset in zip(lights,[(-2,-1.8,2.8),(-1.5,2,1.3),(2,1,2.2)]):
            light.location=center+Vector(offset)*span
            light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
            light.data.size=span*1.4
            light.data.energy={'Inspection key':90,'Inspection fill':32,'Inspection rim':48}[light.name]*span*span
        row=dict(name=name,dimensionsMetres=list(extent),materials=[m.name for m in obj.data.materials if m],views=[])
        mesh=evaluated.to_mesh(); row['triangles']=sum(len(p.vertices)-2 for p in mesh.polygons); evaluated.to_mesh_clear()
        if native:
            resolved=thestra_camera.create_or_update_camera(native,scene=scene,make_active=True)
            bpy.context.view_layer.update()
            projected=[thestra_camera.project_world_point(scene,resolved,p) for p in points]
            row['nativeProjectedBounds']=[min(p[0] for p in projected),min(p[1] for p in projected),max(p[0] for p in projected),max(p[1] for p in projected)]
            row['nativeProjectedSize']=[row['nativeProjectedBounds'][2]-row['nativeProjectedBounds'][0],row['nativeProjectedBounds'][3]-row['nativeProjectedBounds'][1]]
        scene.camera=camera; data.ortho_scale=span*1.5
        scene.render.resolution_x=512;scene.render.resolution_y=384;scene.render.resolution_percentage=100
        scene.render.pixel_aspect_x=scene.render.pixel_aspect_y=1
        scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
        for mode in ('beauty','clay'):
            if mode=='beauty':
                render_profiles.apply(scene,profile,device='AUTO');scene.view_settings.view_transform='AgX'
            else:
                scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO'
                scene.display.shading.color_type='SINGLE';scene.display.shading.single_color=(.65,.65,.65)
                scene.display.shading.show_cavity=True;scene.display.shading.show_shadows=True
                scene.display.shading.show_backface_culling=True;scene.display.shading.background_type='WORLD'
                scene.world.color=(.08,.08,.08)
            for tag,offset in directions:
                camera.location=center+Vector(offset)*span
                camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
                camera.data.shift_x=camera.data.shift_y=0
                scene.render.filepath=str((args.output/f'{name}-{mode}-{tag}.png').resolve())
                bpy.ops.render.render(write_still=True)
                row['views'].append(f'{name}-{mode}-{tag}.png')
        rows.append(row);obj.hide_render=True
    assert before==hashlib.sha256(args.source.read_bytes()).hexdigest()
    (args.output/'parts.json').write_text(json.dumps(dict(sourceSHA256=before,profile=profile.record(),parts=rows,companions=args.companions,dependencies=dependencies,
        limits='Studio closeups inspect source meshes. Projected bounds include occluded geometry and are not visible-pixel coverage. No source or global preferences saved.'),indent=2)+'\n',encoding='utf-8')
    print('ENVIRONMENT PART INSPECTION OK')


if __name__=='__main__':main()
