from __future__ import annotations

import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "towngen"
SCREENS = {
    "port": ("1713,437,49,97", 534, .515, "west_quay"),
    "churchyard": ("1916,205,54,115", 320, .425, "port_climb"),
    "cortico": ("765,362,70,127", 489, .485, "lodging_door"),
    "market": ("1693,326,61,136", 462, .355, "east_quay"),
    "quay": ("1091,422,61,136", 558, .38, "pub_door"),
    "weaponsmith": ("661,338,135,157", 495, .22, "exit_door"),
    "alicias_padaria": ("932,347,135,157", 504, .235, "exit_door"),
    "pub": ("779,347,77,175", 522, .265, "exit_door"),
    "chapel": ("985,362,74,181", 543, .31, "exit_door"),
    "house_laura": ("1163,362,102,181", 543, .37, "exit_door"),
    "house_alicia": ("355,326,102,193", 519, .195, "exit_door"),
    "lodging": ("1008,326,146,193", 519, .21, "exit_door"),
}

def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def main():
    staging=json.loads((ROOT/"projects/hichaukitoden-game/assets/authoring/town-plates/staging.json").read_text())
    for key,(box,feet,scale,label) in SCREENS.items():
        raw=OUT/key/"replacement/raw-001.png"
        x,y,w,h=map(int,box.split(','))
        target_x=staging["screens"][key]["winner"]["observedPlateX"][label]
        # The support line is deliberately explicit and reviewed in raw space.
        # Its centre is the paired contact row; the small slope records the
        # painted perspective without changing the runtime ground row.
        supports=[[0,feet-10],[1086,feet],[2171,feet+10]]
        ann={
            "screen":key,"sourceSize":[2172,724],"sourceSha256":sha(raw),
            "runtimeCell":[24,48],"targetGroundY":136,
            "actorRefs":[{
                "id":"primary_same_plane","box":[x,y,w,h],"feetY":feet,
                "identity":"adult_or_runtime_scale_reference",
                "eligible":True,"reason":"fully visible standing figure on the action-plane",
                "sourceVisibleHeight":h,"targetVisibleHeight":round(h*scale,4)
            }],
            "floorSupports":supports,
            "portalPairs":[{"label":label,"sourceX":round(target_x/scale,3),"sourceY":feet,"targetX":target_x}],
            "maxFloorResidualPx":15,"maxScaleMad":0.01,
            "excludedRefs":["all detections not demonstrably on the same continuous action plane"],
            "policy":"raw-only v2 calibration; no promoted plate is an input; empty lower border is intentional"
        }
        out=OUT/key/"replacement/calibration-v2"; out.mkdir(parents=True,exist_ok=True)
        (out/"annotation.json").write_text(json.dumps(ann,indent=2)+"\n")

if __name__=='__main__': main()
