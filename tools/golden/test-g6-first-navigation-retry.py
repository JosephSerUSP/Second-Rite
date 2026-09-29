"""#1263: a stalled FIRST Chrome navigation is retried once -- and nothing else is.

Observed: Chrome answered Page.enable, Runtime.enable, the metrics/media
overrides and both addScriptToEvaluateOnNewDocument, then never replied to the
first Page.navigate (hosted run 36592271681: 30 s, zero frames, nothing loaded).
No evidence exists before that call returns, so a fresh Chrome loses none.

The retry is the dangerous half of this change: a harness that retries broadly
turns a real editor failure into a green run. The negative controls therefore
carry the suite -- each asserts that something which must NOT be retried was not,
so a retry widened by mistake fails here rather than silently in CI.
"""
import io
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "golden"))

CORE_PATH = ROOT / "tools/golden/editor-screens-core.py"
CORE_TEXT = io.open(CORE_PATH, encoding="utf-8").read()
# The module resolves ROOT from __file__ at import time, so supply it.
core = {"__file__": str(CORE_PATH), "__name__": "editor_screens_core_under_test"}
exec(compile(CORE_TEXT, str(CORE_PATH), "exec"), core)

open_editor_page = core["open_editor_page"]
discard_chrome = core["discard_chrome"]
HarnessStall = core["HarnessStall"]
ATTEMPTS = core["FIRST_NAVIGATION_ATTEMPTS"]
Timeout = core["websocket"].WebSocketTimeoutException

failures = []


def check(name, condition, detail=""):
    if condition:
        print("ok   %s" % name)
    else:
        print("FAIL %s %s" % (name, detail))
        failures.append(name)


class FakeChrome(object):
    """Only what open_editor_page touches: call() and close()."""

    def __init__(self, navigate_outcome):
        self.navigate_outcome = navigate_outcome
        self.calls = []
        self.closed = False

    def call(self, method, **params):
        self.calls.append((method, params))
        if method == "Page.navigate" and self.navigate_outcome is not None:
            raise self.navigate_outcome
        return {}

    def close(self):
        self.closed = True


class LaunchFails(BaseException):
    """Marks an outcome as a failure of launch() itself, not of navigate."""

    def __init__(self, inner):
        self.inner = inner


