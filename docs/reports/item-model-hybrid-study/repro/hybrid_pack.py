"""Retain exact study products and original input evidence; not shipping assets."""
from pathlib import Path
import shutil,json,hashlib
out=Path('docs/reports/item-model-hybrid-study');p=Path('out/work/hybrid');products=out/'source-project/assets/models/items';products.mkdir(parents=True,exist_ok=True)
for path in Path('out/work/hybrid-products').iterdir():
 if path.suffix in ['.obj','.mtl','.png']:shutil.copy2(path,products/path.name)
for name in ['reference-carved.png','reference-salvage.png','hybrid_surface_atlas.png','panels.png','layout.png','actual-layout.json','requested-layout.json','panel-meshes.json','calibration.json','plain-colours.json','initial-source-evidence.json','initial-surfaces.json']:shutil.copy2(p/name,out/name)
for src,dst in [('hybrid-refinements.json','source-refinements.json'),('hybrid-boundary-refinements.json','boundary-refinements.json'),('hybrid-dimension-refinements.json','dimension-refinements.json')]:shutil.copy2(Path('out/work')/src,out/dst)
images=[('reference-carved.png','exec-f0011718-3ecb-4007-8be3-ae334ae3b89c.png','refs','carved',True),('reference-salvage.png','exec-b29275a4-d80e-4ee6-89f7-1c932278f795.png','refs','salvage',True),('hybrid_surface_atlas.png','exec-44e7a029-4879-4a3d-9986-dffb33d8ff52.png','surfaces','atlas',False),('panels.png','exec-63421155-cf58-4d46-951d-93a66856b9f1.png','surfaces','panels',True)]
original=Path(r'C:\Users\josep\.codex\generated_images\01a111e6-2b3c-7281-9302-7ca09dbf4e4c');digest=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();prompts=json.loads((out/'generation-prompts.json').read_text())
records=[]
for name,original_name,group,key,alpha in images:
 assert (out/name).read_bytes()==(original/original_name).read_bytes()
 records.append({'file':name,'originalFile':str(original/original_name),'sha256':digest(out/name),'provider':'built-in imagegen','transparentBackground':alpha,'prompt':prompts[group][key]})
(out/'generation.json').write_text(json.dumps({'calls':4,'studies':6,'images':records,'guide':'layout.png is code-native, not an imagegen output','boundary':'Call count only; no monetary or render-cost savings measured. Original generated PNGs unchanged.'},indent=2)+'\n')
repro=out/'repro';repro.mkdir(exist_ok=True)
for name in ['author_hybrid_study.py','hybrid_prepare.py','hybrid_refine.py','hybrid_boundary_refine.py','hybrid_recalibrate.py','hybrid_audit.py','hybrid_uv_audit.py','hybrid_render.py','hybrid_controls.py','hybrid_pack.py']:
 shutil.copy2(Path('out/work')/name,repro/name)
print('STUDY PRODUCTS/ORIGINAL INPUTS RETAINED; source and compiled atlas unchanged')
