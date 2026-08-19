#!/usr/bin/env python3
"""Regression tests for G6 process contract and exit status semantics (#792)."""

import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EDITOR_FRONT = ROOT / "tools/golden/editor-screens.py"
EDITOR_CORE = ROOT / "tools/golden/editor-screens-core.py"
CHECK_EDITOR_PS1 = ROOT / "tools/golden/check-editor.ps1"
RECORD_PATH = ROOT / "tools/golden/record.py"
CAPTURE_PATH = ROOT / "tools/golden/relative-capture.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load module: %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CORE_MOD = load_module(EDITOR_CORE, "test_g6_core_mod")
RECORD_MOD = load_module(RECORD_PATH, "test_g6_record_mod")
CAPTURE_MOD = load_module(CAPTURE_PATH, "test_g6_capture_mod")


def parse_result_json(stdout_text):
    for line in stdout_text.splitlines():
        line = line.strip()
        if line.startswith("G6_RESULT_JSON "):
            return json.loads(line[len("G6_RESULT_JSON "):])
    return None


class G6ExitContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="test-g6-exit-")
        self.root = Path(self.temp_dir.name)
        self.ref_dir = self.root / "tools/golden/editor-screens"
        self.actual_dir = self.root / "tools/golden/editor-screens-actual"
        self.ref_dir.mkdir(parents=True, exist_ok=True)
        self.actual_dir.mkdir(parents=True, exist_ok=True)

        # Save and monkey-patch directories in CORE_MOD
        self._orig_ref = CORE_MOD.REF_DIR
        self._orig_actual = CORE_MOD.ACTUAL_DIR
        CORE_MOD.REF_DIR = str(self.ref_dir)
        CORE_MOD.ACTUAL_DIR = str(self.actual_dir)

    def tearDown(self):
        CORE_MOD.REF_DIR = self._orig_ref
        CORE_MOD.ACTUAL_DIR = self._orig_actual
        self.temp_dir.cleanup()

    def test_green_complete_comparison_reports_success(self):
        (self.ref_dir / "step1.png").write_bytes(b"image1")
        (self.ref_dir / "step2.png").write_bytes(b"image2")
        captures = [
            {"path": "step1.png", "image": b"image1"},
            {"path": "step2.png", "image": b"image2"},
        ]

        with io.StringIO() as stderr, io.StringIO() as stdout:
            old_stdout, old_stderr = sys.stdout, sys.stderr
            try:
                sys.stdout, sys.stderr = stdout, stderr
                CORE_MOD.do_check(captures, total_declared=2)
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr
            out_str = stdout.getvalue()

        self.assertIn("EDITOR SCREENS OK", out_str)
        self.assertIn("Golden editor screenshots: 2/2 match.", out_str)
        result = parse_result_json(out_str)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["matched"], 2)
        self.assertEqual(result["compared"], 2)
        self.assertEqual(result["totalDeclared"], 2)
        self.assertEqual(result["differing"], 0)

    def test_completed_comparison_with_mismatch_exits_1(self):
        (self.ref_dir / "step1.png").write_bytes(b"image1")
        (self.ref_dir / "step2.png").write_bytes(b"old_image2")
        captures = [
            {"path": "step1.png", "image": b"image1"},
            {"path": "step2.png", "image": b"new_image2"},
        ]

        with io.StringIO() as stdout, io.StringIO() as stderr:
            old_stdout, old_stderr = sys.stdout, sys.stderr
            try:
                sys.stdout, sys.stderr = stdout, stderr
                with self.assertRaises(SystemExit) as caught:
                    CORE_MOD.do_check(captures, total_declared=2)
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr
            out_str = stdout.getvalue()

        self.assertEqual(caught.exception.code, 1)
        self.assertIn("MISMATCH  step2.png", out_str)
        result = parse_result_json(out_str)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "mismatch")
        self.assertEqual(result["matched"], 1)
        self.assertEqual(result["compared"], 2)
        self.assertEqual(result["totalDeclared"], 2)
        self.assertEqual(result["differing"], 1)
        self.assertIn("step2.png", result["mismatched"])

    def test_compared_count_less_than_declared_steps_exits_2(self):
        (self.ref_dir / "step1.png").write_bytes(b"image1")
        (self.ref_dir / "step2.png").write_bytes(b"image2")
        # Only 1 step was captured out of 2 declared steps
        captures = [
            {"path": "step1.png", "image": b"image1"},
        ]

        with io.StringIO() as stdout, io.StringIO() as stderr:
            old_stdout, old_stderr = sys.stdout, sys.stderr
            try:
                sys.stdout, sys.stderr = stdout, stderr
                with self.assertRaises(SystemExit) as caught:
                    CORE_MOD.do_check(captures, total_declared=2)
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr
            out_str = stdout.getvalue()
            err_str = stderr.getvalue()

        self.assertEqual(caught.exception.code, 2)
        self.assertIn("G6 INCOMPLETE CAPTURE: measured 1 of 2 declared steps", err_str)
        # It must NOT report false orphaned references or 1/1 match
        self.assertNotIn("ORPHANED REFERENCE", out_str)
        self.assertNotIn("1/1 match", out_str)
        result = parse_result_json(out_str)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["completedSteps"], 1)
        self.assertEqual(result["totalDeclared"], 2)

    def test_readiness_stall_reports_incomplete_and_exit_2(self):
        stall = CORE_MOD.HarnessStall(
            step="map-editor/generated-inspection.png",
            predicate="typeof dbPayload !== 'undefined'",
            last_error="page element not found",
            completed_steps=4,
            total_declared=46,
        )
        # When run_core in editor-screens.py catches this stall
        front_mod = load_module(EDITOR_FRONT, "test_g6_front_mod")
        fake_core = {
            "run_capture_set": lambda: None,
            "HarnessStall": CORE_MOD.HarnessStall,
            "Chrome": CORE_MOD.Chrome,
            "build_steps": lambda: [],
            "WORKSPACE_READY_JS": "1",
            "STEP_TIMEOUT": 30.0,
            "EditorServer": CORE_MOD.EditorServer,
            "RuntimeBridge": CORE_MOD.RuntimeBridge,
        }
        def fake_main():
            raise stall

        fake_core["main"] = fake_main
        front_mod.runpy.run_path = lambda *a, **kw: fake_core
        front_mod.bind_core_root = lambda c: c
        front_mod.configure_runtime_authority_readiness = lambda c: c

        with io.StringIO() as stdout, io.StringIO() as stderr:
            old_stdout, old_stderr = sys.stdout, sys.stderr
            try:
                sys.stdout, sys.stderr = stdout, stderr
                code = front_mod.run_core()
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr
            out_str = stdout.getvalue()
            err_str = stderr.getvalue()

        self.assertEqual(code, 2)
        self.assertIn("G6 HARNESS STALL", err_str)
        self.assertIn("map-editor/generated-inspection.png", err_str)
        result = parse_result_json(out_str)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["completedSteps"], 4)
        self.assertEqual(result["totalDeclared"], 46)
        self.assertEqual(result["stall"]["step"], "map-editor/generated-inspection.png")

    def test_record_manifest_marks_incomplete_g6_as_unmeasured(self):
        stdout_text = (
            "G6 HARNESS STALL\n"
            "  step: map-editor/workspace-perspective.png\n"
            "G6_RESULT_JSON " + json.dumps({
                "status": "incomplete",
                "completedSteps": 4,
                "totalDeclared": 46,
                "stall": {"step": "map-editor/workspace-perspective.png"},
            }) + "\n"
        )
        parsed = RECORD_MOD.parse_gate_output("g6", stdout_text)
        manifest = RECORD_MOD.build_manifest(
            gate="g6",
            gate_exit_code=2,
            gate_timed_out=False,
            started=RECORD_MOD.utc_now(),
            ended=RECORD_MOD.utc_now(),
            git_info={"sha": "abc", "shortSha": "abc"},
            host_info={},
            steps=[{"name": "editor-check", "outcome": "failed", "exitCode": 2}],
            parsed=parsed,
            shim_present=False,
        )
        self.assertEqual(manifest["outcome"], "failed")
        self.assertEqual(manifest["frameCounts"]["editor"]["measurement"], "unmeasured")
        self.assertIsNone(manifest["frameCounts"]["editor"]["compared"])
        self.assertIsNone(manifest["frameCounts"]["editor"]["matched"])

    def test_relative_materializer_rejects_incomplete_capture(self):
        manifest = {
            "outcome": "failed",
            "frameCounts": {"editor": {"compared": None, "measurement": "unmeasured"}},
            "incomplete": {
                "status": "incomplete",
                "completedSteps": 4,
                "totalDeclared": 46,
                "stall": {
                    "step": "map-editor/generated-inspection.png",
                    "predicate": "status === 'Resolved preview'",
                    "lastError": "Inspection timeout",
                },
            },
            "steps": [{"name": "editor-check", "outcome": "failed", "wrapperExitCode": 2}],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(RuntimeError) as caught:
                CAPTURE_MOD.materialize_g6(root, manifest, root / "out")
            message = str(caught.exception)
            self.assertIn("map-editor/generated-inspection.png", message)
            self.assertIn("status === 'Resolved preview'", message)
            self.assertIn("Inspection timeout", message)

    def test_check_editor_ps1_propagates_exit_codes(self):
        # Verify check-editor.ps1 uses Write-Error + exit $g6Exit
        ps1_text = CHECK_EDITOR_PS1.read_text(encoding="utf-8")
        self.assertIn("exit 1", ps1_text)
        self.assertIn("exit 2", ps1_text)
        self.assertIn("exit $g6Exit", ps1_text)
        self.assertNotIn("throw \"G6 visual mismatch", ps1_text)
        self.assertNotIn("throw \"G6 harness stalled", ps1_text)


if __name__ == "__main__":
    unittest.main()
