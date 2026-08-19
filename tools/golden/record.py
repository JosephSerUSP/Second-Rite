#!/usr/bin/env python3
"""Compatibility front for the gate evidence recorder with G6 dependency state.

record-core.py is the byte-preserved recorder implementation. This front keeps
its public API/CLI while teaching manifests one additional causal state emitted
by the G6 dependency preflight: `dependency-missing` rather than `unmeasured`.

G6 is also a special recorder child: `editor-screens.py check` is the complete
multi-screen harness, not one semantic readiness step. The harness owns named
positive-readiness waits while record-core keeps a 1200-second outer gate
failsafe. Applying the ordinary recorder child timeout to the whole 46-screen
process makes cumulative healthy work look like one stalled step. This front
therefore delegates only `editor-check` to G6's semantic bounds and runs it
unbuffered so the last announced screen survives an outer failure. Other
recorder children retain the ordinary per-step timeout.

Relative A/B needs one more distinction: base-A, base-B and candidate are
*different product roots* but they must be driven by the *same harness*. If the
base checkout supplies its older editor-screens.py, a harness-reliability PR can
never repair the base side it is meant to measure. The recorder shim therefore
routes `editor-check` through the canonical editor-screens.py beside this
recorder, while SECOND_RITE_G6_ROOT points that harness at the detached target's
product code, data, references, server and runtime bridge. No product file is
overlaid or copied between targets.

The temporary PATH shims created by record-core must invoke this canonical
front, not record-core.py directly; otherwise front-owned dependency/timeout
semantics disappear precisely inside the subprocess being measured.
"""

import importlib.util
import json
import os
from pathlib import Path
import sys

_CORE_PATH = Path(__file__).with_name("record-core.py")
_SPEC = importlib.util.spec_from_file_location("second_rite_golden_record_core", _CORE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("cannot load gate recorder core from %s" % _CORE_PATH)
_core = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_core)

_original_parse_gate_output = _core.parse_gate_output
_original_build_manifest = _core.build_manifest
_original_exec_step = _core.exec_step
_original_run_live = _core.run_live
_PREFIX = "G6_DEPENDENCY_MISSING_JSON "
_RESULT_PREFIX = "G6_RESULT_JSON "


def parse_gate_output(gate, stdout_text):
    parsed = _original_parse_gate_output(gate, stdout_text)
    if gate == "g6":
        for raw_line in stdout_text.splitlines():
            line = raw_line.strip()
            if line.startswith(_RESULT_PREFIX):
                try:
                    payload = json.loads(line[len(_RESULT_PREFIX):])
                    parsed["resultJson"] = payload
                except json.JSONDecodeError:
                    pass
            elif line.startswith(_PREFIX):
                try:
                    payload = json.loads(line[len(_PREFIX):])
                except json.JSONDecodeError:
                    payload = {"kind": "unknown", "paths": [], "repair": None,
                               "parseError": line[len(_PREFIX):]}
                parsed["dependencyMissing"] = payload
    return parsed


def build_manifest(gate, gate_exit_code, gate_timed_out, started, ended, git_info,
                   host_info, steps, parsed, shim_present, source="live",
                   source_details=None, output_ignored=None):
    manifest = _original_build_manifest(
        gate, gate_exit_code, gate_timed_out, started, ended, git_info,
        host_info, steps, parsed, shim_present, source=source,
        source_details=source_details, output_ignored=output_ignored,
    )
    missing = parsed.get("dependencyMissing") if gate == "g6" else None
    result_json = parsed.get("resultJson") if gate == "g6" else None
    if missing:
        manifest["outcome"] = "dependency-missing"
        manifest["missingDependency"] = missing
        editor = manifest.get("frameCounts", {}).get("editor")
        if editor is not None:
            editor["measurement"] = "dependency-missing"
            editor["matched"] = None
            editor["compared"] = None
            editor["differing"] = 0
    elif gate == "g6" and (gate_exit_code == 2 or (result_json and result_json.get("status") == "incomplete")):
        manifest["outcome"] = "failed"
        if result_json:
            manifest["incomplete"] = result_json
        editor = manifest.get("frameCounts", {}).get("editor")
        if editor is not None:
            editor["measurement"] = "unmeasured"
            editor["matched"] = None
            editor["compared"] = None
            editor["differing"] = 0
    return manifest



