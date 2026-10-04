#!/usr/bin/env python3
"""Compare three same-runner G5/G6 capture trees at decoded RGBA pixel level."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("compare-relative.py needs Pillow (python -m pip install pillow)")

SURFACES = {"g5": ("classic", "wide"), "g6": ("editor",)}


def load_expected_delta_module():
    path = Path(__file__).with_name("expected_delta.py")
    spec = importlib.util.spec_from_file_location("second_rite_expected_delta", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("could not import expected-delta support from %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXPECTED_DELTA = load_expected_delta_module()


def pngs(root):
    root = Path(root)
    if not root.exists():
        return {}
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*.png")}


def rgba(path):
    with Image.open(str(path)) as image:
        return image.convert("RGBA").copy()


def image_signature(path):
    if path is None:
        return None
    image = rgba(path)
    return {
        "width": image.width,
        "height": image.height,
        "rgbaSha256": hashlib.sha256(image.tobytes()).hexdigest(),
    }


def capture_fingerprint(root):
    items = []
    for rel, path in sorted(pngs(root).items()):
        item = {"path": rel}
        item.update(image_signature(path))
        items.append(item)
    return EXPECTED_DELTA.digest_json(items)


def changed_pixels(left, right):
    if left is None and right is None:
        return 0
    if left is None:
        image = rgba(right)
        return image.width * image.height
    if right is None:
        image = rgba(left)
        return image.width * image.height

    a = rgba(left)
    b = rgba(right)
    width = max(a.width, b.width)
    height = max(a.height, b.height)
    if a.size != (width, height):
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.paste(a, (0, 0))
        a = canvas
    if b.size != (width, height):
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.paste(b, (0, 0))
        b = canvas
    return sum(px_a != px_b for px_a, px_b in zip(a.getdata(), b.getdata()))


def compare_surface(left_root, right_root):
    left = pngs(left_root)
    right = pngs(right_root)
    details = []
    changed_total = 0
    for rel in sorted(set(left) | set(right)):
        lp = left.get(rel)
        rp = right.get(rel)
        if lp is not None and rp is not None:
            a = rgba(lp)
            b = rgba(rp)
            if a.size == b.size and a.tobytes() == b.tobytes():
                continue
        count = changed_pixels(lp, rp)
        changed_total += count
        details.append({
            "path": rel,
            "changedPixels": count,
            "leftPresent": lp is not None,
            "rightPresent": rp is not None,
            "leftImage": image_signature(lp),
            "rightImage": image_signature(rp),
        })
    return {
        "leftFrames": len(left),
        "rightFrames": len(right),
        "differingFrames": len(details),
        "changedPixels": changed_total,
        "details": details,
    }


def capture_evidence(root):
    path = Path(root) / "relative-capture.json"
    if not path.is_file():
        return {"recorded": False, "complete": None}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"recorded": True, "complete": False, "error": str(exc)}
    return {
        "recorded": True,
        "complete": payload.get("captureComplete") is True,
        "error": payload.get("error"),
    }


def state_label(result):
    state = result.get("state")
    if state == "orange":
        return "ORANGE - expected delta pending canonical reference reconciliation"
    if state == "green":
        return "GREEN - candidate and base agree on repeat-stable evidence"
    if state == "red":
        return "RED - visual delta is unreviewed, rejected, or exceeds recorded approval"
    return "INCONCLUSIVE / INFRASTRUCTURE - evidence is incomplete or unstable"


def report_markdown(result):
    lines = [
        "# Relative %s same-runner A/B" % result["gate"].upper(),
        "",
        "This is a **relative regression check**, not an absolute golden-correctness check. "
        "It compares base and candidate on the same hosted runner and does not use an Effekseer shim. "
        "A green or orange relative result never authorizes recapturing committed references by itself.",
        "",
        "- base: `%s`" % result["baseRef"],
        "- candidate: `%s`" % result["candidateRef"],
        "- state: **%s**" % state_label(result),
        "- repeat control is read first; unstable control frames are excluded from candidate verdicts",
        "",
        "| surface | base A -> base B differing | repeat changed pixels | base B -> candidate differing | candidate changed pixels | new targets | missing targets | unstable excluded | stable pixel diffs |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for surface in result["surfaces"]:
        row = result["surfaces"][surface]
        lines.append(
            "| %s | %d | %d | %d | %d | %d | %d | %d | %d |" % (
                surface,
                row["repeat"]["differingFrames"], row["repeat"]["changedPixels"],
                row["candidate"]["differingFrames"], row["candidate"]["changedPixels"],
                len(row["newCandidateFrames"]), len(row["missingCandidateFrames"]),
                len(row["unstableFrames"]), len(row["stableCandidateDifferences"]),
            )
        )

    lines += ["", "## Verdict", "", "**%s**" % result["verdict"], ""]

    if result.get("status") == "expected-delta":
        approval = result["expectedDelta"]
        summary = approval.get("summary", {})
        lines += [
            "## Expected visual delta",
            "",
            "**EXPECTED VISUAL DELTA (ORANGE)**",
            "",
            "- rationale: %s" % approval.get("rationale", ""),
            "- reviewed by: %s" % approval.get("reviewer", ""),
            "- durable record: `%s`" % approval.get("recordPath", ""),
            "- evidence fingerprint: `%s`" % approval.get("evidenceFingerprint", ""),
            "- added candidate states: %d" % len(summary.get("newTargets", [])),
            "- superseded base states: %d" % len(summary.get("missingTargets", [])),
            "- reviewed stable pixel differences: %d" % len(summary.get("stableDifferences", [])),
            "- unexplained stable differences: **0**",
            "- pending: **approved reference recapture/update**",
            "",
        ]
        references = approval.get("references") or []
        if references:
            lines += ["Explaining references: " + ", ".join("`%s`" % ref for ref in references), ""]

    unstable = []
    stable_diffs = []
    new_targets = []
    missing_targets = []
    for surface, row in result["surfaces"].items():
        unstable.extend("%s/%s" % (surface, p) for p in row["unstableFrames"])
        new_targets.extend("%s/%s" % (surface, p) for p in row["newCandidateFrames"])
        missing_targets.extend("%s/%s" % (surface, p) for p in row["missingCandidateFrames"])
        stable_diffs.extend(
            "%s/%s (%d changed pixels)" % (surface, d["path"], d["changedPixels"])
            for d in row["stableCandidateDifferences"]
        )
    if unstable:
        lines += ["## Repeat-control unstable frames", ""] + ["- `%s`" % p for p in unstable] + [""]
    if stable_diffs:
        title = "Reviewed stable pixel differences" if result.get("state") == "orange" else "Candidate-only differences on stable frames"
        lines += ["## %s" % title, ""] + ["- %s" % p for p in stable_diffs] + [""]
    if new_targets:
        lines += [
            "## New candidate capture targets", "",
            "These targets are present in the complete candidate capture but not in the base capture.", "",
        ] + ["- `%s`" % p for p in new_targets] + [""]
    if missing_targets:
        lines += [
            "## Missing/superseded base capture targets", "",
            "These targets are present in the complete base capture but absent from the candidate capture. "
            "With complete capture metadata this is a topology delta, not by itself an infrastructure failure.", "",
        ] + ["- `%s`" % p for p in missing_targets] + [""]

    if result.get("status") == "candidate-diff":
        lines += [
            "## Manual Red -> Orange promotion", "",
            "If review determines that **all** evidence above is expected, persist that decision from this report JSON:", "",
            "`python tools/golden/promote-expected-delta.py --report <report.json> --id <short-id> --reviewer <name> --rationale <why> --reference <PR/issue>`",
            "",
            "The resulting `tools/golden/expected-deltas/*.json` record must be committed. A rerun becomes Orange only when the complete capture fingerprint still matches exactly; additional or changed evidence remains Red.",
            "",
        ]
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", choices=("g5", "g6"), required=True)
    parser.add_argument("--base-a", type=Path, required=True)
    parser.add_argument("--base-b", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--candidate-ref", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-summary", type=Path)
    parser.add_argument("--expected-deltas", type=Path,
                        default=EXPECTED_DELTA.DEFAULT_APPROVAL_DIR)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    result = {
        "schemaVersion": 2,
        "gate": args.gate,
        "baseRef": args.base_ref,
        "candidateRef": args.candidate_ref,
        "surfaces": {},
        "captureEvidence": {
            "baseA": capture_evidence(args.base_a),
            "baseB": capture_evidence(args.base_b),
            "candidate": capture_evidence(args.candidate),
        },
    }
    stable_candidate_count = 0
    unstable_count = 0
    missing_candidate_count = 0
    new_candidate_count = 0

    for surface in SURFACES[args.gate]:
        a = args.base_a / "captures" / surface
        b = args.base_b / "captures" / surface
        c = args.candidate / "captures" / surface
        repeat = compare_surface(a, b)
        candidate = compare_surface(b, c)
        missing_candidate = [d["path"] for d in candidate["details"] if d["leftPresent"] and not d["rightPresent"]]
        new_candidate = [d["path"] for d in candidate["details"] if not d["leftPresent"] and d["rightPresent"]]
        unstable = {d["path"] for d in repeat["details"]}
        stable_candidate = [
            d for d in candidate["details"]
            if d["path"] not in unstable and d["leftPresent"] and d["rightPresent"]
        ]
        result["surfaces"][surface] = {
            "repeat": repeat,
            "candidate": candidate,
            "unstableFrames": sorted(unstable),
            "stableCandidateDifferences": stable_candidate,
            "newCandidateFrames": new_candidate,
            "missingCandidateFrames": missing_candidate,
            "baseCaptureFingerprint": capture_fingerprint(b),
            "candidateCaptureFingerprint": capture_fingerprint(c),
        }
        stable_candidate_count += len(stable_candidate)
        unstable_count += len(unstable)
        missing_candidate_count += len(missing_candidate)
        new_candidate_count += len(new_candidate)

    incomplete = [
        name for name, evidence in result["captureEvidence"].items()
        if evidence.get("recorded") and evidence.get("complete") is not True
    ]
    visual_delta_count = stable_candidate_count + missing_candidate_count + new_candidate_count

    if incomplete:
        result["status"] = "incomplete-capture"
        result["state"] = "infrastructure"
        result["verdict"] = (
            "INFRASTRUCTURE FAILURE: incomplete capture evidence for %s; Red/Orange review is not applicable."
            % ", ".join(incomplete)
        )
        exit_code = 1
    elif visual_delta_count:
        result["status"] = "candidate-diff"
        result["state"] = "red"
        result["evidenceFingerprint"] = EXPECTED_DELTA.evidence_fingerprint(result)
        result["verdict"] = (
            "REGRESSION SIGNAL (RED): %d stable pixel difference(s), %d new target(s), and %d missing/superseded target(s)."
            % (stable_candidate_count, new_candidate_count, missing_candidate_count)
        )
        exit_code = 1

        try:
            approval = EXPECTED_DELTA.find_matching_approval(result, args.expected_deltas)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            result["status"] = "approval-state-invalid"
            result["state"] = "infrastructure"
            result["verdict"] = "INFRASTRUCTURE FAILURE: expected-delta approval store is invalid: %s" % exc
            exit_code = 1
        else:
            ok, _ = EXPECTED_DELTA.promotable(result)
            if approval and ok:
                result["status"] = "expected-delta"
                result["state"] = "orange"
                result["expectedDelta"] = approval
                result["verdict"] = (
                    "EXPECTED VISUAL DELTA (ORANGE): reviewed evidence matches durable approval '%s'; "
                    "canonical reference reconciliation is still pending."
                    % approval.get("id", "unnamed")
                )
                exit_code = 0
    elif unstable_count:
        result["status"] = "control-unstable"
        result["state"] = "inconclusive"
        result["verdict"] = (
            "NO CANDIDATE-ONLY DIFF ON STABLE FRAMES; %d repeat-control frame(s) are inconclusive and excluded."
            % unstable_count
        )
        exit_code = 0
    else:
        result["status"] = "exact"
        result["state"] = "green"
        result["verdict"] = "EXACT (GREEN): repeat control is stable and candidate is decoded-pixel identical to base."
        exit_code = 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = report_markdown(result)
    args.output.write_text(report, encoding="utf-8")
    args.output.with_suffix(".json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.github_summary:
        with args.github_summary.open("a", encoding="utf-8") as handle:
            handle.write(report)
    if result.get("state") == "orange" and os.environ.get("GITHUB_ACTIONS") == "true":
        print("::warning title=Expected visual delta (Orange)::Reviewed visual delta matches durable approval; reference reconciliation is still pending.")
    print(report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
