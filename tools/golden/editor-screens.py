#!/usr/bin/env python3
"""G6 dependency/readiness front, then the byte-preserved screenshot core.

The actual capture implementation lives in editor-screens-core.py. Keeping this
front small makes dependency failures causal: a fresh worktree without the
ignored Three.js vendor surface fails before Node, Chrome, or any screenshot
wait expression can hide the missing module behind a timeout (#579).

The front also owns the host-bound readiness exceptions required by #739. The
initial Map workspace boot and the four Map workspace frames that require
runtime-authored geometry wait on a positive observation of the actual
loadRenderable producer. Their observation budget is derived from the measured
worktree's exported runtime-bridge timeout contract, plus a small publication
headroom. Other G6 waits keep the core's ordinary bound. Mutable toolbar prose
is diagnostic only: fallback/error cannot certify runtime-authority readiness.

When the relative recorder invokes this canonical harness against a detached
base/candidate worktree, SECOND_RITE_G6_ROOT names that target. The harness code
comes from one revision, while every observed product path (data, references,
server and runtime bridge) is rebound to the target root. This is what lets a
harness-reliability change repair base capture without overlaying candidate
product code onto the base.
"""

import json
import os
from pathlib import Path
import re
import runpy
import sys
import time

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("SECOND_RITE_G6_ROOT", str(DEFAULT_ROOT))).resolve()
CORE = Path(__file__).with_name("editor-screens-core.py")
REPAIR = "npm ci --ignore-scripts && node studio/editor/sync-three-vendor.js"
REQUIRED_THREE = (
    "three.module.js",
    "three.core.js",
    "OrbitControls.js",
    "TransformControls.js",
    "OBJLoader.js",
    "MTLLoader.js",
)

BRIDGE_TIMEOUT_PATTERN = re.compile(r"\bconst\s+BRIDGE_TIMEOUT_MS\s*=\s*(\d+)\s*;")
RUNTIME_AUTHORITY_SETTLE_HEADROOM = 5.0


def studio_editor_dir(root):
    """Locate the Studio editor as the measured checkout spells it.

    One harness revision drives base-A/base-B/candidate, and those worktrees can
    straddle the Studio root move (#702). Every product path the harness rebinds
    to the target root has to be spelled by that target, not by the harness.
    """
    target = Path(root)
    for parts in (("studio", "editor"), ("tools", "editor")):
        candidate = target.joinpath(*parts)
        if candidate.is_dir():
            return candidate
    # A checkout with neither spelling is a missing dependency, not a harness
    # fault: name the current one so the preflight can report it as absent.
    return target / "studio" / "editor"


def runtime_authority_ready_timeout(root=DEFAULT_ROOT):
    """Derive the observation bound from the target bridge's executable contract."""
    bridge = studio_editor_dir(root) / "runtime-bridge-server.js"
    try:
        source = bridge.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError("cannot read G6 runtime-authority timeout contract: %s" % bridge) from exc
    match = BRIDGE_TIMEOUT_PATTERN.search(source)
    if not match:
        raise RuntimeError("G6 runtime bridge no longer exposes BRIDGE_TIMEOUT_MS: %s" % bridge)
    timeout_ms = int(match.group(1))
    if timeout_ms <= 0:
        raise RuntimeError("G6 runtime bridge has invalid BRIDGE_TIMEOUT_MS=%s" % timeout_ms)
    return timeout_ms / 1000.0 + RUNTIME_AUTHORITY_SETTLE_HEADROOM


# Compatibility/default fixture value. The live canonical harness derives this
# again from SECOND_RITE_G6_ROOT so base-A/base-B/candidate obey the producer
# contract of the exact worktree being measured rather than coordinator prose.
RUNTIME_AUTHORITY_READY_TIMEOUT = runtime_authority_ready_timeout(DEFAULT_ROOT)

# The initial workspace is producer-bound too: page boot starts loadActiveMap()
# before the first screenshot step and can therefore start loadRenderable before
# a wait-loop-installed wrapper gets a chance to observe it.
INITIAL_RUNTIME_WAIT = "the initial workspace to settle"

