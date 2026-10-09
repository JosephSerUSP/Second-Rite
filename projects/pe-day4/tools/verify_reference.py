#!/usr/bin/env python3
"""Validate the PE Day 4 public reference contract (#1464)."""
from __future__ import annotations
import json
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference"
VALID_STATUSES = {"verified", "corroborated", "single_source", "prototype", "unknown"}
PRIMARY_KINDS = {"primary_manual", "owner_observation", "game_data"}

def load(name):
    with (REF / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)

def fail(errors, message): errors.append(message)

def walk_tagged_values(value, path="root"):
    if isinstance(value, dict):
        if any(k in value for k in ("status", "factLinks", "sourceIds")): yield path, value
        for key, child in value.items(): yield from walk_tagged_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value): yield from walk_tagged_values(child, f"{path}[{i}]")

def validate_facts(data, errors):
    sources = data.get("sources") or {}; groups = {}
    for sid, source in sources.items():
        group = source.get("independenceGroup")
        if not group: fail(errors, f"source {sid}: missing independenceGroup")
        groups[sid] = group
    facts = data.get("facts") or []; ids = [f.get("id") for f in facts]
    if None in ids or len(ids) != len(set(ids)): fail(errors, "facts: ids must be present and unique")
    fact_ids = set(ids)
    for fact in facts:
        fid = fact.get("id", "<missing>"); status = fact.get("status"); refs = fact.get("sources")
        if "value" not in fact: fail(errors, f"{fid}: missing value")
        if status not in VALID_STATUSES: fail(errors, f"{fid}: invalid status {status!r}"); continue
        if not isinstance(refs, list): fail(errors, f"{fid}: sources must be an array"); refs = []
        missing = [sid for sid in refs if sid not in sources]
        if missing: fail(errors, f"{fid}: unknown sources {missing}")
        independent = {groups[sid] for sid in refs if sid in groups}
        if status == "corroborated" and len(independent) < 2: fail(errors, f"{fid}: corroborated needs >=2 independent source groups")
        if status == "verified" and (not refs or not any(sources[s].get("kind") in PRIMARY_KINDS for s in refs if s in sources)): fail(errors, f"{fid}: verified needs a primary/direct source")
        if status == "single_source" and len(independent) != 1: fail(errors, f"{fid}: single_source needs exactly one independent source group")
        if status == "unknown" and fact.get("value") is not None: fail(errors, f"{fid}: unknown value must stay null")
        if status == "prototype" and not fact.get("note"): fail(errors, f"{fid}: prototype needs a rationale note")
    for d in data.get("disagreements") or []:
        unknown = [fid for fid in d.get("factIds") or [] if fid not in fact_ids]
        if unknown: fail(errors, f"disagreement {d.get('id')}: unknown fact ids {unknown}")
    return fact_ids, set(sources)

def validate_route(route, fact_ids, errors):
    vocab = set(route.get("stateVocabulary") or []); nodes = route.get("nodes") or []; edges = route.get("edges") or []
    node_ids = [n.get("id") for n in nodes]; node_set = set(node_ids)
    for group in route.get('exclusiveStateGroups') or []:
        if len(group) < 2 or len(group) != len(set(group)) or any(state not in vocab for state in group):
            fail(errors, 'route: invalid mutually exclusive state group')
    if None in node_ids or len(node_ids) != len(node_set): fail(errors, "route: node ids must be present and unique")
    if route.get("start") not in node_set: fail(errors, "route: invalid start node")
    terminal = route.get("terminal")
    if terminal not in vocab: fail(errors, "route: terminal state is not declared")
    edge_ids = [e.get("id") for e in edges]
    if None in edge_ids or len(edge_ids) != len(set(edge_ids)): fail(errors, "route: edge ids must be present and unique")
    def check(owner, entry):
        for field in ("requiresAll", "grants", "clears"):
            for state in entry.get(field) or []:
                if state not in vocab: fail(errors, f"{owner}: undeclared state {state!r}")
        if entry.get("fact") is not None and entry["fact"] not in fact_ids: fail(errors, f"{owner}: unknown fact {entry['fact']!r}")
    interactions = {}; outgoing = {}
    for node in nodes:
        for state in node.get("entryRequirements") or []:
            if state not in vocab: fail(errors, f"node {node.get('id')}: undeclared entry requirement {state!r}")
        seen = set()
        for it in node.get("interactions") or []:
            if not it.get("id") or it["id"] in seen: fail(errors, f"node {node.get('id')}: invalid interaction id"); continue
            seen.add(it["id"]); interactions.setdefault(node["id"], []).append(it); check(f"interaction {node['id']}.{it['id']}", it)
    for edge in edges:
        if edge.get("from") not in node_set or edge.get("to") not in node_set: fail(errors, f"edge {edge.get('id')}: invalid endpoint"); continue
        check(f"edge {edge.get('id')}", edge); outgoing.setdefault(edge["from"], []).append((edge["to"], edge))
        if edge.get("oneShot") and not edge.get("grants"): fail(errors, f"edge {edge['id']}: oneShot needs a persistent grant marker")
        if edge.get("bidirectional"): outgoing.setdefault(edge["to"], []).append((edge["from"], edge))
    def mutate(flags, entry):
        out=set(flags)
        for state in entry.get("clears") or []: out.discard(state)
        out.update(entry.get("grants") or []); return frozenset(out)
    requirements = route.get("criticalRequirements") or {}
    targets = route.get("requirementTargets") or {}
    for name, needed in requirements.items():
        if name not in targets: fail(errors, f"critical requirement {name}: missing target")
        for state in needed:
            if state not in vocab: fail(errors, f"critical requirement {name}: undeclared state {state!r}")
    for name, target in targets.items():
        if name not in requirements: fail(errors, f"requirement target {name}: no requirements")
        if len(target) != 1 or (target.get('state') not in vocab and target.get('node') not in node_set):
            fail(errors, f"requirement target {name}: invalid state/node target")
    node_defs = {node['id']: node for node in nodes}
    start=(route.get("start"), frozenset()); q=deque([start]); seen={start}; reached=False
    while q:
        node, flags=q.popleft()
        needed = node_defs.get(node, {}).get('entryRequirements') or []
        if not all(state in flags for state in needed):
            fail(errors, f"route: {node} reachable without entry requirements {needed}")
            break
        if any(sum(state in flags for state in group) > 1 for group in route.get('exclusiveStateGroups', [])):
            fail(errors, 'route: mutually exclusive states are simultaneously reachable')
            break
        invalid = False
        for name, target in targets.items():
            if target.get('state') in flags or target.get('node') == node:
                needed = requirements.get(name, [])
                if not all(state in flags for state in needed):
                    fail(errors, f"route: {name} reachable without critical requirements {needed}")
                    invalid = True
                    break
        if invalid: break
        if terminal in flags: reached=True; continue
        for it in interactions.get(node, []):
            if all(r in flags for r in it.get("requiresAll") or []):
                nxt=(node, mutate(flags,it))
                if nxt not in seen: seen.add(nxt); q.append(nxt)
        for dst, edge in outgoing.get(node, []):
            if edge.get('oneShot') and edge.get('grants') and edge['grants'][0] in flags: continue
            if all(r in flags for r in edge.get("requiresAll") or []):
                nxt=(dst, mutate(flags,edge))
                if nxt not in seen: seen.add(nxt); q.append(nxt)
    if not reached: fail(errors, f"route: terminal {terminal!r} is not statefully reachable")
    return node_set, vocab

