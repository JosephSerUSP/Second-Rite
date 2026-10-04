"""Install a derived navigation candidate into a canonical disposable export."""
import json,copy,shutil,hashlib,sys
from pathlib import Path
from PIL import Image
R=Path(__file__).resolve().parents[7];O=R/'projects/hichaukitoden-game/assets/authoring/candidates/st_maria_layout/core-run';G=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else R/'out/st-maria-core-run/game';D=R/'projects/hichaukitoden-game/data/maps'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
d=read(O/'screen-contract.json');maps=[m for m in read(G/'data/maps.json') if m['id']<1000];byid={m['id']:m for m in maps};native=[];packages={};byname={r['id']:r for r in d['screens']};geometry=G/'assets/environments/review/core_run';geometry.mkdir(parents=True,exist_ok=True)
# A valid derived mesh remains available for inspection. The native plate owns the beauty draw.
(geometry/'support.obj').write_text('mtllib support.mtl\nv -1 0 0\nv 1 0 0\nv 1 100 0\nv -1 100 0\nvt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\nusemtl stone\nf 1/1 2/2 3/3 4/4\n',encoding='utf-8')
(geometry/'support.mtl').write_text('newmtl stone\nKd 1 1 1\nmap_Kd support.png\n',encoding='utf-8');Image.new('RGBA',(8,8),(135,130,110,255)).save(geometry/'support.png')
for row in d['screens']:
 ident=row['id'];folder=geometry/ident;folder.mkdir(exist_ok=True);shutil.copy2(O/'plates'/ident/'background.png',folder/'background.png');shutil.copy2(O/'plates'/ident/'foreground.png',folder/'foreground.png')
 plate=row['plate'];manifest=dict(contractVersion=1,renderMesh='../support.obj',materialLibrary='../support.mtl',textureAtlas='../support.png',collisionMesh=None,bounds=[-2,0,-2,2,row['span'],20],anchors={'spawn_player':dict(position=[0,row['span']/2,0])},bakedLighting=True,preRendered=dict(mode='layered_2d',cameraMode='panning',imageSize=[plate['width'],240],slicePositions=[plate['sliceY']],backgrounds=['background.png'],scenes=['background.png'],foregrounds=['foreground.png'],lane=dict(runtimeCenterY=plate['sliceY'],depthX=0),playerProjection=plate['playerProjection']),provenance=dict(sourceBlend=d['sourceBlend'],sourceSHA256=d['sourceSHA256'],sourceScreen=ident,plateRecord=plate['record'],reviewOnly=True))
 packages[ident]=manifest
 camera=dict(profile='town_sideview',target=dict(x=0,y=row['span']/2,z=0),distance=128/plate['playerProjection']['pixelsPerRuntimeY']/.25,yawDegrees=0,pitchDegrees=0,eyeHeight=2.2604166667,fovDegrees=28.072486935852957,nearPlane=.05,farPlane=128,projectionScale=dict(x=1,y=1),projectionFrame=dict(baseViewportWidth=256,baseViewportHeight=144,compositionWidth=256,canonicalCenterX=128,canonicalHorizonY=66),tracking=dict(axis='y',center=row['span']/2,minOffsetX=0,maxOffsetX=0,interpolationSpeed=12,movementInterpolationSpeed=14,animationFps=8))
 m=dict(id=row['mapId'],title='St. Maria / '+row['label'],intro='Core route authoring candidate',depth=0,safe=True,category='town',generation='Fixed',tileset='town_default',ceilingStyle='sky',music='town1',layout=['.'],spawn=dict(x=0,y=0,dir='E'),traversal=dict(provider='bounded_lane',environmentPackage='assets/environments/review/core_run/'+ident+'/environment.json',spawnAnchor='spawn_player',lane=dict(minY=0,maxY=row['span'],depthX=0,groundZ=0,speed=3.4),blockedRanges=[],camera=camera,doorways=[]),events=[],treasures=[],encounters=[],recruits=[])
 if row.get('groundProfile'):m['traversal']['lane']['groundProfile']=row['groundProfile']
 camera['target']['z']=2.2604
 camera.update(plate['runtimeOptics'])
 native.append(m)
