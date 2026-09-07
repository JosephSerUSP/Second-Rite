"""Gate: the St. Maria generator must still reproduce the town it owns.

`build_town.py` writes straight into `data/`. Nothing in a generated map says
so, which is how three doors came to be hand-added to Market Row on 27 Aug and
sat there for four days: correct in the shipped data, invisible to the
generator, and destined to be deleted by the next rebuild. The same silence
would have reverted map 20 - now the authored `lauras_smith` 3D room - back to
a flat plate with the wrong camera distance.

This gate regenerates the town into a throwaway copy of the Project and
compares the result against what is committed. A hand-edit to a generated map
now fails here instead of surviving until someone runs the generator.

It also gates two cross-reference invariants (#1011):
  1. Environment package existence: every map declaring a traversal environmentPackage
     resolves to an existing file on disk.
  2. Door target and arrival anchor resolution: every LOAD_MAP command resolves
     to an existing map, its arrival anchor is published by the target, and all
     town maps remain reachable from spawn (map 17).

    python tools/towngen/check_town.py

Exit 0 when the generator and Project agree and all references resolve, 1 when they drift.

Line endings are normalised before comparing. The generator writes LF; a
Windows checkout holds CRLF, so a byte comparison reports every line of every
file as different and tells you nothing.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from build_town import SCREENS, AUTHORED_NOT_GENERATED  # noqa: E402

PROJECT_REL = os.path.join("projects", "hichaukitoden-game")
ENV_REL = os.path.join("assets", "environments", "st_maria_town")

# Written by main() alongside the maps themselves.
EXTRA_FILES = [
    os.path.join("data", "maps", "index.json"),
    os.path.join("data", "engine.json"),
    os.path.join("data", "system.json"),
    os.path.join("data", "commonEvents.json"),
]


def owned_map_files():
    """The maps the generator claims. Anything else is authored by hand."""
    return [os.path.join("data", "maps", "%d.json" % screen["id"])
            for key, screen in SCREENS.items()
            if key not in AUTHORED_NOT_GENERATED]


def owned_environment_files():
    """Environment manifests are generator output too, not hand-editable data."""
    return [os.path.join(ENV_REL, key, "environment.json")
            for key in SCREENS if key not in AUTHORED_NOT_GENERATED]


def read_normalised(path):
    if not os.path.exists(path):
        return None
    with io.open(path, "rb") as handle:
        return handle.read().replace(b"\r\n", b"\n")


def regenerate(into):
    """Run the generator against a copy, so a check never writes to the tree."""
    project = os.path.join(into, PROJECT_REL)
    os.makedirs(os.path.join(project, "assets", "environments"), exist_ok=True)
    shutil.copytree(os.path.join(ROOT, PROJECT_REL, "data"),
                    os.path.join(project, "data"))
    shutil.copytree(os.path.join(ROOT, PROJECT_REL, ENV_REL),
                    os.path.join(project, ENV_REL))
    result = subprocess.run(
        [sys.executable, os.path.join(HERE, "build_town.py")],
        cwd=into, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        sys.stdout.write(result.stdout.decode("utf-8", "replace"))
        raise SystemExit("towngen: the generator itself failed (exit %d)"
                         % result.returncode)


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
    town_map_ids = {s["id"] for s in SCREENS.values()} | {29}
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

    spawn_map = 17
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
    drifted = []
    with tempfile.TemporaryDirectory(prefix="towngen-check-") as tmp:
        regenerate(tmp)
        for rel in owned_map_files() + owned_environment_files() + EXTRA_FILES:
            committed = read_normalised(os.path.join(ROOT, PROJECT_REL, rel))
            rebuilt = read_normalised(os.path.join(tmp, PROJECT_REL, rel))
            if committed != rebuilt:
                drifted.append(rel)

    print("towngen: checked %d generated maps + %d environment manifests + %d data files"
          % (len(owned_map_files()), len(owned_environment_files()), len(EXTRA_FILES)))
    for key in sorted(AUTHORED_NOT_GENERATED):
        print("towngen: map %d (%s) is authored, not generated - not checked"
              % (SCREENS[key]["id"], key))

    pkg_errors = check_environment_packages()
    if pkg_errors:
        print("")
        print("towngen: %d environment package error(s):" % len(pkg_errors))
        for err in pkg_errors:
            print("  ERROR: %s" % err)

    door_errors, edges_checked = check_door_and_arrival_resolution()
    print("towngen: verified %d town door edges and arrival anchors" % edges_checked)
    if door_errors:
        print("")
        print("towngen: %d door/arrival/reachability error(s):" % len(door_errors))
        for err in door_errors:
            print("  ERROR: %s" % err)

    if not drifted and not pkg_errors and not door_errors:
        print("TOWNGEN CHECK OK")
        return 0

    if drifted:
        print("")
        print("towngen: %d file(s) differ from what build_town.py produces:"
              % len(drifted))
        for rel in drifted:
            print("  %s" % rel.replace("\\", "/"))
        print("")
        print("These files are GENERATED. A hand-edit to them is not durable - the")
        print("next `python tools/towngen/build_town.py` will overwrite it.")
        print("")
        print("Fix it in one of two places, not in the map:")
        print("  * a door, an NPC or a plate  -> edit SCREENS in build_town.py,")
        print("    then re-run the generator;")
        print("  * the map is authored now and should stop being generated ->")
        print("    add its key to AUTHORED_NOT_GENERATED and say why.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

