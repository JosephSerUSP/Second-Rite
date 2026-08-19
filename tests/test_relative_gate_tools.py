import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPARE = load_module(ROOT / "tools/golden/compare-relative.py", "relative_compare")
CAPTURE = load_module(ROOT / "tools/golden/relative-capture.py", "relative_capture")
RECORD = load_module(ROOT / "tools/golden/record.py", "relative_record")
EDITOR_FRONT = load_module(ROOT / "tools/golden/editor-screens.py", "relative_editor_screens")


def write_png(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (2, 2), value).save(str(path))


class RelativeComparatorTests(unittest.TestCase):
    def test_exact_repeat_and_candidate_are_green(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for label in ("base-a", "base-b", "candidate"):
                write_png(root / label / "captures/classic/frame.png", (4, 4, 4, 255))
                write_png(root / label / "captures/wide/frame.png", (7, 7, 7, 255))

            output = root / "report.md"
            code = COMPARE.main([
                "--gate", "g5",
                "--base-a", str(root / "base-a"),
                "--base-b", str(root / "base-b"),
                "--candidate", str(root / "candidate"),
                "--base-ref", "main",
                "--candidate-ref", "candidate",
                "--output", str(output),
            ])
            self.assertEqual(code, 0)
            payload = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "exact")
            self.assertIn("EXACT", payload["verdict"])

    def test_unstable_control_frame_is_excluded_from_candidate_verdict(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for label in ("base-a", "base-b", "candidate"):
                (root / label / "captures/editor").mkdir(parents=True)

            write_png(root / "base-a/captures/editor/unstable.png", (0, 0, 0, 255))
            write_png(root / "base-b/captures/editor/unstable.png", (1, 0, 0, 255))
            write_png(root / "candidate/captures/editor/unstable.png", (2, 0, 0, 255))
            write_png(root / "base-a/captures/editor/stable.png", (5, 5, 5, 255))
            write_png(root / "base-b/captures/editor/stable.png", (5, 5, 5, 255))
            write_png(root / "candidate/captures/editor/stable.png", (5, 5, 5, 255))

            output = root / "report.md"
            code = COMPARE.main([
                "--gate", "g6",
                "--base-a", str(root / "base-a"),
                "--base-b", str(root / "base-b"),
                "--candidate", str(root / "candidate"),
                "--base-ref", "main",
                "--candidate-ref", "candidate",
                "--output", str(output),
            ])
            self.assertEqual(code, 0)
            payload = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "control-unstable")
            self.assertEqual(payload["surfaces"]["editor"]["unstableFrames"], ["unstable.png"])
            self.assertEqual(payload["surfaces"]["editor"]["stableCandidateDifferences"], [])

    def test_stable_candidate_difference_is_red(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for label in ("base-a", "base-b", "candidate"):
                (root / label / "captures/classic").mkdir(parents=True)
                (root / label / "captures/wide").mkdir(parents=True)
                write_png(root / label / "captures/wide/wide.png", (8, 8, 8, 255))
            write_png(root / "base-a/captures/classic/frame.png", (0, 0, 0, 255))
            write_png(root / "base-b/captures/classic/frame.png", (0, 0, 0, 255))
            write_png(root / "candidate/captures/classic/frame.png", (9, 0, 0, 255))

            output = root / "report.md"
            code = COMPARE.main([
                "--gate", "g5",
                "--base-a", str(root / "base-a"),
                "--base-b", str(root / "base-b"),
                "--candidate", str(root / "candidate"),
                "--base-ref", "main",
                "--candidate-ref", "candidate",
                "--output", str(output),
            ])
            self.assertEqual(code, 1)
            payload = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "candidate-diff")
            self.assertEqual(len(payload["surfaces"]["classic"]["stableCandidateDifferences"]), 1)

    def test_missing_candidate_frame_is_an_infrastructure_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for label in ("base-a", "base-b", "candidate"):
                (root / label / "captures/editor").mkdir(parents=True)
            write_png(root / "base-a/captures/editor/frame.png", (3, 3, 3, 255))
            write_png(root / "base-b/captures/editor/frame.png", (3, 3, 3, 255))

            output = root / "report.md"
            code = COMPARE.main([
                "--gate", "g6",
                "--base-a", str(root / "base-a"),
                "--base-b", str(root / "base-b"),
                "--candidate", str(root / "candidate"),
                "--base-ref", "main",
                "--candidate-ref", "candidate",
                "--output", str(output),
            ])
            self.assertEqual(code, 1)
            payload = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "incomplete-capture")
            self.assertEqual(payload["surfaces"]["editor"]["missingCandidateFrames"], ["frame.png"])

    def test_new_candidate_target_is_reported_without_a_false_regression(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for label in ("base-a", "base-b", "candidate"):
                (root / label / "captures/editor").mkdir(parents=True)
            write_png(root / "base-a/captures/editor/shared.png", (3, 3, 3, 255))
            write_png(root / "base-b/captures/editor/shared.png", (3, 3, 3, 255))
            write_png(root / "candidate/captures/editor/shared.png", (3, 3, 3, 255))
            write_png(root / "candidate/captures/editor/new.png", (4, 4, 4, 255))

            output = root / "report.md"
            code = COMPARE.main([
                "--gate", "g6",
                "--base-a", str(root / "base-a"),
                "--base-b", str(root / "base-b"),
                "--candidate", str(root / "candidate"),
                "--base-ref", "main",
                "--candidate-ref", "candidate",
                "--output", str(output),
            ])
            self.assertEqual(code, 0)
            payload = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "coverage-expanded")
            self.assertEqual(payload["surfaces"]["editor"]["newCandidateFrames"], ["new.png"])
            self.assertEqual(payload["surfaces"]["editor"]["stableCandidateDifferences"], [])


