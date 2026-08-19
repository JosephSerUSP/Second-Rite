#!/usr/bin/env python3
"""Passive per-frame timing for G6 (#815).

This module is intentionally a wrapper around the canonical screenshot harness,
not part of its capture algorithm. It observes existing method calls and return
values, keeps every measurement in memory while pixels are being captured, and
writes the timing batch only after the harness has finished. No extra CDP call,
sleep, readiness predicate, screenshot, or filesystem write is introduced into
the measured capture path.
"""

import json
import os
from pathlib import Path
import subprocess
import time


def relative_leg(target_root, environ=None):
    """Name the existing relative G6 control/candidate worktree when present."""
    environ = os.environ if environ is None else environ
    explicit = str(environ.get("THESTRA_G6_TIMING_LEG", "")).strip()
    if explicit:
        return explicit
    name = Path(target_root).name.lower()
    if name.startswith("g6-"):
        return name[3:]
    return "g6"


def timings_enabled(environ=None, target_root=None):
    environ = os.environ if environ is None else environ
    if str(environ.get("THESTRA_TIMINGS", "")).strip() == "0":
        return False
    # The existing Relative visual A/B workflow deliberately captures the same
    # base SHA twice as g6-base-a and g6-base-b. #815 uses that repeat as its
    # perturbation control: base-a stays byte-for-byte uninstrumented, base-b is
    # measured, and the already-authoritative relative comparator proves whether
    # timing changed any pixel. Ordinary/local G6 runs remain instrumented.
    return not (target_root is not None and relative_leg(target_root, environ) == "base-a")


def _ms(started):
    return max(0.0, (time.perf_counter() - started) * 1000.0)


def _round_ms(value):
    return max(0, int(round(float(value or 0))))


def timing_run_id(environ=None):
    environ = os.environ if environ is None else environ
    explicit = str(environ.get("THESTRA_TIMINGS_RUN_ID", "")).strip()
    if explicit:
        return explicit
    github = str(environ.get("GITHUB_RUN_ID", "")).strip()
    attempt = str(environ.get("GITHUB_RUN_ATTEMPT", "")).strip()
    if github:
        return "gh-%s-%s" % (github, attempt) if attempt else "gh-%s" % github
    return "g6-local-%d-%d" % (os.getpid(), int(time.time() * 1000))


def binding_condition(pending_checks, settled):
    """Name the last observed co-condition blocking canonical settlement.

    PENDING_IMAGES_JS is evaluated only after two frames match because Python
    short-circuits the canonical `and`. We record the screenshot ordinal beside
    each existing pending-images result. If the immediately preceding matching
    iteration was blocked only by pending images, pending-images was the last
    observed blocker. Otherwise the final frame match was the last observed
    blocker. This adds no browser observation and no duplicate pixel compare.
    """
    if not settled:
        return "unresolved"
    if len(pending_checks) < 2:
        return "frame-match"
    final_check = pending_checks[-1]
    previous = pending_checks[-2]
    if (int(previous.get("pending") or 0) > 0
            and int(previous.get("shot") or 0) == int(final_check.get("shot") or 0) - 1):
        return "pending-images"
    return "frame-match"


def _new_frame(path, index):
    return {
        "path": path,
        "index": index,
        "started": time.perf_counter(),
        "readinessMs": 0.0,
        "settlePreludeMs": 0.0,
        "stableWallMs": 0.0,
        "screenshotRoundTripsMs": [],
        "pendingChecks": [],
        "stableShotCount": 0,
        "iterations": 0,
        "settled": False,
        "ok": False,
    }


def _finalize_frame(state, frame):
    if frame.get("ended") is None:
        frame["ended"] = time.perf_counter()
    frame["wallMs"] = max(0.0, (frame["ended"] - frame["started"]) * 1000.0)
    screenshot_ms = sum(frame["screenshotRoundTripsMs"])
    frame["screenshotMs"] = screenshot_ms
    # stableWall includes screenshot round trips. The residual is sleeps plus
    # the existing PENDING_IMAGES_JS evaluations. SETTLE_JS is part of settling
    # too, but runs immediately before stable_screenshot in the canonical core.
    frame["settlingMs"] = max(
        0.0,
        frame["settlePreludeMs"] + frame["stableWallMs"] - screenshot_ms,
    )
    frame["otherMs"] = max(
        0.0,
        frame["wallMs"] - frame["readinessMs"] - frame["settlingMs"] - screenshot_ms,
    )
    frame["binding"] = binding_condition(frame["pendingChecks"], frame["settled"])
    state["frames"].append(frame)
    if state.get("current") is frame:
        state["current"] = None


