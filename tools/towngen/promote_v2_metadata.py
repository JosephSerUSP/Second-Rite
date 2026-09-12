from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'projects/hichaukitoden-game/assets/authoring/town-plates/staging.json'
d=json.loads(p.read_text(encoding='utf-8'))
for key in d['screenOrder']:
    winner=d['screens'][key]['winner']
    record=json.loads((ROOT/'out/towngen'/key/'replacement/calibration-v2/calibration.json').read_text())
    base=f'out/towngen/{key}/replacement/calibration-v2'
    winner['calibration']=f'{base}/calibration.json'
    winner['review']=f'{base}/review/review.json'
    winner['visualPersonAudit']=f'{base}/calibration.json'
    winner['calibrationV2']={
        'source': 'immutable raw-001.png',
        'sourceSha256': record['sourceSha256'],
        'matrix': record['matrix'],
        'scale': record['scale'],
        'floorYAtSourceCentre': record['floorYAtSourceCentre'],
        'targetGroundY': record['targetGroundY'],
        'floorResidualMaxPx': record['floorResidualMaxPx'],
        'portalResidualsPx': record['portalResidualsPx'],
        'actorRefs': record['actorRefs'],
        'excludedRefs': record['excludedRefs'],
    }
    winner['calibrationCorrection']={
        'runtimeGroundY': 136,
        'actorPx': [24,48],
        'source': 'raw-only v2 identity-normalized actor and paired floor calibration',
        'scale': record['scale'],
        'matrix': record['matrix'],
    }
    d['screens'][key]['status']='accepted-replacement-v2'
    d['calibrationRecords'][key]=f'{base}/calibration.json'
p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
