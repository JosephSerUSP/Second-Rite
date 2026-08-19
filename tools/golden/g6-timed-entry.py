#!/usr/bin/env python3
"""Run canonical G6 with passive timing installed in the same Python process.

This is an instrumentation entrypoint, not another screenshot harness. It
executes editor-screens.py in this process and intercepts only the moment that
front loads editor-screens-core.py. The core and readiness front remain the
canonical files; no child Python process is spawned around them.
"""

import os
from pathlib import Path
import runpy
import sys

GOLDEN = Path(__file__).resolve().parent
HARNESS_ROOT = GOLDEN.parents[1]
EDITOR_FRONT = GOLDEN / "editor-screens.py"
TIMING_MODULE = GOLDEN / "g6-capture-timings.py"
TARGET_ROOT = Path(os.environ.get("SECOND_RITE_G6_ROOT", str(HARNESS_ROOT))).resolve()
ORIGINAL_RUN_PATH = runpy.run_path


def load_timing_module():
    return ORIGINAL_RUN_PATH(str(TIMING_MODULE), run_name="second_rite_g6_capture_timings")


def install_timing(timing):
    """Intercept the core load; configure only after readiness front patches it."""
    if not timing["timings_enabled"](os.environ, TARGET_ROOT):
        return

    def instrumented_run_path(path_name, init_globals=None, run_name=None):
        loaded = ORIGINAL_RUN_PATH(path_name, init_globals=init_globals, run_name=run_name)
        try:
            is_core = Path(path_name).resolve().name == "editor-screens-core.py"
        except (OSError, TypeError, ValueError):
            is_core = False
        if not is_core or "run_capture_set" not in loaded or "main" not in loaded:
            return loaded

        original_main = loaded["main"]

        def timed_main():
            # editor-screens.py configures host-bound readiness *after* run_path
            # returns. Defer the observational wrappers until main() is called,
            # so they see the final canonical Chrome.wait_for implementation.
            try:
                state = timing["configure_capture_timings"](loaded, TARGET_ROOT, os.environ)
            except Exception as exc:
                # #811's hard lesson: instrumentation must never change whether
                # a gate passes. Configuration failure degrades to ordinary G6.
                print(
                    "G6 timings: instrumentation disabled after configure error: %s" % exc,
                    file=sys.stderr,
                )
                return original_main()
            try:
                return original_main()
            finally:
                timing["flush_capture_timings"](state, HARNESS_ROOT, os.environ)

        loaded["main"] = timed_main
        return loaded

    runpy.run_path = instrumented_run_path


def main():
    try:
        timing = load_timing_module()
        install_timing(timing)
    except Exception as exc:
        # The timing layer is optional evidence. If it cannot initialize, run
        # the canonical front normally rather than converting a green G6 red.
        print("G6 timings: instrumentation disabled after setup error: %s" % exc, file=sys.stderr)

    # Keep the caller's argv (`check`/`capture`) intact. Running the front with
    # __main__ preserves its exact exit contract while staying in this process.
    ORIGINAL_RUN_PATH(str(EDITOR_FRONT), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