def configure_capture_timings(core, target_root, environ=None):
    """Wrap the already-configured G6 core with passive in-memory timers."""
    environ = os.environ if environ is None else environ
    if not timings_enabled(environ, target_root):
        return None

    globals_ = core["run_capture_set"].__globals__
    Chrome = globals_["Chrome"]
    pending_images_js = globals_["PENDING_IMAGES_JS"]
    settle_js = globals_["SETTLE_JS"]
    reset_js = globals_["RESET_JS"]

    state = {
        "frames": [],
        "current": None,
        "stepPaths": [],
        "nextIndex": 0,
        "setupReadinessMs": 0.0,
        "legWallMs": 0.0,
        "legStarted": None,
        "inStable": False,
        "leg": relative_leg(target_root, environ),
        "runId": timing_run_id(environ),
        "targetSha": str(environ.get("THESTRA_G6_TIMING_TARGET_SHA", "")).strip() or None,
        "targetRoot": str(Path(target_root).resolve()),
    }

    original_build_steps = globals_["build_steps"]
    original_run_capture_set = globals_["run_capture_set"]
    original_wait_for = Chrome.wait_for
    original_evaluate = Chrome.evaluate
    original_screenshot = Chrome.screenshot
    original_stable_screenshot = Chrome.stable_screenshot

    def build_steps():
        steps = original_build_steps()
        state["stepPaths"] = [step.get("path", "unknown") for step in steps]
        return steps

    def run_capture_set():
        state["legStarted"] = time.perf_counter()
        try:
            return original_run_capture_set()
        finally:
            if state.get("current") is not None:
                _finalize_frame(state, state["current"])
            state["legWallMs"] = _ms(state["legStarted"])

    def wait_for(self, expression, what):
        started = time.perf_counter()
        try:
            return original_wait_for(self, expression, what)
        finally:
            elapsed = _ms(started)
            if state.get("current") is None:
                state["setupReadinessMs"] += elapsed
            else:
                state["current"]["readinessMs"] += elapsed

    def evaluate(self, expression, await_promise=False):
        if expression == reset_js and await_promise:
            if state.get("current") is not None:
                _finalize_frame(state, state["current"])
            index = state["nextIndex"]
            path = state["stepPaths"][index] if index < len(state["stepPaths"]) else "frame-%d" % (index + 1)
            state["current"] = _new_frame(path, index + 1)
            state["nextIndex"] += 1

        started = time.perf_counter() if (expression == settle_js and await_promise and state.get("current")) else None
        result = original_evaluate(self, expression, await_promise=await_promise)
        if started is not None:
            state["current"]["settlePreludeMs"] += _ms(started)
        if state.get("inStable") and expression == pending_images_js and state.get("current") is not None:
            state["current"]["pendingChecks"].append({
                "shot": state["current"].get("stableShotCount", 0),
                "pending": result,
            })
        return result

    def screenshot(self):
        started = time.perf_counter()
        result = original_screenshot(self)
        if state.get("inStable") and state.get("current") is not None:
            state["current"]["screenshotRoundTripsMs"].append(_ms(started))
            state["current"]["stableShotCount"] += 1
        return result

    def stable_screenshot(self, label, attempts=25, pause=0.2):
        frame = state.get("current")
        started = time.perf_counter()
        before = len(frame["screenshotRoundTripsMs"]) if frame is not None else 0
        state["inStable"] = True
        try:
            result = original_stable_screenshot(self, label, attempts=attempts, pause=pause)
            if frame is not None:
                frame["settled"] = True
                frame["ok"] = True
            return result
        finally:
            state["inStable"] = False
            if frame is not None:
                frame["stableWallMs"] += _ms(started)
                shots = len(frame["screenshotRoundTripsMs"]) - before
                # One initial screenshot precedes the comparison loop.
                frame["iterations"] = max(0, shots - 1)
                frame["ended"] = time.perf_counter()
                _finalize_frame(state, frame)

    globals_["build_steps"] = build_steps
    globals_["run_capture_set"] = run_capture_set
    Chrome.wait_for = wait_for
    Chrome.evaluate = evaluate
    Chrome.screenshot = screenshot
    Chrome.stable_screenshot = stable_screenshot
    return state