class PullRequestIntegrationSelectionTests(unittest.TestCase):
    PAYLOAD = {
        "pull_request": {
            "head": {"sha": "head123"},
            "base": {"sha": "payload-base-old"},
        }
    }

    def test_raw_pr_head_uses_synthetic_merge(self):
        self.assertEqual(
            CAPTURE.select_pull_request_integration_sha(
                "head123", "pull_request", self.PAYLOAD,
                "merge456", "current-base789",
            ),
            {"role": "candidate", "sha": "merge456"},
        )

    def test_payload_base_uses_synthetic_merges_current_first_parent(self):
        self.assertEqual(
            CAPTURE.select_pull_request_integration_sha(
                "payload-base-old", "pull_request", self.PAYLOAD,
                "merge456", "current-base789",
            ),
            {"role": "base", "sha": "current-base789"},
        )

    def test_already_current_base_needs_no_checkout(self):
        payload = {
            "pull_request": {
                "head": {"sha": "head123"},
                "base": {"sha": "current-base789"},
            }
        }
        self.assertIsNone(
            CAPTURE.select_pull_request_integration_sha(
                "current-base789", "pull_request", payload,
                "merge456", "current-base789",
            )
        )

    def test_non_pr_capture_keeps_requested_commit(self):
        self.assertIsNone(
            CAPTURE.select_pull_request_integration_sha(
                "head123", "push", self.PAYLOAD,
                "merge456", "current-base789",
            )
        )


class G6WorkspaceReadinessContractTests(unittest.TestCase):
    def _steps(self):
        clause = EDITOR_FRONT.RUNTIME_STATUS_WAIT_CLAUSE
        return [
            {"path": path, "wait": "button.disabled" + clause + " && canvas.width > 0"}
            for path in sorted(EDITOR_FRONT.WORKSPACE_RUNTIME_STEPS)
        ] + [{"path": "engine/flows.png", "wait": "canvas.dataset.previewReady === '1'"}]

    def test_workspace_steps_use_revision_authority_not_toolbar_copy(self):
        steps = self._steps()
        rewritten = EDITOR_FRONT.rewrite_workspace_runtime_steps(steps)
        workspace = [step for step in rewritten if step["path"] in EDITOR_FRONT.WORKSPACE_RUNTIME_STEPS]
        self.assertEqual(len(workspace), 4)
        for step in workspace:
            self.assertNotIn(EDITOR_FRONT.RUNTIME_STATUS_WAIT_CLAUSE, step["wait"])
            self.assertIn("button.disabled", step["wait"])
            self.assertIn("canvas.width > 0", step["wait"])
        flows = next(step for step in rewritten if step["path"] == "engine/flows.png")
        self.assertEqual(flows["wait"], "canvas.dataset.previewReady === '1'")

    def test_only_positive_workspace_readiness_inherits_producer_budget(self):
        workspace_ready = "status.dataset.workspaceReady === '1'"
        self.assertEqual(
            EDITOR_FRONT.readiness_timeout(workspace_ready, workspace_ready, 30.0),
            EDITOR_FRONT.RUNTIME_AUTHORITY_READY_TIMEOUT,
        )
        self.assertEqual(
            EDITOR_FRONT.readiness_timeout("canvas.width > 0", workspace_ready, 30.0),
            30.0,
        )

    def test_workspace_step_contract_drift_fails_loudly(self):
        steps = self._steps()
        steps[0]["wait"] = "button.disabled && canvas.width > 0"
        with self.assertRaises(RuntimeError) as caught:
            EDITOR_FRONT.rewrite_workspace_runtime_steps(steps)
        self.assertIn("workspace readiness front no longer matches", str(caught.exception))


class RelativeCaptureTimeoutTests(unittest.TestCase):
    def test_g6_uses_harness_readiness_without_relaxing_other_recorder_children(self):
        self.assertEqual(CAPTURE.default_step_timeout("g5"), 180)
        self.assertEqual(CAPTURE.default_step_timeout("g6"), 180)
        self.assertFalse(RECORD.recorder_owns_step_timeout(
            "python", ["tools/golden/editor-screens.py", "check"]
        ))
        self.assertTrue(RECORD.recorder_owns_step_timeout(
            "python", ["tools/golden/test-g6-harness-boundaries.py"]
        ))
        args = CAPTURE.parse_args([
            "--repo-root", ".", "--gate", "g6", "--output", "out"
        ])
        self.assertIsNone(args.step_timeout,
            "CLI omission must defer to the gate-specific default in main")


