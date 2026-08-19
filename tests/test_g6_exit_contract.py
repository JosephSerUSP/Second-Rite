#!/usr/bin/env python3
"""Regression tests for G6 fail-closed process semantics (#792, #805)."""

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
CHECK_EDITOR_PS1 = ROOT / "tools/golden/check-editor.ps1"
RECORD_PATH = ROOT / "tools/golden/record.py"
RECORD_CORE_PATH = ROOT / "tools/golden/record-core.py"
CAPTURE_PATH = ROOT / "tools/golden/relative-capture.py"
WORKFLOW_PATH = ROOT / ".github/workflows/relative-golden-ab.yml"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load module: %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FRONT = load_module(EDITOR_FRONT, "test_g6_front")
RECORD = load_module(RECORD_PATH, "test_g6_record")
CAPTURE = load_module(CAPTURE_PATH, "test_g6_capture")


class FrontContractTests(unittest.TestCase):
    def _run_fake_core(self, fake_core):
        original_run_path = FRONT.runpy.run_path
        original_bind = FRONT.bind_core_root
        original_configure = FRONT.configure_runtime_authority_readiness
        FRONT.runpy.run_path = lambda *args, **kwargs: fake_core
        FRONT.bind_core_root = lambda core: core
        FRONT.configure_runtime_authority_readiness = lambda core: core
        try:
            return FRONT.run_core()
        finally:
            FRONT.runpy.run_path = original_run_path
            FRONT.bind_core_root = original_bind
            FRONT.configure_runtime_authority_readiness = original_configure

    def test_visual_mismatch_system_exit_is_propagated(self):
        class FakeHarnessStall(RuntimeError):
            pass

        def fake_main():
            raise SystemExit(1)

        code = self._run_fake_core({"HarnessStall": FakeHarnessStall, "main": fake_main})
        self.assertEqual(code, 1)

    def test_harness_stall_is_distinct_incomplete_exit(self):
        class FakeHarnessStall(RuntimeError):
            def __init__(self, step, predicate, last_error=None):
                super().__init__(step)
                self.step = step
                self.predicate = predicate
                self.last_error = last_error

        def fake_main():
            raise FakeHarnessStall(
                "map-editor/generated-inspection.png",
                "status === 'Resolved preview'",
                RuntimeError("observed page state: pending"),
            )

        stdout = io.StringIO()
        stderr = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = stdout, stderr
            code = self._run_fake_core({"HarnessStall": FakeHarnessStall, "main": fake_main})
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
        stdout_text = stdout.getvalue()
        stderr_text = stderr.getvalue()
        stdout.close()
        stderr.close()

        self.assertEqual(code, 2)
        self.assertIn("G6 HARNESS STALL", stderr_text)
        result_line = next(
            line for line in stdout_text.splitlines()
            if line.startswith("G6_RESULT_JSON ")
        )
        payload = json.loads(result_line[len("G6_RESULT_JSON "):])
        self.assertEqual(payload["status"], "incomplete")
        self.assertEqual(payload["stall"]["step"], "map-editor/generated-inspection.png")
        self.assertIn("pending", payload["stall"]["lastError"])

    def test_non_integer_system_exit_is_failure(self):
        class FakeHarnessStall(RuntimeError):
            pass

        def fake_main():
            raise SystemExit("broken harness")

        stderr = io.StringIO()
        old_stderr = sys.stderr
        try:
            sys.stderr = stderr
            code = self._run_fake_core({"HarnessStall": FakeHarnessStall, "main": fake_main})
        finally:
            sys.stderr = old_stderr
        stderr_text = stderr.getvalue()
        stderr.close()
        self.assertEqual(code, 1)
        self.assertIn("broken harness", stderr_text)


class RecorderContractTests(unittest.TestCase):
    def _manifest(self, exit_code, parsed):
        started = RECORD._core.utc_now()
        ended = RECORD._core.utc_now()
        return RECORD.build_manifest(
            gate="g6",
            gate_exit_code=exit_code,
            gate_timed_out=False,
            started=started,
            ended=ended,
            git_info={"sha": "abc", "shortSha": "abc", "dirty": False},
            host_info={},
            steps=[{"name": "editor-check", "outcome": "failed", "exitCode": exit_code}],
            parsed=parsed,
            shim_present=False,
        )

    def test_full_visual_mismatch_is_measured_red(self):
        parsed = RECORD.parse_gate_output(
            "g6",
            "Golden editor screenshots: 45/46 match.\n"
            "  MISMATCH  map-editor/mode-event.png\n",
        )
        manifest = self._manifest(1, parsed)
        editor = manifest["frameCounts"]["editor"]
        self.assertEqual(manifest["outcome"], "failed")
        self.assertEqual(editor["measurement"], "measured")
        self.assertEqual(editor["matched"], 45)
        self.assertEqual(editor["compared"], 46)
        self.assertEqual(editor["differing"], 1)

    def test_stall_is_unmeasured_not_visual_red(self):
        payload = {
            "status": "incomplete",
            "completedSteps": None,
            "totalDeclared": None,
            "stall": {
                "step": "map-editor/generated-inspection.png",
                "predicate": "status === 'Resolved preview'",
                "lastError": "observed page state: pending",
            },
        }
        parsed = RECORD.parse_gate_output("g6", "G6_RESULT_JSON " + json.dumps(payload) + "\n")
        manifest = self._manifest(2, parsed)
        editor = manifest["frameCounts"]["editor"]
        self.assertEqual(manifest["outcome"], "failed")
        self.assertEqual(editor["measurement"], "unmeasured")
        self.assertIsNone(editor["matched"])
        self.assertIsNone(editor["compared"])
        self.assertEqual(manifest["incomplete"]["stall"]["step"], payload["stall"]["step"])

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(RuntimeError) as caught:
                CAPTURE.materialize_g6(root, manifest, root / "out")
            self.assertIn("generated-inspection.png", str(caught.exception))
            self.assertIn("Resolved preview", str(caught.exception))


