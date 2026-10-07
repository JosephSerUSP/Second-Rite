"""Runtime painted faces must stay in the assigned original atlas allocation."""
import json,sys,hashlib
from pathlib import Path
from PIL import Image
sys.path.insert(0,'tools/blender')
from surface_atlas import pixel_rectangle_uv,seam_color_report
layout=json.loads(Path('out/work/staves/actual-layout.json').read_text());regions=layout['regions'];atlas=Path('projects/hichaukitoden-game/assets/authoring/items/_textures/ritual_staff_family_atlas.png');im=Image.open(atlas);assert list(im.size)==layout['imageSize'] and im.mode=='RGB'
stats=[];failures=[]
for stem in ('silver_rod', 'mage_staff', 'sage_staff', 'ether_staff', 'war_staff', 'healing_staff'):
 path=Path('out/work/staves-products')/f'{stem}.obj';uv=[];mat=None;records={}
 for line in path.read_text().splitlines():
  if line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:3])))
  elif line.startswith('usemtl '):
   mat=line.split()[1];region=mat.removeprefix(stem+'_');assert region in regions and stem in regions[region]['users'],mat
  elif line.startswith('f '):
   region=mat.removeprefix(stem+'_');bounds=pixel_rectangle_uv(regions[region]['pixels'],im.size,inset=layout['insetPixels']);a,b,c,d=bounds
   coords=[uv[int(t.split('/')[1])-1] for t in line.split()[1:]]
   if any(not(a-1e-6<=x<=c+1e-6 and b-1e-6<=y<=d+1e-6) for x,y in coords):failures.append((stem,mat,coords))
   rec=records.setdefault(region,{'faces':0,'uvMin':[1,1],'uvMax':[0,0]});rec['faces']+=1
   for x,y in coords:rec['uvMin']=[min(rec['uvMin'][0],x),min(rec['uvMin'][1],y)];rec['uvMax']=[max(rec['uvMax'][0],x),max(rec['uvMax'][1],y)]
 stats.append({'item':stem,'regions':records,'allocationContainmentFailures':0})
assert not failures,failures[:4]
seams={n:seam_color_report(im,pixel_rectangle_uv(regions[n]['pixels'],im.size,inset=layout['insetPixels'])) for n in ('silver','brass','iron','dark_wood','ash_wood','indigo','plum','brown','green_cloth')}
report={'atlasSHA256':hashlib.sha256(atlas.read_bytes()).hexdigest(),'opaqueRGB':True,'oneOriginalImageSixSources':True,'runtimeRegions':stats,'stripEndDiagnostics':seams,
 'boundary':'Six models consume one original image with explicit region users and original filename. Region containment is not a texel quality, memory or draw-call benchmark; strip endpoints can differ.'}
Path('out/work/staves-region-evidence.json').write_text(json.dumps(report,indent=2)+'\n');print('SHARED REGION AUDIT OK',json.dumps(seams))
