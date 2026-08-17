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
import os
import shutil
import subprocess
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


def default_step_timeout(gate):
    # G6 waits for semantic readiness across the full browser capture suite.
    # #721 observed an unchanged healthy base killed at 308.922s by the 300s
    # recorder watchdog before G6 could reach its own readiness/pixel verdict.
    # Keep enough CI headroom for the outer process while leaving G5 and the
    # 1200s gate failsafe unchanged; this is execution budget, not a
    # pixel/readiness tolerance.
    return 420 if gate == "g6" else 180


def _git_rev_parse(root, ref="HEAD"):
    proc = subprocess.run(
        ["git", "rev-parse", ref], cwd=str(root), stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("cannot resolve git ref %s: %s" % (ref, proc.stderr.strip()))
    return proc.stdout.strip()


def select_pull_request_integration_sha(current_sha, event_name, event_payload,
                                        merge_sha, merge_base_sha):
    """Select the integration tree corresponding to a PR worktree.

    GitHub's pull-request payload may retain an older `base.sha` while the
    synthetic `GITHUB_SHA` is rebuilt against the actual current base branch.
    Relative A/B must therefore use the synthetic merge's first parent for the
    base controls and the synthetic merge itself for the candidate.
    """
    if event_name != "pull_request" or not isinstance(event_payload, dict):
        return None
    pull = event_payload.get("pull_request") or {}
    head_sha = (pull.get("head") or {}).get("sha")
    payload_base_sha = (pull.get("base") or {}).get("sha")

    if head_sha and current_sha == head_sha and merge_sha and merge_sha != head_sha:
        return {"role": "candidate", "sha": merge_sha}
    if payload_base_sha and current_sha == payload_base_sha and merge_base_sha:
        if merge_base_sha != current_sha:
            return {"role": "base", "sha": merge_base_sha}
    return None


def normalize_pull_request_worktree(target, gate, environ=None):
    """Normalize PR base/head worktrees to the exact synthetic integration pair."""
    environ = os.environ if environ is None else environ
    current_sha = _git_rev_parse(target)
    event_path = environ.get("GITHUB_EVENT_PATH")
    payload = {}
    if event_path and Path(event_path).is_file():
        payload = json.loads(Path(event_path).read_text(encoding="utf-8-sig"))

    merge_sha = environ.get("GITHUB_SHA")
    merge_base_sha = None
    if environ.get("GITHUB_EVENT_NAME") == "pull_request" and merge_sha:
        merge_base_sha = _git_rev_parse(target, merge_sha + "^1")

    selection = select_pull_request_integration_sha(
        current_sha,
        environ.get("GITHUB_EVENT_NAME"),
        payload,
        merge_sha,
        merge_base_sha,
    )
    if not selection:
        return {
            "normalized": False,
            "role": None,
            "requestedSha": current_sha,
            "effectiveSha": current_sha,
        }

    target_sha = selection["sha"]
    checkout = subprocess.run(
        ["git", "checkout", "--detach", target_sha], cwd=str(target),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True,
    )
    if checkout.returncode != 0:
        raise RuntimeError(
            "cannot normalize PR %s worktree to %s: %s"
            % (selection["role"], target_sha, checkout.stderr.strip())
        )

    # The workflow provisioned dependencies against the originally requested
    # commit before calling this helper. Either normalized tree can inherit
    # dependency/vendor changes from current main, so refresh after checkout.
    if gate == "g6":
        npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
        install = subprocess.run(
            [npm, "ci", "--ignore-scripts"], cwd=str(target), check=False,
        )
        if install.returncode != 0:
            raise RuntimeError("npm ci failed after PR integration normalization")
        vendor = subprocess.run(
            ["node", "tools/editor/sync-three-vendor.js"], cwd=str(target), check=False,
        )
        if vendor.returncode != 0:
            raise RuntimeError("Three.js vendor sync failed after PR integration normalization")

    effective_sha = _git_rev_parse(target)
    if effective_sha != target_sha:
        raise RuntimeError(
            "PR integration normalization resolved %s, expected %s" % (effective_sha, target_sha)
        )
    return {
        "normalized": True,
        "role": selection["role"],
        "requestedSha": current_sha,
        "effectiveSha": effective_sha,
    }


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
    parser.add_argument("--step-timeout", type=int, default=None,
                        help="per-subprocess timeout; default 180s for G5, 420s for G6")
    parser.add_argument("--gate-timeout", type=int, default=1200)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    step_timeout = args.step_timeout if args.step_timeout is not None else default_step_timeout(args.gate)
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
        "stepTimeoutSeconds": step_timeout,
        "recorderPasses": [],
    }

    try:
        result["prIntegration"] = normalize_pull_request_worktree(target, args.gate)
        if args.gate == "g5":
            code1, dir1, manifest1 = run_recorder(
                record, target, "g5", output / "recorder-pass-1",
                step_timeout, args.gate_timeout,
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
                step_timeout, args.gate_timeout,
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
                step_timeout, args.gate_timeout,
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
