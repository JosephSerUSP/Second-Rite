#!/usr/bin/env python3
"""Compatibility front for the gate evidence recorder with G6 dependency state.

record-core.py is the byte-preserved recorder implementation. This front keeps
its public API/CLI while teaching manifests one additional causal state emitted
by the G6 dependency preflight: `dependency-missing` rather than `unmeasured`.
"""

import importlib.util
import json
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
_PREFIX = "G6_DEPENDENCY_MISSING_JSON "


def parse_gate_output(gate, stdout_text):
    parsed = _original_parse_gate_output(gate, stdout_text)
    if gate == "g6":
        for raw_line in stdout_text.splitlines():
            line = raw_line.strip()
            if not line.startswith(_PREFIX):
                continue
            try:
                payload = json.loads(line[len(_PREFIX):])
            except json.JSONDecodeError:
                payload = {"kind": "unknown", "paths": [], "repair": None,
                           "parseError": line[len(_PREFIX):]}
            parsed["dependencyMissing"] = payload
            break
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
    if missing:
        manifest["outcome"] = "dependency-missing"
        manifest["missingDependency"] = missing
        editor = manifest.get("frameCounts", {}).get("editor")
        if editor is not None:
            editor["measurement"] = "dependency-missing"
            editor["matched"] = None
            editor["compared"] = None
            editor["differing"] = 0
    return manifest


# Patch the core module because its live-run functions resolve these names from
# the core module's own globals. Then re-export its ordinary public surface so
# existing tests/importers continue to see record.py as the canonical module.
_core.parse_gate_output = parse_gate_output
_core.build_manifest = build_manifest
for _name, _value in vars(_core).items():
    if not _name.startswith("__") and _name not in {"parse_gate_output", "build_manifest"}:
        globals().setdefault(_name, _value)


if __name__ == "__main__":
    _core.main()