# These workspace-view steps historically duplicated the producer contract by
# waiting on mutable toolbar prose (`runtime geometry|fallback`). Their actual
# positive contract is the latest workspace revision PLUS successful completion
# of the runtime-authority producer. Keep the remaining predicate about the
# user-facing control/canvas the frame intends to photograph.
WORKSPACE_RUNTIME_STEPS = frozenset({
    "map-editor/workspace-perspective.png",
    "map-editor/workspace-top-ortho.png",
    "map-editor/workspace-light.png",
    "map-editor/workspace-event-gizmo.png",
})
# #815: these two frames are bound by a runtime-authority REQUEST rather than
# by workspace lifecycle. POST /api/map-inspection is allowed BRIDGE_TIMEOUT_MS
# (60s) to answer, but their readiness waits were falling through to
# STEP_TIMEOUT (30s) -- so the harness abandoned, and reported a stall against,
# an operation the system was still legitimately performing. That is the whole
# of the ~10-15% G6 flake: every observed occurrence had
# map-inspection-status still on "Resolving through the real engine...".
#
# They are kept separate from WORKSPACE_RUNTIME_STEPS because the two need
# different treatment: those gate on a workspace-readiness EXPRESSION, these
# on a request completing.
INSPECTION_RUNTIME_STEPS = frozenset({
    "map-editor/generated-inspection.png",
    "map-editor/generated-inspection-stale.png",
})
RUNTIME_STATUS_WAIT_CLAUSE = (
    " && /(runtime geometry|fallback)$/.test("
    "document.getElementById('thestra-map-view-status').textContent)"
)

RUNTIME_AUTHORITY_READY_JS = r"""
(function () {
    var status = document.getElementById('thestra-map-view-status');
    var authority = window.__g6RuntimeAuthority || {};
    return !!(status &&
              status.dataset.workspaceReady === '1' &&
              authority.pending === 0 &&
              authority.lastOutcome === 'runtime');
})()
""".strip()

# Install before any page script executes. The adapter's browser UMD assigns
# window.SecondRiteEditorAdapter during script evaluation; the temporary property
# trap wraps loadRenderable at that exact assignment, before page boot can call
# loadActiveMap(). Later wait loops call the same installer defensively.
EARLY_RUNTIME_AUTHORITY_OBSERVABILITY_JS = r"""
(function () {
    function install(adapter) {
        if (!adapter || typeof adapter.loadRenderable !== 'function') return false;
        if (adapter.loadRenderable.__g6AuthorityWrapped) return true;

        var upstream = adapter.loadRenderable;
        var state = window.__g6RuntimeAuthority = window.__g6RuntimeAuthority || {
            generation: 0,
            pending: 0,
            started: 0,
            succeeded: 0,
            failed: 0,
            lastOutcome: 'none',
            lastError: ''
        };

        function fail(generation, error) {
            state.pending = Math.max(0, state.pending - 1);
            state.failed += 1;
            if (generation === state.generation) {
                state.lastOutcome = 'fallback';
                state.lastError = String(error && error.message || error || 'unknown runtime-authority error');
            }
        }

        function wrappedLoadRenderable() {
            var generation = ++state.generation;
            state.pending += 1;
            state.started += 1;
            state.lastOutcome = 'pending';
            state.lastError = '';
            var result;
            try {
                result = upstream.apply(this, arguments);
            } catch (error) {
                fail(generation, error);
                throw error;
            }
            return Promise.resolve(result).then(function (value) {
                state.pending = Math.max(0, state.pending - 1);
                state.succeeded += 1;
                if (generation === state.generation) {
                    state.lastOutcome = 'runtime';
                    state.lastError = '';
                }
                return value;
            }, function (error) {
                fail(generation, error);
                throw error;
            });
        }
        wrappedLoadRenderable.__g6AuthorityWrapped = true;
        adapter.loadRenderable = wrappedLoadRenderable;
        return true;
    }

    window.__g6InstallRuntimeAuthorityObservability = install;
    if (window.SecondRiteEditorAdapter) {
        install(window.SecondRiteEditorAdapter);
        return;
    }

    var assigned;
    Object.defineProperty(window, 'SecondRiteEditorAdapter', {
        configurable: true,
        get: function () { return assigned; },
        set: function (value) {
            assigned = value;
            install(value);
        }
    });
})();
"""

