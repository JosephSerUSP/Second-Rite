from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GEN=Path(r'C:\Users\josep\.codex\generated_images\01a06bd2-7b02-73d3-93f7-ff903d298166')
FILES={
 'port':'exec-3b12218f-63a3-4247-bd5c-34f77bb16f65.png',
 'churchyard':'exec-be35697b-d82e-4f1d-9eab-cc770d5ac1fe.png',
 'cortico':'exec-ac98610a-30e1-4be9-a34b-e90c24698237.png',
 'market':'exec-8f3729ef-a663-45ca-8b54-04559e6bcba3.png',
 'quay':'exec-18c01029-c399-4399-ad34-7b68e747f127.png',
 'weaponsmith':'exec-4767639f-e98a-41e6-b042-931078fdb8eb.png',
 'alicias_padaria':'exec-3efbdb51-5861-446b-8ae6-2568acc08e4b.png',
 'pub':'exec-f32e95db-09aa-4762-a8b8-904d21280078.png',
 'chapel':'exec-89e293ae-22e1-4bb9-97b8-854d94b5ee11.png',
 'house_laura':'exec-0d16783d-c12e-41ef-9084-b815e2646546.png',
 'house_alicia':'exec-192bea7e-018a-4202-90d3-9102e0147452.png',
 'lodging':'exec-0cf2aef0-915d-4d20-8a19-771a77a36c91.png',
}
def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def main():
 for key,file in FILES.items():
  base=ROOT/'out/towngen'/key/'replacement'
  raw=base/'raw-001.png'; old=json.loads((base/'calibration-v2/annotation.json').read_text())
  generated=GEN/file
  out=ROOT/'out/towngen/repaint-v3'/key
  (out/'source').mkdir(parents=True,exist_ok=True)
  clean=out/'source/clean-source.png'; shutil.copy2(generated,clean)
  from PIL import Image
  with Image.open(clean) as im: cw,ch=im.size
  sx=cw/old['sourceSize'][0]; sy=ch/old['sourceSize'][1]
  ann=dict(old); ann['sourceSize']=[cw,ch]; ann['sourceSha256']=sha(clean)
  ann['actorRefs']=[dict(r,box=[round(r['box'][0]*sx),round(r['box'][1]*sy),round(r['box'][2]*sx),round(r['box'][2]*0+r['box'][3]*sy)],feetY=round(r['feetY']*sy,3),sourceVisibleHeight=round(r['sourceVisibleHeight']*sy,3)) for r in old['actorRefs']]
  ann['floorSupports']=[[round(x*sx,3),round(y*sy,3)] for x,y in old['floorSupports']]
  for p in ann['portalPairs']:
   p['sourceX']=round(p['sourceX']*sx,3); p['sourceY']=round(p.get('sourceY',0)*sy,3)
  ann['lineage']={'rawSource':str(raw.relative_to(ROOT)),'rawSha256':sha(raw),'generatedCleanSource':str(clean.relative_to(ROOT)),'generatedCleanSha256':sha(clean),'mask':None,'outpaint':None,'crop':None}
  (out/'source/repaint-annotation.json').write_text(json.dumps(ann,indent=2)+'\n')
  req={'screen':key,'input':str(raw.relative_to(ROOT)),'inputSha256':sha(raw),'output':str(clean.relative_to(ROOT)),'outputSha256':sha(clean),'edit':'remove baked characters and reconstruct occluded background','outpaint':None,'crop':None,'generator':'built-in image_gen','attempt':'independent-001'}
  (out/'source/repaint-request.json').write_text(json.dumps(req,indent=2)+'\n')
if __name__=='__main__': main()
