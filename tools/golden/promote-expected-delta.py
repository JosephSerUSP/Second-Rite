#!/usr/bin/env python3
"""Persist a reviewed Red -> Orange visual-gate promotion from a report JSON."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import expected_delta


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True,
                        help="report.json emitted by compare-relative.py")
    parser.add_argument("--id", required=True, help="durable short id for this approval")
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--rationale", required=True)
    parser.add_argument("--reference", action="append", default=[],
                        help="PR/issue/file explaining the expected change; repeatable")
    parser.add_argument("--output-dir", type=Path,
                        default=expected_delta.DEFAULT_APPROVAL_DIR)
    parser.add_argument("--replace", action="store_true",
                        help="replace an existing record with the same id")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    result = json.loads(args.report.read_text(encoding="utf-8"))
    approval = expected_delta.build_approval(
        result, args.id, args.reviewer, args.rationale, args.reference
    )
    approval["recordedAt"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / expected_delta.safe_filename(args.id)
    if output.exists() and not args.replace:
        raise SystemExit("approval already exists: %s (use --replace to revise it)" % output)
    output.write_text(json.dumps(approval, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("EXPECTED VISUAL DELTA recorded: %s" % output)
    print("evidence fingerprint: %s" % approval["evidenceFingerprint"])
    print("Commit this record, then rerun the same visual comparison. Matching evidence becomes Orange;")
    print("changed or additional evidence remains Red. Infrastructure/incomplete captures cannot be promoted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
