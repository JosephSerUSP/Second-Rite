"""Actual Cycles selected-to-active atlas study; source stays unchanged."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import bpy,bmesh
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/blender'))
import export_exterior_environment as exporter
import town_environment_pipeline as pipeline
import atlas_allocation

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--samples',type=int,default=1)
    parser.add_argument('--atlas-size',type=int,default=1024)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if args.output.exists():raise ValueError('Use a new output directory')
    before=hashlib.sha256(args.source.read_bytes()).hexdigest()
    start=time.perf_counter();bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    for obj in list(bpy.data.collections['TH_SOURCE'].all_objects):
        if obj.type!='MESH':continue
        if obj.name.endswith(' roof'):
            bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update()
        elif obj.name.endswith('gable'):
            bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update();obj['sr_bake_open_surface']=True
    exporter.rebuild_render_mesh(12,6,.03,24,0,clip_ground=None,layout='legacy',atlas_size=args.atlas_size)
    # One derived beauty mesh avoids per-object bake setup while preserving
    # UVs, world placement and per-object procedural coordinates.
    source=bpy.data.collections['TH_SOURCE']
    members=[o for o in list(source.all_objects) if o.type=='MESH' and o.get('sr_bake_role')!='receiver']
    graph=bpy.context.evaluated_depsgraph_get()
    vertices=[];faces=[];uvs=[];generated=[];local=[];materials=[];material_indices=[];smooth=[]
    material_map={}
    for obj in members:
        evaluated=obj.evaluated_get(graph);mesh=evaluated.to_mesh()
        offset=len(vertices);world=obj.matrix_world
        lows=[min(v.co[axis] for v in mesh.vertices) for axis in range(3)]
        highs=[max(v.co[axis] for v in mesh.vertices) for axis in range(3)]
        for v in mesh.vertices:
            vertices.append(tuple(world@v.co));local.append(tuple(v.co))
            generated.append(tuple((v.co[a]-lows[a])/max(highs[a]-lows[a],1e-8) for a in range(3)))
        uv=mesh.uv_layers.active
        for face in mesh.polygons:
            faces.append(tuple(offset+i for i in face.vertices));smooth.append(face.use_smooth)
            uvs.extend(tuple(uv.data[i].uv) if uv else (0,0) for i in face.loop_indices)
            material=mesh.materials[face.material_index] if mesh.materials else None
            if material and material.name not in material_map:
                material_map[material.name]=len(materials);materials.append(material)
            material_indices.append(material_map[material.name] if material else 0)
        evaluated.to_mesh_clear()
    data=bpy.data.meshes.new('Study batched beauty');data.from_pydata(vertices,[],faces);data.update()
    layer=data.uv_layers.new(name='Source UV');layer.data.foreach_set('uv',[v for uv in uvs for v in uv])
    for name,values in [('sr_source_generated',generated),('sr_source_object',local)]:
        attr=data.attributes.new(name,'FLOAT_VECTOR','POINT');attr.data.foreach_set('vector',[v for row in values for v in row])
    def adapt(tree):
        attr=tree.nodes.new('ShaderNodeAttribute');attr.attribute_name='sr_source_generated'
        objattr=tree.nodes.new('ShaderNodeAttribute');objattr.attribute_name='sr_source_object'
        for node in list(tree.nodes):
            if node.type=='TEX_COORD':
                for link in list(node.outputs['Generated'].links):tree.links.new(attr.outputs['Vector'],link.to_socket)
                if node.object is None:
                    for link in list(node.outputs['Object'].links):tree.links.new(objattr.outputs['Vector'],link.to_socket)
            elif node.type=='GROUP' and node.node_tree:
                node.node_tree=node.node_tree.copy();adapt(node.node_tree)
            elif node.type in ['TEX_NOISE','TEX_VORONOI','TEX_WAVE','TEX_GRADIENT','TEX_MAGIC','TEX_CHECKER','TEX_BRICK']:
                socket=node.inputs.get('Vector')
                if socket and not socket.is_linked:tree.links.new(attr.outputs['Vector'],socket)
    for material in materials:
        copy=material.copy()
        if copy.use_nodes:adapt(copy.node_tree)
        data.materials.append(copy)
    data.polygons.foreach_set('material_index',material_indices);data.polygons.foreach_set('use_smooth',smooth)
    batch=bpy.data.objects.new('Study beauty batch',data);source.objects.link(batch)
    for obj in members:
        source.objects.unlink(obj) if obj.name in source.objects else None
        bpy.data.objects.remove(obj,do_unlink=True)
    print('SOURCE BATCH',len(members),'objects to one mesh',len(vertices),'vertices',flush=True)
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    devices=[d for d in prefs.devices if d.type=='OPTIX']
    if not devices:raise ValueError('No OptiX device available for this GPU study')
    for d in prefs.devices:d.use=d.type=='OPTIX'
    scene=bpy.context.scene;scene.view_settings.exposure=0
    scene.cycles.use_adaptive_sampling=False;scene.cycles.max_bounces=4
    scene.cycles.diffuse_bounces=2;scene.cycles.glossy_bounces=2
    scene.cycles.seed=3201
    prepared=time.perf_counter()
    print('SURFACE BAKE START',args.samples,flush=True)
    pipeline.run_pipeline_in_blender(args.source,args.output,atlas_size=args.atlas_size,
        bake_samples=args.samples,flat_bake=False,backend='cycles',cycles_device='GPU')
    end=time.perf_counter()
    result={'sourceSHA256':before,'samples':args.samples,'atlasSize':args.atlas_size,
        'backend':'Cycles selected-to-active OptiX GPU','devices':[d.name for d in devices],
        'prepareSeconds':prepared-start,'bakeAndPackageSeconds':end-prepared,'totalSeconds':end-start,
        'geometry':'Roof winding repaired; open gables outward and protected; production source unchanged',
        'layout':'Legacy deterministic UV allocation, no camera-projection bake'}
    (args.output/'study.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    assert hashlib.sha256(args.source.read_bytes()).hexdigest()==before
    print('SURFACE BAKE OK',json.dumps(result),flush=True)
if __name__=='__main__':main()