INSTALL_RUNTIME_AUTHORITY_OBSERVABILITY_JS = r"""
(function () {
    var install = window.__g6InstallRuntimeAuthorityObservability;
    return typeof install === 'function' ? install(window.SecondRiteEditorAdapter) : false;
})()
"""

FETCH_OBSERVABILITY_JS = r"""
(function () {
    var upstreamFetch = window.fetch.bind(window);
    var state = window.__g6RuntimeRenderableRequest = {
        pending: 0,
        url: '',
        method: '',
        completed: 0,
        failed: 0
    };
    // #1263: POST /api/map-inspection is a different request from
    // /api/map-renderable, so the counters above say "nothing pending" while the
    // page is genuinely waiting on it. Track it separately, with timing, so a
    // stall on an inspection frame can be told apart: still in flight (and for
    // how long), answered with an error, aborted by the client's own deadline,
    // or never started.
    var inspection = window.__g6MapInspectionRequest = {
        pending: 0,
        started: 0,
        completed: 0,
        failed: 0,
        url: '',
        method: '',
        lastStatus: 0,
        lastDurationMs: 0,
        lastError: '',
        nextId: 0,
        pendingSince: {}
    };
    window.fetch = function (input, init) {
        var url = (typeof input === 'string') ? input : (input && input.url) || '';
        if (url.indexOf('/api/map-inspection') >= 0) {
            var id = inspection.nextId += 1;
            var began = performance.now();
            inspection.pending += 1;
            inspection.started += 1;
            inspection.url = url;
            inspection.method = (init && init.method) || 'GET';
            inspection.pendingSince[id] = began;
            var settle = function () {
                inspection.pending -= 1;
                delete inspection.pendingSince[id];
                inspection.lastDurationMs = Math.round(performance.now() - began);
            };
            return upstreamFetch.apply(null, arguments).then(function (response) {
                settle();
                inspection.completed += 1;
                inspection.lastStatus = response.status;
                return response;
            }, function (error) {
                settle();
                inspection.failed += 1;
                inspection.lastError = String(error && error.message || error);
                throw error;
            });
        }
        if (url.indexOf('/api/map-renderable') < 0) {
            return upstreamFetch.apply(null, arguments);
        }
        state.pending += 1;
        state.url = url;
        state.method = (init && init.method) || 'GET';
        return upstreamFetch.apply(null, arguments).then(function (response) {
            state.pending -= 1;
            state.completed += 1;
            return response;
        }, function (error) {
            state.pending -= 1;
            state.failed += 1;
            throw error;
        });
    };
})();
"""

