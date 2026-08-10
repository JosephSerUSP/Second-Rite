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


def write_png(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (2, 2), value).save(str(path))


class RelativeComparatorTests(unittest.TestCase):
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

    def test_missing_candidate_frame_is_a_stable_regression(self):
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
            diff = payload["surfaces"]["editor"]["stableCandidateDifferences"]
            self.assertEqual([entry["path"] for entry in diff], ["frame.png"])
            self.assertFalse(diff[0]["rightPresent"])


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