class Launcher(object):
    """A launch() that hands out scripted Chromes, each with a real profile dir."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.launched = []
        self.profiles = []

    def __call__(self, bridge):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, LaunchFails):
            raise outcome.inner
        chrome = FakeChrome(outcome)
        profile = tempfile.mkdtemp(prefix="g6-retry-test-")
        self.launched.append(chrome)
        self.profiles.append(profile)
        return chrome, profile


def run(outcomes, attempts=None):
    launcher = Launcher(outcomes)
    lines = []
    kwargs = {} if attempts is None else {"attempts": attempts}
    result = error = None
    try:
        result = open_editor_page("http://127.0.0.1:1", object(), launch=launcher,
                                  log=lines.append, **kwargs)
    except BaseException as caught:  # the tests classify what escaped
        error = caught
    return launcher, lines, result, error


def navigates(chrome):
    return [c for c in chrome.calls if c[0] == "Page.navigate"]


# --- the retry that must happen ----------------------------------------------
launcher, lines, result, error = run([Timeout("stalled"), None])
check("a stalled first navigation is retried and the run continues",
      error is None and result is not None and len(launcher.launched) == 2)
check("the page handed back is the SECOND Chrome, the one that navigated",
      result is not None and result[0] is launcher.launched[1]
      and len(navigates(result[0])) == 1)
check("the stalled Chrome was closed and its profile removed",
      launcher.launched[0].closed and not os.path.exists(launcher.profiles[0]))
check("the retry is announced, once, naming the attempt",
      len(lines) == 1 and "restarting Chrome" in lines[0] and "1/%d" % ATTEMPTS in lines[0],
      repr(lines))
check("navigation targets the editor root on both attempts",
      len(launcher.launched) == 2
      and all([c[1] for c in navigates(chrome)] == [{"url": "http://127.0.0.1:1/"}]
              for chrome in launcher.launched))
if result:
    discard_chrome(*result)

# --- the healthy path is untouched --------------------------------------------
launcher, lines, result, error = run([None])
check("NEGATIVE CONTROL: a healthy first navigation launches Chrome once",
      error is None and len(launcher.launched) == 1)
check("NEGATIVE CONTROL: a healthy navigation logs nothing", lines == [], repr(lines))
if result:
    discard_chrome(*result)

# --- a real, persistent failure must still fail -------------------------------
launcher, lines, result, error = run([Timeout("first"), Timeout("second")])
check("NEGATIVE CONTROL: stalling on every attempt still fails",
      result is None and isinstance(error, HarnessStall), repr(error))
check("the exhausted retry is a HarnessStall, so the gate reports a stall not a traceback",
      isinstance(error, HarnessStall) and "first Chrome navigation" in error.step
      and "Page.navigate" in error.predicate)
check("the stall carries the last timeout as its cause",
      isinstance(error, HarnessStall) and isinstance(error.last_error, Timeout)
      and str(error.last_error) == "second")
check("every attempt was made, and none was left running",
      len(launcher.launched) == ATTEMPTS and all(c.closed for c in launcher.launched)
      and not any(os.path.exists(p) for p in launcher.profiles))
check("only the non-final attempt announces a restart", len(lines) == ATTEMPTS - 1,
      repr(lines))

# --- nothing else may be retried ----------------------------------------------
launcher, lines, result, error = run([RuntimeError("Page.navigate: {'code': -32000}"), None])
check("NEGATIVE CONTROL: a CDP error reply is NOT retried",
      isinstance(error, RuntimeError) and not isinstance(error, HarnessStall)
      and len(launcher.launched) == 1, repr(error))
check("NEGATIVE CONTROL: the failed Chrome is still cleaned up",
      launcher.launched[0].closed and not os.path.exists(launcher.profiles[0]))
check("NEGATIVE CONTROL: no retry is announced for a CDP error", lines == [], repr(lines))

launcher, lines, result, error = run([KeyboardInterrupt(), None])
check("NEGATIVE CONTROL: an interrupt is NOT retried and still cleans up",
      isinstance(error, KeyboardInterrupt) and len(launcher.launched) == 1
      and launcher.launched[0].closed and not os.path.exists(launcher.profiles[0]))

launcher, lines, result, error = run([LaunchFails(Timeout("setup stalled")), None])
check("NEGATIVE CONTROL: a stall during Chrome SETUP is not this fix's business",
      isinstance(error, Timeout) and not isinstance(error, HarnessStall)
      and len(launcher.launched) == 0 and lines == [], repr(error))

# --- the fix cannot be silently inert -----------------------------------------
check("the retry budget allows at least one retry", ATTEMPTS >= 2, str(ATTEMPTS))
launcher, lines, result, error = run([Timeout("a"), Timeout("b"), None], attempts=1)
check("NEGATIVE CONTROL: with a single attempt a stall is fatal (no hidden retry)",
      isinstance(error, HarnessStall) and len(launcher.launched) == 1)

body = re.search(r"def open_editor_page\(.*?\n(?=\n\ndef |\Z)", CORE_TEXT, re.S)
check("open_editor_page is found in the harness source", body is not None)
outside = CORE_TEXT.replace(body.group(0), "") if body else CORE_TEXT
check("the harness navigates through open_editor_page and nowhere else",
      CORE_TEXT.count('"Page.navigate"') == 1 and '"Page.navigate"' not in outside,
      "found %d" % CORE_TEXT.count('"Page.navigate"'))
check("run_capture_set opens the page through open_editor_page",
      "open_editor_page(server.url, bridge)" in CORE_TEXT)

if failures:
    print("")
    print("FIRST-NAVIGATION RETRY TEST FAILED: %d check(s)" % len(failures))
    sys.exit(1)
print("")
print("all G6 first-navigation retry checks passed")
