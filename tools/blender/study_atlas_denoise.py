"""Create a denoised comparison package without overwriting its raw input."""
import argparse,json,shutil,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
import atlas_denoise

parser=argparse.ArgumentParser()
parser.add_argument('--package',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output.exists():raise ValueError('Use a new output directory')
shutil.copytree(args.package,args.output)
bpy.ops.wm.obj_import(filepath=str((args.package/'environment.obj').resolve()))
meshes=[o for o in bpy.context.selected_objects if o.type=='MESH']
if len(meshes)!=1:raise ValueError('Expected one exported atlas receiver')
image=bpy.data.images.load(str((args.package/'environment.png').resolve()))
report=atlas_denoise.denoise(image,meshes[0].data)
image.filepath_raw=str((args.output/'environment.png').resolve());image.file_format='PNG';image.save()
manifest_path=args.output/'environment.json'
manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
manifest['provenance']['bake']['atlasDenoise']=report
manifest['stats']['pngSizeBytes']=(args.output/'environment.png').stat().st_size
manifest['stats']['packageSizeBytes']=sum((args.output/name).stat().st_size for name in
    ['environment.png','environment.obj','environment.mtl','collision.obj'] if (args.output/name).exists())
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
(args.output/'denoise-study.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('ATLAS DENOISE OK',json.dumps(report))
