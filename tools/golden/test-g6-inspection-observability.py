"""#1263: a stalled Map-inspection wait must say what the request was doing.

The two inspection frames stall with `#map-inspection-status = "Resolving through
the real engine..."` while every counter the harness kept read "nothing pending",
because those counters only watched /api/map-renderable. So the stall could not
be told apart: request still in flight (and for how long), answered with an
error, aborted by the client's own deadline, or never started.

This suite does NOT change any timeout. It checks that:
  * the in-page tracker counts /api/map-inspection requests and their timing,
    and touches nothing else (executed for real, in Node, against a fake clock
    and a controllable fetch);
  * a stall reports that state plus how long the harness waited and against
    which bound, with the existing "observed page state:" prefix intact;
  * a passing wait on an inspection frame reports its latency once, so ordinary
    runs build the distribution the timeout decision needs -- and a failed read
    of it can never fail the gate.

Negative controls carry the suite: each asserts that something which must NOT
change (other URLs, other frames, the renderable counters, the gate outcome) did
not.
"""
import contextlib
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCREENS = ROOT / "tools/golden/editor-screens.py"
CORE = ROOT / "tools/golden/editor-screens-core.py"

mod = {"__file__": str(SCREENS), "__name__": "editor_screens_under_test"}
exec(compile(io.open(SCREENS, encoding="utf-8").read(), str(SCREENS), "exec"), mod)
core = mod["runpy"].run_path(str(CORE), run_name="second_rite_g6_core_under_test")
mod["bind_core_root"](core)
mod["configure_runtime_authority_readiness"](core)

Chrome = core["Chrome"]
HarnessStall = core["HarnessStall"]
INSPECTION_STEPS = sorted(mod["INSPECTION_RUNTIME_STEPS"])
STALL_JS = mod["STALL_OBSERVATION_JS"]
OBS_JS = mod["INSPECTION_OBSERVATION_JS"]
INSTALL_JS = mod["INSTALL_RUNTIME_AUTHORITY_OBSERVABILITY_JS"]
# The bounds the harness really uses, read from the same source it reads them
# from -- not restated here, so a change to either is a change to this test's
# expectations rather than a silent mismatch.
ORDINARY = core["STEP_TIMEOUT"]
PRODUCER = mod["runtime_authority_ready_timeout"](ROOT)

failures = []


def check(name, condition, detail=""):
    if condition:
        print("ok   %s" % name)
    else:
        print("FAIL %s %s" % (name, detail))
        failures.append(name)


# --- 1. the in-page tracker, executed for real --------------------------------
DRIVER = r"""
const vm = require('vm');
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
let clock = 1000;
const upstream = [];
const sandbox = {
    performance: { now: () => clock },
    document: { getElementById: () => null, querySelector: () => null },
    location: { href: 'http://127.0.0.1/' },
};
sandbox.window = sandbox;
sandbox.fetch = (url, init) => new Promise((resolve, reject) =>
    upstream.push({ url, init, resolve, reject }));
vm.createContext(sandbox);
vm.runInContext(input.fetchJs, sandbox);
const snap = () => JSON.parse(vm.runInContext(input.stallJs, sandbox));
const out = {};
(async () => {
    out.initial = snap();

    // A request that has not answered, 40 s in.
    const a = sandbox.window.fetch('/api/map-inspection', { method: 'POST' });
    clock += 40000;
    out.pending = snap();
    out.upstreamSawIt = upstream[0].url === '/api/map-inspection'
        && upstream[0].init.method === 'POST';
    upstream[0].resolve({ status: 200, marker: 'same-object' });
    const response = await a;
    out.passthroughResponse = response.marker === 'same-object';
    out.answered = snap();

    // A request the client aborts at its own deadline.
    const b = sandbox.window.fetch('/api/map-inspection');
    clock += 75000;
    upstream[1].reject(new Error('The user aborted a request.'));
    try { await b; out.rejectionRethrown = false; }
    catch (error) { out.rejectionRethrown = error.message === 'The user aborted a request.'; }
    out.aborted = snap();

    // Requests to anything else must not touch the inspection counters, and an
    // inspection request must not touch the renderable ones.
    const before = snap();
    const c = sandbox.window.fetch('/api/somewhere-else');
    upstream[2].resolve({ status: 200 });
    await c;
    const d = sandbox.window.fetch('/api/map-renderable', { method: 'POST' });
    upstream[3].resolve({ status: 200 });
    await d;
    out.beforeOthers = before;
    out.afterOthers = snap();

    // Two in flight: the oldest one is what a stall should report.
    const e = sandbox.window.fetch('/api/map-inspection');
    clock += 10000;
    const f = sandbox.window.fetch('/api/map-inspection');
    clock += 5000;
    out.two = snap();
    upstream[4].resolve({ status: 200 });
    await e;
    out.afterFirstOfTwo = snap();
    upstream[5].resolve({ status: 200 });
    await f;
    console.log(JSON.stringify(out));
})();
"""

