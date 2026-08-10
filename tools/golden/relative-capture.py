#!/usr/bin/env python3
"""Materialize one hosted-relative G5/G6 capture using the canonical recorder.

This is not another screenshot driver. It calls tools/golden/record.py against a
specified checkout, then turns the recorder evidence into a complete PNG tree
that a same-runner A/B comparison can consume.

G5 has one awkward property: the canonical check stops after a Classic mismatch,
so a hosted run against owner-machine references never reaches Wide. To preserve
the canonical sequence without teaching this tool how to render, the first
recorder pass is used to reconstruct a disposable Classic reference tree inside
the throwaway worktree. A second recorder pass then reaches the existing crop
invariant and Wide capture. No tracked reference is committed or exported.
"""

import argparse
import base64
import importlib.util
import json
import shutil
import sys
from pathlib import Path


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("could not import %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def newest_record(root):
    candidates = [p for p in Path(root).glob("*") if (p / "manifest.json").is_file()]
    if not candidates:
        raise RuntimeError("recorder produced no manifest under %s" % root)
    return max(candidates, key=lambda p: p.stat().st_mtime_ns)


def run_recorder(record, target, gate, output_root, step_timeout, gate_timeout):
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    code = record.run_live(target, gate, output_root, step_timeout, gate_timeout)
    record_dir = newest_record(output_root)
    manifest = json.loads((record_dir / "manifest.json").read_text(encoding="utf-8"))
    return code, record_dir, manifest


def normalize_classic_reference(target, manifest):
    """Make only this disposable worktree's Classic refs equal pass-1 capture."""
    target = Path(target)
    ref_root = target / "tools/golden/screens"
    actual_root = target / "tools/golden/screens-actual"

    for frame in manifest.get("frames", []):
        if frame.get("surface") == "classic" and frame.get("status") == "orphaned":
            victim = ref_root / Path(frame["path"])
            if victim.exists():
                victim.unlink()

    if actual_root.exists():
        for src in actual_root.rglob("*.png"):
            rel = src.relative_to(actual_root)
            dest = ref_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)


def load_g5_captures(target, raw_path, surface):
    screens = load_module(Path(target) / "tools/golden/screens.py",
                          "second_rite_relative_screens_%s" % surface)
    captures = screens.load_captures(str(raw_path))
    if surface != "classic":
        allowed = screens.select_surface(surface)
        captures = [cap for cap in captures
                    if screens.safe_relpath(cap["path"]).startswith(allowed)]
    return screens, captures


def materialize_g5(target, record_dir, output):
    output = Path(output)
    counts = {}
    for surface in ("classic", "wide"):
        raw = Path(record_dir) / "captures" / (surface + ".txt")
        if not raw.is_file():
            raise RuntimeError("G5 recorder did not preserve %s capture" % raw)
        screens, captures = load_g5_captures(target, raw, surface)
        dest_root = output / "captures" / surface
        for cap in captures:
            rel = screens.safe_relpath(cap["path"])
            dest = dest_root / Path(rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(base64.b64decode(cap["image"]))
        counts[surface] = len(captures)
    return counts


def materialize_g6(target, manifest, output):
    target = Path(target)
    output = Path(output)
    compared = manifest.get("frameCounts", {}).get("editor", {}).get("compared")
    if not isinstance(compared, int) or compared <= 0:
        raise RuntimeError("G6 recorder did not reach a complete editor comparison")

    ref_root = target / "tools/golden/editor-screens"
    actual_root = target / "tools/golden/editor-screens-actual"
    dest_root = output / "captures" / "editor"
    orphaned = {
        frame["path"] for frame in manifest.get("frames", [])
        if frame.get("surface") == "editor" and frame.get("status") == "orphaned"
    }

    if ref_root.exists():
        for src in ref_root.rglob("*.png"):
            rel = src.relative_to(ref_root).as_posix()
            if rel in orphaned:
                continue
            dest = dest_root / Path(rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    if actual_root.exists():
        for src in actual_root.rglob("*.png"):
            rel = src.relative_to(actual_root)
            dest = dest_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    materialized = sum(1 for _ in dest_root.rglob("*.png")) if dest_root.exists() else 0
    if materialized != compared:
        raise RuntimeError(
            "G6 reconstructed %d captures but recorder compared %d" % (materialized, compared)
        )
    return {"editor": materialized}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True,
                        help="detached checkout whose gate is being measured")
    parser.add_argument("--gate", choices=("g5", "g6"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--step-timeout", type=int, default=180)
    parser.add_argument("--gate-timeout", type=int, default=1200)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    target = args.repo_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    tool_root = Path(__file__).resolve().parents[2]
    record = load_module(tool_root / "tools/golden/record.py", "second_rite_gate_record")

    result = {
        "schemaVersion": 1,
        "gate": args.gate,
        "repoRoot": str(target),
        "captureComplete": False,
        "recorderPasses": [],
    }

    try:
        if args.gate == "g5":
            code1, dir1, manifest1 = run_recorder(
                record, target, "g5", output / "recorder-pass-1",
                args.step_timeout, args.gate_timeout,
            )
            result["recorderPasses"].append({
                "name": "owner-reference-probe", "exitCode": code1,
                "record": str(dir1.relative_to(output)).replace("\\", "/"),
            })
            classic_raw = dir1 / "captures" / "classic.txt"
            if not classic_raw.is_file():
                raise RuntimeError("first G5 recorder pass did not reach Classic capture")

            normalize_classic_reference(target, manifest1)

            code2, dir2, manifest2 = run_recorder(
                record, target, "g5", output / "recorder-pass-2",
                args.step_timeout, args.gate_timeout,
            )
            result["recorderPasses"].append({
                "name": "classic-normalized-full-sequence", "exitCode": code2,
                "record": str(dir2.relative_to(output)).replace("\\", "/"),
            })
            crop = manifest2.get("surfaceCropCheck", {})
            if crop.get("outcome") != "passed":
                raise RuntimeError("G5 surface-crop invariant did not pass: %s" % crop)
            counts = materialize_g5(target, dir2, output)
            result["counts"] = counts
            result["captureComplete"] = True
            result["note"] = (
                "Recorder pass 1 only normalizes Classic references inside this disposable worktree "
                "so the canonical G5 sequence can reach crop-check and Wide. No golden is committed."
            )
        else:
            code, record_dir, manifest = run_recorder(
                record, target, "g6", output / "recorder",
                args.step_timeout, args.gate_timeout,
            )
            result["recorderPasses"].append({
                "name": "owner-reference-probe", "exitCode": code,
                "record": str(record_dir.relative_to(output)).replace("\\", "/"),
            })
            result["counts"] = materialize_g6(target, manifest, output)
            result["captureComplete"] = True
            result["note"] = (
                "The full hosted capture is reconstructed from the recorder's committed references "
                "plus its differing actual frames; this does not alter or recapture repository goldens."
            )
    except Exception as exc:
        result["error"] = str(exc)
        (output / "relative-capture.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print("relative-capture: %s" % exc, file=sys.stderr)
        return 2

    (output / "relative-capture.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
