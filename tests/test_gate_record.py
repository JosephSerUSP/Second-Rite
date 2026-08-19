import datetime as dt
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD_PATH = ROOT / "tools" / "golden" / "record.py"
spec = importlib.util.spec_from_file_location("gate_record", RECORD_PATH)
record = importlib.util.module_from_spec(spec)
spec.loader.exec_module(record)
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "gate-record-g5-failure.json"

# 1x1 PNGs, deliberately different so diff.png is non-empty evidence.
REF_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
    "0000000c49444154789c63606060000000040001f61738550000000049454e44ae426082"
)
ACTUAL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
    "0000000c49444154789c63f8ffff3f0005fe02fea73581980000000049454e44ae426082"
)


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class GateRecordTests(unittest.TestCase):
    def test_manifest_assembly_from_fixture(self):
        fixture = load_fixture()
        parsed = record.parse_gate_output(fixture["gate"], fixture["stdout"])
        started = dt.datetime.fromisoformat(fixture["startedAtUtc"].replace("Z", "+00:00"))
        ended = dt.datetime.fromisoformat(fixture["endedAtUtc"].replace("Z", "+00:00"))
        manifest = record.build_manifest(
            fixture["gate"], fixture["exitCode"], fixture["gateTimedOut"],
            started, ended, fixture["git"], fixture["host"], fixture["steps"],
            parsed, fixture["shimPresent"], output_ignored=True,
        )
        self.assertEqual(manifest["gate"], "g5")
        self.assertEqual(manifest["exitCode"], 1)
        self.assertEqual(manifest["outcome"], "unmeasured")
        self.assertEqual(manifest["gitSha"], fixture["git"]["sha"])
        self.assertTrue(manifest["dirtyTree"])
        self.assertEqual(manifest["frameCounts"]["classic"], {
            "matched": 140, "compared": 141, "differing": 1,
            "measurement": "measured",
        })
        self.assertEqual(manifest["frameCounts"]["wide"]["compared"], None)
        self.assertEqual(manifest["frameCounts"]["wide"]["measurement"], "unmeasured")
        self.assertEqual(manifest["surfaceCropCheck"]["outcome"], "not-run")

    def test_unmeasured_surface_is_loud_and_not_passed(self):
        parsed = {
            "surfaces": {
                "editor": {"matched": None, "compared": None, "differing": 0, "frames": []},
            },
        }
        started = dt.datetime(2026, 8, 13, tzinfo=dt.timezone.utc)
        manifest = record.build_manifest(
            "g6", 0, False, started, started, {}, {}, [], parsed, False,
        )
        self.assertEqual(manifest["outcome"], "unmeasured")
        self.assertEqual(manifest["frameCounts"]["editor"]["measurement"], "unmeasured")
        with tempfile.TemporaryDirectory() as temp_name:
            triage = record._triage_custom(Path(temp_name), "g6", parsed, Path(temp_name))
        self.assertIn("The gate did not compare any frames", triage)
        self.assertIn("measurement: unmeasured", triage)

    def test_clean_measured_surface_remains_a_clean_pass(self):
        parsed = {
            "surfaces": {
                "editor": {"matched": 42, "compared": 42, "differing": 0, "frames": []},
            },
        }
        started = dt.datetime(2026, 8, 13, tzinfo=dt.timezone.utc)
        manifest = record.build_manifest(
            "g6", 0, False, started, started, {}, {}, [], parsed, False,
        )
        self.assertEqual(manifest["outcome"], "passed")
        self.assertEqual(manifest["frameCounts"]["editor"]["measurement"], "measured")
        with tempfile.TemporaryDirectory() as temp_name:
            triage = record._triage_custom(Path(temp_name), "g6", parsed, Path(temp_name))
        self.assertEqual(triage, "# Golden gate triage\n\nNo differing frames were reported by the gate.\n")

    def test_partial_replay_marks_its_other_surface_not_expected(self):
        parsed = record.parse_gate_output("g5", "Golden screenshots: 42/42 match.\n")
        started = dt.datetime(2026, 8, 13, tzinfo=dt.timezone.utc)
        manifest = record.build_manifest(
            "g5", 0, False, started, started, {}, {}, [], parsed, False,
            source="from-capture", source_details={"partialGate": True, "surface": "classic"},
        )
        self.assertEqual(manifest["outcome"], "passed")
        self.assertEqual(manifest["frameCounts"]["classic"]["measurement"], "measured")
        self.assertEqual(manifest["frameCounts"]["wide"]["measurement"], "not-expected")

    def test_per_step_exit_codes_are_not_collapsed(self):
        fixture = load_fixture()
        parsed = record.parse_gate_output("g5", fixture["stdout"])
        started = dt.datetime.fromisoformat(fixture["startedAtUtc"].replace("Z", "+00:00"))
        ended = dt.datetime.fromisoformat(fixture["endedAtUtc"].replace("Z", "+00:00"))
        manifest = record.build_manifest(
            "g5", 1, False, started, ended, fixture["git"], fixture["host"],
            fixture["steps"], parsed, False,
        )
        self.assertEqual([(s["name"], s["exitCode"]) for s in manifest["steps"]], [
            ("classic-capture", 0), ("classic-check", 1),
        ])

    def test_timeout_is_distinct_from_failure(self):
        fixture = load_fixture()
        fixture["steps"][-1] = {
            "name": "classic-check", "command": "python", "args": [],
            "outcome": "timeout", "exitCode": None,
            "wrapperExitCode": record.TIMEOUT_EXIT_CODE,
        }
        parsed = record.parse_gate_output("g5", fixture["stdout"])
        started = dt.datetime.fromisoformat(fixture["startedAtUtc"].replace("Z", "+00:00"))
        ended = dt.datetime.fromisoformat(fixture["endedAtUtc"].replace("Z", "+00:00"))
        manifest = record.build_manifest(
            "g5", 1, False, started, ended, fixture["git"], fixture["host"],
            fixture["steps"], parsed, False,
        )
        self.assertEqual(manifest["outcome"], "timeout")
        self.assertIsNone(manifest["steps"][-1]["exitCode"])
        self.assertEqual(manifest["steps"][-1]["wrapperExitCode"], 124)

    def test_differing_frame_layout_is_fixture_driven_and_read_only(self):
        fixture = load_fixture()
        parsed = record.parse_gate_output("g5", fixture["stdout"])
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            ref = root / "tools/golden/screens/map/map/01-after-enter.png"
            actual = root / "tools/golden/screens-actual/map/map/01-after-enter.png"
            ref.parent.mkdir(parents=True)
            actual.parent.mkdir(parents=True)
            ref.write_bytes(REF_PNG)
            actual.write_bytes(ACTUAL_PNG)
            before_ref = ref.read_bytes()
            before_actual = actual.read_bytes()
            record_dir = root / "out/gate-records/fixture"
            record_dir.mkdir(parents=True)
            frames = record.copy_differing_frames(root, record_dir, "g5", parsed)
            self.assertEqual(len(frames), 1)
            frame_dir = record_dir / frames[0]["directory"]
            self.assertEqual((frame_dir / "reference.png").read_bytes(), REF_PNG)
            self.assertEqual((frame_dir / "actual.png").read_bytes(), ACTUAL_PNG)
            self.assertTrue((frame_dir / "diff.png").is_file())
            self.assertEqual(ref.read_bytes(), before_ref)
            self.assertEqual(actual.read_bytes(), before_actual)

    def test_g5_wide_summary_is_kept_separate(self):
        text = (
            "Golden screenshots: 141/141 match.\nSCREENS OK\n"
            "Golden screenshots: 31/32 match.\n"
            "  MISMATCH  battle/battle/07-after-confirm.png\n"
        )
        parsed = record.parse_gate_output("g5", text)
        self.assertEqual(parsed["surfaces"]["classic"]["compared"], 141)
        self.assertEqual(parsed["surfaces"]["wide"]["compared"], 32)
        self.assertEqual(parsed["surfaces"]["wide"]["differing"], 1)

    def test_step_classifier_matches_existing_gate_commands(self):
        self.assertEqual(record.classify_step("lovec", [".", "screenshots"]), "classic-capture")
        self.assertEqual(record.classify_step("lovec", [".", "surface-crop-check"]), "surface-crop-check")
        self.assertEqual(record.classify_step("lovec", [".", "surface=wide", "screenshots"]), "wide-capture")
        self.assertEqual(record.classify_step("python", ["tools/golden/screens.py", "check", "--input", "x"]), "classic-check")
        self.assertEqual(record.classify_step("python", ["tools/golden/screens.py", "check", "--input", "x", "--surface", "wide"]), "wide-check")
        self.assertEqual(record.classify_step("python", ["tools/golden/editor-screens.py", "check"]), "editor-check")

    def test_g6_recorder_uses_canonical_harness_but_preserves_target_root(self):
        target = str(Path("C:/detached/base-a").resolve())
        args, env = record.canonical_g6_invocation(
            "python",
            ["tools/golden/editor-screens.py", "check"],
            {"SECOND_RITE_RECORD_ROOT": target},
        )
        self.assertEqual(Path(args[0]).name, "editor-screens.py")
        self.assertEqual(Path(args[0]).parent, RECORD_PATH.parent)
        self.assertEqual(args[1:], ["check"])
        self.assertEqual(env, {"SECOND_RITE_G6_ROOT": target})

        ordinary_args = ["tools/golden/screens.py", "check", "--input", "capture.txt"]
        rewritten, ordinary_env = record.canonical_g6_invocation(
            "python", ordinary_args, {"SECOND_RITE_RECORD_ROOT": target}
        )
        self.assertEqual(rewritten, ordinary_args)
        self.assertEqual(ordinary_env, {})

    def test_live_recorder_routes_temporary_shims_back_through_record_front(self):
        original_run_live = record._original_run_live
        original_core_file = record._core.__file__
        observed = []

        def fake_run_live(*args):
            observed.append(Path(record._core.__file__).name)
            return 17

        record._original_run_live = fake_run_live
        try:
            result = record.run_live(Path("."), "g6", Path("out"), 180, 1200)
        finally:
            record._original_run_live = original_run_live

        self.assertEqual(result, 17)
        self.assertEqual(observed, ["record.py"])
        self.assertEqual(record._core.__file__, original_core_file)


if __name__ == "__main__":
    unittest.main()
