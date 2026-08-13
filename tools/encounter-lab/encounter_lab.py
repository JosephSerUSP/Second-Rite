#!/usr/bin/env python3
"""Deterministic encounter-model development lab (#374).

Tooling only. It consumes a resolved grid from the engine's existing
preview-map-inspection seam; it never changes production encounter behavior.
"""
from __future__ import annotations
import argparse, collections, json, math, os, random, subprocess, tempfile
from dataclasses import dataclass
from pathlib import Path

DIRS = {"N": (0,-1), "E": (1,0), "S": (0,1), "W": (-1,0)}
DIR_ORDER = ("N","E","S","W")
PRESENCE_PURSUIT_PER_STEP = 2.0
CHARACTERIZATION_RATES = (0.05, 0.10, 0.20)
CHARACTERIZATION_SEEDS = (37, 374, 811)

@dataclass(frozen=True)
class Cell:
    x:int; y:int

def passable(grid, c):
    return 0 <= c.y < len(grid) and 0 <= c.x < len(grid[c.y]) and grid[c.y][c.x] != "#"

def neighbors(grid, c):
    for d in DIR_ORDER:
        dx,dy=DIRS[d]; n=Cell(c.x+dx,c.y+dy)
        if passable(grid,n): yield d,n

def shortest_path(grid, start, goal):
    if start==goal: return [start]
    q=collections.deque([start]); prev={start:None}
    while q:
        c=q.popleft()
        for _,n in neighbors(grid,c):
            if n in prev: continue
            prev[n]=c
            if n==goal:
                out=[n]
                while out[-1]!=start: out.append(prev[out[-1]])
                return list(reversed(out))
            q.append(n)
    return None

def topology_distance(grid,start,goal):
    p=shortest_path(grid,start,goal)
    return None if p is None else len(p)-1

def distances(grid,start):
    q=collections.deque([start]); dist={start:0}
    while q:
        c=q.popleft()
        for _,n in neighbors(grid,c):
            if n not in dist: dist[n]=dist[c]+1; q.append(n)
    return dist

def arrival_beside(grid, landmark):
    for c in (Cell(landmark.x,landmark.y+1),Cell(landmark.x,landmark.y-1),Cell(landmark.x+1,landmark.y),Cell(landmark.x-1,landmark.y)):
        if passable(grid,c): return c
    raise ValueError("no passable arrival cell beside landmark")

def engine_map(repo, map_id, seed, lovec):
    mp=repo/"data"/"maps"/f"{map_id}.json"
    snap=json.loads(mp.read_text(encoding="utf-8"))
    # The production Studio bridge deliberately puts transient requests under
    # installRoot and passes a source-relative path because LOVE's
    # love.filesystem.read does not accept an arbitrary OS temp path. Mirror
    # that host contract here instead of inventing another file-access path.
    request_dir=repo/"tmp"/"encounter-lab"
    request_dir.mkdir(parents=True,exist_ok=True)
    fd,request_name=tempfile.mkstemp(prefix="map-inspection-",suffix=".json",dir=request_dir)
    os.close(fd); req=Path(request_name)
    try:
        req.write_text(json.dumps({"map":snap,"seed":seed}),encoding="utf-8")
        env=os.environ.copy(); env["SECOND_RITE_MAP_INSPECTION_REQUEST"]=req.relative_to(repo).as_posix()
        p=subprocess.run([lovec,".","preview-map-inspection",str(map_id)],cwd=repo,env=env,text=True,capture_output=True)
    finally:
        req.unlink(missing_ok=True)
    if p.returncode: raise RuntimeError(p.stdout+"\n"+p.stderr)
    a=p.stdout.index("MAP INSPECTION BEGIN")+len("MAP INSPECTION BEGIN")
    b=p.stdout.index("MAP INSPECTION END",a)
    payload=json.loads(p.stdout[a:b].strip())
    if payload.get("error"): raise RuntimeError(payload["error"])
    grid=payload["generated"]["grid"]
    ent=payload["generated"]["entrance"]; ext=payload["generated"]["exit"]
    start=arrival_beside(grid,Cell(ent["x"],ent["y"])); goal=arrival_beside(grid,Cell(ext["x"],ext["y"]))
    route=shortest_path(grid,start,goal)
    if not route: raise RuntimeError("engine-resolved entrance/exit have no route")
    return grid,route,{"kind":"engine-map-inspection","mapId":map_id,"mapSeed":seed,"title":payload["map"].get("title")}