STALL_OBSERVATION_JS = r"""
(function () {
    var status = document.getElementById('thestra-map-view-status');
    var viewport = document.getElementById('thestra-map-viewport');
    var canvas = viewport && viewport.querySelector('canvas');
    var perspective = document.querySelector('#thestra-map-view-toolbar button[data-mode=perspective]');
    var top = document.querySelector('#thestra-map-view-toolbar button[data-mode=top]');
    var request = window.__g6RuntimeRenderableRequest || {};
    var authority = window.__g6RuntimeAuthority || {};
    var inspection = window.__g6MapInspectionRequest || {};
    var inspectionOldestPendingMs = 0;
    var pendingSince = inspection.pendingSince || {};
    Object.keys(pendingSince).forEach(function (id) {
        inspectionOldestPendingMs = Math.max(
            inspectionOldestPendingMs, Math.round(performance.now() - pendingSince[id]));
    });
    var map = (typeof dbPayload !== 'undefined' && dbPayload.maps &&
               typeof currentMapIndex !== 'undefined') ? dbPayload.maps[currentMapIndex] : null;
    return JSON.stringify({
        href: location.href,
        mapIndex: (typeof currentMapIndex === 'undefined') ? null : currentMapIndex,
        mapId: map && map.id,
        workspaceStatus: status && status.textContent,
        workspaceDetail: status && status.title,
        workspaceReady: status && status.dataset.workspaceReady,
        workspaceRevision: status && status.dataset.workspaceRevision,
        runtimeAuthorityOutcome: authority.lastOutcome || 'unobserved',
        runtimeAuthorityPending: authority.pending || 0,
        runtimeAuthorityStarted: authority.started || 0,
        runtimeAuthoritySucceeded: authority.succeeded || 0,
        runtimeAuthorityFailed: authority.failed || 0,
        runtimeAuthorityError: authority.lastError || '',
        perspectiveDisabled: perspective && perspective.disabled,
        topDisabled: top && top.disabled,
        viewportVisible: !!(viewport && viewport.getClientRects().length),
        canvasWidth: canvas && canvas.width,
        canvasHeight: canvas && canvas.height,
        renderableRequestPending: request.pending || 0,
        renderableRequestUrl: request.url || '',
        renderableRequestMethod: request.method || '',
        renderableRequestsCompleted: request.completed || 0,
        renderableRequestsFailed: request.failed || 0,
        inspectionRequestPending: inspection.pending || 0,
        inspectionRequestsStarted: inspection.started || 0,
        inspectionRequestsCompleted: inspection.completed || 0,
        inspectionRequestsFailed: inspection.failed || 0,
        inspectionRequestOldestPendingMs: inspectionOldestPendingMs,
        inspectionRequestLastDurationMs: inspection.lastDurationMs || 0,
        inspectionRequestLastStatus: inspection.lastStatus || 0,
        inspectionRequestLastError: inspection.lastError || ''
    });
})()
"""

# What the two inspection frames report when they SUCCEED. Same fields as the
# stall snapshot, read on their own so the success path stays cheap and a failed
# read can be ignored without touching the stall path.
INSPECTION_OBSERVATION_JS = r"""
(function () {
    var i = window.__g6MapInspectionRequest;
    if (!i) { return null; }
    return JSON.stringify({
        started: i.started, completed: i.completed, failed: i.failed,
        pending: i.pending, lastDurationMs: i.lastDurationMs,
        lastStatus: i.lastStatus, lastError: i.lastError
    });
})()
"""


def required_paths(root=ROOT):
    vendor = studio_editor_dir(root) / "vendor" / "three"
    return [vendor / name for name in REQUIRED_THREE]


def missing_dependencies(root=ROOT):
    return [path for path in required_paths(root) if not path.is_file()]


def emit_missing(paths, root=ROOT):
    root = Path(root)
    relative = []
    for path in paths:
        try:
            relative.append(path.relative_to(root).as_posix())
        except ValueError:
            relative.append(str(path))
    payload = {"kind": "three-vendor", "paths": relative, "repair": REPAIR}
    print("G6_DEPENDENCY_MISSING_JSON " + json.dumps(payload, sort_keys=True))
    print("editor-screens.py: required Three.js editor vendor files are missing:", file=sys.stderr)
    for path in relative:
        print("  - " + path, file=sys.stderr)
    print("Prepare them with: " + REPAIR, file=sys.stderr)


def rewrite_workspace_runtime_steps(steps):
    """Replace mutable toolbar copy with positive runtime-authority state."""
    seen = set()
    authority_clause = " && (" + RUNTIME_AUTHORITY_READY_JS + ")"
    for step in steps:
        path = step.get("path")
        if path not in WORKSPACE_RUNTIME_STEPS:
            continue
        wait = step.get("wait", "")
        if RUNTIME_STATUS_WAIT_CLAUSE not in wait:
            raise RuntimeError(
                "G6 workspace readiness front no longer matches %s; update the contract explicitly"
                % path
            )
        step["wait"] = wait.replace(RUNTIME_STATUS_WAIT_CLAUSE, authority_clause)
        seen.add(path)
    if seen != set(WORKSPACE_RUNTIME_STEPS):
        missing = sorted(set(WORKSPACE_RUNTIME_STEPS) - seen)
        raise RuntimeError("G6 workspace readiness steps missing: %s" % ", ".join(missing))
    return steps