ns={r['id']:next(m for m in native if m['id']==r['mapId']) for r in d['screens']}
def doorway(ident,anchor,y,target,arrival,name,commands=None,direction=None):
 m=ns[ident];y=max(0,min(byname[ident]['span'],y));instance='core-run-'+ident+'-'+anchor;eventId=m['id']*100+len(m['events'])+1
 packages[ident]['anchors'][anchor]=dict(position=[0,y,0]);direction=direction or ('left' if y==0 else 'right' if y==byname[ident]['span'] else 'away')
 m['traversal']['doorways'].append(dict(anchor=anchor,eventInstanceId=instance,radius=.65))
 event=dict(id=eventId,instanceId=instance,name=name,x=0,y=0,worldPosition=[0,y,0],trigger='bump',direction=direction,commands=commands if commands is not None else [dict(cmd='LOAD_MAP',mapId=target,arrival=arrival)])
 event['model']='assets/models/st_maria/transition_arrow.obj'
 m['events'].append(event)
for c in d['connections']:
 doorway(c['a'],'to-'+c['b'],c['aS'],byname[c['b']]['mapId'],'to-'+c['a'],byname[c['b']]['label'],direction=c['aDirection'])
 doorway(c['b'],'to-'+c['a'],c['bS'],byname[c['a']]['mapId'],'to-'+c['b'],byname[c['a']]['label'],direction=c['bDirection'])
# The workers stair completes the preparation circuit without retracing the market.
doorway('court','to-port',3,1008,'to-court','Workers stair to port',direction=d['workerCourtDirection']);doorway('port','to-court',d.get('workerPortArrivalS',2),1001,'to-port','Workers stair to Cortiço',direction=d['workerPortDirection'])
facilitymaps={'forge':29,'pub':21,'bakery':28,'passage-house':25,'chapel':22,'registry':33}
for row in d['buildings']:
 if not row['visitable']:continue
 ident=row['laneScreen'];anchor='door-'+row['id'];interior=facilitymaps[row['id']];doorway(ident,anchor,row['laneS'],interior,'exit_door',row['label'])
 for event in byid[interior]['events']:
  if event.get('instanceId','').endswith('exit_door'):
   event['commands']=[dict(cmd='LOAD_MAP',mapId=byname[ident]['mapId'],arrival=anchor)];event['name']='Out to '+byname[ident]['label'];event['direction']='toward'
gate=next(e for e in read(D/'16.json')['events'] if e.get('name')=='Labyrinth Gate');doorway('threshold','labyrinth-gate',18,None,None,'Labyrinth Gate',copy.deepcopy(gate['commands']))
# Preserve authored interactions and sprites in the candidate exterior addresses.
for sourceId,ident in [(17,'praca'),(18,'market'),(19,'quay'),(26,'court'),(31,'port'),(16,'churchyard')]:
 original=read(D/(str(sourceId)+'.json'));lane=original['traversal']['lane'];lo,hi=lane['minY'],lane['maxY']
 for event in original['events']:
  if not event.get('sprite') or not event.get('worldPosition'):continue
  e=copy.deepcopy(event);e['instanceId']='core-run-'+str(e.get('instanceId'));e['id']=ns[ident]['id']*100+len(ns[ident]['events'])+1;e['worldPosition']=[0,max(.9,min(byname[ident]['span']-.9,(event['worldPosition'][1]-lo)/(hi-lo)*byname[ident]['span'])),0];ns[ident]['events'].append(e)
# Unselected shipping exteriors remain data-valid but are outside this review graph.
selected=set(facilitymaps.values())
for m in maps:
 if m['id'] not in selected and m.get('traversal',{}).get('provider')=='bounded_lane':m.pop('traversal')
maps.extend(native);maps.sort(key=lambda m:m['id']);write(G/'data/maps.json',maps);system=read(G/'data/system.json');system['spawn']['mapId']=1001;write(G/'data/system.json',system)
for ident,manifest in packages.items():write(geometry/ident/'environment.json',manifest)
write(O/'runtime-stage.json',dict(sourceSHA256=d['sourceSHA256'],stage=str(G),screens=[dict(id=r['id'],mapId=r['mapId'],span=r['span']) for r in d['screens']],facilities=facilitymaps,scope='Disposable native candidate; shipping Project and canonical references unchanged',limits=['Depth approaches use map transfers; no stair animation is implied.','Source terrain grounding is checked separately.','Only the selected opening facilities are part of this candidate graph.']))
print('CORE NATIVE STAGE INSTALLED',len(native),'exteriors and',len(selected),'authored facility interiors')