class WrapperAndWorkflowTests(unittest.TestCase):
    def test_check_editor_propagates_g6_exit_codes(self):
        text = CHECK_EDITOR_PS1.read_text(encoding="utf-8")
        self.assertIn("exit 1", text)
        self.assertIn("exit 2", text)
        self.assertIn("exit $g6Exit", text)
        self.assertNotIn('throw "G6 visual mismatch', text)
        self.assertNotIn('throw "G6 harness stalled', text)

    def test_relative_tooling_runs_only_owned_suites(self):
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        owned = (
            "python -m unittest tests/test_g6_exit_contract.py "
            "tests/test_gate_record.py tests/test_relative_gate_tools.py -v"
        )
        self.assertIn(owned, text)
        self.assertNotIn("python -m unittest discover", text)
        self.assertIn("pillow websocket-client", text)


class ProcessContractTests(unittest.TestCase):
    """record.py and record-core.py must be one process contract (#805).

    RecorderContractTests above hands build_manifest an explicit
    gate_exit_code, so it stays green even if nothing upstream can ever
    deliver a non-zero one -- which is exactly what happened. The defect was
    only visible as a process: record.py is what the recorder's temporary
    PATH shims invoke (run_live points SECOND_RITE_RECORD_SCRIPT at it), and
    its __main__ dropped main()'s return value. Every gate child therefore
    reported success to its gate script, and a red G5/G6 recorded as
    `"outcome": "passed"` with `"exitCode": 0`.

    So these tests run both entrypoints as real subprocesses and compare
    them. Asserting only that record-core.py is correct is what let this
    through.
    """

    ENTRYPOINTS = (RECORD_PATH, RECORD_CORE_PATH)

    def _exec_step(self, entrypoint, child_argv, with_real_python=True):
        """Run one entrypoint's shim path; return (exit code, trace events)."""
        with tempfile.TemporaryDirectory() as temp:
            trace = Path(temp) / "steps.jsonl"
            env = dict(os.environ)
            env["SECOND_RITE_RECORD_TRACE"] = str(trace)
            env["SECOND_RITE_RECORD_RAW"] = str(Path(temp) / "raw")
            env["SECOND_RITE_RECORD_STEP_TIMEOUT"] = "60"
            if with_real_python:
                env["SECOND_RITE_RECORD_REAL_PYTHON"] = sys.executable
            else:
                env.pop("SECOND_RITE_RECORD_REAL_PYTHON", None)
            completed = subprocess.run(
                [sys.executable, str(entrypoint), "_exec-step", "--tool", "python", "--"]
                + list(child_argv),
                cwd=str(ROOT), env=env, capture_output=True,
            )
            events = [
                json.loads(line)
                for line in trace.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            return completed.returncode, events

    def test_failing_child_status_reaches_the_gate_script(self):
        codes = {}
        for entrypoint in self.ENTRYPOINTS:
            code, events = self._exec_step(entrypoint, ["-c", "import sys; sys.exit(7)"])
            codes[entrypoint.name] = code
            # The trace was already truthful while the process contract was
            # not, so assert the two agree rather than either alone.
            self.assertEqual(len(events), 1, entrypoint.name)
            self.assertEqual(events[0]["exitCode"], 7, entrypoint.name)
            self.assertEqual(events[0]["wrapperExitCode"], code, entrypoint.name)
        self.assertEqual(codes[RECORD_PATH.name], 7)
        self.assertEqual(codes[RECORD_PATH.name], codes[RECORD_CORE_PATH.name])

    def test_passing_child_still_reports_success(self):
        """Negative control: the fix must not make every step look failed."""
        for entrypoint in self.ENTRYPOINTS:
            code, events = self._exec_step(entrypoint, ["-c", "import sys; sys.exit(0)"])
            self.assertEqual(code, 0, entrypoint.name)
            self.assertEqual(events[0]["outcome"], "passed", entrypoint.name)

    def test_unavailable_tool_status_is_identical(self):
        codes = set()
        for entrypoint in self.ENTRYPOINTS:
            code, events = self._exec_step(
                entrypoint, ["-c", "import sys; sys.exit(0)"], with_real_python=False,
            )
            self.assertEqual(events[0]["outcome"], "unavailable", entrypoint.name)
            codes.add(code)
        self.assertEqual(codes, {RECORD._core.UNAVAILABLE_EXIT_CODE})

    def test_front_entrypoint_propagates_main_status(self):
        """Name the one line, so a future edit back to `_core.main()` fails here."""
        text = RECORD_PATH.read_text(encoding="utf-8")
        # assertTrue, not assertIn: a failing assertIn prints the whole
        # module, which buries the one thing that is wrong.
        self.assertTrue(
            "raise SystemExit(_core.main())" in text,
            "record.py's __main__ must propagate main()'s exit status (#805)",
        )


if __name__ == "__main__":
    unittest.main()
