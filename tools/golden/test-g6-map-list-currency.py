#!/usr/bin/env python3
"""G6 map-list currency check: detect when authored maps drift from G6 goldens.

G6 captures editor screens with the live Project loaded, so the left-sidebar
Map list is authored content. Adding, deleting or renaming maps in
projects/hichaukitoden-game/data/maps/ shifts the Map list in the sidebar and
causes 19 G6 editor frames to differ from reference goldens (Issue #1035).

This script compares the authored map list against the golden baseline
recorded in `tools/golden/g6-map-list-baseline.json`.

Usage:
    python tools/golden/test-g6-map-list-currency.py
    python tools/golden/test-g6-map-list-currency.py --strict
    python tools/golden/test-g6-map-list-currency.py --update
"""

import argparse
import io
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROJECT_MAPS = ROOT / "projects" / "hichaukitoden-game" / "data" / "maps"
BASELINE_PATH = HERE / "g6-map-list-baseline.json"

AFFECTED_FRAMES = [
    "asset-picker/sprite.png",
    "campaign-gen/default.png",
    "export/default.png",
    "icon-picker/default.png",
    "map-editor/command-selector.png",
    "map-editor/event-modal.png",
    "map-editor/generated-inspection-stale.png",
    "map-editor/generated-inspection.png",
    "map-editor/map-properties.png",
    "map-editor/mode-event.png",
    "map-editor/mode-light.png",
    "map-editor/mode-map.png",
    "map-editor/mode-override.png",
    "map-editor/workspace-event-gizmo.png",
    "map-editor/workspace-light.png",
    "map-editor/workspace-perspective.png",
    "map-editor/workspace-top-ortho.png",
    "model-picker/item-model.png",
    "studio/preferences.png",
]


def load_current_map_list():
    index_path = PROJECT_MAPS / "index.json"
    if not index_path.is_file():
        raise FileNotFoundError(f"Missing map index: {index_path}")
    with io.open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)
    maps = []
    for fname in index.get("files", []):
        map_path = PROJECT_MAPS / fname
        if not map_path.is_file():
            continue
        with io.open(map_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        maps.append({
            "id": data.get("id"),
            "file": fname,
            "title": data.get("title"),
        })
    return maps


def load_baseline():
    if not BASELINE_PATH.is_file():
        return None
    with io.open(BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_baseline(maps, commit_ref=None):
    payload = {
        "provenance": {
            "lastOwnerSignedCommit": commit_ref or "local",
            "description": "Map list as photographed in tools/golden/editor-screens/",
        },
        "maps": maps,
    }
    with io.open(BASELINE_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    print(f"Updated {BASELINE_PATH} with {len(maps)} maps.")


def compare_map_lists(current, baseline):
    cur_by_id = {m["id"]: m for m in current}
    base_by_id = {m["id"]: m for m in baseline.get("maps", [])}

    added_ids = sorted(set(cur_by_id.keys()) - set(base_by_id.keys()))
    removed_ids = sorted(set(base_by_id.keys()) - set(cur_by_id.keys()))
    renamed = []

    for mid in sorted(set(cur_by_id.keys()) & set(base_by_id.keys())):
        cur_t = cur_by_id[mid].get("title")
        base_t = base_by_id[mid].get("title")
        if cur_t != base_t:
            renamed.append((mid, base_t, cur_t))

    return added_ids, removed_ids, renamed, cur_by_id, base_by_id


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="exit with code 1 if authored maps differ from golden baseline")
    parser.add_argument("--update", action="store_true",
                        help="update g6-map-list-baseline.json to match current data/maps")
    args = parser.parse_args(argv)

    current_maps = load_current_map_list()

    if args.update:
        save_baseline(current_maps)
        return 0

    baseline = load_baseline()
    if not baseline:
        print(f"No baseline found at {BASELINE_PATH}. Run with --update to initialize.")
        return 1 if args.strict else 0

    added, removed, renamed, cur_by_id, base_by_id = compare_map_lists(current_maps, baseline)
    has_drift = bool(added or removed or renamed)

    if not has_drift:
        print("G6 MAP LIST CURRENCY OK (authored maps match golden baseline)")
        return 0

    base_commit = baseline.get("provenance", {}).get("lastOwnerSignedCommit", "unknown")
    print(f"G6 MAP LIST DRIFT: authored maps differ from golden baseline ({base_commit})")
    print("")
    if added:
        print("  Added maps:")
        for mid in added:
            print(f"    + Map {mid}: {cur_by_id[mid].get('title')!r} ({cur_by_id[mid].get('file')})")
    if removed:
        print("  Removed maps:")
        for mid in removed:
            print(f"    - Map {mid}: {base_by_id[mid].get('title')!r}")
    if renamed:
        print("  Renamed maps:")
        for mid, old_t, new_t in renamed:
            print(f"    * Map {mid}: {old_t!r} -> {new_t!r}")

    print("")
    print(f"  This drift shifts the editor's Map list sidebar across {len(AFFECTED_FRAMES)} frames:")
    for frame in AFFECTED_FRAMES:
        print(f"    - {frame}")
    print("")
    print("  Resolution: G6 reference frames require an owner-signed recapture:")
    print("    powershell -NoProfile -ExecutionPolicy Bypass -File tools/golden/capture-editor.ps1")
    print("  Then update the baseline:")
    print("    python tools/golden/test-g6-map-list-currency.py --update")

    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
