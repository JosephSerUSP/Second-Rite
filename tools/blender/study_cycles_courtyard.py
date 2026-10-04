"""Native full-geometry Cycles budget study; never saves or exports the source."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/blender'))
import atlas_allocation,render_profiles

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--camera',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--budgets',type=float,nargs='+',default=[30,60,120])
    parser.add_argument('--lane-y',type=float,default=5)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if args.out.exists():raise ValueError('Use a new study directory')
    if any(t<=0 for t in args.budgets):raise ValueError('Budgets must be positive')
    args.out.mkdir(parents=True)
    before=hashlib.sha256(args.source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    scene=bpy.context.scene
    source=bpy.data.collections['TH_SOURCE'];source.hide_render=False
    for name in ['TH_RENDER','TH_COLLISION','TH_ANCHORS','TH_PREVIEW_ACTORS']:
        bpy.data.collections[name].hide_render=True
    for obj in list(source.all_objects):obj.hide_render=obj.get('sr_bake_role')=='receiver'
    atlas_allocation.lane_camera(scene,args.lane_y,mirrored=False,record_path=args.camera,width=426)
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='AgX'
    scene.view_settings.exposure=0
    render_profiles.apply(scene,render_profiles.resolve('review'))
    scene.render.filepath=str((args.out/'eevee-reference.png').resolve())
    started=time.perf_counter();bpy.ops.render.render(write_still=True)
    reference_seconds=time.perf_counter()-started
    scene.render.engine='CYCLES'
    prefs=bpy.context.preferences.addons['cycles'].preferences
    devices=[];backend='CPU'
    for kind in ['OPTIX','CUDA']:
        try:
            prefs.compute_device_type=kind;prefs.get_devices()
            available=[d for d in prefs.devices if d.type==kind]
            if available:
                for device in prefs.devices:device.use=device.type==kind
                backend=kind;devices=[d.name for d in available];break
        except Exception:continue
    scene.cycles.device='GPU' if backend!='CPU' else 'CPU'
    scene.cycles.samples=1000000
    scene.cycles.use_adaptive_sampling=False
    scene.cycles.use_denoising=True
    scene.cycles.denoiser='OPENIMAGEDENOISE'
    scene.cycles.seed=3201
    scene.cycles.use_animated_seed=False
    scene.render.use_persistent_data=True
    result={'sourceSHA256':before,'blender':bpy.app.version_string,'backend':backend,'devices':devices,
        'resolution':[426,240],'laneY':args.lane_y,'exposureEV':0,'viewTransform':'AgX',
        'denoiser':'OPENIMAGEDENOISE','adaptiveSampling':False,'sampleCeiling':1000000,
        'budgetInterpretation':'Cycles integration time per image; actual wall time also includes synchronization and denoising. First Cycles frame is cold; later frames reuse persistent data.',
        'eeveeReferenceSeconds':reference_seconds,'frames':[]}
    print('CYCLES STUDY DEVICE',backend,devices,flush=True)
    for budget in args.budgets:
        scene.cycles.time_limit=budget
        scene.render.filepath=str((args.out/f'cycles-{budget:g}s.png').resolve())
        started=time.perf_counter();bpy.ops.render.render(write_still=True)
        elapsed=time.perf_counter()-started
        result['frames'].append({'budgetSeconds':budget,'wallSeconds':elapsed,'image':Path(scene.render.filepath).name})
        (args.out/'measurements.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print('CYCLES BUDGET COMPLETE',budget,elapsed,flush=True)
    assert hashlib.sha256(args.source.read_bytes()).hexdigest()==before,'Source was modified'
    print('CYCLES STUDY OK',args.out,flush=True)
if __name__=='__main__':main()
