#!/usr/bin/env python3
"""Regression tests for #646 persistent scoping and #688 recorder-local triage."""

import contextlib
import io
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import actual_run
import triage


def write(path, data=b"not-a-real-png-needed-for-this-branch"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def capture_gate(root):
    triage.ROOT = str(root)
    triage.GATES = {
        "g6": ("G6 test", "tools/golden/editor-screens", "tools/golden/editor-screens-actual")
    }
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        triage.triage_gate("g6", False)
    return out.getvalue()


def capture_record_gate(root, ref_rel="tools/golden/editor-screens", actual_rel="record/current"):
    """Mirror record.py's dynamic, TemporaryDirectory-backed triage entry."""
    triage.ROOT = str(root)
    triage.GATES = {
        "record-editor": ("G6 editor record", ref_rel, actual_rel)
    }
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        triage.triage_gate("record-editor", False)
    return out.getvalue()


def main():
    with tempfile.TemporaryDirectory(prefix="triage-scope-") as temp:
        root = Path(temp)
        refs = root / "tools/golden/editor-screens"
        actual = root / "tools/golden/editor-screens-actual"
        refs.mkdir(parents=True)
        write(actual / "database/actors.png")

        # #646 negative control: an unmarked persistent actual tree is stale by
        # definition and must never be interpreted as current NEW/regression evidence.
        legacy = capture_gate(root)
        assert "ORPHAN     database/actors.png" in legacy, legacy
        assert "NEW        database/actors.png" not in legacy, legacy

        actual_run.reset_scope("g6", root=str(root))
        assert not (actual / "database/actors.png").exists(), "reset must remove the prior run"
        assert actual_run.read_marker(str(actual), expected_scope="g6"), "fresh run marker missing"

        write(actual / "database/new-surface.png")
        current = capture_gate(root)
        assert "NEW        database/new-surface.png" in current, current
        assert "ORPHAN     database/new-surface.png" not in current, current

        # A second gate run starts from an empty actual tree, so a frame emitted
        # only by the first run cannot leak into the second triage.
        actual_run.reset_scope("g6", root=str(root))
        second = capture_gate(root)
        assert "database/new-surface.png" not in second, second
        assert "nothing in tools/golden/editor-screens-actual" in second, second

        # #688: record.py creates its own fresh temporary actual tree from the
        # current parsed frame list. It is intentionally not the persistent
        # *-actual tree, so requiring the persistent marker here turns live
        # evidence into ORPHAN. A recorder-local frame without a reference must
        # therefore remain current NEW evidence even without a marker file.
        record_actual = root / "record/current"
        write(record_actual / "database/current-run.png")
        recorder = capture_record_gate(root)
        assert "NEW        database/current-run.png" in recorder, recorder
        assert "ORPHAN     database/current-run.png" not in recorder, recorder
        assert "current-run frame(s)" in recorder, recorder

    print("ACTUAL RUN SCOPE TEST OK")


if __name__ == "__main__":
    main()
