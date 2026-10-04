"""Gate the adopted Project town: packages, arrival anchors and reachability.

The legacy generator is retired. Authored maps are the live authority.
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_REL = os.path.join("projects", "hichaukitoden-game")


def check_environment_packages():
    """Assert that every map declaring an environmentPackage resolves on disk."""
    errors = []
    maps_dir = os.path.join(ROOT, PROJECT_REL, "data", "maps")
    if not os.path.isdir(maps_dir):
        return ["data/maps directory not found at %s" % maps_dir]
    for fname in sorted(os.listdir(maps_dir)):
        if not fname.endswith(".json") or fname == "index.json":
            continue
        path = os.path.join(maps_dir, fname)
        with io.open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        traversal = data.get("traversal") or {}
        pkg_rel = traversal.get("environmentPackage")
        if pkg_rel:
            pkg_path = os.path.join(ROOT, PROJECT_REL, pkg_rel)
            if not os.path.isfile(pkg_path):
                errors.append("map %s: environmentPackage does not exist: %s"
                              % (data.get("id", fname), pkg_rel))
    return errors


def find_load_map_commands(commands):
    found = []
    if not isinstance(commands, list):
        return found
    for cmd in commands:
        if isinstance(cmd, dict):
            if cmd.get("cmd") == "LOAD_MAP":
                found.append(cmd)
            for v in cmd.values():
                if isinstance(v, list):
                    found.extend(find_load_map_commands(v))
    return found


def check_door_and_arrival_resolution():
    """Assert door target/arrival anchor resolution and town reachability."""
    errors = []
    maps_dir = os.path.join(ROOT, PROJECT_REL, "data", "maps")
    # The active town is the Project's authored bounded-lane graph.
    with open(os.path.join(maps_dir, "index.json"), encoding="utf-8") as handle:
        index = json.load(handle)
    town_map_ids = set()
    for name in index["files"]:
        with open(os.path.join(maps_dir, name), encoding="utf-8") as handle:
            row = json.load(handle)
        if row.get("category") != "fixture" and row.get("traversal", {}).get("provider") == "bounded_lane":
            town_map_ids.add(row["id"])
    town_maps = {}
    for mid in town_map_ids:
        map_file = os.path.join(maps_dir, "%d.json" % mid)
        if not os.path.isfile(map_file):
            errors.append("town map %d is missing on disk (%s)" % (mid, map_file))
            continue
        with io.open(map_file, "r", encoding="utf-8") as handle:
            town_maps[mid] = json.load(handle)

    adj = {mid: set() for mid in town_maps}
    edges_checked = 0

    for mid, data in sorted(town_maps.items()):
        events = data.get("events") or []
        for ev in events:
            load_cmds = find_load_map_commands(ev.get("commands"))
            for cmd in load_cmds:
                target_id = cmd.get("mapId")
                arrival = cmd.get("arrival")
                edges_checked += 1

                target_file = os.path.join(maps_dir, "%s.json" % target_id)
                if not os.path.isfile(target_file):
                    errors.append("map %d event %r -> target map %s does not exist"
                                  % (mid, ev.get("name"), target_id))
                    continue

                if target_id in town_maps:
                    target_data = town_maps[target_id]
                else:
                    with io.open(target_file, "r", encoding="utf-8") as handle:
                        target_data = json.load(handle)

                if target_id in town_map_ids:
                    adj[mid].add(target_id)

                if arrival:
                    doorways = (target_data.get("traversal") or {}).get("doorways") or []
                    doorway_anchors = {d.get("anchor") for d in doorways if isinstance(d, dict)}
                    env_pkg = (target_data.get("traversal") or {}).get("environmentPackage")
                    env_anchors = set()
                    if env_pkg:
                        env_file = os.path.join(ROOT, PROJECT_REL, env_pkg)
                        if os.path.isfile(env_file):
                            with io.open(env_file, "r", encoding="utf-8") as handle:
                                env_anchors = set((json.load(handle).get("anchors") or {}).keys())
                    target_events = target_data.get("events") or []
                    event_ids = {e.get("instanceId") for e in target_events if isinstance(e, dict)}
                    event_names = {e.get("name") for e in target_events if isinstance(e, dict)}

                    published = (
                        arrival in doorway_anchors
                        or arrival in env_anchors
                        or arrival in event_ids
                        or arrival in event_names
                        or any(eid and eid.endswith("-" + arrival) for eid in event_ids)
                    )
                    if not published:
                        errors.append("map %d event %r -> target map %d specifies arrival %r, "
                                      "which is NOT published by target map"
                                      % (mid, ev.get("name"), target_id, arrival))

    with open(os.path.join(ROOT, PROJECT_REL, "data", "system.json"), encoding="utf-8") as handle:
        spawn_map = json.load(handle)["spawn"]["mapId"]
    visited = {spawn_map}
    queue = [spawn_map]
    while queue:
        curr = queue.pop(0)
        for nxt in adj.get(curr, ()):
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)

    unreached = set(town_maps.keys()) - visited
    if unreached:
        errors.append("town maps unreachable from spawn map %d: %s"
                      % (spawn_map, sorted(unreached)))

    return errors, edges_checked


def main():
    pkg_errors = check_environment_packages()
    door_errors, edges_checked = check_door_and_arrival_resolution()
    print("town: verified %d door edges and arrival anchors" % edges_checked)
    errors = pkg_errors + door_errors
    for error in errors:
        print("  ERROR: " + error)
    if errors:
        return 1
    print("TOWNGEN CHECK OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