def timing_records(state):
    if not state:
        return []
    records = []
    for frame in state.get("frames", []):
        rounds = [_round_ms(value) for value in frame.get("screenshotRoundTripsMs", [])]
        tags = {
            "kind": "g6-frame",
            "leg": state.get("leg"),
            "targetSha": state.get("targetSha"),
            "frame": frame.get("path"),
            "index": frame.get("index"),
            "iterations": frame.get("iterations", 0),
            "binding": frame.get("binding", "unresolved"),
            "readinessMs": _round_ms(frame.get("readinessMs")),
            "settlingMs": _round_ms(frame.get("settlingMs")),
            "stableScreenshotMs": _round_ms(frame.get("stableWallMs")),
            "settlePreludeMs": _round_ms(frame.get("settlePreludeMs")),
            "screenshotMs": _round_ms(frame.get("screenshotMs")),
            "screenshotRoundTripsMs": rounds,
            "otherMs": _round_ms(frame.get("otherMs")),
        }
        records.append({
            "label": "G6 capture frame",
            "ms": _round_ms(frame.get("wallMs")),
            "exitCode": 0 if frame.get("ok") else 1,
            "ok": bool(frame.get("ok")),
            "tags": tags,
        })

    leg_wall = _round_ms(state.get("legWallMs"))
    frame_wall = sum(_round_ms(frame.get("wallMs")) for frame in state.get("frames", []))
    setup_readiness = _round_ms(state.get("setupReadinessMs"))
    records.append({
        "label": "G6 capture leg",
        "ms": leg_wall,
        "exitCode": 0 if all(frame.get("ok") for frame in state.get("frames", [])) else 1,
        "ok": bool(state.get("frames")) and all(frame.get("ok") for frame in state.get("frames", [])),
        "tags": {
            "kind": "g6-leg",
            "leg": state.get("leg"),
            "targetSha": state.get("targetSha"),
            "frameCount": len(state.get("frames", [])),
            "frameWallMs": frame_wall,
            "setupReadinessMs": setup_readiness,
            "setupOtherMs": max(0, leg_wall - frame_wall - setup_readiness),
        },
    })
    return records


def flush_capture_timings(state, harness_root, environ=None):
    """Persist the in-memory batch after capture; failure is diagnostic only."""
    if not state:
        return False
    environ = os.environ if environ is None else environ
    recorder = Path(harness_root) / "tools" / "ci" / "record-timings-batch.js"
    child_env = dict(environ)
    child_env["THESTRA_TIMINGS_RUN_ID"] = state["runId"]
    try:
        proc = subprocess.run(
            ["node", str(recorder)],
            cwd=str(Path(harness_root)),
            env=child_env,
            input=json.dumps(timing_records(state)),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "unknown recorder failure").strip()
            print("G6 timings: could not record capture metrics: %s" % message)
            return False

        # Relative G6 always runs base-a, base-b, then candidate in one job.
        # Report once, after candidate, so the GitHub summary contains the
        # instrumented base control and candidate together without duplicates.
        # A standalone G6 run reports immediately. Slow reporting happens only
        # after every pixel has already been captured and compared.
        if state.get("leg") in ("candidate", "g6"):
            report = Path(harness_root) / "tools" / "ci" / "report-timings.js"
            report_proc = subprocess.run(
                ["node", str(report), "--run", state["runId"]],
                cwd=str(Path(harness_root)), env=child_env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
            )
            if report_proc.stdout:
                print(report_proc.stdout.rstrip())
            if report_proc.returncode != 0:
                message = (report_proc.stderr or "unknown report failure").strip()
                print("G6 timings: could not render capture report: %s" % message)
        return True
    except Exception as exc:
        # #811 rule 1: instrumentation is never allowed to turn a gate red.
        print("G6 timings: could not record capture metrics: %s" % exc)
        return False
