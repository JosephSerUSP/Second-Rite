#!/usr/bin/env python3
"""Focused regression coverage for #579 without Chrome, Node, or Three.js."""

import datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
EDITOR = ROOT / "tools" / "golden" / "editor-screens.py"
RECORD = ROOT / "tools" / "golden" / "record.py"
REQUIRED = (
    "three.module.js", "three.core.js", "OrbitControls.js",
    "TransformControls.js", "OBJLoader.js", "MTLLoader.js",
)


def run_editor(root, preflight_only=False):
    env = os.environ.copy()
    env["SECOND_RITE_G6_ROOT"] = str(root)
    if preflight_only:
        env["SECOND_RITE_G6_PREFLIGHT_ONLY"] = "1"
    return subprocess.run(
        [sys.executable, str(EDITOR), "check"], cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5,
        check=False,
    )


def load_record():
    spec = importlib.util.spec_from_file_location("g6_record_front", RECORD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    with tempfile.TemporaryDirectory(prefix="g6-dependency-negative-") as temp:
        temp = Path(temp)
        proc = run_editor(temp)
        assert proc.returncode == 86, proc
        assert "G6_DEPENDENCY_MISSING_JSON " in proc.stdout
        assert "tools/editor/vendor/three/three.module.js" in proc.stderr
        assert "sync-three-vendor.js" in proc.stderr
        payload_line = next(line for line in proc.stdout.splitlines()
                            if line.startswith("G6_DEPENDENCY_MISSING_JSON "))
        payload = json.loads(payload_line.split(" ", 1)[1])
        assert len(payload["paths"]) == len(REQUIRED)

        vendor = temp / "tools" / "editor" / "vendor" / "three"
        vendor.mkdir(parents=True)
        for name in REQUIRED:
            (vendor / name).write_text("// fixture\n", encoding="utf-8")
        passed = run_editor(temp, preflight_only=True)
        assert passed.returncode == 0, passed
        assert "G6 DEPENDENCIES OK" in passed.stdout

    record = load_record()
    sentinel = ('G6_DEPENDENCY_MISSING_JSON '
                '{"kind":"three-vendor","paths":["tools/editor/vendor/three/three.module.js"],'
                '"repair":"node tools/editor/sync-three-vendor.js"}')
    parsed = record.parse_gate_output("g6", sentinel)
    now = datetime.datetime.now(datetime.timezone.utc)
    manifest = record.build_manifest(
        "g6", 86, False, now, now,
        {"sha": "abc", "shortSha": "abc", "dirty": False},
        {}, [{"name": "editor-check", "outcome": "failed", "exitCode": 86}],
        parsed, False,
    )
    assert manifest["outcome"] == "dependency-missing"
    assert manifest["frameCounts"]["editor"]["measurement"] == "dependency-missing"
    assert manifest["frameCounts"]["editor"]["compared"] is None
    assert manifest["missingDependency"]["kind"] == "three-vendor"
    print("G6 DEPENDENCY PREFLIGHT TEST OK")


if __name__ == "__main__":
    main()
