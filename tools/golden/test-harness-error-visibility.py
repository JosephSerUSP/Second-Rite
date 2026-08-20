"""#831: a stall must report what the page said, not just that it waited.

The bug being fixed is that resolveMapInspection() writes
"Preview unavailable: <reason>" on failure while the harness waits on
"Resolved preview", so a terminal, self-describing failure was reported as a
generic readiness timeout for the full STEP_TIMEOUT.

The negative controls matter more than the positive ones here. That error branch
had presumably been firing for some time with nobody able to see it, so a suite
that passes proves nothing on its own -- each behaviour is asserted to be ABSENT
before the change is simulated.
"""
import io
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "golden"))

CORE_PATH = ROOT / "tools/golden/editor-screens-core.py"
# The module resolves ROOT from __file__ at import time, so supply it.
core = {"__file__": str(CORE_PATH), "__name__": "editor_screens_core_under_test"}
exec(compile(io.open(CORE_PATH, encoding="utf-8").read(), str(CORE_PATH), "exec"), core)

WATCHED_ELEMENT_ID = core["WATCHED_ELEMENT_ID"]
TERMINAL_STATUS_PREFIXES = core["TERMINAL_STATUS_PREFIXES"]
HarnessStall = core["HarnessStall"]
stall_detail = core["stall_detail"]
Chrome = core["Chrome"]

failures = []


def check(name, condition, detail=""):
    if condition:
        print("ok   %s" % name)
    else:
        print("FAIL %s %s" % (name, detail))
        failures.append(name)


class FakePage(object):
    """Only the two Chrome methods wait_for touches."""

    def __init__(self, texts, predicate_value=False):
        self.texts = texts
        self.predicate_value = predicate_value

    evaluate = None  # bound below


def make_page(texts, predicate_value=False):
    page = Chrome.__new__(Chrome)

    def evaluate(expression, await_promise=False):
        if expression.startswith("!!("):
            return predicate_value
        if "JSON.stringify(out)" in expression:
            ids = WATCHED_ELEMENT_ID.findall(expression)
            return json.dumps({i: texts.get(i) for i in ids})
        raise RuntimeError("unexpected evaluate: %s" % expression[:40])

    page.evaluate = evaluate
    return page


PREDICATE = ("document.getElementById('map-inspection-status').textContent"
             ".indexOf('Resolved preview') === 0")

# --- id extraction -----------------------------------------------------------
check("extracts the watched id",
      WATCHED_ELEMENT_ID.findall(PREDICATE) == ["map-inspection-status"])
check("extracts every id in a compound predicate",
      sorted(set(WATCHED_ELEMENT_ID.findall(
          "document.getElementById('a').textContent === '' "
          "&& document.getElementById(\"b\").value === '1'"))) == ["a", "b"])
check("no ids in an id-free predicate",
      WATCHED_ELEMENT_ID.findall("window.someFlag === true") == [])

# --- reporting what was watched ---------------------------------------------
page = make_page({"map-inspection-status": "Preview unavailable: HTTP 500"})
described = page.describe_watched(PREDICATE)
check("reports the element's actual text",
      described and "Preview unavailable: HTTP 500" in described, described)

page = make_page({"map-inspection-status": None})
check("reports an absent element as absent",
      "(absent)" in (page.describe_watched(PREDICATE) or ""))

check("an id-free predicate describes nothing",
      make_page({}).describe_watched("window.x === 1") is None)

# --- terminal-failure detection ---------------------------------------------
page = make_page({"map-inspection-status": "Preview unavailable: HTTP 500"})
failure = page.terminal_failure(PREDICATE)
check("detects the terminal failure", failure and "HTTP 500" in failure, failure)

# NEGATIVE CONTROLS: states that must NOT be treated as terminal.
for text, why in [
    ("Resolving through the real engine...", "in-progress"),
    ("Resolved preview only · seed 424242", "success"),
    ("Preview cleared: Map changed. Resolve Preview again.",
     "a legitimate state another step waits for"),
    ("", "empty"),
]:
    page = make_page({"map-inspection-status": text})
    check("NEGATIVE CONTROL: %s is not terminal" % why,
          page.terminal_failure(PREDICATE) is None, repr(text))

check("the terminal list stays narrow", TERMINAL_STATUS_PREFIXES == ("Preview unavailable:",),
      repr(TERMINAL_STATUS_PREFIXES))

# --- stall_detail ------------------------------------------------------------
check("combines watched text with a page error",
      "watched" in str(stall_detail("watched", RuntimeError("boom")))
      and "boom" in str(stall_detail("watched", RuntimeError("boom"))))
check("survives having only one half",
      str(stall_detail("watched", None)) == "watched"
      and str(stall_detail(None, RuntimeError("boom"))) == "boom")
check("nothing to report stays None", stall_detail(None, None) is None)

# --- the end-to-end behaviour, and its negative control ----------------------
core["STEP_TIMEOUT"] = 2.0

page = make_page({"map-inspection-status": "Preview unavailable: HTTP 500"})
started = time.time()
try:
    page.wait_for(PREDICATE, "map-editor/generated-inspection.png")
    check("wait_for raises on a terminal failure", False, "it returned")
except HarnessStall as stall:
    elapsed = time.time() - started
    check("wait_for reports the real message",
          "HTTP 500" in str(stall.last_error), str(stall.last_error))
    # The point of failing fast: not merely a better message, a sooner one.
    check("wait_for fails fast rather than waiting out the timeout",
          elapsed < 1.0, "took %.2fs of a 2.0s timeout" % elapsed)

# NEGATIVE CONTROL: a genuinely slow (non-terminal) page must still wait, and
# must still report what it was watching. If this ever fails fast, the terminal
# list has grown too broad and real waits are being cut short.
page = make_page({"map-inspection-status": "Resolving through the real engine..."})
started = time.time()
try:
    page.wait_for(PREDICATE, "map-editor/generated-inspection.png")
    check("NEGATIVE CONTROL: a slow page still stalls", False, "it returned")
except HarnessStall as stall:
    elapsed = time.time() - started
    check("NEGATIVE CONTROL: a slow page waits out the timeout", elapsed >= 1.9,
          "took %.2fs" % elapsed)
    check("NEGATIVE CONTROL: a timeout still reports the watched text",
          "Resolving through the real engine" in str(stall.last_error),
          str(stall.last_error))

print()
if failures:
    print("FAILED: %d" % len(failures))
    raise SystemExit(1)
print("all harness error-visibility checks passed")
