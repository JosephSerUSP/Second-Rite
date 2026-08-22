import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools/golden/g6-capture-timings.py"
spec = importlib.util.spec_from_file_location("g6_capture_timings", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fake_core():
    namespace = {}
    exec(
        """
EVENTS = []
PENDING_IMAGES_JS = 'PENDING'
SETTLE_JS = 'SETTLE'
RESET_JS = 'RESET'

class Chrome:
    def __init__(self):
        self.pending = [0]

    def wait_for(self, expression, what):
        EVENTS.append(('wait_for', expression, what))
        return None

    def evaluate(self, expression, await_promise=False):
        EVENTS.append(('evaluate', expression, await_promise))
        if expression == PENDING_IMAGES_JS:
            return self.pending.pop(0)
        return True

    def screenshot(self):
        EVENTS.append(('screenshot',))
        return b'same'

    def stable_screenshot(self, label, attempts=25, pause=0.2):
        previous = self.screenshot()
        for _ in range(attempts):
            current = self.screenshot()
            if current == previous and self.evaluate(PENDING_IMAGES_JS) == 0:
                return current
            previous = current
        raise RuntimeError('not settled')

def build_steps():
    return [{'path': 'database/items.png'}]

def run_capture_set():
    steps = build_steps()
    chrome = Chrome()
    for step in steps:
        chrome.evaluate(RESET_JS, await_promise=True)
        chrome.wait_for('READY', step['path'])
        chrome.evaluate(SETTLE_JS, await_promise=True)
        chrome.stable_screenshot(step['path'])
    return [b'same']
""",
        namespace,
    )
    return namespace


class G6CaptureTimingTests(unittest.TestCase):
    def test_disabled_instrumentation_is_a_noop(self):
        core = fake_core()
        state = module.configure_capture_timings(core, ".", {"THESTRA_TIMINGS": "0"})
        self.assertIsNone(state)
        core["run_capture_set"]()
        self.assertEqual(
            core["EVENTS"],
            [
                ("evaluate", "RESET", True),
                ("wait_for", "READY", "database/items.png"),
                ("evaluate", "SETTLE", True),
                ("screenshot",),
                ("screenshot",),
                ("evaluate", "PENDING", False),
            ],
        )

    def test_enabled_instrumentation_adds_no_browser_calls(self):
        baseline = fake_core()
        baseline["run_capture_set"]()
        expected = list(baseline["EVENTS"])

        measured = fake_core()
        state = module.configure_capture_timings(
            measured,
            ".",
            {
                "THESTRA_TIMINGS": "1",
                "THESTRA_G6_TIMING_LEG": "base-b",
                "THESTRA_G6_TIMING_TARGET_SHA": "abc123",
            },
        )
        measured["run_capture_set"]()

        self.assertEqual(measured["EVENTS"], expected)
        self.assertEqual(len(state["frames"]), 1)
        frame = state["frames"][0]
        self.assertEqual(frame["iterations"], 1)
        self.assertEqual(len(frame["screenshotRoundTripsMs"]), 2)
        self.assertEqual(frame["binding"], "frame-match")
        self.assertTrue(frame["ok"])

    def test_relative_base_a_is_the_uninstrumented_same_sha_control(self):
        self.assertFalse(module.timings_enabled({}, Path("C:/runner/g6-base-a")))
        self.assertTrue(module.timings_enabled({}, Path("C:/runner/g6-base-b")))
        self.assertTrue(module.timings_enabled({}, Path("C:/runner/g6-candidate")))

    def test_pending_images_is_binding_only_when_it_was_the_last_observed_blocker(self):
        self.assertEqual(module.binding_condition([{"shot": 2, "pending": 0}], True), "frame-match")
        self.assertEqual(
            module.binding_condition(
                [{"shot": 2, "pending": 3}, {"shot": 3, "pending": 0}], True
            ),
            "pending-images",
        )
        self.assertEqual(
            module.binding_condition(
                [{"shot": 2, "pending": 3}, {"shot": 4, "pending": 0}], True
            ),
            "frame-match",
        )
        self.assertEqual(module.binding_condition([], False), "unresolved")

    def test_records_reconcile_frame_wall_into_named_components(self):
        state = {
            "leg": "base-b",
            "runId": "test-run",
            "targetSha": "abc123",
            "legWallMs": 140,
            "setupReadinessMs": 10,
            "frames": [
                {
                    "path": "x.png", "index": 1, "wallMs": 100, "readinessMs": 20,
                    "settlingMs": 30, "stableWallMs": 45, "settlePreludeMs": 5,
                    "screenshotMs": 40, "screenshotRoundTripsMs": [18, 22],
                    "otherMs": 10, "iterations": 1, "binding": "frame-match", "ok": True,
                }
            ],
        }
        records = module.timing_records(state)
        frame, leg = records
        self.assertEqual(frame["tags"]["readinessMs"], 20)
        self.assertEqual(frame["tags"]["settlingMs"], 30)
        self.assertEqual(frame["tags"]["screenshotMs"], 40)
        self.assertEqual(frame["tags"]["otherMs"], 10)
        self.assertEqual(sum([20, 30, 40, 10]), frame["ms"])
        self.assertEqual(leg["tags"]["setupOtherMs"], 30)
        self.assertEqual(leg["ms"], 140)


if __name__ == "__main__":
    unittest.main()
