#!/usr/bin/env python3
"""Compare three same-runner G5/G6 capture trees at decoded RGBA pixel level."""

import argparse
import json
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("compare-relative.py needs Pillow (python -m pip install pillow)")

SURFACES = {"g5": ("classic", "wide"), "g6": ("editor",)}


def pngs(root):
    root = Path(root)
    if not root.exists():
        return {}
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*.png")}


def rgba(path):
    with Image.open(str(path)) as image:
        return image.convert("RGBA").copy()


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
        })
    return {
        "leftFrames": len(left),
        "rightFrames": len(right),
        "differingFrames": len(details),
        "changedPixels": changed_total,
        "details": details,
    }


def report_markdown(result):
    lines = [
        "# Relative %s same-runner A/B" % result["gate"].upper(),
        "",
        "This is a **relative regression check**, not an absolute golden-correctness check. "
        "It compares base and candidate on the same hosted runner and does not use an Effekseer shim. "
        "A green result never licenses recapturing committed goldens.",
        "",
        "- base: `%s`" % result["baseRef"],
        "- candidate: `%s`" % result["candidateRef"],
        "- repeat control is read first; unstable control frames are excluded from candidate verdicts",
        "",
        "| surface | base A -> base B differing | repeat changed pixels | base B -> candidate differing | candidate changed pixels | new candidate targets | unstable frames excluded | stable candidate diffs |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for surface in result["surfaces"]:
        row = result["surfaces"][surface]
        lines.append(
            "| %s | %d | %d | %d | %d | %d | %d | %d |" % (
                surface,
                row["repeat"]["differingFrames"], row["repeat"]["changedPixels"],
                row["candidate"]["differingFrames"], row["candidate"]["changedPixels"],
                len(row["newCandidateFrames"]),
                len(row["unstableFrames"]), len(row["stableCandidateDifferences"]),
            )
        )

    lines += ["", "## Verdict", "", "**%s**" % result["verdict"], ""]
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
        lines += ["## Candidate-only differences on stable frames", ""] + ["- %s" % p for p in stable_diffs] + [""]
    if new_targets:
        lines += ["## New candidate capture targets", "", "These targets are owner-signed additions and have no base image for a relative pixel comparison.", ""] + ["- `%s`" % p for p in new_targets] + [""]
    if missing_targets:
        lines += ["## Missing candidate capture targets", "", "A base target was not captured by the candidate, so this comparison is incomplete.", ""] + ["- `%s`" % p for p in missing_targets] + [""]
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
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    result = {
        "schemaVersion": 1,
        "gate": args.gate,
        "baseRef": args.base_ref,
        "candidateRef": args.candidate_ref,
        "surfaces": {},
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
        }
        stable_candidate_count += len(stable_candidate)
        unstable_count += len(unstable)
        missing_candidate_count += len(missing_candidate)
        new_candidate_count += len(new_candidate)

    if missing_candidate_count:
        result["status"] = "incomplete-capture"
        result["verdict"] = (
            "INFRASTRUCTURE FAILURE: candidate omitted %d frame(s) present in the base capture."
            % missing_candidate_count
        )
        exit_code = 1
    elif stable_candidate_count:
        result["status"] = "candidate-diff"
        result["verdict"] = (
            "REGRESSION SIGNAL: candidate differs from base on %d frame(s) that were stable in the repeat control."
            % stable_candidate_count
        )
        exit_code = 1
    elif unstable_count:
        result["status"] = "control-unstable"
        result["verdict"] = (
            "NO CANDIDATE-ONLY DIFF ON STABLE FRAMES; %d repeat-control frame(s) are inconclusive and excluded."
            % unstable_count
        )
        exit_code = 0
    elif new_candidate_count:
        result["status"] = "coverage-expanded"
        result["verdict"] = (
            "COVERAGE EXPANDED: %d new owner-signed candidate target(s) have no base image for relative comparison; shared targets are exact."
            % new_candidate_count
        )
        exit_code = 0
    else:
        result["status"] = "exact"
        result["verdict"] = "EXACT: repeat control is stable and candidate is decoded-pixel identical to base."
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
    print(report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
