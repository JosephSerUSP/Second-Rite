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
