"""Review-only canonical stage with six synthetic items; no shipping data writes."""
import json, shutil, sys, argparse, re
from pathlib import Path
sys.path.insert(0,'tools/asset-production')
import item_review as review
p=argparse.ArgumentParser();p.add_argument('--tag',default='hybrid-first96');p.add_argument('--cell',type=int,default=96);p.add_argument('--cardinal',action='store_true');p.add_argument('--products',default='out/work/hybrid-products');a=p.parse_args()
review.STAGE_DIR=review.ROOT/'out/stage-carved-revision'
if not review.STAGE_DIR.is_dir():review.stage()
stage=review.STAGE_DIR
names=['Before','Geometry','Features','Baked']
stems=['hybrid_carved_hull','carved_capsule_geometry','carved_capsule_features','carved_capsule_baked']
items=json.loads((stage/'data/items.json').read_text(encoding='utf-8'))
items=[i for i in items if i['id']<10001]
for i,name in enumerate(names):items.append({'id':10001+i,'name':name,'type':'accessory','model':'assets/models/items/'+stems[i]+'.obj','icon':1,'price':0,'description':'Nonshipping hybrid study'})
(stage/'data/items.json').write_text(json.dumps(items,indent=2)+'\n',encoding='utf-8')
for f in list(Path(a.products).iterdir())+list(Path('docs/reports/item-model-hybrid-study/source-project/assets/models/items').iterdir()):
 if f.suffix in ['.obj','.mtl','.png']:shutil.copy2(f,stage/'assets/models/items'/f.name)
view=stage/'engine/item_model_sheet.lua';original=view.read_text(encoding='utf-8')
try:
 if a.cardinal:
  block='local VIEWS = {\n'+''.join('    { yaw = math.rad('+str(y)+'), tilt = 0 },\n' for y in [0,90,180,270])+'}'
  view.write_text(re.sub(r'local VIEWS = \{.*?\n\}',block,original,flags=re.S),encoding='utf-8')
 review.render(a.tag,names,a.cell,False,240)
finally:view.write_text(original,encoding='utf-8')
