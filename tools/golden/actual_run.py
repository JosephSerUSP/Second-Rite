#!/usr/bin/env python3
"""Scope G5/G6 gitignored actual-output trees to one gate run.

The pixel gates keep differing frames in `*-actual/` for side-by-side review.
Those directories are deliberately gitignored, so without an explicit run
boundary an older mismatch can survive indefinitely and later look like part of
a new triage. Starting a gate resets only its actual-output trees and stamps a
small marker that `triage.py` can use to distinguish current evidence from
legacy/unscoped leftovers.

This never touches owner-signed reference trees.
"""

import argparse
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MARKER_NAME = "_triage-run.json"
SCOPES = {
    "g5": ("tools/golden/screens-actual", "tools/golden/screens-actual-wide"),
    "g6": ("tools/golden/editor-screens-actual",),
}


def marker_path(directory):
    return os.path.join(directory, MARKER_NAME)


def reset_scope(scope, root=ROOT):
    """Reset only `scope`'s gitignored actual trees and stamp this run."""
    if scope not in SCOPES:
        raise ValueError("unknown actual-output scope: %s" % scope)

    prepared = []
    for rel in SCOPES[scope]:
        directory = os.path.join(root, *rel.split("/"))
        shutil.rmtree(directory, ignore_errors=True)
        os.makedirs(directory, exist_ok=True)
        payload = {"version": 1, "scope": scope, "output": rel}
        with open(marker_path(directory), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
        prepared.append(rel)
    return prepared


def read_marker(directory, expected_scope=None):
    """Return validated run metadata, or None for legacy/corrupt output."""
    try:
        with open(marker_path(directory), "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError, TypeError):
        return None

    if payload.get("version") != 1 or payload.get("scope") not in SCOPES:
        return None
    if expected_scope is not None and payload.get("scope") != expected_scope:
        return None
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scope", choices=sorted(SCOPES))
    args = parser.parse_args()
    for rel in reset_scope(args.scope):
        print("Prepared current-run actual output: %s/" % rel)


if __name__ == "__main__":
    main()
