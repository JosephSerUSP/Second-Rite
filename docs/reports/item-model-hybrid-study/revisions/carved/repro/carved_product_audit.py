"""Saved-product controls, UV coverage and unchanged upstream hashes."""
from pathlib import Path
import json,hashlib,collections,subprocess,shutil
import numpy as np
from PIL import Image
BASE=Path('docs/reports/item-model-hybrid-study');OUT=BASE/'revisions/carved';P=Path('out/work/carved-products')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 v=[];uv=[];faces=[]
 for line in p.read_text().splitlines():
  f=line.split()
  if not f:continue
  if f[0]=='v':v.append(tuple(map(float,f[1:4])))
  elif f[0]=='vt':uv.append(tuple(map(float,f[1:3])))
  elif f[0]=='f':faces.append([(int(c.split('/')[0])-1,int(c.split('/')[1])-1) for c in f[1:]])
 return v,uv,faces
G=read(P/'carved_capsule_geometry.obj');B=read(P/'carved_capsule_baked.obj')
def triangles(data):
 v,uv,faces=data
 return collections.Counter(tuple(sorted(tuple(round(c,6) for c in v[i]) for i,j in f)) for f in faces)
assert triangles(G)==triangles(B),'Geometry changed between geometry and surface controls'
assert (P/'carved_capsule_features.obj').read_text().replace('mtllib carved_capsule_features.mtl','mtllib carved_capsule_baked.mtl')==(P/'carved_capsule_baked.obj').read_text()
assert (P/'carved_capsule_features.mtl').read_text()==(P/'carved_capsule_baked.mtl').read_text().replace('carved_baked.png','carved_features.png')
coverage=np.zeros((1536,1536),dtype=np.uint8);areas=[];findings=[]
for index,f in enumerate(B[2]):
 pts=np.asarray([B[1][j] for i,j in f]);a,b,c=pts;det=np.cross(b-a,c-a);areas.append(float(abs(det)*.5))
 if abs(det)<1e-12 or np.any(pts<0) or np.any(pts>1):findings.append(index);continue
 p=pts*1536;low=np.maximum(0,np.floor(p.min(axis=0)-.5).astype(int));high=np.minimum(1535,np.ceil(p.max(axis=0)-.5).astype(int))
 if np.any(high<low):continue
 yy,xx=np.mgrid[low[1]:high[1]+1,low[0]:high[0]+1];q=np.stack([xx+.5,yy+.5],axis=-1)/1536
 first=((q[:,:,0]-a[0])*(c[1]-a[1])-(q[:,:,1]-a[1])*(c[0]-a[0]))/det
 second=((b[0]-a[0])*(q[:,:,1]-a[1])-(b[1]-a[1])*(q[:,:,0]-a[0]))/det
 inside=(first>1e-8)&(second>1e-8)&(first+second<1-1e-8)
 coverage[low[1]:high[1]+1,low[0]:high[0]+1]+=inside
assert not findings,findings[:10]
overlap=int(np.count_nonzero(coverage>1));assert overlap==0,overlap
unchanged=[]
for p in sorted((BASE/'source-project/assets/authoring/items').glob('*.blend')):
 rel=p.as_posix();previous=subprocess.check_output(['git','show','09b865f20faec85a7e4e55b9e3ea5dc8fc2090f8:'+rel]);assert hashlib.sha256(previous).hexdigest()==sha(p);unchanged.append({'path':rel,'sha256':sha(p)})
for path in [BASE/'reference-carved.png',BASE/'reference-salvage.png',BASE/'hybrid_surface_atlas.png',BASE/'panels.png']:
 prior=subprocess.check_output(['git','show','09b865f20faec85a7e4e55b9e3ea5dc8fc2090f8:'+path.as_posix()]);assert hashlib.sha256(prior).hexdigest()==sha(path)
files=[]
for p in sorted(P.iterdir()):
 if p.suffix in ['.obj','.mtl','.png']:files.append({'file':p.name,'sha256':sha(p)})
render={}
for tag in ['carved-baked96','carved-baked192','carved-cardinal96']:
 a=np.asarray(Image.open(Path('out/review')/tag/'features.png').convert('RGB'),dtype=np.int16);b=np.asarray(Image.open(Path('out/review')/tag/'baked.png').convert('RGB'),dtype=np.int16);d=b-a
 render[tag]={'differentPixels':int(np.count_nonzero(np.any(d!=0,axis=2))),'meanAbsoluteChannelDeltaAllPixels':float(np.mean(np.abs(d))),'brightenedChannels':int(np.count_nonzero(d>0)),'darkenedChannels':int(np.count_nonzero(d<0))}
report={'geometryAndBakedTrianglePositionsMatch':True,'featuresAndBakedOnlyTextureBindingsDiffer':True,'uvFindings':findings,'bakedUVMinTriangleArea':min(areas),'bakedUVArea':sum(areas),'atlasInteriorCoverageFraction':float(np.count_nonzero(coverage)/coverage.size),'atlasInteriorOverlappingTexels':overlap,'overlapTest':'1536x1536 texel centres strictly inside triangles; shared edges excluded. Does not prove absence of subtexel overlaps.','unchangedOriginalSources':unchanged,'unchangedOriginalGeneratedImages':True,'productHashes':files,'bakeRuntimeDelta':render}
(OUT/'product-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
print('REVISION PRODUCT AUDIT OK: matched geometry, material-only controls, unique UVs, upstream hashes unchanged');print(json.dumps(render))