def readiness_timeout(expression, workspace_ready, ordinary_timeout, producer_timeout=None):
    """Return the predicate budget; callers still scope where it may apply."""
    if expression.strip() == workspace_ready.strip():
        return (RUNTIME_AUTHORITY_READY_TIMEOUT if producer_timeout is None
                else producer_timeout)
    return ordinary_timeout


def runtime_step_for_wait(what):
    if what == INITIAL_RUNTIME_WAIT:
        return INITIAL_RUNTIME_WAIT
    for path in WORKSPACE_RUNTIME_STEPS:
        if what == path or what.startswith(path + " "):
            return path
    return None


def inspection_step_for_wait(what):
    for path in INSPECTION_RUNTIME_STEPS:
        if what == path or what.startswith(path + " "):
            return path
    return None


def scoped_readiness_timeout(expression, what, workspace_ready, ordinary_timeout, producer_timeout):
    """Give producer headroom only to waits that require runtime authority."""
    # A wait on an in-flight authority request gets the producer bound, whatever
    # its predicate looks like: the thing being waited on is the request.
    if inspection_step_for_wait(what) is not None:
        return producer_timeout
    if runtime_step_for_wait(what) is None:
        return ordinary_timeout
    if (expression.strip() == workspace_ready.strip()
            or RUNTIME_AUTHORITY_READY_JS in expression):
        return producer_timeout
    return ordinary_timeout


def effective_readiness_expression(expression, what, workspace_ready):
    """Make runtime-bound workspace lifecycle waits require actual runtime success."""
    if (runtime_step_for_wait(what) is not None
            and expression.strip() == workspace_ready.strip()):
        return RUNTIME_AUTHORITY_READY_JS
    return expression


def bind_core_root(core, root=ROOT):
    """Point canonical harness globals and host classes at the product target."""
    target = Path(root).resolve()
    globals_ = core["run_capture_set"].__globals__
    server_js = str(studio_editor_dir(target) / "server.js")
    bridge_js = str(studio_editor_dir(target) / "runtime-bridge-server.js")
    globals_["ROOT"] = str(target)
    globals_["REF_DIR"] = str(target / "tools" / "golden" / "editor-screens")
    globals_["ACTUAL_DIR"] = str(target / "tools" / "golden" / "editor-screens-actual")
    globals_["SERVER_JS"] = server_js
    globals_["BRIDGE_JS"] = bridge_js
    # These class attributes were initialized when the canonical core module was
    # executed. Updating only the globals is too late: the classes would keep
    # launching the workflow checkout's servers, which have no target worktree
    # vendor preparation. Rebind the concrete host classes too.
    globals_["EditorServer"].script = server_js
    globals_["RuntimeBridge"].script = bridge_js
    return core


def report_inspection_wait(page, what, waited, bound, log=print):
    """One line for a SUCCESSFUL wait on a Map inspection frame.

    #1263: the stall reports say what a failing wait saw, but the question the
    timeout decision needs answered is how close the passing ones come to the
    bound. Printing this for every leg puts that distribution in ordinary run
    output. Only the step's own wait reports (a sub-wait such as
    "<path> reset workspace" would double-count), and this is observability:
    a failed read must never fail the gate.
    """
    if what not in INSPECTION_RUNTIME_STEPS:
        return
    try:
        raw = page.evaluate(INSPECTION_OBSERVATION_JS)
        seen = json.loads(raw) if raw else {}
    except (RuntimeError, ValueError):
        return
    if not seen:
        return
    log("           inspection wait: %.1fs of a %.0fs bound; last request %.1fs, "
        "status %s (started %s / completed %s / failed %s)"
        % (waited, bound, seen.get("lastDurationMs", 0) / 1000.0,
           seen.get("lastStatus", 0), seen.get("started", 0),
           seen.get("completed", 0), seen.get("failed", 0)))