def synthetic_fixture():
    grid=[
      "#############",
      "#.....#.....#",
      "#.###.#.###.#",
      "#.#...#...#.#",
      "#.#.#####.#.#",
      "#...#.....#.#",
      "###.#.#####.#",
      "#...#.......#",
      "#.#########.#",
      "#...........#",
      "#############",
    ]
    route=[Cell(1,1),Cell(2,1),Cell(3,1),Cell(4,1),Cell(5,1),Cell(5,2),Cell(5,3),Cell(4,3),Cell(3,3),Cell(3,4),Cell(3,5),Cell(2,5),Cell(1,5),Cell(1,4),Cell(1,3),Cell(1,2),Cell(1,1)]
    return grid,route,{"kind":"synthetic","id":"loop-branch-wall-dead-end-v1"}

def extend_route(route, steps):
    if len(route)<2: return route*steps
    cycle=route+list(reversed(route[1:-1])); return [cycle[i%len(cycle)] for i in range(steps+1)]

def spacing(encounters,total):
    gaps=[]; prev=0
    for s in encounters: gaps.append(s-prev); prev=s
    if encounters: gaps.append(total-encounters[-1])
    else: gaps=[total]
    return gaps

def summarize(encounters,total):
    gaps=spacing(encounters,total); between=[encounters[i]-encounters[i-1] for i in range(1,len(encounters))]
    return {"encounterCount":len(encounters),"spacing":{"min":min(gaps),"max":max(gaps),"mean":sum(gaps)/len(gaps),"distribution":dict(sorted(collections.Counter(gaps).items()))},"consecutiveEncounters":sum(1 for x in between if x==1),"longestDrySpell":max(gaps)}

def chance_model(rng,steps,rate,modifier):
    enc=[]; trace=[]
    for s in range(1,steps+1):
        p=max(0,min(1,rate*modifier(s,"chance"))); roll=rng.random(); hit=roll<p
        if hit: enc.append(s)
        trace.append({"step":s,"chance":p,"roll":roll,"encounter":hit})
    return enc,trace

def countdown_model(rng,steps,rate,modifier):
    mean=max(2,1/rate); lo=max(2,int(math.floor(mean*.45))); hi=max(lo+1,int(math.ceil(mean*1.55)))
    remaining=rng.randint(lo,hi); enc=[]; trace=[]
    for s in range(1,steps+1):
        remaining-=max(.01,modifier(s,"countdown")); hit=remaining<=0
        if hit: enc.append(s); remaining=rng.randint(lo,hi)
        trace.append({"step":s,"remaining":remaining,"encounter":hit})
    return enc,trace

def pressure_model(rng,steps,rate,modifier):
    mean=max(2,1/rate); base=1/mean; threshold=rng.uniform(.72,1.28); pressure=0; enc=[]; trace=[]
    for s in range(1,steps+1):
        pressure += base*modifier(s,"pressure"); danger=min(1,pressure/threshold); hit=pressure>=threshold
        trace.append({"step":s,"pressure":pressure,"threshold":threshold,"danger":danger,"encounter":hit})
        if hit: enc.append(s); pressure=0; threshold=rng.uniform(.72,1.28)
    return enc,trace