class RelativeCaptureDiagnosticTests(unittest.TestCase):
    def test_named_readiness_stall_surfaces_step_and_predicate(self):
        manifest = {
            "outcome": "failed",
            "frameCounts": {"editor": {"compared": None}},
            "steps": [{
                "name": "editor-check", "outcome": "failed",
                "durationSeconds": 30.2, "wrapperExitCode": 2,
            }],
        }
        with tempfile.TemporaryDirectory() as temp:
            record_dir = Path(temp)
            (record_dir / "stderr.txt").write_text(
                "G6 HARNESS STALL\n"
                "  step: engine/flows.png\n"
                "  predicate: document.querySelector('#engine-form-panel canvas[data-preview-ready]')\n"
                "  No pixel comparison completed for this step.\n",
                encoding="utf-8",
            )
            reason = CAPTURE.g6_incomplete_reason(manifest, record_dir)
        self.assertIn("engine/flows.png", reason)
        self.assertIn("data-preview-ready", reason)
        self.assertNotIn("did not reach a complete editor comparison", reason)

    def test_watchdog_failure_keeps_recorder_step_and_last_announced_screen(self):
        manifest = {
            "outcome": "timeout",
            "frameCounts": {"editor": {"compared": None}},
            "steps": [{
                "name": "editor-check", "outcome": "timeout",
                "durationSeconds": 420.375, "wrapperExitCode": 124,
            }],
        }
        with tempfile.TemporaryDirectory() as temp:
            record_dir = Path(temp)
            (record_dir / "stdout.txt").write_text(
                "  [41/46] engine/windows.png\n"
                "             6.7s\n"
                "  [42/46] studio/preferences.png\n",
                encoding="utf-8",
            )
            (record_dir / "stderr.txt").write_text("", encoding="utf-8")
            reason = CAPTURE.g6_incomplete_reason(manifest, record_dir)
        self.assertIn("editor-check timeout", reason)
        self.assertIn("420.375s", reason)
        self.assertIn("studio/preferences.png", reason)

    def test_materializer_raises_causal_named_readiness_failure(self):
        manifest = {
            "outcome": "failed",
            "frameCounts": {"editor": {"compared": None}},
            "steps": [{"name": "editor-check", "outcome": "failed", "wrapperExitCode": 2}],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record_dir = root / "record"
            record_dir.mkdir()
            (record_dir / "stderr.txt").write_text(
                "G6 HARNESS STALL\n"
                "  step: map-editor/workspace-perspective.png workspace refresh\n"
                "  predicate: status.dataset.workspaceReady === '1'\n",
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError) as caught:
                CAPTURE.materialize_g6(root, manifest, root / "out", record_dir)
        message = str(caught.exception)
        self.assertIn("workspace-perspective.png workspace refresh", message)
        self.assertIn("workspaceReady", message)


class RelativeCaptureAssemblyTests(unittest.TestCase):
    def test_classic_normalization_overlays_actual_and_removes_orphans(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ref = root / "tools/golden/screens"
            actual = root / "tools/golden/screens-actual"
            write_png(ref / "same.png", (1, 1, 1, 255))
            write_png(ref / "changed.png", (1, 1, 1, 255))
            write_png(ref / "orphan.png", (1, 1, 1, 255))
            write_png(actual / "changed.png", (2, 2, 2, 255))
            CAPTURE.normalize_classic_reference(root, {
                "frames": [{"surface": "classic", "path": "orphan.png", "status": "orphaned"}]
            })
            self.assertFalse((ref / "orphan.png").exists())
            self.assertEqual((ref / "changed.png").read_bytes(), (actual / "changed.png").read_bytes())

    def test_g6_reconstruction_requires_complete_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / "out"
            ref = root / "tools/golden/editor-screens"
            actual = root / "tools/golden/editor-screens-actual"
            write_png(ref / "a.png", (1, 1, 1, 255))
            write_png(ref / "b.png", (1, 1, 1, 255))
            write_png(ref / "orphan.png", (1, 1, 1, 255))
            write_png(actual / "b.png", (2, 2, 2, 255))
            counts = CAPTURE.materialize_g6(root, {
                "frameCounts": {"editor": {"compared": 2}},
                "frames": [{"surface": "editor", "path": "orphan.png", "status": "orphaned"}],
            }, out)
            self.assertEqual(counts, {"editor": 2})
            self.assertTrue((out / "captures/editor/a.png").exists())
            self.assertEqual((out / "captures/editor/b.png").read_bytes(), (actual / "b.png").read_bytes())
            self.assertFalse((out / "captures/editor/orphan.png").exists())


if __name__ == "__main__":
    unittest.main()
