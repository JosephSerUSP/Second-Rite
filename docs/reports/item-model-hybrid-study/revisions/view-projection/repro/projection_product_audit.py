"""Audit saved products and package the mesh-conditioned projection study."""
from pathlib import Path
import collections, hashlib, json, shutil, subprocess
import numpy as np
from PIL import Image, ImageDraw

BASE = Path('docs/reports/item-model-hybrid-study')
OUT = BASE/'revisions/view-projection'
PRODUCTS = Path('out/work/projection-products')
BASE_REF = '6ecf989751e4c1f3ab6b8a1f671f32013b187713'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    vertices, uvs, faces = [], [], []
    for line in p.read_text().splitlines():
        f = line.split()
        if not f:
            continue
        if f[0] == 'v':
            vertices.append(tuple(map(float, f[1:4])))
        elif f[0] == 'vt':
            uvs.append(tuple(map(float, f[1:3])))
        elif f[0] == 'f':
            faces.append([(int(c.split('/')[0])-1, int(c.split('/')[1])-1) for c in f[1:]])
    return vertices, uvs, faces

def triangles(data):
    vertices, _, faces = data
    return collections.Counter(tuple(sorted(tuple(round(c, 6) for c in vertices[i]) for i, j in f)) for f in faces)

previous = read(BASE/'revisions/carved/source-project/assets/models/items/carved_capsule_baked.obj')
current = read(PRODUCTS/'carved_capsule_projected.obj')
assert triangles(previous) == triangles(current), 'Projection changed geometry'
assert previous == current, 'Projection changed vertex order, triangle winding or baked UVs'
assert (PRODUCTS/'carved_capsule_single.obj').read_text().replace('mtllib carved_capsule_single.mtl', 'mtllib carved_capsule_projected.mtl') == (PRODUCTS/'carved_capsule_projected.obj').read_text()
assert (PRODUCTS/'carved_capsule_single.mtl').read_text() == (PRODUCTS/'carved_capsule_projected.mtl').read_text().replace('mesh_projection_multi.png', 'mesh_projection_single.png')

