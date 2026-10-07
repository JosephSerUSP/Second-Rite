"""Actual runtime comparisons and source/input evidence, never model regeneration."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib,shutil
out=Path('docs/reports/item-model-hybrid-study');source=out/'source-project/assets/authoring/items';products=out/'source-project/assets/models/items'
stems=[f'hybrid_{d}_{r}' for d in ['carved','salvage'] for r in ['hull','sdf','conform']]
digest=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
inspection={r['item']:r for r in json.loads(Path('out/work/hybrid-source-evidence.json').read_text())};cal=json.loads((out/'calibration.json').read_text())
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18);small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',13)
label={'hull':'Shadows + loft + sweeps','sdf':'Fabricated plates + SDF + sweeps','conform':'Alpha panels + conformance + loft'}
def strip(stem,tag):return Image.open(Path('out/review')/tag/(stem.removeprefix('hybrid_')+'.png')).convert('RGB')
native=Image.new('RGB',(1152,288),(26,26,31));show=Image.new('RGB',(1152,528),(26,26,31));yaw=Image.new('RGB',native.size,(26,26,31));plain=Image.new('RGB',native.size,(26,26,31));detail=Image.new('RGB',(2304,496),(26,26,31))
for b,title in [(native,'Two directions x three hybrid routes | actual 96px / four runtime poses'),(show,'Native 96px pixels enlarged 2x | gameplay yaw 20 and side yaw 110'),(yaw,'Actual 96px cardinal yaw 0 / 90 / 180 / 270'),(plain,'Same OBJ bytes / allocation-mean colours / sphere overlays retained'),(detail,'Actual 192px diagnostic render / four runtime poses')]:ImageDraw.Draw(b).text((8,5),title,font=font,fill=(228,228,232))
records=[]
for i,stem in enumerate(stems):
 _,direction,route=stem.split('_');x=i%3*384;y=32+i//3*128
 painted=strip(stem,'hybrid-final96');assert painted.size==(384,96)
 for board,tag in [(native,'hybrid-final96'),(yaw,'hybrid-yaw96'),(plain,'hybrid-plain96')]:
  ImageDraw.Draw(board).text((x+5,y),direction.title()+' | '+label[route],font=small,fill=(215,215,223));board.paste(strip(stem,tag),(x,y+24))
 ys=36+i//3*244;ImageDraw.Draw(show).text((x+8,ys),direction.title()+' | '+label[route],font=small,fill=(220,220,226));show.paste(painted.crop((0,0,192,96)).resize((384,192),Image.Resampling.NEAREST),(x,ys+30))
 dx=i%3*768;dy=32+i//3*232;ImageDraw.Draw(detail).text((dx+8,dy),direction.title()+' | '+label[route],font=font,fill=(220,220,226));detail.paste(strip(stem,'hybrid-detail192'),(dx,dy+32))
 audit=inspection[stem];assert audit['sourceHash']==digest(source/(stem+'.blend'))
 assert all(o['rawNonmanifold']==0 and o['weldedNonmanifold']==0 and o['signedVolume']>0 for o in audit['objects'])
 assert all(abs(a-b)<2e-6 for a,b in zip(audit['dimensions'],cal[direction]['targetDimensions']))
 assert (products/(stem+'.obj')).read_bytes()==(Path('out/work/hybrid-plain-products')/(stem+'.obj')).read_bytes()
 text=(products/(stem+'.obj')).read_text();control=strip(stem,'hybrid-plain96')
 records.append({'item':stem,'sourceSHA256':digest(source/(stem+'.blend')),'objSHA256':digest(products/(stem+'.obj')),'mtlSHA256':digest(products/(stem+'.mtl')),'vertices':sum(l.startswith('v ') for l in text.splitlines()),'triangles':sum(len(l.split())-3 for l in text.splitlines() if l.startswith('f ')),'dimensions':audit['dimensions'],'plainOBJBytesIdentical':True,'changedPixelsPlainFirstTwoViews':sum(a!=b for a,b in zip(control.crop((0,0,192,96)).getdata(),painted.crop((0,0,192,96)).getdata()))})
for board,name in [(native,'native96.png'),(show,'showcase.png'),(yaw,'yaw96.png'),(plain,'plain96.png'),(detail,'detail192.png')]:board.save(out/name)
lineup=Image.new('RGB',(1200,880),(26,26,31));d=ImageDraw.Draw(lineup)
for i,stem in enumerate(stems):
 _,direction,route=stem.split('_');x=i%3*400;y=i//3*440;d.text((x+8,y+4),direction.title()+' | '+route,font=font,fill=(220,220,226))
 im=Image.open(f'out/work/hybrid-source-views/{stem}-front.png').convert('RGBA');box=im.getchannel('A').getbbox();im=im.crop(box);im.thumbnail((384,400),Image.Resampling.LANCZOS);lineup.paste(im,(x+(400-im.width)//2,y+32+(400-im.height)//2),im)
lineup.save(out/'source-front-lineup.png')
for stem in stems:
 direction=stem.split('_')[1];ref=Image.open(out/f'reference-{direction}.png').convert('RGBA');board=Image.new('RGB',(760,508),(26,26,31));d=ImageDraw.Draw(board)
 for j,view in enumerate(['front','right','back','top']):
  x=j%2*380;y=j//2*254;d.text((x+4,y+3),view.upper()+' reference / actual source',font=small,fill=(220,220,226))
  actual=Image.open(f'out/work/hybrid-source-views/{stem}-{view}.png').convert('RGBA');actual.save(out/f'{stem}-source-{view}.png')
  for offset,im in [(0,ref.crop(cal[direction]['clips'][j])),(190,actual)]:
   box=im.getchannel('A').point(lambda p:255 if p>=225 else 0).getbbox()
   if box:im=im.crop(box)
   im.thumbnail((180,222),Image.Resampling.LANCZOS);board.paste(im,(x+offset+(190-im.width)//2,y+24+(226-im.height)//2),im)
 board.save(out/f'{stem}-reference-to-source.png')
core=Image.new('RGB',(768,276),(26,26,31));d=ImageDraw.Draw(core);d.text((5,3),'Same assembly / saved loft core',font=font,fill=(220,220,226));d.text((389,3),'Same assembly / live SDF core',font=font,fill=(220,220,226));core_records=[]
controls=json.loads(Path('out/work/hybrid-core-controls.json').read_text());controls_by={r['item']:r for r in controls}
for i,direction in enumerate(['carved','salvage']):
 stem='hybrid_'+direction+'_sdf';y=40+i*116;d.text((6,y),direction.title(),font=small,fill=(220,220,226));d.text((390,y),direction.title(),font=small,fill=(220,220,226))
 a=strip(stem,'hybrid-core-control96');b=strip(stem,'hybrid-final96');core.paste(a,(0,y+18));core.paste(b,(384,y+18))
 control_path=Path('out/work/hybrid-core-control-products')/(stem+'.obj');text=control_path.read_text();triangles=sum(len(l.split())-3 for l in text.splitlines() if l.startswith('f '))
 def bounds(path):
  vs=[list(map(float,l.split()[1:4])) for l in path.read_text().splitlines() if l.startswith('v ')]
  return [[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]]
 assert bounds(control_path)==bounds(products/(stem+'.obj'))
 core_records.append(dict(controls_by[stem],controlTriangles=triangles,controlledOBJBoundsIdentical=True,changedPixelsFirstTwoViews=sum(x!=y for x,y in zip(a.crop((0,0,192,96)).getdata(),b.crop((0,0,192,96)).getdata()))))
core.save(out/'core-control96.png');(out/'core-control-evidence.json').write_text(json.dumps(core_records,indent=2)+'\n')
for src,dst in [('hybrid-source-evidence.json','source-evidence.json'),('hybrid-surfaces.json','surface-evidence.json')]:shutil.copy2(Path('out/work')/src,out/dst)
atlas=source/'_textures/hybrid_surface_atlas.png';assert atlas.read_bytes()==(products/atlas.name).read_bytes()==(out/atlas.name).read_bytes()
evidence={'items':records,'evaluatedVisibleComponents':sum(len(x['objects']) for x in inspection.values()),'allRawClosedPositiveVolume':True,'assignedPaintedRegionFindings':0,'sourceAtlasAndCompiledAtlasBytesIdentical':True,'readOnlyCompileCheckPassed':True,'nativeCell':96,'diagnosticCell':192,'boundary':'Whole route comparison, not one-factor causality: plate construction, smoothing and core vary. Same direction reference, overall dimensions, atlas, view poses and pre-fit assembly controls. Root fitting can change assembly proportions. Core ablation independently keeps noncore evaluated geometry and bounds identical. Closed components do not prove no intersections or projection misses. Native review is not owner aesthetic acceptance; no shipping item assets changed.'}
(out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print('HYBRID EVIDENCE',evidence['evaluatedVisibleComponents'],[(r['item'],r['triangles']) for r in records],core_records)
shutil.copy2(Path(__file__),out/'repro/hybrid_boards.py');shutil.copy2('out/work/hybrid_core_controls.py',out/'repro/hybrid_core_controls.py');shutil.copy2('out/work/verify_hybrid.ps1',out/'repro/verify_hybrid.ps1')
