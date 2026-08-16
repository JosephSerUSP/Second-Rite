#!/usr/bin/env python3
"""G6 dependency preflight, then the byte-preserved editor screenshot driver.

The actual capture implementation lives in editor-screens-core.py. Keeping this
wrapper tiny makes dependency failures causal: a fresh worktree without the
ignored Three.js vendor surface fails before Node, Chrome, or any screenshot
wait expression can hide the missing module behind a timeout (#579).
"""

import json
import os
from pathlib import Path
import runpy
import sys

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("SECOND_RITE_G6_ROOT", str(DEFAULT_ROOT))).resolve()
CORE = Path(__file__).with_name("editor-screens-core.py")
REPAIR = "npm ci --ignore-scripts && node tools/editor/sync-three-vendor.js"
REQUIRED_THREE = (
    "three.module.js",
    "three.core.js",
    "OrbitControls.js",
    "TransformControls.js",
    "OBJLoader.js",
    "MTLLoader.js",
)


def required_paths(root=ROOT):
    vendor = Path(root) / "tools" / "editor" / "vendor" / "three"
    return [vendor / name for name in REQUIRED_THREE]


def missing_dependencies(root=ROOT):
    return [path for path in required_paths(root) if not path.is_file()]


def emit_missing(paths, root=ROOT):
    root = Path(root)
    relative = []
    for path in paths:
        try:
            relative.append(path.relative_to(root).as_posix())
        except ValueError:
            relative.append(str(path))
    payload = {"kind": "three-vendor", "paths": relative, "repair": REPAIR}
    print("G6_DEPENDENCY_MISSING_JSON " + json.dumps(payload, sort_keys=True))
    print("editor-screens.py: required Three.js editor vendor files are missing:", file=sys.stderr)
    for path in relative:
        print("  - " + path, file=sys.stderr)
    print("Prepare them with: " + REPAIR, file=sys.stderr)


def main():
    missing = missing_dependencies()
    if missing:
        emit_missing(missing)
        return 86
    if os.environ.get("SECOND_RITE_G6_PREFLIGHT_ONLY") == "1":
        print("G6 DEPENDENCIES OK")
        return 0
    if not CORE.is_file():
        print("editor-screens.py: missing capture core: " + str(CORE), file=sys.stderr)
        return 87
    # run_name='__main__' preserves the existing CLI and its SystemExit behavior.
    runpy.run_path(str(CORE), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