coverage = np.zeros((1536,1536), dtype=np.uint8)
areas = []
for face in current[2]:
    pts = np.asarray([current[1][j] for i,j in face])
    a,b,c = pts
    det = (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    assert abs(det) > 1e-12 and np.all(pts >= 0) and np.all(pts <= 1)
    areas.append(float(abs(det)*.5))
    p = pts*1536
    low = np.maximum(0, np.floor(p.min(axis=0)-.5).astype(int))
    high = np.minimum(1535, np.ceil(p.max(axis=0)-.5).astype(int))
    if np.any(high < low):
        continue
    yy,xx = np.mgrid[low[1]:high[1]+1,low[0]:high[0]+1]
    q = np.stack([xx+.5,yy+.5], axis=-1)/1536
    first = ((q[:,:,0]-a[0])*(c[1]-a[1])-(q[:,:,1]-a[1])*(c[0]-a[0]))/det
    second = ((b[0]-a[0])*(q[:,:,1]-a[1])-(b[1]-a[1])*(q[:,:,0]-a[0]))/det
    inside = (first>1e-8)&(second>1e-8)&(first+second<1-1e-8)
    coverage[low[1]:high[1]+1,low[0]:high[0]+1] += inside
assert not np.any(coverage > 1)

sample_coverage = {}
tex = OUT/'source-project/assets/authoring/items/_textures'
for stem in ['mesh_projection_single','mesh_projection_multi']:
    # OBJ UV origin is bottom-left; PNG scanlines are top-left.
    pixels = np.asarray(Image.open(tex/(stem+'_coverage.png')).convert('RGB'))[::-1].astype(float)
    mask = coverage > 0
    sample_coverage[stem] = float(np.mean((pixels[:,:,1] > pixels[:,:,0])[mask]))

unchanged = []
sources = sorted((BASE/'source-project/assets/authoring/items').glob('*.blend')) + sorted((BASE/'revisions/carved/source-project/assets/authoring/items').glob('*.blend'))
for path in sources + [BASE/n for n in ['reference-carved.png','reference-salvage.png','hybrid_surface_atlas.png','panels.png']]:
    old = subprocess.check_output(['git','show',BASE_REF+':'+path.as_posix()])
    assert hashlib.sha256(old).hexdigest() == sha(path)
    unchanged.append({'path':path.as_posix(),'sha256':sha(path)})

record = json.loads((OUT/'projection.json').read_text())
source = OUT/'source-project/assets/authoring/items/carved_capsule_projected.blend'
assert sha(source) == record['sourceSHA256']
for n in ['mesh-paint-v2.png','fixed-mesh-support.png']:
    assert sha(OUT/n) == sha(tex/n)
for item in record['bakes']:
    assert sha(tex/(item['name']+'.png')) == item['sha256']

models = OUT/'source-project/assets/models/items'
controls = OUT/'controls'
models.mkdir(parents=True, exist_ok=True)
controls.mkdir(parents=True, exist_ok=True)
for name in ['carved_capsule_projected.obj','carved_capsule_projected.mtl','mesh_projection_multi.png']:
    shutil.copy2(PRODUCTS/name,models/name)
for name in ['carved_capsule_single.obj','carved_capsule_single.mtl','mesh_projection_single.png']:
    shutil.copy2(PRODUCTS/name,controls/name)

for tag, dest in [('mesh-projection96','native96'),('mesh-projection192','native192'),('mesh-projection-cardinal96','cardinal96')]:
    target = OUT/dest
    target.mkdir(exist_ok=True)
    for p in (Path('out/review')/tag).glob('*.png'):
        shutil.copy2(p,target/p.name)

for cell,name,folder in [(96,'comparison.png','native96'),(192,'comparison192.png','native192'),(96,'comparison-cardinal.png','cardinal96')]:
    scale = 2 if cell == 96 else 1
    rows = [('previous','Previous procedural + contact bake'),('single','Mesh paint: front only + unseen fallback'),('multiview','Mesh paint: four views + unseen fallback')]
    images = [Image.open(OUT/folder/(stem+'.png')).convert('RGB') for stem,label in rows]
    width = max(im.width for im in images)*scale
    height = sum(im.height*scale+30 for im in images)+40
    board = Image.new('RGB',(width,height),(32,33,39))
    draw = ImageDraw.Draw(board)
    draw.text((12,10),f'Actual native item viewer | {cell}px cells'+(' | enlarged 2x nearest' if scale==2 else ''),fill='white')
    y = 40
    for (stem,label),im in zip(rows,images):
        draw.text((12,y),label,fill='white')
        board.paste(im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST),(0,y+25))
        y += im.height*scale+30
    board.save(OUT/name)

shutil.copy2('out/work/projection-source-evidence.json',OUT/'source-evidence.json')
source_views = OUT/'source-views'
source_views.mkdir(exist_ok=True)
for p in Path('out/work/projection-source-views').glob('*.png'):
    shutil.copy2(p,source_views/p.name)
report = {
    'base':BASE_REF,
    'exactVertexOrderTriangleWindingAndBakedUVsUnchanged':True,
    'singleAndMultiOnlyTextureBindingsDiffer':True,
    'vertices':len(current[0]),'triangles':len(current[2]),
    'atlasInteriorCoverageFraction':float(np.count_nonzero(coverage)/coverage.size),
    'atlasInteriorOverlappingTexels':0,'minimumUVTriangleArea':min(areas),
    'uvTestBoundary':'1536-square texel centres strictly inside triangles, shared edges excluded. Not a subtexel overlap proof.',
    'observedInteriorTexelFraction':sample_coverage,
    'coverageBoundary':'Green dominance in actual coverage bakes on UV triangle interiors. Reports sampled paint availability, not correspondence or art acceptance.',
    'unchangedPriorSourcesAndGeneratedImages':unchanged,
    'sourceSHA256':sha(source),
    'canonicalProductHashes':[{'file':p.name,'sha256':sha(p)} for p in sorted(models.iterdir())],
}
(OUT/'product-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
print('PROJECTION PRODUCT AUDIT OK: exact geometry and baked UV preservation, material-only controls, unchanged prior sources/images')
print(json.dumps(sample_coverage))
