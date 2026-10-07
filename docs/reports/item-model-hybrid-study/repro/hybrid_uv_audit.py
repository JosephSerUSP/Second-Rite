"""Check runtime painted faces against their exact atlas regions."""
from pathlib import Path
import json,sys,math
sys.path.insert(0,'tools/blender')
from surface_atlas import pixel_rectangle_uv
root=Path('out/work/hybrid-products');layout=json.loads(Path('out/work/hybrid/actual-layout.json').read_text());regions={k:pixel_rectangle_uv(v['pixels'],layout['imageSize'],inset=layout['insetPixels']) for k,v in layout['regions'].items()}
report=[];bad=0
for path in sorted(root.glob('*.obj')):
 stem=path.stem;_,direction,route=stem.split('_');painted={};material=None;stats={}
 for line in path.with_suffix('.mtl').read_text().splitlines():
  if line.startswith('newmtl '):material=line.split(maxsplit=1)[1]
  elif line.startswith('map_Kd '):painted[material]=line.split(maxsplit=1)[1]
 uvs=[];normals=[]
 for line in path.read_text().splitlines():
  if line.startswith('vt '):uvs.append(tuple(map(float,line.split()[1:3])))
  elif line.startswith('vn '):normals.append(tuple(map(float,line.split()[1:4])))
  elif line.startswith('usemtl '):material=line.split(maxsplit=1)[1]
  elif line.startswith('f ') and material in painted:
   refs=[t.split('/') for t in line.split()[1:]];rec=stats.setdefault(material,{'faces':0,'missing':0,'collapsed':0,'outsideRegion':0,'varyingNormals':0});rec['faces']+=1
   if any(len(r)<2 or not r[1] for r in refs):rec['missing']+=1;continue
   pts=[uvs[int(r[1])-1] for r in refs];area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(pts,pts[1:]+pts[:1])))*.5
   if area<1e-10:rec['collapsed']+=1
   role=material.removeprefix(stem+'_');u0,v0,u1,v1=regions[direction+'_'+role]
   if any(not (u0-1e-5<=u<=u1+1e-5 and v0-1e-5<=v<=v1+1e-5) for u,v in pts):rec['outsideRegion']+=1
   ns=[normals[int(r[2])-1] for r in refs if len(r)>2 and r[2]]
   if len(set(ns))>1:rec['varyingNormals']+=1
 findings=sum(r['missing']+r['collapsed']+r['outsideRegion'] for r in stats.values());bad+=findings
 report.append({'item':stem,'paintedMaterials':stats,'findings':findings});print(stem,stats)
Path('out/work/hybrid-surfaces.json').write_text(json.dumps(report,indent=2)+'\n')
print('PAINTED SURFACE FINDINGS',bad);raise SystemExit(bool(bad))
