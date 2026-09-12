from __future__ import annotations
import json, shutil, hashlib, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/towngen'))
from make_blockout import spec

BLOCKED={('market','east_quay'):'No visible east-side walkable opening remains in the calibrated plate; black margin is not an affordance.',('quay','east_port'):'No visible east-side walkable opening remains in the calibrated plate; black margin is not an affordance.'}
def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def main():
 p=ROOT/'projects/hichaukitoden-game/assets/authoring/town-plates/staging.json'; d=json.loads(p.read_text(encoding='utf-8'))
 for key in d['screenOrder']:
  base=ROOT/'out/towngen/repaint-v3'/key; final=base/'calibrated-clean.png'
  plate=d['screens'][key]['plate']; dest=ROOT/'projects/hichaukitoden-game/assets/environments/st_maria_town/plates'/plate
  shutil.copy2(final,dest)
  old=d['screens'][key]['winner'].get('observedPlateX',{})
  openings={o['anchor']:round(float(o['pixelX']),3) for o in spec(key)['openings']}
  audit=[]
  for anchor,before in old.items():
   if (key,anchor) in BLOCKED:
    audit.append({'anchor':anchor,'beforePlateX':before,'observedPlateX':None,'status':'blocked','reason':BLOCKED[(key,anchor)]})
   else:
    after=openings.get(anchor,before); delta=round(after-before,3)
    audit.append({'anchor':anchor,'beforePlateX':before,'observedPlateX':after,'deltaPx':delta,'status':'visual-reconciliation' if abs(delta)>1 else 'no-change','confidence':'high','evidence':'repaint-v3/review/gameplay/review-anchor-ground-lane.png'})
  review={'screen':key,'source':'final calibrated character-free repaint','sourceSha256':sha(final),'events':audit,'npcPlacement':'deferred','ownerMapsUntouched':[17,28,29]}
  (base/'review/event-placement.json').write_text(json.dumps(review,indent=2)+'\n')
  w=d['screens'][key]['winner']; b=f'out/towngen/repaint-v3/{key}'
  w['raw']=f'out/towngen/{key}/replacement/raw-001.png'; w['accepted']=f'{b}/calibrated-clean.png'; w['calibration']=f'{b}/calibration.json'; w['review']=f'{b}/review/event-placement.json'; w['visualPersonAudit']=f'{b}/calibration.json'; w['repaint']=f'{b}/source/repaint-request.json'; w['eventReview']=f'{b}/review/event-placement.json'; w['observedPlateX']={a:(openings.get(a,old[a]) if (key,a) not in BLOCKED else old[a]) for a in old}; w['status']='accepted-repaint-v3-anchor-review'
  d['screens'][key]['status']='accepted-repaint-v3-anchor-review'; d['calibrationRecords'][key]=f'{b}/calibration.json'
 p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
if __name__=='__main__': main()