def presence_parameters(rate):
    mean=max(3,round(1/rate))
    return {"targetMeanSpacing":1/rate,"minimumSpawnDistance":max(3,mean//2),"pursuitTopologyMovesPerPlayerStep":PRESENCE_PURSUIT_PER_STEP}

def far_spawn(grid,player,rng,min_distance):
    ds=distances(grid,player); cells=[c for c,d in ds.items() if d>=min_distance]
    if not cells: cells=[c for c in ds if c!=player]
    cells.sort(key=lambda c:(c.y,c.x)); return cells[rng.randrange(len(cells))]

def direction_signal(grid,player,presence):
    path=shortest_path(grid,player,presence)
    if not path: return {"sector":None,"proximity":"none","strength":0}
    d=len(path)-1; sector=None
    if d:
        nxt=path[1]; dx,dy=nxt.x-player.x,nxt.y-player.y
        sector=next(k for k,v in DIRS.items() if v==(dx,dy))
    prox="contact" if d==0 else "near" if d<=2 else "mid" if d<=5 else "far"
    return {"sector":sector,"proximity":prox,"strength":1/(1+d)}

def player_move_separation(grid,presence,player_before,player_after):
    if not passable(grid,player_before) or not passable(grid,player_after):
        raise ValueError("player separation probe requires passable cells")
    if abs(player_before.x-player_after.x)+abs(player_before.y-player_after.y) != 1:
        raise ValueError("player separation probe requires one cardinal committed move")
    before=topology_distance(grid,presence,player_before)
    after=topology_distance(grid,presence,player_after)
    return {"before":before,"after":after,"delta":None if before is None or after is None else after-before}

def presence_model(rng,route,grid,rate,modifier):
    steps=len(route)-1; params=presence_parameters(rate); min_spawn=params["minimumSpawnDistance"]
    presence=far_spawn(grid,route[0],rng,min_spawn); enc=[]; trace=[]; move_acc=0.0
    for s in range(1,steps+1):
        player_before=route[s-1]; player=route[s]
        player_sep=player_move_separation(grid,presence,player_before,player)
        after_player_d=player_sep["after"]
        presence_before={"x":presence.x,"y":presence.y}
        move_acc += PRESENCE_PURSUIT_PER_STEP*max(0,modifier(s,"presence")); moved=[]
        while move_acc>=1.0 and presence!=player:
            p=shortest_path(grid,presence,player)
            if p and len(p)>1: presence=p[1]; moved.append({"x":presence.x,"y":presence.y})
            move_acc-=1.0
        after_presence_d=topology_distance(grid,presence,player)
        presence_delta=None if after_player_d is None or after_presence_d is None else after_presence_d-after_player_d
        hit=presence==player; sig=direction_signal(grid,player,presence)
        trace.append({
            "step":s,
            "player":{"x":player.x,"y":player.y},
            "authoritative":{
                "presence":{"x":presence.x,"y":presence.y},
                "presenceBeforePursuit":presence_before,
                "path":[{"x":c.x,"y":c.y} for c in (shortest_path(grid,presence,player) or [])],
                "distance":after_presence_d,
                "moved":moved,
                "separation":{
                    "beforePlayerMove":player_sep["before"],
                    "afterPlayerMove":after_player_d,
                    "afterPresencePursuit":after_presence_d,
                    "playerMovementDelta":player_sep["delta"],
                    "presencePursuitDelta":presence_delta,
                },
            },
            "playerFacing":{"directionalThreat":sig},
            "encounter":hit,
        })
        if hit: enc.append(s); presence=far_spawn(grid,player,rng,min_spawn); move_acc=0
    return enc,trace

def run_policy(name,seed,route,grid,rate,modifier):
    rng=random.Random(seed); steps=len(route)-1
    if name=="chance": enc,tr=chance_model(rng,steps,rate,modifier)
    elif name=="countdown": enc,tr=countdown_model(rng,steps,rate,modifier)
    elif name=="pressure": enc,tr=pressure_model(rng,steps,rate,modifier)
    elif name=="presence": enc,tr=presence_model(rng,route,grid,rate,modifier)
    else: raise ValueError(name)
    return {"model":name,"seed":seed,"summary":summarize(enc,steps),"encounterSteps":enc,"steps":tr}

def default_modifier(step,channel): return 1.0

def presence_characterization(grid,base_route,steps=240,rates=CHARACTERIZATION_RATES,seeds=CHARACTERIZATION_SEEDS):
    route=extend_route(base_route,steps)
    rows=[]
    for rate in rates:
        params=presence_parameters(rate); counts=[]
        for seed in seeds:
            enc,_=presence_model(random.Random(seed),route,grid,rate,default_modifier)
            counts.append({"seed":seed,"encounterCount":len(enc)})
        rows.append({"rate":rate,**params,"samples":counts})
    return {
        "scope":"fixed-fixture characterization only; not a general rate-normalization guarantee",
        "rateControls":"minimum spawn distance; pursuit speed remains fixed",
        "rows":rows,
    }

def run_lab(grid,base_route,identity,seed,steps,rate):
    route=extend_route(base_route,steps)
    runs=[run_policy(n,seed,route,grid,rate,default_modifier) for n in ("chance","countdown","pressure","presence")]
    return {
        "schemaVersion":2,
        "kind":"encounter-model-lab",
        "route":identity|{"committedSteps":steps},
        "calibration":{"targetPerStepRate":rate,"targetMeanSpacing":1/rate},
        "presenceCalibration":presence_characterization(grid,base_route,steps),
        "modifierSeam":{"contract":"modifier(step, channel) -> multiplier","default":1.0,"veilEconomics":"not implemented"},
        "runs":runs,
    }

def markdown_report(doc):
    lines=["# Encounter-model lab comparison","",f"Route: `{doc['route']}`","",f"Calibration target: {doc['calibration']['targetPerStepRate']:.3f} encounters/step (mean {doc['calibration']['targetMeanSpacing']:.1f} steps).","","| model | encounters | mean spacing | consecutive | longest dry spell |","|---|---:|---:|---:|---:|"]
    for r in doc["runs"]:
        s=r["summary"]; lines.append(f"| {r['model']} | {s['encounterCount']} | {s['spacing']['mean']:.2f} | {s['consecutiveEncounters']} | {s['longestDrySpell']} |")
    lines += ["","The comparison intentionally does not select a winner. `chance` is the production-control shape; `countdown` bounds spacing; `pressure` exposes normalized danger; `presence` stores exact coordinates/path and decomposed player/pursuit separation only under `authoritative`, while `playerFacing.directionalThreat` contains only coarse N/E/S/W proximity data.","","## Presence calibration limits","",f"Presence pursuit is fixed at {PRESENCE_PURSUIT_PER_STEP:.1f} topology moves per committed player step. The rate parameter changes minimum spawn distance but does not independently normalize pursuit speed, so similar counts in one seed/fixture are not a general rate-normalization guarantee.","","| rate | target mean | min spawn distance | fixed-seed encounter counts |","|---:|---:|---:|---|"]
    for row in doc["presenceCalibration"]["rows"]:
        counts=", ".join(f"{x['seed']}: {x['encounterCount']}" for x in row["samples"])
        lines.append(f"| {row['rate']:.2f} | {row['targetMeanSpacing']:.1f} | {row['minimumSpawnDistance']} | {counts} |")
    lines += ["","This characterization is deliberately descriptive evidence for this topology and seed set, not a production recommendation or proof of normalized rates."]
    return "\n".join(lines)+"\n"

def assert_cardinal_path(grid,cells):
    for c in cells:
        assert passable(grid,c), c
    for a,b in zip(cells,cells[1:]):
        assert abs(a.x-b.x)+abs(a.y-b.y)==1, (a,b)

def self_test():
    grid,route,_=synthetic_fixture()
    a,b=Cell(5,1),Cell(7,1); p=shortest_path(grid,a,b)
    assert p and len(p)-1 > 2, (a,b,p)
    d=direction_signal(grid,a,b); assert d["sector"] in DIR_ORDER

    # Falsifying topology cases: from the same branch point and fixed presence,
    # one committed player move goes away (+distance) while another approaches (-distance).
    presence=Cell(1,1); branch=Cell(3,5)
    away=player_move_separation(grid,presence,branch,Cell(3,4))
    approach=player_move_separation(grid,presence,branch,Cell(2,5))
    assert away["delta"] > 0, away
    assert approach["delta"] < 0, approach

    one=run_lab(grid,route,{"kind":"test"},12345,120,.1); two=run_lab(grid,route,{"kind":"test"},12345,120,.1)
    assert one==two, "same seed/route must replay byte-equivalent as data"
    pres=next(r for r in one["runs"] if r["model"]=="presence")
    assert all("authoritative" in s and "playerFacing" in s for s in pres["steps"])
    assert all("presence" not in s["playerFacing"] for s in pres["steps"])
    assert all("separation" in s["authoritative"] for s in pres["steps"])
    assert any(s["authoritative"]["separation"]["playerMovementDelta"] not in (None,0) for s in pres["steps"])
    assert all(s["authoritative"]["separation"]["presencePursuitDelta"] is None or s["authoritative"]["separation"]["presencePursuitDelta"] <= 0 for s in pres["steps"])
    for s in pres["steps"]:
        start=s["authoritative"]["presenceBeforePursuit"]
        moved=s["authoritative"]["moved"]
        cells=[Cell(start["x"],start["y"])]+[Cell(x["x"],x["y"]) for x in moved]
        assert_cardinal_path(grid,cells)
    assert len(one["presenceCalibration"]["rows"])==3
    return True

def engine_self_test(repo,lovec):
    # This acceptance proof intentionally uses the real engine-owned Map 2 path.
    # It does not substitute a Python map compiler or copied topology fixture.
    grid,route,ident=engine_map(repo,2,37402,lovec)
    assert ident["kind"]=="engine-map-inspection" and ident["mapId"]==2, ident
    assert ident.get("title"), ident
    assert len(route)>=2, route
    assert_cardinal_path(grid,route)
    grid2,route2,ident2=engine_map(repo,2,37402,lovec)
    assert grid==grid2 and route==route2 and ident==ident2, "fixed Map 2 seed must resolve deterministically"
    doc=run_lab(grid,route,ident,374,64,.10)
    assert doc["route"]["mapId"]==2 and doc["route"]["mapSeed"]==37402
    assert len(doc["runs"])==4
    return {"title":ident["title"],"routeCells":len(route),"committedSteps":64}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[2]); ap.add_argument("--lovec",default=os.environ.get("LOVEC","lovec")); ap.add_argument("--map",type=int,default=2); ap.add_argument("--map-seed",type=int,default=37402); ap.add_argument("--seed",type=int,default=374); ap.add_argument("--steps",type=int,default=240); ap.add_argument("--rate",type=float,default=.10); ap.add_argument("--synthetic",action="store_true"); ap.add_argument("--out",type=Path); ap.add_argument("--report",type=Path); ap.add_argument("--self-test",action="store_true"); ap.add_argument("--engine-self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test: self_test(); print("ENCOUNTER LAB SELF-TEST OK"); return
    if a.engine_self_test:
        proof=engine_self_test(a.repo,a.lovec); print(f"ENCOUNTER LAB MAP 2 ENGINE SELF-TEST OK: {proof['title']} / {proof['routeCells']} route cells")
        return
    if a.synthetic: grid,route,ident=synthetic_fixture()
    else: grid,route,ident=engine_map(a.repo,a.map,a.map_seed,a.lovec)
    doc=run_lab(grid,route,ident,a.seed,a.steps,a.rate); text=json.dumps(doc,indent=2,sort_keys=True)
    if a.out: a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(text+"\n",encoding="utf-8")
    else: print(text)
    if a.report: a.report.parent.mkdir(parents=True,exist_ok=True); a.report.write_text(markdown_report(doc),encoding="utf-8")
if __name__=="__main__": main()
