#!/usr/bin/env python3
"""Focused regression coverage for G6 dependency and target-root contracts."""

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


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_record():
    return load_module(RECORD, "g6_record_front")


def test_target_root_binding(editor):
    # `EditorServer.script` and `RuntimeBridge.script` are class attributes set
    # when editor-screens-core.py executes. A canonical relative harness must
    # rewrite those attributes as well as the module globals, or base-A launches
    # the workflow checkout's host and misses the detached target's vendor tree.
    namespace = {}
    exec("def run_capture_set():\n    return None\n", namespace)

    class EditorServer:
        script = "workflow/editor/server.js"

    class RuntimeBridge:
        script = "workflow/editor/runtime-bridge-server.js"

    namespace.update({
        "ROOT": "workflow",
        "REF_DIR": "workflow/refs",
        "ACTUAL_DIR": "workflow/actual",
        "SERVER_JS": EditorServer.script,
        "BRIDGE_JS": RuntimeBridge.script,
        "EditorServer": EditorServer,
        "RuntimeBridge": RuntimeBridge,
    })
    core = {"run_capture_set": namespace["run_capture_set"]}

    with tempfile.TemporaryDirectory(prefix="g6-target-root-") as temp:
        target = Path(temp).resolve()
        editor.bind_core_root(core, target)
        globals_ = core["run_capture_set"].__globals__
        expected_server = str(target / "tools" / "editor" / "server.js")
        expected_bridge = str(target / "tools" / "editor" / "runtime-bridge-server.js")
        assert globals_["ROOT"] == str(target)
        assert globals_["REF_DIR"] == str(target / "tools" / "golden" / "editor-screens")
        assert globals_["ACTUAL_DIR"] == str(target / "tools" / "golden" / "editor-screens-actual")
        assert globals_["SERVER_JS"] == expected_server
        assert globals_["BRIDGE_JS"] == expected_bridge
        assert EditorServer.script == expected_server
        assert RuntimeBridge.script == expected_bridge


def test_runtime_authority_contract(editor):
    # The longer wait is not a second guessed timeout. It is read from the
    # runtime bridge in the measured worktree, then scoped only to the four
    # screenshots whose contract explicitly requires runtime-authored geometry.
    with tempfile.TemporaryDirectory(prefix="g6-authority-contract-") as temp:
        target = Path(temp)
        bridge = target / "tools" / "editor" / "runtime-bridge-server.js"
        bridge.parent.mkdir(parents=True)
        bridge.write_text("const BRIDGE_TIMEOUT_MS = 12345;\n", encoding="utf-8")
        derived = editor.runtime_authority_ready_timeout(target)
        assert abs(derived - 17.345) < 0.0001, derived

        workspace_ready = "status.dataset.workspaceReady === '1'"
        runtime_step = sorted(editor.WORKSPACE_RUNTIME_STEPS)[0]
        assert editor.scoped_readiness_timeout(
            workspace_ready, runtime_step + " reset workspace",
            workspace_ready, 30.0, derived,
        ) == derived
        assert editor.scoped_readiness_timeout(
            workspace_ready, "engine/flows.png reset workspace",
            workspace_ready, 30.0, derived,
        ) == 30.0
        assert editor.effective_readiness_expression(
            workspace_ready, runtime_step + " workspace refresh", workspace_ready,
        ) == editor.RUNTIME_AUTHORITY_READY_JS
        assert editor.effective_readiness_expression(
            workspace_ready, "engine/flows.png workspace refresh", workspace_ready,
        ) == workspace_ready

        bridge.write_text("const OTHER_TIMEOUT_MS = 12345;\n", encoding="utf-8")
        try:
            editor.runtime_authority_ready_timeout(target)
        except RuntimeError as error:
            assert "BRIDGE_TIMEOUT_MS" in str(error)
        else:
            raise AssertionError("missing producer timeout contract did not fail loudly")

    # Semantic readiness must not depend on mutable toolbar copy. The latest
    # workspace revision and latest producer generation both have to be positive;
    # rejected producer calls preserve a distinct fallback outcome + error.
    assert "textContent" not in editor.RUNTIME_AUTHORITY_READY_JS
    assert "workspaceReady" in editor.RUNTIME_AUTHORITY_READY_JS
    assert "lastOutcome === 'runtime'" in editor.RUNTIME_AUTHORITY_READY_JS
    assert "lastOutcome = 'fallback'" in editor.INSTALL_RUNTIME_AUTHORITY_OBSERVABILITY_JS
    assert "lastError" in editor.INSTALL_RUNTIME_AUTHORITY_OBSERVABILITY_JS


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

    editor = load_module(EDITOR, "g6_editor_front")
    test_target_root_binding(editor)
    test_runtime_authority_contract(editor)

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
