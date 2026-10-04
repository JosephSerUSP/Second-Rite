import bpy,json,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent;d=json.loads((O/'screen-contract.json').read_text(encoding='utf-8'));s=bpy.data.scenes['B7 Churchyard plate and ecological material study'];bpy.context.window.scene=s;bpy.context.view_layer.update()
assert Path(bpy.data.filepath).name==d['sourceBlend']
assert hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()==d['sourceSHA256']
def tree(o):return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
t=tree(next(o for o in s.objects if 'landforms' in o));bodies=[(o.name,tree(o)) for o in s.objects if o.type=='MESH' and not o.hide_render and ('place' in o or 'background_place' in o or 'labyrinth_surface' in o)]
checks=[]
for ident,points in [(x['id'],[p['p'] for p in x['profile']]) for x in d['screens']]+[(x['id'],x['profile']) for x in d['routes']]+[(x['id']+'-depth',[p['p'] for p in x.get('physicalProfile',[])]) for x in d['connections'] if x.get('physicalProfile')]:
 collisions=[];intrusions=[]
 for i,p in enumerate(points):
  v=Vector(p);hit=t.ray_cast(v+Vector((0,0,500)),Vector((0,0,-1)))[0]
  if hit is not None and hit.z>v.z+.035:intrusions.append(dict(index=i,height=hit.z-v.z))
  for name,body in bodies:
   for h in (.2,1,1.65):
    q=v+Vector((0,0,h))
    if body.ray_cast(q,Vector((0,0,1)))[0] is not None and body.ray_cast(q,Vector((0,0,-1)))[0] is not None:collisions.append(dict(index=i,body=name,height=h))
 checks.append(dict(id=ident,samples=len(points),collisions=collisions,intrusions=intrusions))
retained=[]
for b in d['buildings']:
 obj=s.objects[b['object']];vs=[obj.matrix_world@Vector(v) for v in obj.bound_box];bounds=[[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]];assert max(abs(bounds[a][i]-b['bounds'][a][i]) for a in range(2) for i in range(3))<.001;retained.append(b['id'])
r=dict(sourceSHA256=d['sourceSHA256'],retainedBuildings=retained,checks=checks,samples=sum(x['samples'] for x in checks),collisions=sum(len(x['collisions']) for x in checks),terrainIntrusions=sum(len(x['intrusions']) for x in checks),scope='Source lane and approach point checks; not swept body or owner play')
(O/'source-checks.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print('CORE CHECKS',r['samples'],r['collisions'],r['terrainIntrusions'],flush=True)
assert r['collisions']==0 and r['terrainIntrusions']==0
