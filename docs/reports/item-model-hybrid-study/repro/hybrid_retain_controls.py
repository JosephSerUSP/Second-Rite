"""Archive actual control inputs/products, not additional adopted study sources."""
from pathlib import Path
import shutil,json,hashlib
out=Path('docs/reports/item-model-hybrid-study/controls');digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plain=out/'plain';plain.mkdir(parents=True,exist_ok=True);records=[]
for p in Path('out/work/hybrid-plain-products').glob('*.mtl'):
 shutil.copy2(p,plain/p.name);records.append({'item':p.stem,'mtl':'plain/'+p.name,'sha256':digest(plain/p.name),'geometry':'Reuse exact retained study OBJ; control OBJ bytes identical.'})
core=out/'core/assets';src=core/'authoring/items';models=core/'models/items';(src/'_textures').mkdir(parents=True,exist_ok=True);models.mkdir(parents=True,exist_ok=True)
original=Path('out/work/hybrid-core-control/assets/authoring/items')
for p in original.glob('*.blend'):shutil.copy2(p,src/p.name)
shutil.copy2(original/'_textures/hybrid_surface_atlas.png',src/'_textures/hybrid_surface_atlas.png')
for direction in ['carved','salvage']:
 for suffix in ['.obj','.mtl']:
  p=Path('out/work/hybrid-core-control-products')/('hybrid_'+direction+'_sdf'+suffix);shutil.copy2(p,models/p.name)
shutil.copy2(original/'_textures/hybrid_surface_atlas.png',models/'hybrid_surface_atlas.png')
evidence=Path('docs/reports/item-model-hybrid-study/core-control-evidence.json');data=json.loads(evidence.read_text())
for r in data:
 name=r['item']+'.blend';assert digest(src/name)==r['controlSHA256']
 r['retainedControlSource']='controls/core/assets/authoring/items/'+name;r['retainedControlOBJ']='controls/core/assets/models/items/'+r['item']+'.obj';r['controlObjSHA256']=digest(models/(r['item']+'.obj'));r['controlMtlSHA256']=digest(models/(r['item']+'.mtl'))
evidence.write_text(json.dumps(data,indent=2)+'\n');(out/'plain-evidence.json').write_text(json.dumps(records,indent=2)+'\n')
shutil.copy2(Path(__file__),out.parent/'repro/hybrid_retain_controls.py');print('ACTUAL CONTROL PRODUCTS AND DERIVATIVE CORE COPIES RETAINED')