node = shutil.which("node")
check("node is available (G6 needs it to boot the editor anyway)", node is not None)
tracker = None
if node:
    fetch_js = mod["FETCH_OBSERVABILITY_JS"]
    proc = subprocess.run(
        [node, "-e", DRIVER], input=json.dumps({"fetchJs": fetch_js, "stallJs": STALL_JS}),
        capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        print("FAIL node driver exited %d: %s" % (proc.returncode, proc.stderr[-400:]))
        failures.append("node driver")
    else:
        tracker = json.loads(proc.stdout)

if tracker:
    t = tracker
    check("nothing is reported before any request",
          t["initial"]["inspectionRequestsStarted"] == 0
          and t["initial"]["inspectionRequestPending"] == 0
          and t["initial"]["inspectionRequestOldestPendingMs"] == 0)
    check("an unanswered request is pending, and its age is reported",
          t["pending"]["inspectionRequestPending"] == 1
          and t["pending"]["inspectionRequestsStarted"] == 1
          and t["pending"]["inspectionRequestOldestPendingMs"] == 40000,
          repr({k: v for k, v in t["pending"].items() if k.startswith("inspection")}))
    check("the request still reaches the upstream fetch unchanged", t["upstreamSawIt"])
    check("the caller still receives the very same response", t["passthroughResponse"])
    check("an answered request records status and duration",
          t["answered"]["inspectionRequestPending"] == 0
          and t["answered"]["inspectionRequestsCompleted"] == 1
          and t["answered"]["inspectionRequestLastStatus"] == 200
          and t["answered"]["inspectionRequestLastDurationMs"] == 40000
          and t["answered"]["inspectionRequestOldestPendingMs"] == 0)
    check("a rejected request is counted, timed and its reason kept",
          t["aborted"]["inspectionRequestsFailed"] == 1
          and t["aborted"]["inspectionRequestLastError"] == "The user aborted a request."
          and t["aborted"]["inspectionRequestLastDurationMs"] == 75000
          and t["aborted"]["inspectionRequestPending"] == 0)
    check("a rejected request is still rethrown to the page", t["rejectionRethrown"])
    b, a_ = t["beforeOthers"], t["afterOthers"]
    check("NEGATIVE CONTROL: other URLs leave the inspection counters alone",
          all(a_[k] == b[k] for k in a_ if k.startswith("inspectionRequest")),
          repr({k: (b[k], a_[k]) for k in a_ if k.startswith("inspectionRequest")
                and a_[k] != b[k]}))
    check("NEGATIVE CONTROL: an inspection request does not touch the renderable counters",
          b["renderableRequestsCompleted"] == 0 and b["renderableRequestPending"] == 0)
    check("the renderable tracker still counts its own request",
          a_["renderableRequestsCompleted"] == 1 and a_["renderableRequestMethod"] == "POST")
    check("with two in flight the OLDEST age is reported",
          t["two"]["inspectionRequestPending"] == 2
          and t["two"]["inspectionRequestOldestPendingMs"] == 15000,
          str(t["two"]["inspectionRequestOldestPendingMs"]))
    check("answering the older one leaves the younger one's age",
          t["afterFirstOfTwo"]["inspectionRequestPending"] == 1
          and t["afterFirstOfTwo"]["inspectionRequestOldestPendingMs"] == 5000,
          str(t["afterFirstOfTwo"]["inspectionRequestOldestPendingMs"]))
    # runpy hands back a COPY of the module namespace; the live one is the
    # namespace the harness functions actually run in.
    live = core["run_capture_set"].__globals__
    check("the tracker is installed for every page (in DETERMINISM_JS)",
          "__g6MapInspectionRequest" in live["DETERMINISM_JS"])

# --- 2. the wait, driven by a fake clock and a fake page ------------------------


class FakeTime(object):
    """A clock that only moves when the harness sleeps."""

    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def make_page(predicate=False, observation=None, inspection=None, inspection_error=False):
    page = Chrome.__new__(Chrome)

    def evaluate(expression, await_promise=False):
        if expression == INSTALL_JS:
            return True
        if expression.startswith("!!("):
            return predicate
        if expression == STALL_JS:
            return observation
        if expression == OBS_JS:
            if inspection_error:
                raise RuntimeError("page gone")
            return inspection
        if "JSON.stringify(out)" in expression:
            return "{}"
        raise RuntimeError("unexpected evaluate: %s" % expression[:60])

    page.evaluate = evaluate
    return page


STATE = json.dumps({"workspaceStatus": "Event", "inspectionRequestPending": 0,
                    "inspectionRequestOldestPendingMs": 0})
PRED = "document.getElementById('x').textContent === 'y'"
STEP = INSPECTION_STEPS[0]
real_time = mod["time"]
mod["time"] = clock = FakeTime()


def run_wait(page, what):
    """Returns (stall_or_None, printed_lines)."""
    clock.now = 1000.0
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            page.wait_for(PRED, what)
        stall = None
    except HarnessStall as caught:
        stall = caught
    return stall, [line for line in out.getvalue().splitlines() if line.strip()]


# A stall on an inspection frame: the producer bound, and the wait reported.
stall, printed = run_wait(make_page(observation=STATE), STEP)
text = str(stall.last_error) if stall else ""
check("a stalled inspection wait still raises HarnessStall", stall is not None)
check("the existing 'observed page state:' prefix is intact",
      "observed page state: " + STATE in text, text[:200])
check("the stall says how long it waited, against which bound",
      "waited " in text and "s of a %.0fs bound" % PRODUCER in text, text[-120:])
waited = float(text.split("waited ")[1].split("s of")[0]) if "waited " in text else -1
check("the waited time is the real wait (about the bound), not zero",
      PRODUCER - 1.0 <= waited <= PRODUCER + 1.5, str(waited))

# NEGATIVE CONTROL: the bound reported is the one actually used.
stall, printed = run_wait(make_page(observation=STATE), "database/units.png")
text = str(stall.last_error) if stall else ""
check("NEGATIVE CONTROL: an ordinary frame reports the ORDINARY bound",
      "s of a %.0fs bound" % ORDINARY in text and "%.0fs bound" % PRODUCER not in text,
      text[-80:])

# A passing wait on an inspection frame reports its latency, once.
INS = json.dumps({"started": 2, "completed": 2, "failed": 0, "pending": 0,
                  "lastDurationMs": 3400, "lastStatus": 200, "lastError": ""})
stall, printed = run_wait(make_page(predicate=True, inspection=INS), STEP)
check("a passing inspection wait does not stall", stall is None)
check("it reports exactly one latency line", len(printed) == 1, repr(printed))
line = printed[0] if printed else ""
check("the line carries the request latency, status and counts",
      "last request 3.4s" in line and "status 200" in line
      and "started 2 / completed 2 / failed 0" in line
      and "of a %.0fs bound" % PRODUCER in line, line)
check("the line is anchored to the frame's own wait time",
      "inspection wait: 0.0s" in line, line)

# NEGATIVE CONTROLS: nothing else reports, and reporting can never fail the gate.
for other in ("database/units.png", STEP + " reset workspace",
              STEP + " workspace refresh", "map-editor/workspace-light.png"):
    stall, printed = run_wait(make_page(predicate=True, inspection=INS), other)
    check("NEGATIVE CONTROL: %r prints nothing" % other,
          stall is None and printed == [], repr(printed))
stall, printed = run_wait(make_page(predicate=True, inspection_error=True), STEP)
check("NEGATIVE CONTROL: a failed observation read does not fail the wait",
      stall is None and printed == [])
stall, printed = run_wait(make_page(predicate=True, inspection="not json"), STEP)
check("NEGATIVE CONTROL: an unparseable observation does not fail the wait",
      stall is None and printed == [])
stall, printed = run_wait(make_page(predicate=True, inspection=None), STEP)
check("NEGATIVE CONTROL: no tracker in the page reports nothing, and does not fail",
      stall is None and printed == [])

# The timeout contract is untouched: this suite adds observability only.
scoped = mod["scoped_readiness_timeout"]
check("NEGATIVE CONTROL: the inspection bound is still the producer bound",
      scoped(PRED, STEP, "ws", ORDINARY, PRODUCER) == PRODUCER
      and scoped(PRED, "database/units.png", "ws", ORDINARY, PRODUCER) == ORDINARY)

mod["time"] = real_time

if failures:
    print("")
    print("INSPECTION OBSERVABILITY TEST FAILED: %d check(s)" % len(failures))
    sys.exit(1)
print("")
print("all G6 inspection-observability checks passed")