def recorder_owns_step_timeout(tool, args):
    """Whether the recorder should impose its generic child timeout."""
    return _core.classify_step(tool, args) != "editor-check"


def canonical_g6_invocation(tool, args, environ=None):
    """Return the canonical harness invocation for an intercepted G6 check."""
    environ = os.environ if environ is None else environ
    if _core.classify_step(tool, args) != "editor-check":
        return list(args), {}
    target_root = environ.get("SECOND_RITE_RECORD_ROOT")
    if not target_root:
        raise RuntimeError("G6 recorder shim is missing SECOND_RITE_RECORD_ROOT")
    canonical = Path(__file__).with_name("editor-screens.py").resolve()
    return [str(canonical)] + list(args[1:]), {"SECOND_RITE_G6_ROOT": target_root}


def exec_step(tool, args):
    if recorder_owns_step_timeout(tool, args):
        return _original_exec_step(tool, args)

    canonical_args, env_updates = canonical_g6_invocation(tool, args)

    # `_exec-step` runs in the shim's own Python process. Temporarily replace
    # only this process's low-level runner so the parent recorder still keeps
    # its independent gate timeout around check-editor.ps1.
    original_runner = _core._run_with_timeout
    original_env = {key: os.environ.get(key) for key in env_updates}

    def run_g6_harness(command, cwd, env, _timeout_seconds):
        child_env = dict(env)
        # The G6 harness prints each screen before driving it. Without this,
        # stdout is block-buffered into the recorder pipe and a killed process
        # leaves no clue which screen had begun.
        child_env["PYTHONUNBUFFERED"] = "1"
        child_env.update(env_updates)
        return original_runner(command, cwd, child_env, None)

    _core._run_with_timeout = run_g6_harness
    for key, value in env_updates.items():
        os.environ[key] = value
    try:
        return _original_exec_step(tool, canonical_args)
    finally:
        _core._run_with_timeout = original_runner
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_live(root, gate, output_root, step_timeout, gate_timeout):
    """Run the core recorder while making its temporary shims re-enter here.

    record-core builds SECOND_RITE_RECORD_SCRIPT from its own module __file__.
    That is correct when core is the public entrypoint, but record.py now owns
    recorder semantics that the shim process must preserve. The two files live
    beside each other, so temporarily substituting only this path leaves repo
    resolution unchanged and is restored before returning.
    """
    original_core_file = _core.__file__
    _core.__file__ = str(Path(__file__).resolve())
    try:
        return _original_run_live(root, gate, output_root, step_timeout, gate_timeout)
    finally:
        _core.__file__ = original_core_file


# Patch the core module because its live-run functions resolve these names from
# the core module's own globals. Then re-export its ordinary public surface so
# existing tests/importers continue to see record.py as the canonical module.
_core.parse_gate_output = parse_gate_output
_core.build_manifest = build_manifest
_core.exec_step = exec_step
_core.run_live = run_live
for _name, _value in vars(_core).items():
    if not _name.startswith("__") and _name not in {
        "parse_gate_output", "build_manifest", "exec_step", "run_live"
    }:
        globals().setdefault(_name, _value)


if __name__ == "__main__":
    # `main()` RETURNS the exit status; it does not raise it. record-core.py
    # ends with `raise SystemExit(main())` for exactly that reason. This front
    # is also what the recorder's temporary PATH shims invoke -- run_live points
    # SECOND_RITE_RECORD_SCRIPT here -- so dropping the status made every gate
    # child report success to its gate script, and a red G5/G6 recorded as
    # `"outcome": "passed"` with `"exitCode": 0` (#805). The two entrypoints must
    # keep identical process contracts; tests/test_g6_exit_contract.py asserts it.
    raise SystemExit(_core.main())