def validate_snapshot(snapshot, fact_ids, source_ids, errors):
    for path, tagged in walk_tagged_values(snapshot):
        if tagged.get("status") is not None and tagged["status"] not in VALID_STATUSES: fail(errors, f"{path}: invalid status")
        if tagged.get('status') == 'unknown' and tagged.get('value') is not None: fail(errors, f"{path}: unknown value must remain null")
        for fid in tagged.get("factLinks") or []:
            if fid not in fact_ids: fail(errors, f"{path}: unknown fact {fid!r}")
        for sid in tagged.get("sourceIds") or []:
            if sid not in source_ids: fail(errors, f"{path}: unknown source {sid!r}")
    if snapshot.get("entry",{}).get("scene") != "hospital_entrance": fail(errors, "snapshot: entry must match route start")
    level = snapshot.get('actor', {}).get('level')
    if type(level) is not int or level < 1: fail(errors, 'snapshot: level must be a positive integer')
    item_ids = set()
    for item in snapshot.get('inventory') or []:
        item_id = item.get('id')
        if not isinstance(item_id, str) or not item_id or item_id in item_ids: fail(errors, 'snapshot: invalid/duplicate item id')
        item_ids.add(item_id)
        if type(item.get('quantity')) is not int or item['quantity'] < 1: fail(errors, f'snapshot: invalid quantity for {item_id}')

def validate_generalization(data, errors):
    ids=[]
    for cap in data.get("capabilities") or []:
        cid=cap.get("id"); ids.append(cid)
        for field in ("hospitalNeed","otherPeCase","preferredLayer","engineChangePolicy"):
            if not cap.get(field): fail(errors, f"generalization {cid}: missing {field}")
        if cap.get("secondGateAnalogue") is None and "project-local" not in cap.get("engineChangePolicy",""): fail(errors, f"generalization {cid}: no Second Gate analogue; keep it project-local")
    if None in ids or len(ids)!=len(set(ids)): fail(errors, "generalization: ids must be present and unique")

def validate_capture_plan(data, fact_ids, source_ids, errors):
    ids = set()
    for entry in data.get('scenarios') or []:
        eid = entry.get('id')
        if not eid or eid in ids: fail(errors, 'capture plan: invalid/duplicate scenario id')
        ids.add(eid)
        if entry.get('status') != 'unmeasured': fail(errors, f'capture {eid}: promote observations into facts with evidence before changing this protocol')
        if not entry.get('observe'): fail(errors, f'capture {eid}: no observations specified')
        for fid in entry.get('factLinks') or []:
            if fid not in fact_ids: fail(errors, f'capture {eid}: unknown fact {fid}')
        for sid in entry.get('sources') or []:
            if sid not in source_ids: fail(errors, f'capture {eid}: unknown source {sid}')

def main():
    errors=[]; facts=load("facts.json"); route=load("route.json"); snap=load("canonical-start.json"); gen=load("generalization.json")
    fact_ids, source_ids=validate_facts(facts,errors); nodes,vocab=validate_route(route,fact_ids,errors); validate_snapshot(snap,fact_ids,source_ids,errors); validate_generalization(gen,errors)
    validate_capture_plan(load('capture-plan.json'), fact_ids, source_ids, errors)
    if errors:
        for error in errors: print("ERROR:", error)
        raise SystemExit(1)
    counts={}
    for fact in facts["facts"]: counts[fact["status"]]=counts.get(fact["status"],0)+1
    print(f"PE DAY 4 REFERENCE OK | {len(fact_ids)} facts {counts} | {len(nodes)} route nodes | {len(vocab)} states | {len(gen['capabilities'])} generalization entries")

if __name__ == "__main__": main()
