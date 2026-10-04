"""Compare native transfer captures to their saved Blender graphics and mouths."""
import bpy,json,sys,hashlib
from pathlib import Path
from mathutils import Vector
c=Path(__file__).resolve().parent;r=c.parents[6]
sys.path.insert(0,str(r/'tools/blender'));import thestra_camera as optics
d=json.loads((c/'screen-contract.json').read_text(encoding='utf8'))
assert Path(bpy.data.filepath).name==d['sourceBlend']
assert hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()==d['sourceSHA256']
frames=json.loads((c/'runtime/town-B18-transfers/captures.json').read_text(encoding='utf8'))
s=bpy.data.scenes['B7 Churchyard plate and ecological material study'];bpy.context.window.scene=s
rows={row['mapId']:row for row in d['screens']};results=[]
for f in frames:
 if f['mapId'] not in rows:continue
 assert f['sourceSHA256']==d['sourceSHA256']
 row=rows[f['mapId']];p=Vector(row['a'])+Vector(row['right'])*f['laneY'];p.z=row['groundReferenceZ']+f['groundZ']
 cam=optics.create_or_update_camera(row['plate']['record'],scene=s,name='Transfer verification '+row['id'],make_active=True);bpy.context.view_layer.update()
 pixel=optics.project_world_point(s,cam,p);native=f['composition'];source=[pixel[0]+native['platePanX'],pixel[1]]
 error=[abs(source[0]-native['laneScreenX']),abs(source[1]-native['laneScreenY'])]
 mouth=next(x for x in d['transferMouths'] if x['screen']==row['id'] and x['anchor']==f['anchor'])
 assert abs(mouth['laneS']-f['laneY'])<.0001
 assert (Vector(mouth['point'])-p).length<.0001
 result=dict(screen=row['id'],anchor=f['anchor'],button=f['button'],sourcePixel=source,nativePixel=[native['laneScreenX'],native['laneScreenY']],errorPixels=error)
 if f['anchor'].startswith('door-'):
  building=next(b for b in d['buildings'] if 'door-'+b['id']==f['anchor']);doorX=optics.project_world_point(s,cam,Vector(building['threshold']))[0]+native['platePanX']
  result['doorPixelX']=doorX;result['doorHorizontalErrorPixels']=abs(doorX-native['laneScreenX'])
 results.append(result)
record=dict(sourceSHA256=d['sourceSHA256'],captures=len(frames),exteriorMouths=len(results),maximumErrorPixels=[max(x['errorPixels'][axis] for x in results) for axis in (0,1)],checks=results)
(c/'transfer-projection-checks.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print('TRANSFER PROJECTION ERRORS',record['maximumErrorPixels'],flush=True)
assert len(results)==len(d['transferMouths'])==27
assert all(max(x['errorPixels'])<1.1 for x in results),[x for x in results if max(x['errorPixels'])>=1.1]
assert all(x.get('doorHorizontalErrorPixels',0)<1.1 for x in results)
print('TRANSFER SOURCE/NATIVE GRAPHICS OK',len(results),flush=True)
