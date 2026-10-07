"""Inspect final runtime UVs by painted material, not model-wide presence."""
from pathlib import Path
import json,math
STEMS=['silver_rod', 'mage_staff', 'sage_staff', 'ether_staff', 'war_staff', 'healing_staff']
root=Path('out/work/staves-products');report=[];bad=0
for stem in STEMS:
    painted={};material=None
    for line in (root/f'{stem}.mtl').read_text().splitlines():
        if line.startswith('newmtl '):material=line.split(maxsplit=1)[1]
        elif line.startswith('map_Kd '):painted[material]=line.split(maxsplit=1)[1]
    uv=[];normals=[];material=None;stats={};bounds=0
    for line in (root/f'{stem}.obj').read_text().splitlines():
        if line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:3])))
        elif line.startswith('vn '):normals.append(tuple(map(float,line.split()[1:4])))
        elif line.startswith('usemtl '):material=line.split(maxsplit=1)[1]
        elif line.startswith('f '):
            refs=[token.split('/') for token in line.split()[1:]]
            if material not in painted:continue
            rec=stats.setdefault(material,{'texture':painted[material],'faces':0,'missing':0,'collapsed':0,'outside':0,'varyingNormals':0})
            rec['faces']+=1
            if any(len(r)<2 or not r[1] for r in refs):rec['missing']+=1;continue
            coords=[uv[int(r[1])-1] for r in refs]
            area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(coords,coords[1:]+coords[:1])))*.5
            if area<1e-10:rec['collapsed']+=1
            if any(c<-.00001 or c>1.00001 for p in coords for c in p):rec['outside']+=1
            ns=[normals[int(r[2])-1] for r in refs if len(r)>2 and r[2]]
            if len(set(ns))>1:rec['varyingNormals']+=1
    findings=sum(r['missing']+r['collapsed']+r['outside'] for r in stats.values());bad+=findings
    report.append({'item':stem,'paintedMaterials':stats,'findings':findings})
    print(stem,json.dumps(stats,sort_keys=True))
Path('out/work/staves-surfaces.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('PAINTED SURFACE AUDIT:',bad,'findings')
raise SystemExit(bool(bad))