def configure_runtime_authority_readiness(core):
    """Bind G6 to the Map workspace's positive host readiness contract."""
    globals_ = core["run_capture_set"].__globals__
    workspace_ready = globals_["WORKSPACE_READY_JS"]
    ordinary_timeout = globals_["STEP_TIMEOUT"]
    producer_timeout = runtime_authority_ready_timeout(ROOT)
    HarnessStall = globals_["HarnessStall"]
    stall_detail = globals_["stall_detail"]
    Chrome = globals_["Chrome"]
    original_build_steps = globals_["build_steps"]

    def build_steps():
        return rewrite_workspace_runtime_steps(original_build_steps())

    def wait_for(self, expression, what):
        timeout = scoped_readiness_timeout(
            expression, what, workspace_ready, ordinary_timeout, producer_timeout,
        )
        observed_expression = effective_readiness_expression(expression, what, workspace_ready)
        started = time.time()
        deadline = started + timeout
        last = None
        while time.time() < deadline:
            try:
                # The new-document trap observes page boot itself. Re-run the
                # same installer here defensively in case a test replaces the
                # adapter object after document initialization.
                self.evaluate(INSTALL_RUNTIME_AUTHORITY_OBSERVABILITY_JS)
                if self.evaluate("!!(%s)" % observed_expression):
                    report_inspection_wait(self, what, time.time() - started, timeout)
                    return
                last = None
            except RuntimeError as exc:
                last = exc
            else:
                # #831: stop waiting once the page has reported a failure.
                failure = self.terminal_failure(observed_expression)
                if failure:
                    raise HarnessStall(what, observed_expression, RuntimeError(failure))
            time.sleep(0.1)
        # Preserve a concrete producer snapshot even when the predicate itself
        # simply remained false. relative-capture promotes this as `last error`.
        try:
            observed = self.evaluate(STALL_OBSERVATION_JS)
            if observed:
                # #1263: say how long the harness actually waited and against
                # which bound. The wait ends at the bridge's own timeout, so
                # "stalled" and "the engine answered just after we gave up" are
                # indistinguishable without both numbers.
                last = RuntimeError(
                    "observed page state: %s; waited %.1fs of a %.0fs bound"
                    % (observed, time.time() - started, timeout))
        except RuntimeError as observation_error:
            if last is None:
                last = observation_error
        # #831: the producer snapshot above describes the workspace, not the
        # element the predicate actually reads. Report both.
        last = stall_detail(self.describe_watched(observed_expression), last)
        raise HarnessStall(what, observed_expression, last)

    globals_["build_steps"] = build_steps
    globals_["DETERMINISM_JS"] = (
        globals_["DETERMINISM_JS"] + "\n"
        + EARLY_RUNTIME_AUTHORITY_OBSERVABILITY_JS + "\n"
        + FETCH_OBSERVABILITY_JS
    )
    Chrome.wait_for = wait_for
    return core


def run_core():
    core = runpy.run_path(str(CORE), run_name="second_rite_g6_core")
    bind_core_root(core)
    configure_runtime_authority_readiness(core)
    HarnessStall = core["HarnessStall"]
    try:
        core["main"]()
    except HarnessStall as stall:
        print("G6 HARNESS STALL", file=sys.stderr)
        print("  step: %s" % stall.step, file=sys.stderr)
        print("  predicate: %s" % stall.predicate, file=sys.stderr)
        if stall.last_error:
            print("  last error: %s" % stall.last_error, file=sys.stderr)
        print("  No pixel comparison completed for this step.", file=sys.stderr)
        stall_payload = {
            "status": "incomplete",
            "completedSteps": getattr(stall, "completed_steps", None),
            "totalDeclared": getattr(stall, "total_declared", None),
            "stall": {
                "step": stall.step,
                "predicate": stall.predicate,
                "lastError": str(stall.last_error) if stall.last_error else None,
            },
        }
        print("G6_RESULT_JSON " + json.dumps(stall_payload, sort_keys=True))
        return 2
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, int):
            return code
        if code is None:
            return 0
        print(str(code), file=sys.stderr)
        return 1
    return 0


def main():
    missing = missing_dependencies()
    if missing:
        emit_missing(missing)
        return 86
    if os.environ.get("SECOND_RITE_G6_PREFLIGHT_ONLY") == "1":
        print("G6 DEPENDENCIES OK")
        return 0
    if not CORE.is_file():
        print("editor-screens.py: missing capture core: " + str(CORE), file=sys.stderr)
        return 87
    return run_core()


if __name__ == "__main__":
    raise SystemExit(main())
